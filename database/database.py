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
                subscription_status TEXT NOT NULL DEFAULT 'inactive',
                subscription_start_date TIMESTAMP,
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
        
        # Создание таблицы ролей пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, role)
            )
        """)
        
        # Создание таблицы блогеров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bloggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                platforms TEXT NOT NULL,  -- JSON массив платформ
                
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
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles (user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles (role)")
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
            
            # Миграция ролей: если есть старое поле role, переносим данные в новую таблицу
            if 'role' in columns:
                logger.info("Migrating roles from old 'role' column to new 'user_roles' table")
                cursor = await db.execute("SELECT id, role FROM users WHERE role IS NOT NULL")
                users_with_roles = await cursor.fetchall()
                
                for user_id, role in users_with_roles:
                    try:
                        await db.execute(
                            "INSERT INTO user_roles (user_id, role) VALUES (?, ?)",
                            (user_id, role)
                        )
                        logger.info(f"Migrated role '{role}' for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to migrate role '{role}' for user {user_id}: {e}")
                
                # Удаляем старое поле role
                await db.execute("CREATE TABLE users_new AS SELECT id, telegram_id, username, first_name, last_name, subscription_status, subscription_start_date, subscription_end_date, rating, reviews_count, is_vip, penalty_amount, is_blocked, created_at, updated_at FROM users")
                await db.execute("DROP TABLE users")
                await db.execute("ALTER TABLE users_new RENAME TO users")
                await db.execute("CREATE UNIQUE INDEX idx_users_telegram_id ON users (telegram_id)")
                logger.info("Removed old 'role' column from users table")
            
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
            
            if 'has_reviews' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN has_reviews BOOLEAN DEFAULT FALSE")
                logger.info("Added has_reviews column to bloggers table")
            
            if 'is_registered_rkn' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN is_registered_rkn BOOLEAN DEFAULT FALSE")
                logger.info("Added is_registered_rkn column to bloggers table")
            
            if 'official_payment_possible' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN official_payment_possible BOOLEAN DEFAULT FALSE")
                logger.info("Added official_payment_possible column to bloggers table")
            
            if 'subscribers_count' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN subscribers_count INTEGER")
                logger.info("Added subscribers_count column to bloggers table")
            
            if 'avg_views' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN avg_views INTEGER")
                logger.info("Added avg_views column to bloggers table")
            
            if 'avg_likes' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN avg_likes INTEGER")
                logger.info("Added avg_likes column to bloggers table")
            
            if 'engagement_rate' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN engagement_rate REAL")
                logger.info("Added engagement_rate column to bloggers table")
            
            if 'description' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN description TEXT")
                logger.info("Added description column to bloggers table")
            
            if 'updated_at' not in columns:
                await db.execute("ALTER TABLE bloggers ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                logger.info("Added updated_at column to bloggers table")
                
        except Exception as e:
            logger.error(f"Error during migration: {e}")
        
        await db.commit()
        logger.info("Database initialization completed")


# Функции для работы с пользователями
async def create_user(telegram_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, roles: List[UserRole] = None) -> User:
    """Создание нового пользователя с поддержкой множественных ролей"""
    if roles is None:
        roles = [UserRole.SELLER]  # По умолчанию продажник
    
    logger.info(f"Создание пользователя: telegram_id={telegram_id}, username={username}, first_name={first_name}, last_name={last_name}, roles={[r.value for r in roles]}")
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            logger.info(f"Подключение к базе данных: {DATABASE_PATH}")
            
            # Создаем пользователя
            cursor = await db.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, is_vip, penalty_amount, is_blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name, False, 0, False))
            
            user_id = cursor.lastrowid
            logger.info(f"Пользователь создан с ID: {user_id}")
            
            # Добавляем роли
            for role in roles:
                await db.execute("""
                    INSERT INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user_id, role.value))
                logger.info(f"Добавлена роль {role.value} для пользователя {user_id}")
            
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
    """Получение пользователя по telegram_id с ролями"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем основную информацию о пользователе
            cursor = await db.execute("""
                SELECT * FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Получаем роли пользователя
            cursor = await db.execute("""
                SELECT role FROM user_roles WHERE user_id = ?
            """, (row['id'],))
            
            role_rows = await cursor.fetchall()
            roles = {UserRole(role_row['role']) for role_row in role_rows}
            
            # Создаем объект пользователя
            user = User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                roles=roles,
                subscription_status=SubscriptionStatus(row['subscription_status']) if row['subscription_status'] else SubscriptionStatus.INACTIVE,
                subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                subscription_start_date=datetime.fromisoformat(row['subscription_start_date']) if row['subscription_start_date'] else None,
                rating=row['rating'],
                reviews_count=row['reviews_count'],
                is_vip=bool(row['is_vip']),
                penalty_amount=row['penalty_amount'],
                is_blocked=bool(row['is_blocked']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
            )
            
            return user
            
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None


