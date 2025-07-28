#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с двойным JSON-кодированием stats_images
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import init_db, get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_stats_images():
    """Исправляем проблему с двойным JSON-кодированием"""
    await init_db()
    
    async with get_db_connection() as db:
        # Получаем всех блогеров
        cursor = await db.execute("SELECT id, name, stats_images FROM bloggers")
        bloggers = await cursor.fetchall()
        
        fixed_count = 0
        
        for blogger_id, name, stats_images_raw in bloggers:
            if not stats_images_raw or stats_images_raw == '[]':
                continue
                
            try:
                # Первая попытка распарсить
                stats_images = json.loads(stats_images_raw)
                
                # Проверяем, не является ли результат строкой (двойное кодирование)
                if isinstance(stats_images, str):
                    logger.info(f"Блогер {blogger_id} ({name}): обнаружено двойное кодирование")
                    # Парсим еще раз
                    stats_images = json.loads(stats_images)
                    
                    # Сохраняем исправленные данные
                    await db.execute(
                        "UPDATE bloggers SET stats_images = ? WHERE id = ?",
                        (json.dumps(stats_images), blogger_id)
                    )
                    fixed_count += 1
                    logger.info(f"✅ Исправлено для блогера {blogger_id}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга для блогера {blogger_id}: {e}")
                logger.error(f"Данные: {stats_images_raw[:100]}...")
                
        await db.commit()
        
        logger.info(f"\n=== ИТОГО ===")
        logger.info(f"Проверено блогеров: {len(bloggers)}")
        logger.info(f"Исправлено: {fixed_count}")

if __name__ == "__main__":
    asyncio.run(fix_stats_images())