import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import os

from database.database import get_user, update_subscription_status
from database.models import SubscriptionStatus
from bot.keyboards import get_subscription_keyboard, get_payment_confirmation_keyboard
from utils.payments import create_subscription_payment

router = Router()
logger = logging.getLogger(__name__)

# Цена подписки в копейках (500 рублей = 50000 копеек)
SUBSCRIPTION_PRICE = 50000
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', 'TEST_TOKEN')


@router.message(F.text == "💳 Подписка")
async def subscription_menu(message: Message):
    """Меню подписки"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return
    
    if user.subscription_status == SubscriptionStatus.ACTIVE:
        # Активная подписка
        end_date = user.subscription_end_date.strftime('%d.%m.%Y') if user.subscription_end_date else "Не указана"
        
        subscription_text = (
            f"✅ <b>Подписка активна!</b>\n\n"
            f"📅 <b>Действует до:</b> {end_date}\n\n"
            f"🎯 <b>Ваши возможности:</b>\n"
            f"• Полный доступ ко всем функциям\n"
            f"• Размещение/поиск блогеров\n"
            f"• Получение контактов\n"
            f"• Система рейтингов\n\n"
            f"💡 Подписка продлевается автоматически за 3 дня до окончания."
        )
    else:
        # Неактивная подписка
        subscription_text = (
            f"❌ <b>Подписка неактивна</b>\n\n"
            f"💳 <b>Стоимость:</b> 500₽/месяц\n\n"
            f"🎯 <b>Что включено:</b>\n"
            f"• Размещение блогеров (для продажников)\n"
            f"• Поиск по базе блогеров (для закупщиков)\n"
            f"• Получение контактов продавцов\n"
            f"• Система рейтингов и отзывов\n"
            f"• Приоритетное отображение в результатах\n\n"
            f"💡 Без подписки доступен только просмотр профиля и настройки."
        )
    
    await message.answer(
        subscription_text,
        reply_markup=get_subscription_keyboard() if user.subscription_status != SubscriptionStatus.ACTIVE else None,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "subscription_info")
async def subscription_info(callback: CallbackQuery):
    """Подробная информация о подписке"""
    info_text = (
        f"ℹ️ <b>Подробно о подписке</b>\n\n"
        f"💰 <b>Стоимость:</b> 500₽ в месяц\n\n"
        f"📋 <b>Для продажников:</b>\n"
        f"• Добавление неограниченного количества блогеров\n"
        f"• Отображение в результатах поиска\n"
        f"• Получение заявок от закупщиков\n"
        f"• Система рейтингов\n\n"
        f"🔍 <b>Для закупщиков:</b>\n"
        f"• Поиск по всей базе блогеров\n"
        f"• Расширенные фильтры поиска\n"
        f"• Получение контактов продавцов\n"
        f"• Оценка качества сотрудничества\n\n"
        f"⚡ <b>Преимущества:</b>\n"
        f"• Мгновенная активация\n"
        f"• Без комиссий за сделки\n"
        f"• Техническая поддержка\n"
        f"• Регулярные обновления базы\n\n"
        f"🔄 Подписка продлевается автоматически"
    )
    
    await callback.answer()
    await callback.message.edit_text(
        info_text,
        reply_markup=get_subscription_keyboard(),
        parse_mode="HTML"
    )


# Обработчики для разных типов подписки
@router.callback_query(F.data == "pay_monthly")
async def initiate_monthly_payment(callback: CallbackQuery):
    """Инициация платежа за месячную подписку"""
    await initiate_payment(callback, "monthly")

@router.callback_query(F.data == "pay_quarterly") 
async def initiate_quarterly_payment(callback: CallbackQuery):
    """Инициация платежа за квартальную подписку"""
    await initiate_payment(callback, "quarterly")

@router.callback_query(F.data == "pay_yearly")
async def initiate_yearly_payment(callback: CallbackQuery):
    """Инициация платежа за годовую подписку"""
    await initiate_payment(callback, "yearly")


async def initiate_payment(callback: CallbackQuery, subscription_type: str):
    """Общая функция инициации платежа"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    if user.subscription_status == SubscriptionStatus.ACTIVE:
        await callback.answer("✅ У вас уже есть активная подписка")
        return
    
    # Создаем платеж через Robokassa
    payment_data = create_subscription_payment(user.telegram_id, subscription_type)
    
    # Названия подписок
    subscription_names = {
        "monthly": "1 месяц",
        "quarterly": "3 месяца", 
        "yearly": "12 месяцев"
    }
    
    subscription_name = subscription_names.get(subscription_type, "1 месяц")
    
    # Формируем сообщение
    if payment_data.get('is_mock'):
        payment_text = (
            f"💳 <b>Оплата подписки ({subscription_name})</b>\n\n"
            f"💰 <b>Сумма:</b> {payment_data['amount']}₽\n"
            f"🆔 <b>Номер заказа:</b> {payment_data['invoice_id']}\n\n"
            f"⚠️ <b>ТЕСТОВЫЙ РЕЖИМ</b>\n"
            f"Выберите результат имитации оплаты:"
        )
    else:
        payment_text = (
            f"💳 <b>Оплата подписки ({subscription_name})</b>\n\n"
            f"💰 <b>Сумма:</b> {payment_data['amount']}₽\n"
            f"🆔 <b>Номер заказа:</b> {payment_data['invoice_id']}\n\n"
            f"🔐 <b>Платеж через Robokassa</b>\n"
            f"Нажмите кнопку ниже для перехода к оплате:"
        )
    
    await callback.answer()
    await callback.message.edit_text(
        payment_text,
        reply_markup=get_payment_confirmation_keyboard(payment_data),
        parse_mode="HTML"
    )
    
    # Сохраняем данные платежа в состояние пользователя (можно в БД)
    logger.info(f"Payment initiated for user {user.telegram_id}: {payment_data['invoice_id']}")


