import asyncio
import aiosqlite
import logging
from database.database import get_user, DATABASE_PATH
from database.models import UserRole

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_user_by_telegram_id(telegram_id: int):
    """Детальная диагностика пользователя"""
    logger.info(f"=== ДИАГНОСТИКА ПОЛЬЗОВАТЕЛЯ {telegram_id} ===")
    
    try:
        # Проверяем через нашу функцию get_user
        user = await get_user(telegram_id)
        logger.info(f"get_user() результат: {user}")
        if user:
            logger.info(f"Роли: {user.roles}")
            logger.info(f"has_role(BUYER): {user.has_role(UserRole.BUYER)}")
            logger.info(f"has_role(SELLER): {user.has_role(UserRole.SELLER)}")
        
        # Прямая проверка базы данных
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Ищем пользователя в основной таблице
            cursor = await db.execute("""
                SELECT * FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            user_row = await cursor.fetchone()
            logger.info(f"Запись в users: {dict(user_row) if user_row else None}")
            
            if user_row:
                user_id = user_row['id']
                
                # Проверяем роли
                cursor = await db.execute("""
                    SELECT * FROM user_roles WHERE user_id = ?
                """, (user_id,))
                
                role_rows = await cursor.fetchall()
                logger.info(f"Записи в user_roles: {[dict(row) for row in role_rows]}")
                
                # Проверяем все записи с этим telegram_id (может быть дубли?)
                cursor = await db.execute("""
                    SELECT * FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                all_users = await cursor.fetchall()
                logger.info(f"Все пользователи с telegram_id {telegram_id}: {len(all_users)} штук")
                for i, row in enumerate(all_users):
                    logger.info(f"  Пользователь {i+1}: {dict(row)}")
                
    except Exception as e:
        logger.error(f"Ошибка при диагностике: {e}", exc_info=True)

async def debug_all_users():
    """Посмотреть всех пользователей в базе"""
    logger.info("=== ВСЕ ПОЛЬЗОВАТЕЛИ В БАЗЕ ===")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("SELECT * FROM users")
        users = await cursor.fetchall()
        
        logger.info(f"Всего пользователей: {len(users)}")
        for user in users:
            logger.info(f"User: {dict(user)}")
            
            # Роли для каждого пользователя
            cursor = await db.execute("SELECT * FROM user_roles WHERE user_id = ?", (user['id'],))
            roles = await cursor.fetchall()
            logger.info(f"  Роли: {[dict(role) for role in roles]}")

if __name__ == "__main__":
    # Замените на реальный telegram_id проблемного пользователя
    # Можно узнать из логов бота или из скриншота настроек
    telegram_id = 123456789  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ID
    
    asyncio.run(debug_user_by_telegram_id(telegram_id))
    # asyncio.run(debug_all_users()) 