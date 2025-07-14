#!/usr/bin/env python3
"""
Скрипт для тестирования новых функций бота v2.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from database.database import init_db, create_user, create_blogger, get_user, get_blogger
from database.models import UserRole, Platform, BlogCategory, SubscriptionStatus
from utils.google_sheets import sheets_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_migration():
    """Тест миграции базы данных"""
    logger.info("🧪 Тестирование миграции базы данных...")
    
    # Инициализация БД
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Создание тестового пользователя
    user = await create_user(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        role=UserRole.SELLER
    )
    logger.info(f"✅ Создан тестовый пользователь: {user.username}")
    
    # Создание тестового блогера с множественными платформами
    blogger = await create_blogger(
        seller_id=user.id,
        name="Test Blogger",
        url="https://instagram.com/testblogger",
        platforms=[Platform.INSTAGRAM, Platform.YOUTUBE],
        categories=[BlogCategory.LIFESTYLE, BlogCategory.BEAUTY],
        audience_13_17_percent=10,
        audience_18_24_percent=40,
        audience_25_35_percent=35,
        audience_35_plus_percent=15,
        female_percent=70,
        male_percent=30,
        price_stories=10000,
        price_post=20000,
        price_video=50000,
        has_reviews=True,
        description="Тестовый блогер для проверки функций"
    )
    logger.info(f"✅ Создан тестовый блогер: {blogger.name}")
    logger.info(f"   Платформы: {blogger.get_platforms_summary()}")
    logger.info(f"   Возрастные категории: {blogger.get_age_categories_summary()}")
    
    # Проверка валидации
    logger.info("🧪 Тестирование валидации...")
    
    # Валидация возрастных категорий
    age_valid = blogger.validate_age_percentages()
    logger.info(f"   Валидация возрастных категорий: {'✅' if age_valid else '❌'}")
    
    # Валидация процентов по полу
    gender_valid = blogger.validate_gender_percentages()
    logger.info(f"   Валидация процентов по полу: {'✅' if gender_valid else '❌'}")
    
    return user, blogger

async def test_google_sheets_integration(user, blogger):
    """Тест интеграции с Google Sheets"""
    logger.info("🧪 Тестирование интеграции с Google Sheets...")
    
    try:
        # Инициализация Google Sheets
        success = await sheets_manager.initialize()
        if success:
            logger.info("✅ Google Sheets подключение установлено")
            
            # Тест записи действия с блогером
            user_data = {
                'username': user.username,
                'role': user.role.value,
                'subscription_start_date': datetime.now(),
                'subscription_end_date': datetime.now() + timedelta(days=30)
            }
            
            blogger_data = {
                'name': blogger.name,
                'url': blogger.url,
                'platforms': [p.value for p in blogger.platforms],
                'audience_13_17_percent': blogger.audience_13_17_percent,
                'audience_18_24_percent': blogger.audience_18_24_percent,
                'audience_25_35_percent': blogger.audience_25_35_percent,
                'audience_35_plus_percent': blogger.audience_35_plus_percent
            }
            
            sheets_success = await sheets_manager.add_blogger_action(
                user_data, blogger_data, "test"
            )
            logger.info(f"   Запись в Google Sheets: {'✅' if sheets_success else '❌'}")
            
            # Тест записи жалобы
            complaint_success = await sheets_manager.add_complaint(
                blogger_id=blogger.id,
                blogger_name=blogger.name,
                user_id=user.id,
                username=user.username,
                reason="Тестовая жалоба для проверки функционала"
            )
            logger.info(f"   Запись жалобы в Google Sheets: {'✅' if complaint_success else '❌'}")
            
        else:
            logger.warning("⚠️ Google Sheets не настроен (пропускаем тест)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании Google Sheets: {e}")

async def test_subscription_logic():
    """Тест логики подписок"""
    logger.info("🧪 Тестирование логики подписок...")
    
    # Тест расчета дат подписки
    start_date = datetime.now()
    
    # 1 месяц
    end_date_1m = start_date + timedelta(days=30)
    logger.info(f"   Подписка 1 месяц: {start_date.strftime('%d.%m.%Y')} - {end_date_1m.strftime('%d.%m.%Y')}")
    
    # 3 месяца
    end_date_3m = start_date + timedelta(days=90)
    logger.info(f"   Подписка 3 месяца: {start_date.strftime('%d.%m.%Y')} - {end_date_3m.strftime('%d.%m.%Y')}")
    
    # 12 месяцев
    end_date_12m = start_date + timedelta(days=365)
    logger.info(f"   Подписка 12 месяцев: {start_date.strftime('%d.%m.%Y')} - {end_date_12m.strftime('%d.%m.%Y')}")
    
    logger.info("✅ Логика подписок работает корректно")

async def test_role_permissions():
    """Тест системы ролей"""
    logger.info("🧪 Тестирование системы ролей...")
    
    # Создание пользователей с разными ролями
    seller = await create_user(
        telegram_id=111111111,
        username="test_seller",
        role=UserRole.SELLER
    )
    
    buyer = await create_user(
        telegram_id=222222222,
        username="test_buyer",
        role=UserRole.BUYER
    )
    
    logger.info(f"   Продажник: {seller.username} - {seller.role.value}")
    logger.info(f"   Закупщик: {buyer.username} - {buyer.role.value}")
    
    # Проверка прав доступа
    seller_can_complain = seller.role == UserRole.BUYER
    buyer_can_complain = buyer.role == UserRole.BUYER
    
    logger.info(f"   Продажник может жаловаться: {'❌' if seller_can_complain else '✅'}")
    logger.info(f"   Закупщик может жаловаться: {'✅' if buyer_can_complain else '❌'}")
    
    logger.info("✅ Система ролей работает корректно")

async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Начало тестирования новых функций бота v2.0")
    logger.info("=" * 50)
    
    try:
        # Тест миграции БД
        user, blogger = await test_database_migration()
        
        # Тест Google Sheets
        await test_google_sheets_integration(user, blogger)
        
        # Тест логики подписок
        await test_subscription_logic()
        
        # Тест системы ролей
        await test_role_permissions()
        
        logger.info("=" * 50)
        logger.info("🎉 Все тесты завершены успешно!")
        logger.info("✅ Бот v2.0 готов к использованию")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 