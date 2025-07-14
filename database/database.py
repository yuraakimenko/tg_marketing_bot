import aiosqlite
import os
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .models import User, Blogger, Review, Subscription, Contact, SearchFilter
from .models import UserRole, SubscriptionStatus, Platform, BlogCategory

DATABASE_PATH = "bot_database.db"
logger = logging.getLogger(__name__)


async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Создание таблицы пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT NOT NULL DEFAULT 'seller',
                subscription_status TEXT NOT NULL DEFAULT 'inactive',
                subscription_end_date TIMESTAMP,
                rating REAL DEFAULT 0.0,
                reviews_count INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT FALSE,
                penalty_amount INTEGER DEFAULT 0,
                is_blocked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создание таблицы блогеров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bloggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                platform TEXT NOT NULL,
                
                -- Демография аудитории
                audience_13_17_percent INTEGER,
                audience_18_24_percent INTEGER,
                audience_25_35_percent INTEGER,
                audience_35_plus_percent INTEGER,
                
                -- Пол аудитории
                female_percent INTEGER,
                male_percent INTEGER,
                
                -- Категории (JSON массив)
                categories TEXT,
                
                -- Цены
                price_stories INTEGER,
                price_post INTEGER,
                price_video INTEGER,
                
                -- Дополнительная информация
                has_reviews BOOLEAN DEFAULT FALSE,
                is_registered_rkn BOOLEAN DEFAULT FALSE,
                official_payment_possible BOOLEAN DEFAULT FALSE,
                
                -- Статистика
                subscribers_count INTEGER,
                avg_views INTEGER,
                avg_likes INTEGER,
                engagement_rate REAL,
                
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users (id)
            )
        """)
        
        # Создание таблицы фильтров поиска
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER NOT NULL,
                platforms TEXT,  -- JSON массив платформ
                target_age_min INTEGER,
                target_age_max INTEGER,
                target_gender TEXT,
                categories TEXT,  -- JSON массив категорий
                budget_min INTEGER,
                budget_max INTEGER,
                has_reviews BOOLEAN,
                is_registered_rkn BOOLEAN,
                official_payment_required BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (buyer_id) REFERENCES users (id)
            )
        """)
        
        # Создание таблицы отзывов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER NOT NULL,
                reviewed_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                blogger_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reviewer_id) REFERENCES users (id),
                FOREIGN KEY (reviewed_id) REFERENCES users (id),
                FOREIGN KEY (blogger_id) REFERENCES bloggers (id)
            )
        """)
        
        # Создание таблицы подписок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                payment_id TEXT,
                auto_renewal BOOLEAN DEFAULT 1,
                cancelled_at TIMESTAMP,
                promo_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Создание таблицы контактов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                blogger_id INTEGER NOT NULL,
                deal_completed BOOLEAN,
                rating_given INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (buyer_id) REFERENCES users (id),
                FOREIGN KEY (seller_id) REFERENCES users (id),
                FOREIGN KEY (blogger_id) REFERENCES bloggers (id)
            )
        """)
        
        # Создание таблицы жалоб
        await db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blogger_id INTEGER NOT NULL,
                blogger_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                penalty_applied BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blogger_id) REFERENCES bloggers (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Создание индексов для оптимизации поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bloggers_seller_id ON bloggers (seller_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bloggers_platform ON bloggers (platform)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_id ON reviews (reviewed_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_complaints_blogger_id ON complaints (blogger_id)")
        
        # Миграция: добавляем новые поля в существующие таблицы
        try:
            # Проверяем и добавляем новые поля в users
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'is_vip' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN is_vip BOOLEAN DEFAULT FALSE")
                logger.info("Added is_vip column to users table")
            
            if 'penalty_amount' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN penalty_amount INTEGER DEFAULT 0")
                logger.info("Added penalty_amount column to users table")
            
            if 'is_blocked' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
                logger.info("Added is_blocked column to users table")
            
            # Проверяем и добавляем новые поля в bloggers
            cursor = await db.execute("PRAGMA table_info(bloggers)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'audience_13_17_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN audience_13_17_percent INTEGER")
                logger.info("Added audience_13_17_percent column to bloggers table")
            
            if 'audience_18_24_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN audience_18_24_percent INTEGER")
                logger.info("Added audience_18_24_percent column to bloggers table")
            
            if 'audience_25_35_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN audience_25_35_percent INTEGER")
                logger.info("Added audience_25_35_percent column to bloggers table")
            
            if 'audience_35_plus_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN audience_35_plus_percent INTEGER")
                logger.info("Added audience_35_plus_percent column to bloggers table")
            
            if 'female_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN female_percent INTEGER")
                logger.info("Added female_percent column to bloggers table")
            
            if 'male_percent' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN male_percent INTEGER")
                logger.info("Added male_percent column to bloggers table")
            
            if 'categories' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN categories TEXT")
                logger.info("Added categories column to bloggers table")
            
            if 'price_stories' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN price_stories INTEGER")
                logger.info("Added price_stories column to bloggers table")
            
            if 'price_post' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN price_post INTEGER")
                logger.info("Added price_post column to bloggers table")
            
            if 'price_video' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN price_video INTEGER")
                logger.info("Added price_video column to bloggers table")
            
            if 'is_registered_rkn' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN is_registered_rkn BOOLEAN DEFAULT FALSE")
                logger.info("Added is_registered_rkn column to bloggers table")
            
            if 'official_payment_possible' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN official_payment_possible BOOLEAN DEFAULT FALSE")
                logger.info("Added official_payment_possible column to bloggers table")
            
            if 'avg_views' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN avg_views INTEGER")
                logger.info("Added avg_views column to bloggers table")
            
            if 'avg_likes' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN avg_likes INTEGER")
                logger.info("Added avg_likes column to bloggers table")
            
            if 'engagement_rate' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN engagement_rate REAL")
                logger.info("Added engagement_rate column to bloggers table")
            
            # Проверяем и добавляем новые поля в subscriptions
            cursor = await db.execute("PRAGMA table_info(subscriptions)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'promo_code' not in columns:
                await db.execute("ALTER TABLE subscriptions ADD COLUMN promo_code TEXT")
                logger.info("Added promo_code column to subscriptions table")
                
        except Exception as e:
            logger.error(f"Error during migration: {e}")
        
        await db.commit()


# Функции для работы с пользователями
async def create_user(telegram_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, role: UserRole = UserRole.SELLER) -> User:
    """Создание нового пользователя"""
    logger.info(f"Создание пользователя: telegram_id={telegram_id}, username={username}, first_name={first_name}, last_name={last_name}, role={role}")
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            logger.info(f"Подключение к базе данных: {DATABASE_PATH}")
            
            cursor = await db.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, role, is_vip, penalty_amount, is_blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name, role.value, False, 0, False))
            
            user_id = cursor.lastrowid
            logger.info(f"Пользователь создан с ID: {user_id}")
            
            await db.commit()
            logger.info("Транзакция зафиксирована")
            
            # Получаем созданного пользователя
            created_user = await get_user(telegram_id)
            logger.info(f"Созданный пользователь: {created_user}")
            
            return created_user
            
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise


async def get_user(telegram_id: int) -> Optional[User]:
    """Получение пользователя по telegram_id"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=UserRole(row['role']),
                subscription_status=SubscriptionStatus(row['subscription_status']),
                subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                rating=row['rating'],
                reviews_count=row['reviews_count'],
                is_vip=bool(row['is_vip']) if 'is_vip' in row.keys() else False,
                penalty_amount=row['penalty_amount'] if 'penalty_amount' in row.keys() else 0,
                is_blocked=bool(row['is_blocked']) if 'is_blocked' in row.keys() else False,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        return None


async def update_user_role(telegram_id: int, role: UserRole) -> bool:
    """Обновление роли пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (role.value, telegram_id))
        
        await db.commit()
        return cursor.rowcount > 0


async def update_subscription_status(user_id: int, status: SubscriptionStatus, 
                                   end_date: datetime = None) -> bool:
    """Обновление статуса подписки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            UPDATE users SET subscription_status = ?, subscription_end_date = ?, 
                           updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status.value, end_date.isoformat() if end_date else None, user_id))
        
        await db.commit()
        return cursor.rowcount > 0


# Функции для работы с блогерами
async def create_blogger(seller_id: int, name: str, url: str, platform: Platform,
                        categories: List[BlogCategory], **kwargs) -> Blogger:
    """Создание нового блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Преобразуем категории в JSON
        categories_json = json.dumps([cat.value for cat in categories]) if categories else None
        
        cursor = await db.execute("""
            INSERT INTO bloggers (
                seller_id, name, url, platform, categories,
                audience_13_17_percent, audience_18_24_percent, audience_25_35_percent, audience_35_plus_percent,
                female_percent, male_percent,
                price_stories, price_post, price_video,
                has_reviews, is_registered_rkn, official_payment_possible,
                subscribers_count, avg_views, avg_likes, engagement_rate,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            seller_id, name, url, platform.value, categories_json,
            kwargs.get('audience_13_17_percent'),
            kwargs.get('audience_18_24_percent'),
            kwargs.get('audience_25_35_percent'),
            kwargs.get('audience_35_plus_percent'),
            kwargs.get('female_percent'),
            kwargs.get('male_percent'),
            kwargs.get('price_stories'),
            kwargs.get('price_post'),
            kwargs.get('price_video'),
            kwargs.get('has_reviews', False),
            kwargs.get('is_registered_rkn', False),
            kwargs.get('official_payment_possible', False),
            kwargs.get('subscribers_count'),
            kwargs.get('avg_views'),
            kwargs.get('avg_likes'),
            kwargs.get('engagement_rate'),
            kwargs.get('description')
        ))
        
        blogger_id = cursor.lastrowid
        await db.commit()
        
        return await get_blogger(blogger_id)


async def get_blogger(blogger_id: int) -> Optional[Blogger]:
    """Получение блогера по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bloggers WHERE id = ?", (blogger_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            # Парсим категории из JSON
            categories = []
            if row['categories']:
                try:
                    category_values = json.loads(row['categories'])
                    categories = [BlogCategory(cat) for cat in category_values]
                except (json.JSONDecodeError, ValueError):
                    pass
            
            return Blogger(
                id=row['id'],
                seller_id=row['seller_id'],
                name=row['name'],
                url=row['url'],
                platform=Platform(row['platform']),
                audience_13_17_percent=row['audience_13_17_percent'],
                audience_18_24_percent=row['audience_18_24_percent'],
                audience_25_35_percent=row['audience_25_35_percent'],
                audience_35_plus_percent=row['audience_35_plus_percent'],
                female_percent=row['female_percent'],
                male_percent=row['male_percent'],
                categories=categories,
                price_stories=row['price_stories'],
                price_post=row['price_post'],
                price_video=row['price_video'],
                has_reviews=bool(row['has_reviews']),
                is_registered_rkn=bool(row['is_registered_rkn']),
                official_payment_possible=bool(row['official_payment_possible']),
                subscribers_count=row['subscribers_count'],
                avg_views=row['avg_views'],
                avg_likes=row['avg_likes'],
                engagement_rate=row['engagement_rate'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        return None


async def get_user_bloggers(seller_id: int) -> List[Blogger]:
    """Получение всех блогеров пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bloggers WHERE seller_id = ? ORDER BY created_at DESC", 
            (seller_id,)
        )
        rows = await cursor.fetchall()
        
        bloggers = []
        for row in rows:
            # Парсим категории из JSON
            categories = []
            if row['categories']:
                try:
                    category_values = json.loads(row['categories'])
                    categories = [BlogCategory(cat) for cat in category_values]
                except (json.JSONDecodeError, ValueError):
                    pass
            
            bloggers.append(Blogger(
                id=row['id'],
                seller_id=row['seller_id'],
                name=row['name'],
                url=row['url'],
                platform=Platform(row['platform']),
                audience_13_17_percent=row['audience_13_17_percent'],
                audience_18_24_percent=row['audience_18_24_percent'],
                audience_25_35_percent=row['audience_25_35_percent'],
                audience_35_plus_percent=row['audience_35_plus_percent'],
                female_percent=row['female_percent'],
                male_percent=row['male_percent'],
                categories=categories,
                price_stories=row['price_stories'],
                price_post=row['price_post'],
                price_video=row['price_video'],
                has_reviews=bool(row['has_reviews']),
                is_registered_rkn=bool(row['is_registered_rkn']),
                official_payment_possible=bool(row['official_payment_possible']),
                subscribers_count=row['subscribers_count'],
                avg_views=row['avg_views'],
                avg_likes=row['avg_likes'],
                engagement_rate=row['engagement_rate'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            ))
        
        return bloggers


async def search_bloggers(category: str = None, target_audience: str = None,
                         has_reviews: bool = None, budget_min: int = None,
                         budget_max: int = None, limit: int = 5, offset: int = 0) -> List[Tuple[Blogger, User]]:
    """Поиск блогеров по критериям"""
    query = """
        SELECT b.*, u.telegram_id, u.username, u.first_name, u.last_name, u.rating
        FROM bloggers b
        JOIN users u ON b.seller_id = u.id
        WHERE u.subscription_status = 'active'
    """
    params = []
    
    if category:
        query += " AND b.category LIKE ?"
        params.append(f"%{category}%")
    
    if target_audience:
        query += " AND b.target_audience LIKE ?"
        params.append(f"%{target_audience}%")
    
    if has_reviews is not None:
        query += " AND b.has_reviews = ?"
        params.append(has_reviews)
    
    if budget_min is not None:
        query += " AND (b.price_min IS NULL OR b.price_min >= ?)"
        params.append(budget_min)
    
    if budget_max is not None:
        query += " AND (b.price_max IS NULL OR b.price_max <= ?)"
        params.append(budget_max)
    
    query += " ORDER BY u.rating DESC, b.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        results = []
        for row in rows:
            blogger = Blogger(
                id=row['id'],
                seller_id=row['seller_id'],
                name=row['name'],
                url=row['url'],
                platform=row['platform'],
                category=row['category'],
                target_audience=row['target_audience'],
                has_reviews=bool(row['has_reviews']),
                review_categories=row['review_categories'],
                subscribers_count=row['subscribers_count'],
                price_min=row['price_min'],
                price_max=row['price_max'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            
            seller = User(
                id=row['seller_id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=UserRole.SELLER,
                subscription_status=SubscriptionStatus.ACTIVE,
                rating=row['rating'],
                reviews_count=0
            )
            
            results.append((blogger, seller))
        
        return results


async def update_blogger(blogger_id: int, seller_id: int, **kwargs) -> bool:
    """Обновление данных блогера"""
    # Список полей, которые можно обновлять
    allowed_fields = [
        'name', 'url', 'platform', 'category', 'target_audience',
        'has_reviews', 'price_min', 'price_max', 'description'
    ]
    
    # Фильтруем только разрешенные поля
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    # Строим SQL запрос
    set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
    query = f"UPDATE bloggers SET {set_clause}, updated_at = ? WHERE id = ? AND seller_id = ?"
    
    params = list(updates.values()) + [datetime.now().isoformat(), blogger_id, seller_id]
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.rowcount > 0


async def delete_blogger(blogger_id: int, seller_id: int) -> bool:
    """Удаление блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bloggers WHERE id = ? AND seller_id = ?",
            (blogger_id, seller_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# Функции управления подпиской
async def get_user_subscription(user_id: int) -> Optional[Subscription]:
    """Получение активной подписки пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status IN ('active', 'auto_renewal_off')
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        row = await cursor.fetchone()
        
        if row:
            return Subscription(
                id=row['id'],
                user_id=row['user_id'],
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']),
                amount=row['amount'],
                status=SubscriptionStatus(row['status']),
                payment_id=row['payment_id'] if 'payment_id' in row.keys() else None,
                auto_renewal=bool(row['auto_renewal']) if 'auto_renewal' in row.keys() else True,
                cancelled_at=datetime.fromisoformat(row['cancelled_at']) if 'cancelled_at' in row.keys() and row['cancelled_at'] else None,
                created_at=datetime.fromisoformat(row['created_at'])
            )
        return None


async def toggle_auto_renewal(user_id: int, enable: bool) -> bool:
    """Включение/отключение автопродления подписки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Сначала пробуем обновить существующую подписку
        cursor = await db.execute("""
            UPDATE subscriptions 
            SET auto_renewal = ?
            WHERE user_id = ? AND status IN ('active', 'auto_renewal_off')
        """, (enable, user_id))
        
        updated_existing = cursor.rowcount > 0
        
        # Если не обновили существующую подписку, создаем новую запись для старой подписки
        if not updated_existing:
            # Получаем данные пользователя
            user_cursor = await db.execute("""
                SELECT subscription_end_date, created_at, subscription_status 
                FROM users WHERE id = ?
            """, (user_id,))
            user_row = await user_cursor.fetchone()
            
            if user_row and user_row[0]:  # Если есть дата окончания подписки
                # Создаем запись в subscriptions
                await db.execute("""
                    INSERT INTO subscriptions 
                    (user_id, start_date, end_date, amount, status, auto_renewal, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    user_row[1],  # created_at как start_date
                    user_row[0],  # subscription_end_date
                    50000,        # стандартная цена 500₽
                    user_row[2],  # subscription_status
                    enable,
                    user_row[1]   # created_at
                ))
        
        # Обновляем статус пользователя
        new_status = SubscriptionStatus.ACTIVE if enable else SubscriptionStatus.AUTO_RENEWAL_OFF
        await db.execute("""
            UPDATE users 
            SET subscription_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status.value, user_id))
        
        await db.commit()
        return True


async def cancel_subscription(user_id: int, cancel_immediately: bool = False) -> bool:
    """Отмена подписки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = datetime.now()
        
        # Сначала пробуем обновить существующую подписку
        if cancel_immediately:
            # Немедленная отмена - обновляем дату окончания на текущую
            cursor = await db.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = ?, end_date = ?
                WHERE user_id = ? AND status IN ('active', 'auto_renewal_off')
            """, (now.isoformat(), now.isoformat(), user_id))
            
            # Обновляем статус пользователя
            await db.execute("""
                UPDATE users 
                SET subscription_status = 'inactive', subscription_end_date = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (now.isoformat(), user_id))
        else:
            # Отмена до конца периода - только помечаем как отмененную
            cursor = await db.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = ?, auto_renewal = 0
                WHERE user_id = ? AND status IN ('active', 'auto_renewal_off')
            """, (now.isoformat(), user_id))
            
            updated_existing = cursor.rowcount > 0
            
            # Если не обновили существующую подписку, создаем новую запись
            if not updated_existing:
                # Получаем данные пользователя
                user_cursor = await db.execute("""
                    SELECT subscription_end_date, created_at, subscription_status 
                    FROM users WHERE id = ?
                """, (user_id,))
                user_row = await user_cursor.fetchone()
                
                if user_row and user_row[0]:  # Если есть дата окончания подписки
                    # Создаем запись в subscriptions как отмененную
                    await db.execute("""
                        INSERT INTO subscriptions 
                        (user_id, start_date, end_date, amount, status, auto_renewal, cancelled_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        user_row[1],  # created_at как start_date
                        user_row[0],  # subscription_end_date
                        50000,        # стандартная цена 500₽
                        'cancelled',
                        False,
                        now.isoformat(),
                        user_row[1]   # created_at
                    ))
            
            # Статус пользователя остается активным до окончания периода
            await db.execute("""
                UPDATE users 
                SET subscription_status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
        
        await db.commit()
        return True


async def get_user_payment_history(user_id: int, limit: int = 10) -> List[Subscription]:
    """Получение истории платежей пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        rows = await cursor.fetchall()
        
        history = []
        for row in rows:
            history.append(Subscription(
                id=row['id'],
                user_id=row['user_id'],
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']),
                amount=row['amount'],
                status=SubscriptionStatus(row['status']),
                payment_id=row['payment_id'] if 'payment_id' in row.keys() else None,
                auto_renewal=bool(row['auto_renewal']) if 'auto_renewal' in row.keys() else True,
                cancelled_at=datetime.fromisoformat(row['cancelled_at']) if 'cancelled_at' in row.keys() and row['cancelled_at'] else None,
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return history


# Функции для работы с жалобами и штрафами
async def create_complaint(blogger_id: int, blogger_name: str, user_id: int, 
                          username: str, reason: str) -> bool:
    """Создать жалобу на блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO complaints (blogger_id, blogger_name, user_id, username, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (blogger_id, blogger_name, user_id, username, reason))
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating complaint: {e}")
            return False


async def apply_penalty_to_seller(seller_id: int, amount: int = 100) -> bool:
    """Применить штраф к продавцу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # Увеличиваем сумму штрафов
            await db.execute("""
                UPDATE users 
                SET penalty_amount = penalty_amount + ?, 
                    is_blocked = CASE 
                        WHEN penalty_amount + ? > 0 THEN 1 
                        ELSE is_blocked 
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (amount, amount, seller_id))
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying penalty: {e}")
            return False


async def pay_penalty(user_id: int, amount: int) -> bool:
    """Оплатить штраф"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                UPDATE users 
                SET penalty_amount = CASE 
                        WHEN penalty_amount - ? <= 0 THEN 0 
                        ELSE penalty_amount - ? 
                    END,
                    is_blocked = CASE 
                        WHEN penalty_amount - ? <= 0 THEN 0 
                        ELSE is_blocked 
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (amount, amount, amount, user_id))
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error paying penalty: {e}")
            return False


async def set_vip_status(user_id: int, is_vip: bool) -> bool:
    """Установить VIP статус пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                UPDATE users 
                SET is_vip = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (is_vip, user_id))
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting VIP status: {e}")
            return False


async def get_top_sellers(limit: int = 10) -> List[User]:
    """Получить топ продавцов по рейтингу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM users 
            WHERE role = 'seller' AND is_blocked = 0
            ORDER BY is_vip DESC, rating DESC, reviews_count DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        sellers = []
        for row in rows:
            sellers.append(User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=UserRole(row['role']),
                subscription_status=SubscriptionStatus(row['subscription_status']),
                subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                rating=row['rating'],
                reviews_count=row['reviews_count'],
                is_vip=bool(row['is_vip']) if 'is_vip' in row.keys() else False,
                penalty_amount=row['penalty_amount'] if 'penalty_amount' in row.keys() else 0,
                is_blocked=bool(row['is_blocked']) if 'is_blocked' in row.keys() else False,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            ))
        
        return sellers


async def update_user_rating(user_id: int, new_rating: float) -> bool:
    """Обновить рейтинг пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                UPDATE users 
                SET rating = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_rating, user_id))
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user rating: {e}")
            return False 