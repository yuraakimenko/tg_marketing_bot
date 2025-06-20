import aiosqlite
import os
import json
from typing import List, Optional, Tuple
from datetime import datetime

from .models import User, Blogger, Review, Subscription, Contact, SearchFilter
from .models import UserRole, SubscriptionStatus

DATABASE_PATH = "bot_database.db"


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
                category TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                has_reviews BOOLEAN DEFAULT FALSE,
                review_categories TEXT,
                subscribers_count INTEGER,
                price_min INTEGER,
                price_max INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users (id)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (buyer_id) REFERENCES users (id),
                FOREIGN KEY (seller_id) REFERENCES users (id),
                FOREIGN KEY (blogger_id) REFERENCES bloggers (id)
            )
        """)
        
        # Создание индексов для оптимизации поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bloggers_seller_id ON bloggers (seller_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bloggers_category ON bloggers (category)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_id ON reviews (reviewed_id)")
        
        await db.commit()


# Функции для работы с пользователями
async def create_user(telegram_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, role: UserRole = UserRole.SELLER) -> User:
    """Создание нового пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, (telegram_id, username, first_name, last_name, role.value))
        
        user_id = cursor.lastrowid
        await db.commit()
        
        return await get_user(telegram_id)


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
async def create_blogger(seller_id: int, name: str, url: str, platform: str,
                        category: str, target_audience: str, **kwargs) -> Blogger:
    """Создание нового блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO bloggers (seller_id, name, url, platform, category, target_audience,
                                has_reviews, review_categories, subscribers_count, 
                                price_min, price_max, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            seller_id, name, url, platform, category, target_audience,
            kwargs.get('has_reviews', False),
            json.dumps(kwargs.get('review_categories', [])) if kwargs.get('review_categories') else None,
            kwargs.get('subscribers_count'),
            kwargs.get('price_min'),
            kwargs.get('price_max'),
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
            return Blogger(
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
            bloggers.append(Blogger(
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


async def delete_blogger(blogger_id: int, seller_id: int) -> bool:
    """Удаление блогера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bloggers WHERE id = ? AND seller_id = ?",
            (blogger_id, seller_id)
        )
        await db.commit()
        return cursor.rowcount > 0 