async def update_user_roles(telegram_id: int, roles: List[UserRole]) -> bool:
    """Обновление ролей пользователя (заменяет все существующие роли)"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Получаем ID пользователя
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_row = await cursor.fetchone()
            
            if not user_row:
                logger.error(f"Пользователь с telegram_id {telegram_id} не найден")
                return False
            
            user_id = user_row[0]
            
            # Удаляем все существующие роли
            await db.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
            
            # Добавляем новые роли
            for role in roles:
                await db.execute("""
                    INSERT INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user_id, role.value))
            
            await db.commit()
            logger.info(f"Роли пользователя {telegram_id} обновлены: {[r.value for r in roles]}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении ролей пользователя: {e}")
        return False


async def add_user_role(telegram_id: int, role: UserRole) -> bool:
    """Добавление роли пользователю (не заменяет существующие)"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Получаем ID пользователя
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_row = await cursor.fetchone()
            
            if not user_row:
                logger.error(f"Пользователь с telegram_id {telegram_id} не найден")
                return False
            
            user_id = user_row[0]
            
            # Добавляем роль (UNIQUE constraint предотвратит дублирование)
            await db.execute("""
                INSERT OR IGNORE INTO user_roles (user_id, role)
                VALUES (?, ?)
            """, (user_id, role.value))
            
            await db.commit()
            logger.info(f"Роль {role.value} добавлена пользователю {telegram_id}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли пользователю: {e}")
        return False


async def remove_user_role(telegram_id: int, role: UserRole) -> bool:
    """Удаление роли у пользователя"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Получаем ID пользователя
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_row = await cursor.fetchone()
            
            if not user_row:
                logger.error(f"Пользователь с telegram_id {telegram_id} не найден")
                return False
            
            user_id = user_row[0]
            
            # Удаляем роль
            cursor = await db.execute("""
                DELETE FROM user_roles WHERE user_id = ? AND role = ?
            """, (user_id, role.value))
            
            await db.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Роль {role.value} удалена у пользователя {telegram_id}")
                return True
            else:
                logger.warning(f"Роль {role.value} не найдена у пользователя {telegram_id}")
                return False
            
    except Exception as e:
        logger.error(f"Ошибка при удалении роли у пользователя: {e}")
        return False


# Функция для обратной совместимости
async def update_user_role(telegram_id: int, role: UserRole) -> bool:
    """Обновление роли пользователя (заменяет все существующие роли на одну) - для обратной совместимости"""
    return await update_user_roles(telegram_id, [role])


