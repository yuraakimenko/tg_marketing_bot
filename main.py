import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.database import init_db
from handlers import common, seller, buyer, subscription

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Диагностика токена
logger.info(f"Токен получен, длина: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
if BOT_TOKEN:
    # Проверяем на пробелы и невидимые символы
    logger.info(f"Первые 10 символов: '{BOT_TOKEN[:10]}'")
    logger.info(f"Последние 10 символов: '{BOT_TOKEN[-10:]}'")
    logger.info(f"Содержит пробелы в начале/конце: {BOT_TOKEN != BOT_TOKEN.strip()}")
    
    # Очищаем токен от возможных пробелов и невидимых символов
    BOT_TOKEN = BOT_TOKEN.strip().replace('\n', '').replace('\r', '').replace('\t', '')
    logger.info(f"После очистки, длина: {len(BOT_TOKEN)}")
    
    # Проверим формат токена
    if ':' not in BOT_TOKEN:
        logger.error("❌ Токен не содержит ':' - неверный формат!")
    else:
        parts = BOT_TOKEN.split(':')
        logger.info(f"Токен разделен на части: {len(parts[0])} символов до ':' и {len(parts[1])} после")
        if not parts[0].isdigit():
            logger.error(f"❌ Первая часть токена не является числом: '{parts[0]}'")
    
    # Проверим каждый символ на невидимые
    invisible_chars = []
    for i, char in enumerate(BOT_TOKEN):
        if not char.isprintable() and char not in [':']:
            invisible_chars.append(f"позиция {i}: код {ord(char)}")
    
    if invisible_chars:
        logger.error(f"❌ Найдены невидимые символы: {invisible_chars}")
    else:
        logger.info("✅ Невидимых символов не найдено")


async def main():
    """Главная функция запуска бота"""
    
    # Инициализация базы данных
    await init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация обработчиков
    dp.include_router(common.router)
    dp.include_router(seller.router)
    dp.include_router(buyer.router)
    dp.include_router(subscription.router)
    
    logger.info("Бот запущен")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main()) 