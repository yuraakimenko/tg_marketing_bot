import asyncio
import aiosqlite
import logging

DATABASE_PATH = "bot_database.db"
logger = logging.getLogger(__name__)

async def create_logs_table():
    """Создание таблицы для логирования ошибок бота"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                telegram_id INTEGER,
                message_text TEXT,
                bot_response TEXT,
                error_message TEXT,
                status_code INTEGER,
                handler_name TEXT,
                state_name TEXT,
                additional_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы для быстрого поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bot_logs_event_time ON bot_logs (event_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bot_logs_user_id ON bot_logs (user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bot_logs_telegram_id ON bot_logs (telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bot_logs_error ON bot_logs (error_message)")
        
        await db.commit()
        logger.info("Таблица bot_logs создана успешно")

async def log_bot_event(telegram_id: int, message_text: str = None, bot_response: str = None, 
                       error_message: str = None, status_code: int = 200, 
                       handler_name: str = None, state_name: str = None, 
                       additional_data: str = None):
    """Функция для логирования событий бота в базу данных"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO bot_logs (
                telegram_id, message_text, bot_response, error_message, 
                status_code, handler_name, state_name, additional_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, message_text, bot_response, error_message, 
              status_code, handler_name, state_name, additional_data))
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(create_logs_table()) 