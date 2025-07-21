import asyncio
import aiosqlite
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_PATH = "bot_database.db"

async def comprehensive_user_diagnosis():
    """Комплексная диагностика всех пользователей"""
    
    logger.info("=== КОМПЛЕКСНАЯ ДИАГНОСТИКА ПОЛЬЗОВАТЕЛЕЙ ===")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Получаем всех пользователей
        cursor = await db.execute("SELECT * FROM users ORDER BY created_at")
        all_users = await cursor.fetchall()
        
        logger.info(f"Всего пользователей в базе: {len(all_users)}")
        
        users_without_roles = []
        users_with_roles = []
        problematic_users = []
        
        for user in all_users:
            user_id = user['id']
            telegram_id = user['telegram_id']
            username = user['username'] or user['first_name'] or f"User_{telegram_id}"
            
            # Получаем роли пользователя
            cursor = await db.execute("SELECT * FROM user_roles WHERE user_id = ?", (user_id,))
            roles = await cursor.fetchall()
            
            user_info = {
                'id': user_id,
                'telegram_id': telegram_id,
                'username': username,
                'roles': [role['role'] for role in roles],
                'created_at': user['created_at']
            }
            
            if not roles:
                users_without_roles.append(user_info)
            else:
                users_with_roles.append(user_info)
                
                # Проверяем на проблемы
                role_values = [role['role'] for role in roles]
                if not all(role in ['seller', 'buyer'] for role in role_values):
                    problematic_users.append(user_info)
        
        # Результаты диагностики
        logger.info(f"Пользователей с ролями: {len(users_with_roles)}")
        logger.info(f"Пользователей БЕЗ ролей: {len(users_without_roles)}")
        logger.info(f"Проблемных пользователей: {len(problematic_users)}")
        
        if users_without_roles:
            logger.warning("Пользователи БЕЗ ролей:")
            for user in users_without_roles:
                logger.warning(f"  - {user['username']} (ID: {user['telegram_id']}, создан: {user['created_at']})")
        
        if problematic_users:
            logger.error("Проблемные пользователи:")
            for user in problematic_users:
                logger.error(f"  - {user['username']} (роли: {user['roles']})")
        
        return users_without_roles, users_with_roles, problematic_users