async def update_subscription_status(user_id: int, status: SubscriptionStatus, 
                                   end_date: datetime = None, start_date: datetime = None) -> bool:
    """Обновление статуса подписки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            UPDATE users SET subscription_status = ?, subscription_start_date = ?, subscription_end_date = ?, 
                           updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status.value, start_date.isoformat() if start_date else None, 
              end_date.isoformat() if end_date else None, user_id))
        
        await db.commit()
        return cursor.rowcount > 0


# Функции для работы с блогерами
async def create_blogger(seller_id: int, name: str, url: str, platforms: List[Platform],
                        categories: List[BlogCategory], **kwargs) -> Blogger:
    """Создание нового блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Преобразуем платформы и категории в JSON
        platforms_json = json.dumps([platform.value for platform in platforms]) if platforms else None
        categories_json = json.dumps([cat.value for cat in categories]) if categories else None
        
        # Для совместимости со старой схемой
        primary_platform = platforms[0].value if platforms else 'instagram'
        primary_category = categories[0].value if categories else 'lifestyle'
        
        cursor = await db.execute("""
            INSERT INTO bloggers (
                seller_id, name, url, platform, category, target_audience,
                platforms, categories,
                audience_13_17_percent, audience_18_24_percent, audience_25_35_percent, audience_35_plus_percent,
                female_percent, male_percent,
                price_stories, price_post, price_video,
                has_reviews, is_registered_rkn, official_payment_possible,
                subscribers_count, avg_views, avg_likes, engagement_rate,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            seller_id, name, url, primary_platform, primary_category, 'general',
            platforms_json, categories_json,
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
            # Парсим платформы из JSON
            platforms = []
            if row['platforms']:
                try:
                    platform_values = json.loads(row['platforms'])
                    platforms = [Platform(platform) for platform in platform_values]
                except (json.JSONDecodeError, ValueError):
                    # Fallback для старых данных с одной платформой
                    try:
                        platforms = [Platform(row['platform'])] if row.get('platform') else []
                    except (ValueError, KeyError):
                        pass
            
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
                platforms=platforms,
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
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
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
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
            ))
        
        return bloggers


async def search_bloggers(platforms: List[str] = None, categories: List[str] = None,
                         target_age_min: int = None, target_age_max: int = None,
                         target_gender: str = None, budget_min: int = None,
                         budget_max: int = None, has_reviews: bool = None,
                         limit: int = 10, offset: int = 0) -> List[Tuple[Blogger, User]]:
    """Поиск блогеров по критериям"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Базовый запрос
            query = """
                SELECT b.*, u.* FROM bloggers b
                JOIN users u ON b.seller_id = u.id
                WHERE 1=1
            """
            params = []
            
            # Фильтр по платформам
            if platforms:
                platform_conditions = []
                for platform in platforms:
                    platform_conditions.append("b.platforms LIKE ?")
                    params.append(f'%"{platform}"%')
                query += f" AND ({' OR '.join(platform_conditions)})"
            
            # Фильтр по категориям
            if categories:
                category_conditions = []
                for category in categories:
                    category_conditions.append("b.categories LIKE ?")
                    params.append(f'%"{category}"%')
                query += f" AND ({' OR '.join(category_conditions)})"
            
            # Фильтр по возрасту целевой аудитории
            if target_age_min is not None and target_age_max is not None:
                # Проверяем, что хотя бы одна возрастная категория попадает в диапазон
                age_conditions = []
                if target_age_min <= 17 and target_age_max >= 13:
                    age_conditions.append("b.audience_13_17_percent > 0")
                if target_age_min <= 24 and target_age_max >= 18:
                    age_conditions.append("b.audience_18_24_percent > 0")
                if target_age_min <= 35 and target_age_max >= 25:
                    age_conditions.append("b.audience_25_35_percent > 0")
                if target_age_max >= 35:
                    age_conditions.append("b.audience_35_plus_percent > 0")
                
                if age_conditions:
                    query += f" AND ({' OR '.join(age_conditions)})"
            
            # Фильтр по полу целевой аудитории
            if target_gender and target_gender != "any":
                if target_gender == "female":
                    query += " AND b.female_percent > b.male_percent"
                elif target_gender == "male":
                    query += " AND b.male_percent > b.female_percent"
            
            # Фильтр по бюджету
            if budget_min is not None or budget_max is not None:
                budget_conditions = []
                if budget_min is not None:
                    budget_conditions.append("(b.price_stories >= ? OR b.price_post >= ? OR b.price_video >= ?)")
                    params.extend([budget_min, budget_min, budget_min])
                if budget_max is not None:
                    budget_conditions.append("(b.price_stories <= ? OR b.price_post <= ? OR b.price_video <= ?)")
                    params.extend([budget_max, budget_max, budget_max])
                
                if budget_conditions:
                    query += f" AND ({' OR '.join(budget_conditions)})"
            
            # Фильтр по наличию отзывов
            if has_reviews is not None:
                query += " AND b.has_reviews = ?"
                params.append(has_reviews)
            
            # Сортировка по рейтингу продавца
            query += " ORDER BY u.rating DESC, b.subscribers_count DESC"
            
            # Лимит и смещение
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                # Парсим платформы из JSON
                platforms_data = []
                if row['platforms']:
                    try:
                        platforms_json = json.loads(row['platforms'])
                        platforms_data = [Platform(p) for p in platforms_json]
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid platforms JSON for blogger {row['id']}: {row['platforms']}")
                
                # Парсим категории из JSON
                categories_data = []
                if row['categories']:
                    try:
                        categories_json = json.loads(row['categories'])
                        categories_data = [BlogCategory(c) for c in categories_json]
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid categories JSON for blogger {row['id']}: {row['categories']}")
                
                # Получаем роли продавца
                seller_cursor = await db.execute("""
                    SELECT role FROM user_roles WHERE user_id = ?
                """, (row['seller_id'],))
                
                seller_role_rows = await seller_cursor.fetchall()
                seller_roles = {UserRole(role_row['role']) for role_row in seller_role_rows}
                
                # Создаем объект блогера
                blogger = Blogger(
                    id=row['id'],
                    seller_id=row['seller_id'],
                    name=row['name'],
                    url=row['url'],
                    platforms=platforms_data,
                    audience_13_17_percent=row['audience_13_17_percent'],
                    audience_18_24_percent=row['audience_18_24_percent'],
                    audience_25_35_percent=row['audience_25_35_percent'],
                    audience_35_plus_percent=row['audience_35_plus_percent'],
                    female_percent=row['female_percent'],
                    male_percent=row['male_percent'],
                    categories=categories_data,
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
                
                # Создаем объект пользователя (продавца)
                seller = User(
                    id=row['seller_id'],
                    telegram_id=row['telegram_id'],
                    username=row['username'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    roles=seller_roles,
                    subscription_status=SubscriptionStatus(row['subscription_status']) if row['subscription_status'] else SubscriptionStatus.INACTIVE,
                    subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                    subscription_start_date=datetime.fromisoformat(row['subscription_start_date']) if row['subscription_start_date'] else None,
                    rating=row['rating'],
                    reviews_count=row['reviews_count'],
                    is_vip=bool(row['is_vip']),
                    penalty_amount=row['penalty_amount'],
                    is_blocked=bool(row['is_blocked']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
                
                results.append((blogger, seller))
            
            return results
            
    except Exception as e:
        logger.error(f"Ошибка при поиске блогеров: {e}")
        return []


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
                subscription_status=SubscriptionStatus(row['subscription_status']) if row['subscription_status'] else SubscriptionStatus.INACTIVE,
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