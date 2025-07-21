import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta

DATABASE_PATH = "bot_database.db"

async def analyze_bot_errors():
    """Анализ ошибок бота через SQL"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        print("=== АНАЛИЗ ОШИБОК БОТА ===\n")
        
        # Ваш оригинальный запрос
        cursor = await db.execute("""
            SELECT 
                id,
                event_time,
                telegram_id,
                message_text,
                bot_response,
                error_message,
                status_code,
                handler_name
            FROM bot_logs
            WHERE 
                -- Все ошибки
                (error_message IS NOT NULL AND error_message <> '')
                
                -- Неуспешные статусы
                OR (status_code IS NOT NULL AND status_code != 200)
                
                -- Пустые ответы от бота
                OR (bot_response IS NULL OR TRIM(bot_response) = '')
                
                -- Таймауты или исключения в тексте логов
                OR (LOWER(message_text) LIKE '%timeout%' OR LOWER(error_message) LIKE '%timeout%' OR LOWER(error_message) LIKE '%exception%')
                
            ORDER BY event_time DESC
            LIMIT 100
        """)
        
        errors = await cursor.fetchall()
        
        if errors:
            print(f"Найдено {len(errors)} ошибок:\n")
            for error in errors:
                print(f"ID: {error['id']}")
                print(f"Время: {error['event_time']}")
                print(f"Пользователь: {error['telegram_id']}")
                print(f"Сообщение: {error['message_text']}")
                print(f"Ответ бота: {error['bot_response']}")
                print(f"Ошибка: {error['error_message']}")
                print(f"Статус: {error['status_code']}")
                print(f"Обработчик: {error['handler_name']}")
                print("-" * 50)
        else:
            print("Ошибок не найдено или таблица bot_logs пуста")

async def analyze_user_activity():
    """Анализ активности пользователей"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        print("\n=== АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ ===\n")
        
        # Топ активных пользователей
        cursor = await db.execute("""
            SELECT 
                telegram_id,
                COUNT(*) as message_count,
                MAX(event_time) as last_activity,
                COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as error_count
            FROM bot_logs
            GROUP BY telegram_id
            ORDER BY message_count DESC
            LIMIT 10
        """)
        
        users = await cursor.fetchall()
        
        if users:
            print("Топ-10 активных пользователей:")
            for user in users:
                print(f"ID: {user['telegram_id']}, Сообщений: {user['message_count']}, Ошибок: {user['error_count']}, Последняя активность: {user['last_activity']}")
        
        # Статистика ошибок по обработчикам
        cursor = await db.execute("""
            SELECT 
                handler_name,
                COUNT(*) as error_count,
                COUNT(DISTINCT telegram_id) as affected_users
            FROM bot_logs
            WHERE error_message IS NOT NULL AND error_message <> ''
            GROUP BY handler_name
            ORDER BY error_count DESC
        """)
        
        handlers = await cursor.fetchall()
        
        if handlers:
            print("\nОшибки по обработчикам:")
            for handler in handlers:
                print(f"Обработчик: {handler['handler_name']}, Ошибок: {handler['error_count']}, Пользователей: {handler['affected_users']}")

async def search_logs(query: str):
    """Поиск в логах по тексту"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT *
            FROM bot_logs
            WHERE 
                message_text LIKE ? 
                OR bot_response LIKE ?
                OR error_message LIKE ?
                OR additional_data LIKE ?
            ORDER BY event_time DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
        
        results = await cursor.fetchall()
        
        print(f"\n=== ПОИСК: '{query}' ===")
        print(f"Найдено {len(results)} записей:\n")
        
        for result in results:
            print(f"ID: {result['id']}, Время: {result['event_time']}")
            print(f"Пользователь: {result['telegram_id']}")
            print(f"Сообщение: {result['message_text']}")
            print(f"Ответ: {result['bot_response']}")
            if result['error_message']:
                print(f"Ошибка: {result['error_message']}")
            print("-" * 30)

async def recent_activity(hours: int = 24):
    """Активность за последние N часов"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        since = datetime.now() - timedelta(hours=hours)
        
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT telegram_id) as unique_users,
                COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as total_errors,
                AVG(CASE WHEN status_code = 200 THEN 1.0 ELSE 0.0 END) * 100 as success_rate
            FROM bot_logs
            WHERE datetime(event_time) >= datetime(?)
        """, (since.isoformat(),))
        
        stats = await cursor.fetchone()
        
        print(f"\n=== СТАТИСТИКА ЗА ПОСЛЕДНИЕ {hours} ЧАСОВ ===")
        print(f"Всего сообщений: {stats['total_messages']}")
        print(f"Уникальных пользователей: {stats['unique_users']}")
        print(f"Ошибок: {stats['total_errors']}")
        print(f"Процент успешных ответов: {stats['success_rate']:.1f}%")

if __name__ == "__main__":
    print("Анализ логов Telegram бота")
    print("=" * 40)
    
    # Запускаем основной анализ
    asyncio.run(analyze_bot_errors())
    asyncio.run(analyze_user_activity())
    asyncio.run(recent_activity(24))
    
    # Можно добавить поиск
    # asyncio.run(search_logs("роль"))
    # asyncio.run(search_logs("error")) 