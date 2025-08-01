"""
Миграция базы данных до версии 2
Добавляет поддержку статистики по платформам
"""

import aiosqlite
import logging
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

DATABASE_PATH = "bot_database.db"


async def migrate_to_v2():
    """Выполнить миграцию до версии 2"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            logger.info("Начинаем миграцию до версии 2...")
            
            # Проверяем, существует ли таблица platform_stats
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='platform_stats'
            """)
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                logger.info("Создаем таблицу platform_stats...")
                
                # Создание таблицы статистики по платформам
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS platform_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        blogger_id INTEGER NOT NULL,
                        platform TEXT NOT NULL,  -- instagram, youtube, telegram, tiktok, vk
                        
                        -- Основная статистика
                        subscribers_count INTEGER,
                        engagement_rate REAL,
                        avg_views INTEGER,
                        avg_likes INTEGER,
                        
                        -- Демография аудитории
                        audience_13_17_percent INTEGER,
                        audience_18_24_percent INTEGER,
                        audience_25_35_percent INTEGER,
                        audience_35_plus_percent INTEGER,
                        
                        -- Пол аудитории
                        female_percent INTEGER,
                        male_percent INTEGER,
                        
                        -- Цены
                        price_stories INTEGER,
                        price_reels INTEGER,
                        price_post INTEGER,
                        
                        -- Охваты
                        stories_reach_min INTEGER,
                        stories_reach_max INTEGER,
                        reels_reach_min INTEGER,
                        reels_reach_max INTEGER,
                        
                        -- Ссылки на изображения со статистикой
                        stats_images TEXT,  -- JSON массив
                        
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (blogger_id) REFERENCES bloggers (id) ON DELETE CASCADE,
                        UNIQUE(blogger_id, platform)
                    )
                """)
                
                logger.info("Таблица platform_stats создана успешно")
            else:
                logger.info("Таблица platform_stats уже существует")
            
            # Проверяем и добавляем недостающие колонки в таблицу bloggers
            cursor = await db.execute("PRAGMA table_info(bloggers)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем недостающие колонки для обратной совместимости
            missing_columns = []
            
            if 'engagement_rate' not in column_names:
                missing_columns.append("engagement_rate REAL")
            
            if 'avg_views' not in column_names:
                missing_columns.append("avg_views INTEGER")
            
            if 'avg_likes' not in column_names:
                missing_columns.append("avg_likes INTEGER")
            
            if 'audience_13_17_percent' not in column_names:
                missing_columns.append("audience_13_17_percent INTEGER")
            
            if 'audience_18_24_percent' not in column_names:
                missing_columns.append("audience_18_24_percent INTEGER")
            
            if 'audience_25_35_percent' not in column_names:
                missing_columns.append("audience_25_35_percent INTEGER")
            
            if 'audience_35_plus_percent' not in column_names:
                missing_columns.append("audience_35_plus_percent INTEGER")
            
            if 'female_percent' not in column_names:
                missing_columns.append("female_percent INTEGER")
            
            if 'male_percent' not in column_names:
                missing_columns.append("male_percent INTEGER")
            
            # Добавляем недостающие колонки
            for column_def in missing_columns:
                column_name = column_def.split()[0]
                logger.info(f"Добавляем колонку {column_name} в таблицу bloggers...")
                await db.execute(f"ALTER TABLE bloggers ADD COLUMN {column_def}")
            
            # Создаем индекс для быстрого поиска по платформе
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_stats_platform 
                ON platform_stats (platform)
            """)
            
            # Создаем индекс для быстрого поиска по блогеру
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_stats_blogger 
                ON platform_stats (blogger_id)
            """)
            
            await db.commit()
            logger.info("Миграция до версии 2 завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при миграции: {e}")
            await db.rollback()
            raise


async def migrate_existing_data():
    """Мигрировать существующие данные в новую структуру"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            logger.info("Начинаем миграцию существующих данных...")
            
            # Получаем всех блогеров с данными
            cursor = await db.execute("""
                SELECT id, platforms, subscribers_count, engagement_rate, 
                       avg_views, avg_likes, price_stories, price_reels,
                       stories_reach_min, stories_reach_max, 
                       reels_reach_min, reels_reach_max,
                       stats_images
                FROM bloggers 
                WHERE platforms IS NOT NULL AND platforms != ''
            """)
            
            bloggers = await cursor.fetchall()
            logger.info(f"Найдено {len(bloggers)} блогеров для миграции")
            
            for blogger in bloggers:
                blogger_id, platforms_json, subscribers, engagement, avg_views, avg_likes, \
                price_stories, price_reels, stories_min, stories_max, reels_min, reels_max, \
                stats_images = blogger
                
                try:
                    # Парсим платформы
                    if platforms_json:
                        platforms = json.loads(platforms_json)
                        if not isinstance(platforms, list):
                            platforms = [platforms]
                    else:
                        continue
                    
                    # Для каждой платформы создаем запись в platform_stats
                    for platform_name in platforms:
                        # Проверяем, существует ли уже запись для этой платформы
                        cursor = await db.execute("""
                            SELECT id FROM platform_stats 
                            WHERE blogger_id = ? AND platform = ?
                        """, (blogger_id, platform_name))
                        
                        existing = await cursor.fetchone()
                        if existing:
                            logger.info(f"Запись для блогера {blogger_id} и платформы {platform_name} уже существует")
                            continue
                        
                        # Создаем новую запись
                        await db.execute("""
                            INSERT INTO platform_stats (
                                blogger_id, platform,
                                subscribers_count, engagement_rate, avg_views, avg_likes,
                                price_stories, price_reels,
                                stories_reach_min, stories_reach_max,
                                reels_reach_min, reels_reach_max,
                                stats_images
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            blogger_id, platform_name,
                            subscribers, engagement, avg_views, avg_likes,
                            price_stories, price_reels,
                            stories_min, stories_max,
                            reels_min, reels_max,
                            stats_images
                        ))
                        
                        logger.info(f"Создана запись для блогера {blogger_id} и платформы {platform_name}")
                
                except Exception as e:
                    logger.error(f"Ошибка при миграции блогера {blogger_id}: {e}")
                    continue
            
            await db.commit()
            logger.info("Миграция существующих данных завершена")
            
        except Exception as e:
            logger.error(f"Ошибка при миграции данных: {e}")
            await db.rollback()
            raise


async def run_migration():
    """Запустить полную миграцию"""
    try:
        await migrate_to_v2()
        await migrate_existing_data()
        print("✅ Миграция завершена успешно")
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migration())