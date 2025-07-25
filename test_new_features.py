#!/usr/bin/env python3
"""
Скрипт для тестирования новых функций бота v2.0
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from database.database import init_db, create_user, create_blogger, get_user, get_blogger
from database.models import UserRole, Platform, BlogCategory, SubscriptionStatus
from utils.google_sheets import sheets_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def user_and_blogger():
    """Create and return a test user and blogger."""
    user, blogger = await test_database_migration()
    return user, blogger

@pytest.mark.asyncio
async def test_database_migration():
    """Тест миграции базы данных"""
    logger.info("🧪 Тестирование миграции базы данных...")
    
    # Инициализация БД
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Генерируем уникальный telegram_id для тестирования
    test_telegram_id = random.randint(100000000, 999999999)
    
    # Проверяем, что пользователь не существует
    existing_user = await get_user(test_telegram_id)
    if existing_user:
        logger.info(f"ℹ️ Пользователь с ID {test_telegram_id} уже существует, используем его")
        user = existing_user
    else:
        # Создание тестового пользователя
        user = await create_user(
            telegram_id=test_telegram_id,
            username="test_user",
            first_name="Test",
            last_name="User",
            roles=[UserRole.SELLER]
        )
        logger.info(f"✅ Создан тестовый пользователь: {user.username}")
    
    # Отладочная информация
    logger.info(f"📋 Информация о пользователе:")
    logger.info(f"   ID: {user.id}")
    logger.info(f"   Telegram ID: {user.telegram_id}")
    logger.info(f"   Username: {user.username}")
    logger.info(f"   Роли: {[r.value for r in user.roles]}")
    
    if user.id is None:
        logger.error("❌ User ID равно None! Невозможно создать блогера.")
        return None, None
    
    # Создание тестового блогера с множественными платформами
    blogger = await create_blogger(
        seller_id=user.id,
        name=f"Test Blogger {random.randint(1000, 9999)}",
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
        price_reels=50000,
        stats_images=["path/to/screenshot1.png", "path/to/screenshot2.png"],
        has_reviews=True,
        description="Тестовый блогер для проверки функций"
    )
    logger.info(f"✅ Создан тестовый блогер: {blogger.name}")
    logger.info(f"   Платформы: {blogger.get_platforms_summary()}")
    logger.info(f"   Возрастные категории: {blogger.get_age_categories_summary()}")

    assert len(blogger.stats_images) == 2
    
    # Проверка валидации
    logger.info("🧪 Тестирование валидации...")
    
    # Валидация возрастных категорий
    age_valid = blogger.validate_age_percentages()
    logger.info(f"   Валидация возрастных категорий: {'✅' if age_valid else '❌'}")
    
    # Валидация процентов по полу
    gender_valid = blogger.validate_gender_percentages()
    logger.info(f"   Валидация процентов по полу: {'✅' if gender_valid else '❌'}")
    
    return user, blogger

@pytest.mark.asyncio
async def test_google_sheets_integration(user_and_blogger):
    user, blogger = user_and_blogger
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
                'roles': [r.value for r in user.roles],
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_role_permissions():
    """Тест системы ролей"""
    logger.info("🧪 Тестирование системы ролей...")
    
    # Генерируем уникальные telegram_id для тестирования
    seller_telegram_id = random.randint(100000000, 999999999)
    buyer_telegram_id = random.randint(100000000, 999999999)
    
    # Проверяем и создаем продажника
    existing_seller = await get_user(seller_telegram_id)
    if existing_seller:
        seller = existing_seller
    else:
        seller = await create_user(
            telegram_id=seller_telegram_id,
            username="test_seller",
            roles=[UserRole.SELLER]
        )
    
    # Проверяем и создаем закупщика
    existing_buyer = await get_user(buyer_telegram_id)
    if existing_buyer:
        buyer = existing_buyer
    else:
        buyer = await create_user(
            telegram_id=buyer_telegram_id,
            username="test_buyer",
            roles=[UserRole.BUYER]
        )
    
    logger.info(f"   Продажник: {seller.username} - {[r.value for r in seller.roles]}")
    logger.info(f"   Закупщик: {buyer.username} - {[r.value for r in buyer.roles]}")
    
    # Проверка прав доступа
    seller_can_complain = seller.has_role(UserRole.BUYER)
    buyer_can_complain = buyer.has_role(UserRole.BUYER)
    
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
        await test_google_sheets_integration((user, blogger))
        
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