async def fix_users_without_roles(users_without_roles, default_role='buyer'):
    """Исправление пользователей без ролей"""
    
    if not users_without_roles:
        logger.info("Все пользователи имеют роли - исправления не нужны")
        return
    
    logger.info(f"Исправляю {len(users_without_roles)} пользователей без ролей...")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        fixed_count = 0
        
        for user_info in users_without_roles:
            user_id = user_info['id']
            username = user_info['username']
            
            try:
                # Добавляем роль по умолчанию
                await db.execute("""
                    INSERT OR IGNORE INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user_id, default_role))
                
                logger.info(f"✅ Добавлена роль '{default_role}' пользователю {username}")
                fixed_count += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка при исправлении пользователя {username}: {e}")
        
        await db.commit()
        logger.info(f"Исправлено пользователей: {fixed_count}/{len(users_without_roles)}")

async def verify_specific_user(telegram_id: int):
    """Детальная проверка конкретного пользователя"""
    
    logger.info(f"=== ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ {telegram_id} ===")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Основная информация
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await cursor.fetchone()
        
        if not user:
            logger.error(f"❌ Пользователь с telegram_id {telegram_id} НЕ НАЙДЕН в базе")
            return False
        
        logger.info(f"✅ Пользователь найден:")
        logger.info(f"   - ID: {user['id']}")
        logger.info(f"   - Telegram ID: {user['telegram_id']}")
        logger.info(f"   - Username: {user['username']}")
        logger.info(f"   - Имя: {user['first_name']}")
        logger.info(f"   - Статус подписки: {user['subscription_status']}")
        logger.info(f"   - Создан: {user['created_at']}")
        
        # Роли
        cursor = await db.execute("SELECT * FROM user_roles WHERE user_id = ?", (user['id'],))
        roles = await cursor.fetchall()
        
        if roles:
            logger.info(f"✅ Роли пользователя:")
            for role in roles:
                logger.info(f"   - {role['role']} (добавлена: {role['created_at']})")
        else:
            logger.error(f"❌ У пользователя НЕТ РОЛЕЙ!")
            
            # Автоматическое исправление
            response = input(f"Добавить роль 'buyer' пользователю {user['username'] or user['first_name']}? (y/n): ")
            if response.lower() == 'y':
                await db.execute("""
                    INSERT INTO user_roles (user_id, role)
                    VALUES (?, ?)
                """, (user['id'], 'buyer'))
                await db.commit()
                logger.info("✅ Роль 'buyer' добавлена!")
        
        return True

async def clean_duplicate_users():
    """Очистка дублирующихся пользователей (если есть)"""
    
    logger.info("=== ПОИСК ДУБЛИКАТОВ ПОЛЬЗОВАТЕЛЕЙ ===")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Ищем дубликаты по telegram_id
        cursor = await db.execute("""
            SELECT telegram_id, COUNT(*) as count
            FROM users
            GROUP BY telegram_id
            HAVING COUNT(*) > 1
        """)
        
        duplicates = await cursor.fetchall()
        
        if not duplicates:
            logger.info("✅ Дубликатов не найдено")
            return
        
        logger.warning(f"Найдено {len(duplicates)} дубликатов:")
        
        for dup in duplicates:
            telegram_id = dup['telegram_id']
            count = dup['count']
            logger.warning(f"  - telegram_id {telegram_id}: {count} записей")
            
            # Получаем все записи этого пользователя
            cursor = await db.execute("""
                SELECT * FROM users WHERE telegram_id = ? ORDER BY created_at
            """, (telegram_id,))
            
            user_records = await cursor.fetchall()
            
            # Оставляем самую первую запись, удаляем остальные
            keep_user = user_records[0]
            remove_users = user_records[1:]
            
            logger.info(f"Оставляем пользователя ID {keep_user['id']}, удаляем {len(remove_users)} дубликатов")
            
            for remove_user in remove_users:
                # Удаляем роли дубликата
                await db.execute("DELETE FROM user_roles WHERE user_id = ?", (remove_user['id'],))
                # Удаляем самого пользователя
                await db.execute("DELETE FROM users WHERE id = ?", (remove_user['id'],))
                logger.info(f"  Удален дубликат ID {remove_user['id']}")
        
        await db.commit()
        logger.info("✅ Дубликаты очищены")

async def update_database_structure():
    """Обновление структуры базы данных если нужно"""
    
    logger.info("=== ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ ===")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем существование таблицы user_roles
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_roles'
        """)
        
        table_exists = await cursor.fetchone()
        
        if not table_exists:
            logger.warning("❌ Таблица user_roles не существует! Создаем...")
            
            await db.execute("""
                CREATE TABLE user_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, role)
                )
            """)
            
            await db.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles (user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles (role)")
            
            await db.commit()
            logger.info("✅ Таблица user_roles создана")
        else:
            logger.info("✅ Таблица user_roles существует")

async def main():
    """Основная функция - полная диагностика и исправление"""
    
    print("🔧 КОМПЛЕКСНОЕ ИСПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ И РОЛЕЙ")
    print("=" * 60)
    
    # 1. Обновляем структуру БД
    await update_database_structure()
    
    # 2. Очищаем дубликаты
    await clean_duplicate_users()
    
    # 3. Диагностика
    users_without_roles, users_with_roles, problematic_users = await comprehensive_user_diagnosis()
    
    # 4. Исправление пользователей без ролей
    if users_without_roles:
        print(f"\nНайдено {len(users_without_roles)} пользователей без ролей.")
        response = input("Исправить всех пользователей, добавив роль 'buyer'? (y/n): ")
        if response.lower() == 'y':
            await fix_users_without_roles(users_without_roles, 'buyer')
    
    # 5. Финальная проверка
    print("\n" + "=" * 60)
    print("ФИНАЛЬНАЯ ПРОВЕРКА:")
    await comprehensive_user_diagnosis()
    
    print("\n✅ Исправление завершено!")
    print("Теперь попробуйте использовать бота - проблемы с ролями должны быть решены.")

if __name__ == "__main__":
    # Запуск полного исправления
    asyncio.run(main())
    
    # Или проверка конкретного пользователя:
    # asyncio.run(verify_specific_user(YOUR_TELEGRAM_ID)) 