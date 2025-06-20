#!/usr/bin/env python3
"""
Диагностический скрипт для проверки бота
"""
import asyncio
import logging
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bot():
    """Тест базовой работы бота"""
    
    # Проверяем токен
    bot_token = os.getenv('BOT_TOKEN')
    logger.info(f"BOT_TOKEN найден: {'Да' if bot_token else 'Нет'}")
    
    if bot_token:
        logger.info(f"Длина токена: {len(bot_token)}")
        logger.info(f"Начинается с цифр: {'Да' if bot_token[0].isdigit() else 'Нет'}")
    
    if not bot_token:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        
        logger.info("✅ Aiogram импортирован успешно")
        
        # Создаем бота
        bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        logger.info("✅ Бот создан успешно")
        
        # Проверяем подключение
        me = await bot.get_me()
        logger.info(f"✅ Бот подключен: @{me.username} ({me.first_name})")
        
        await bot.session.close()
        logger.info("✅ Тест завершен успешно!")
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")


if __name__ == '__main__':
    asyncio.run(test_bot()) 