# Обработчики mock-платежей для тестирования
@router.callback_query(F.data.startswith("mock_payment_success_"))
async def handle_mock_payment_success(callback: CallbackQuery):
    """Обработка успешного mock-платежа"""
    invoice_id = callback.data.split("_", 3)[3]
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Определяем тип подписки по сумме (можно улучшить логику)
    subscription_duration = timedelta(days=30)  # По умолчанию месяц
    
    # Здесь можно добавить логику определения типа подписки из invoice_id
    if "quarterly" in invoice_id:
        subscription_duration = timedelta(days=90)
    elif "yearly" in invoice_id:
        subscription_duration = timedelta(days=365)
    
    end_date = datetime.now() + subscription_duration
    
    success = await update_subscription_status(
        user.id, 
        SubscriptionStatus.ACTIVE, 
        end_date
    )
    
    if success:
        await callback.answer("✅ Платеж успешно обработан!")
        await callback.message.edit_text(
            f"🎉 <b>Оплата успешна!</b>\n\n"
            f"✅ Подписка активирована!\n"
            f"📅 Действует до: {end_date.strftime('%d.%m.%Y')}\n"
            f"🆔 Номер заказа: {invoice_id}\n\n"
            f"🚀 Теперь вам доступны все функции бота.\n"
            f"Используйте главное меню для начала работы.",
            parse_mode="HTML"
        )
        logger.info(f"Mock payment successful for user {user.telegram_id}, invoice {invoice_id}")
    else:
        await callback.answer("❌ Ошибка активации подписки")


@router.callback_query(F.data.startswith("mock_payment_failure_"))
async def handle_mock_payment_failure(callback: CallbackQuery):
    """Обработка неудачного mock-платежа"""
    invoice_id = callback.data.split("_", 3)[3]
    
    await callback.answer("❌ Платеж отклонен")
    await callback.message.edit_text(
        f"❌ <b>Платеж не прошел</b>\n\n"
        f"🆔 Номер заказа: {invoice_id}\n"
        f"📝 Причина: Имитация неудачного платежа\n\n"
        f"💡 Попробуйте оплатить еще раз или обратитесь в поддержку.",
        reply_markup=get_subscription_keyboard(),
        parse_mode="HTML"
    )
    
    logger.info(f"Mock payment failure for invoice {invoice_id}")


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Проверка статуса реального платежа"""
    invoice_id = callback.data.split("_", 2)[2]
    
    # Здесь будет реальная проверка статуса через API Robokassa
    from utils.payments import get_payment_status
    
    status = get_payment_status(invoice_id)
    
    if status['status'] == 'paid':
        user = await get_user(callback.from_user.id)
        if user:
            # Активируем подписку
            end_date = datetime.now() + timedelta(days=30)
            
            success = await update_subscription_status(
                user.id, 
                SubscriptionStatus.ACTIVE, 
                end_date
            )
            
            if success:
                await callback.answer("✅ Платеж подтвержден!")
                await callback.message.edit_text(
                    f"🎉 <b>Платеж подтвержден!</b>\n\n"
                    f"✅ Подписка активирована!\n"
                    f"📅 Действует до: {end_date.strftime('%d.%m.%Y')}\n"
                    f"🆔 Номер заказа: {invoice_id}\n\n"
                    f"🚀 Теперь вам доступны все функции бота.",
                    parse_mode="HTML"
                )
            else:
                await callback.answer("❌ Ошибка активации")
    elif status['status'] == 'pending':
        await callback.answer("⏳ Платеж в обработке")
        await callback.message.edit_text(
            f"⏳ <b>Платеж в обработке</b>\n\n"
            f"🆔 Номер заказа: {invoice_id}\n"
            f"📝 Статус: Ожидает подтверждения\n\n"
            f"💡 Проверьте статус через несколько минут.",
            reply_markup=get_payment_confirmation_keyboard({
                'invoice_id': invoice_id,
                'is_mock': False
            }),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Платеж не найден")


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    """Отмена платежа"""
    await callback.answer("Платеж отменен")
    await callback.message.edit_text(
        "❌ Платеж отменен.\n\n"
        "Вы можете вернуться к выбору подписки:",
        reply_markup=get_subscription_keyboard()
    )


# Старые функции Telegram Payments удалены - теперь используем Robokassa


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать статистику пользователя"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    
    role_name = "продажник" if user.role.value == "seller" else "закупщик"
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 <b>Роль:</b> {role_name}\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f}\n"
        f"📝 <b>Отзывов:</b> {user.reviews_count}\n"
        f"📅 <b>В боте с:</b> {user.created_at.strftime('%d.%m.%Y')}\n"
    )
    
    if user.role.value == "seller":
        # Статистика для продажника
        from database.database import get_user_bloggers
        bloggers = await get_user_bloggers(user.id)
        stats_text += f"\n📝 <b>Добавлено блогеров:</b> {len(bloggers)}\n"
        
        # Можно добавить больше статистики:
        # - Количество просмотров блогеров
        # - Количество переходов к контактам
        # - etc.
    
    if user.subscription_end_date:
        stats_text += f"🗓️ <b>Подписка до:</b> {user.subscription_end_date.strftime('%d.%m.%Y')}"
    
    await message.answer(stats_text, parse_mode="HTML") 