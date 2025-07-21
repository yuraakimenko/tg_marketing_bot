import asyncio
import aiosqlite
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = "bot_database.db"

async def fix_user_roles():
    """Исправление проблемы с ролями пользователей"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем всех пользователей без ролей в новой таблице
        cursor = await db.execute("""
            SELECT u.id, u.telegram_id, u.username, u.first_name 
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.user_id IS NULL
        """)
        
        users_without_roles = await cursor.fetchall()
        
        logger.info(f"Найдено {len(users_without_roles)} пользователей без ролей")
        
        for user_row in users_without_roles:
            user_id, telegram_id, username, first_name = user_row
            
            # По умолчанию даем роль buyer (закупщик), так как скорее всего это то что нужно
            # Можно будет изменить через бота
            default_role = "buyer"
            
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user_id, default_role))
                
                logger.info(f"Добавлена роль '{default_role}' пользователю {telegram_id} ({username or first_name})")
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении роли пользователю {telegram_id}: {e}")
        
        await db.commit()
        logger.info("Исправление ролей завершено")

async def check_specific_user(telegram_id: int):
    """Проверка конкретного пользователя"""
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем пользователя в основной таблице
        cursor = await db.execute("""
            SELECT * FROM users WHERE telegram_id = ?
        """, (telegram_id,))
        
        user_row = await cursor.fetchone()
        if user_row:
            logger.info(f"Пользователь найден: ID={user_row[0]}, telegram_id={user_row[1]}")
            
            # Проверяем роли
            cursor = await db.execute("""
                SELECT role FROM user_roles WHERE user_id = ?
            """, (user_row[0],))
            
            roles = await cursor.fetchall()
            logger.info(f"Роли пользователя: {[role[0] for role in roles]}")
            
            if not roles:
                logger.warning("У пользователя нет ролей! Добавляю роль buyer...")
                await db.execute("""
                    INSERT OR IGNORE INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user_row[0], "buyer"))
                await db.commit()
                logger.info("Роль buyer добавлена")
        else:
            logger.error(f"Пользователь с telegram_id {telegram_id} не найден")

if __name__ == "__main__":
    # Запускаем исправление для всех пользователей
    asyncio.run(fix_user_roles())
    
    # Можно также проверить конкретного пользователя
    # asyncio.run(check_specific_user(YOUR_TELEGRAM_ID)) 