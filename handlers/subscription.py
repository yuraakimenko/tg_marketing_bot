import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import os

from database.database import (get_user, update_subscription_status, get_user_subscription, 
                                    toggle_auto_renewal, cancel_subscription, get_user_payment_history)
from database.models import SubscriptionStatus
from bot.keyboards import (get_subscription_keyboard, get_payment_confirmation_keyboard,
                          get_subscription_management_keyboard, get_subscription_cancel_confirmation_keyboard)
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
        
        # Обновляем главное меню с новой клавиатурой
        from bot.keyboards import get_main_menu_seller, get_main_menu_buyer
        from database.models import UserRole
        
        # Получаем обновленные данные пользователя
        updated_user = await get_user(callback.from_user.id)
        if updated_user:
            has_active_subscription = updated_user.subscription_status in [
                SubscriptionStatus.ACTIVE, 
                SubscriptionStatus.AUTO_RENEWAL_OFF, 
                SubscriptionStatus.CANCELLED
            ]
            
            keyboard = get_main_menu_seller(has_active_subscription) if updated_user.role == UserRole.SELLER else get_main_menu_buyer(has_active_subscription)
            
            # Отправляем новое сообщение с обновленной клавиатурой
            await callback.message.answer(
                "🏠 Главное меню обновлено!\n\n"
                "Теперь вам доступна кнопка 'Управление подпиской'.",
                reply_markup=keyboard
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
                
                # Обновляем главное меню с новой клавиатурой
                from bot.keyboards import get_main_menu_seller, get_main_menu_buyer
                from database.models import UserRole
                
                # Получаем обновленные данные пользователя
                updated_user = await get_user(callback.from_user.id)
                if updated_user:
                    has_active_subscription = updated_user.subscription_status in [
                        SubscriptionStatus.ACTIVE, 
                        SubscriptionStatus.AUTO_RENEWAL_OFF, 
                        SubscriptionStatus.CANCELLED
                    ]
                    
                    keyboard = get_main_menu_seller(has_active_subscription) if updated_user.role == UserRole.SELLER else get_main_menu_buyer(has_active_subscription)
                    
                    # Отправляем новое сообщение с обновленной клавиатурой
                    await callback.message.answer(
                        "🏠 Главное меню обновлено!\n\n"
                        "Теперь вам доступна кнопка 'Управление подпиской'.",
                        reply_markup=keyboard
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


# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ ПОДПИСКОЙ ===

@router.message(F.text == "🔧 Управление подпиской")
async def subscription_management_menu(message: Message):
    """Меню управления подпиской"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return
    
    # Проверяем наличие активной подписки
    if user.subscription_status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.AUTO_RENEWAL_OFF, SubscriptionStatus.CANCELLED]:
        await message.answer(
            "❌ У вас нет активной подписки.\n\n"
            "Для управления подпиской сначала оформите её в разделе '💳 Подписка'."
        )
        return
    
    # Получаем подробную информацию о подписке
    subscription = await get_user_subscription(user.id)
    
    # Если подписки нет в таблице subscriptions, но пользователь имеет активную подписку,
    # создаем объект подписки на основе данных из таблицы users
    if not subscription and user.subscription_end_date:
        from database.models import Subscription
        from datetime import datetime
        
        # Создаем временный объект подписки для управления
        subscription = Subscription(
            id=0,  # Временный ID
            user_id=user.id,
            start_date=user.created_at,  # Используем дату регистрации как начало
            end_date=user.subscription_end_date,
            amount=50000,  # Стандартная цена 500₽
            status=user.subscription_status,
            auto_renewal=True,  # По умолчанию включено
            cancelled_at=None,
            created_at=user.created_at
        )
    
    if not subscription:
        await message.answer("❌ Информация о подписке не найдена.")
        return
    
    # Определяем статус автопродления
    auto_renewal_status = "включено" if subscription.auto_renewal else "отключено"
    status_emoji = "✅" if subscription.auto_renewal else "⏸️"
    
    # Формируем текст с информацией
    end_date = subscription.end_date.strftime('%d.%m.%Y %H:%M')
    amount = subscription.amount / 100  # из копеек в рубли
    
    # Статус подписки
    status_text = ""
    if subscription.status == SubscriptionStatus.ACTIVE:
        status_text = "✅ Активна"
    elif subscription.status == SubscriptionStatus.AUTO_RENEWAL_OFF:
        status_text = "⏸️ Активна (без автопродления)"
    elif subscription.status == SubscriptionStatus.CANCELLED:
        status_text = "❌ Отменена (действует до окончания)"
    
    management_text = (
        f"🔧 <b>Управление подпиской</b>\n\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"📅 <b>Действует до:</b> {end_date}\n"
        f"💰 <b>Сумма:</b> {amount}₽\n"
        f"🔄 <b>Автопродление:</b> {status_emoji} {auto_renewal_status}\n\n"
    )
    
    if subscription.cancelled_at:
        cancelled_date = subscription.cancelled_at.strftime('%d.%m.%Y %H:%M')
        management_text += f"⚠️ <b>Отменена:</b> {cancelled_date}\n\n"
    
    # Если это временная подписка (без записи в БД), добавляем примечание
    if subscription.id == 0:
        management_text += "ℹ️ <i>Для полного управления рекомендуется продлить подписку через новую систему.</i>\n\n"
    
    management_text += "Выберите действие:"
    
    await message.answer(
        management_text,
        reply_markup=get_subscription_management_keyboard(subscription.auto_renewal),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "disable_auto_renewal")
async def disable_auto_renewal(callback: CallbackQuery):
    """Отключение автопродления"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    success = await toggle_auto_renewal(user.id, False)
    
    if success:
        await callback.answer("✅ Автопродление отключено")
        await callback.message.edit_text(
            "✅ <b>Автопродление отключено</b>\n\n"
            "📋 Ваша подписка будет действовать до окончания текущего периода, "
            "после чего автоматически не продлится.\n\n"
            "💡 Вы всегда можете включить автопродление обратно или "
            "продлить подписку вручную в любое время.",
            reply_markup=get_subscription_management_keyboard(False),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отключении автопродления")


@router.callback_query(F.data == "enable_auto_renewal")
async def enable_auto_renewal(callback: CallbackQuery):
    """Включение автопродления"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    success = await toggle_auto_renewal(user.id, True)
    
    if success:
        await callback.answer("✅ Автопродление включено")
        await callback.message.edit_text(
            "✅ <b>Автопродление включено</b>\n\n"
            "🔄 Ваша подписка будет автоматически продлеваться за 3 дня до окончания "
            "на тот же период по той же цене.\n\n"
            "💳 Убедитесь, что способ оплаты действителен для автоматического списания.",
            reply_markup=get_subscription_management_keyboard(True),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при включении автопродления")


@router.callback_query(F.data == "suspend_subscription")
async def suspend_subscription(callback: CallbackQuery):
    """Приостановка подписки до окончания периода"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    success = await cancel_subscription(user.id, cancel_immediately=False)
    
    if success:
        await callback.answer("✅ Подписка приостановлена")
        await callback.message.edit_text(
            "⏸️ <b>Подписка приостановлена</b>\n\n"
            "📋 Ваша подписка будет действовать до окончания текущего периода, "
            "после чего будет деактивирована.\n\n"
            "🔄 Автопродление отключено.\n\n"
            "💡 Для возобновления подписки используйте раздел '💳 Подписка'.",
            reply_markup=get_subscription_management_keyboard(False),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при приостановке подписки")


@router.callback_query(F.data == "cancel_subscription_full")
async def request_full_cancellation(callback: CallbackQuery):
    """Запрос полной отмены подписки"""
    await callback.answer()
    await callback.message.edit_text(
        "⚠️ <b>Полная отмена подписки</b>\n\n"
        "❗ Внимание! При полной отмене подписки:\n"
        "• Доступ к функциям бота будет немедленно прекращен\n"
        "• Возврат средств за неиспользованный период не предусмотрен\n"
        "• Все ваши данные сохранятся для возможного восстановления\n\n"
        "🤔 Вы уверены, что хотите полностью отменить подписку?",
        reply_markup=get_subscription_cancel_confirmation_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_cancel_subscription")
async def confirm_full_cancellation(callback: CallbackQuery):
    """Подтверждение полной отмены подписки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    success = await cancel_subscription(user.id, cancel_immediately=True)
    
    if success:
        await callback.answer("✅ Подписка отменена")
        await callback.message.edit_text(
            "❌ <b>Подписка полностью отменена</b>\n\n"
            "📋 Доступ к премиум-функциям деактивирован.\n"
            "💾 Ваши данные сохранены.\n\n"
            "💡 Для восстановления доступа оформите новую подписку "
            "в разделе '💳 Подписка'.\n\n"
            "🙏 Спасибо за использование нашего сервиса!",
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отмене подписки")


@router.callback_query(F.data == "cancel_subscription_cancel")
async def cancel_cancellation(callback: CallbackQuery):
    """Отмена процесса отмены подписки"""
    await callback.answer("Отмена отменена 😊")
    
    # Возвращаемся к меню управления
    user = await get_user(callback.from_user.id)
    subscription = await get_user_subscription(user.id)
    
    await callback.message.edit_text(
        "🔧 <b>Управление подпиской</b>\n\n"
        "Выберите действие:",
        reply_markup=get_subscription_management_keyboard(subscription.auto_renewal if subscription else True),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "payment_history")
async def show_payment_history(callback: CallbackQuery):
    """Показать историю платежей"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    history = await get_user_payment_history(user.id, limit=10)
    
    if not history:
        await callback.answer("📋 История платежей пуста")
        return
    
    history_text = "📊 <b>История платежей</b>\n\n"
    
    for i, payment in enumerate(history, 1):
        amount = payment.amount / 100  # из копеек в рубли
        start_date = payment.start_date.strftime('%d.%m.%Y')
        end_date = payment.end_date.strftime('%d.%m.%Y')
        
        status_emoji = {
            SubscriptionStatus.ACTIVE: "✅",
            SubscriptionStatus.EXPIRED: "⏰",
            SubscriptionStatus.CANCELLED: "❌",
            SubscriptionStatus.INACTIVE: "💤"
        }.get(payment.status, "❓")
        
        history_text += (
            f"{i}. {status_emoji} <b>{amount}₽</b>\n"
            f"   📅 {start_date} - {end_date}\n"
            f"   📝 {payment.status.value}\n"
        )
        
        if payment.payment_id:
            history_text += f"   🆔 {payment.payment_id}\n"
        
        history_text += "\n"
    
    await callback.answer()
    await callback.message.edit_text(
        history_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_subscription_management")]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_subscription_management")
async def back_to_subscription_management(callback: CallbackQuery):
    """Возврат к меню управления подпиской"""
    user = await get_user(callback.from_user.id)
    subscription = await get_user_subscription(user.id)
    
    if not subscription:
        await callback.answer("❌ Подписка не найдена")
        return
    
    await callback.answer()
    
    # Повторяем логику из subscription_management_menu
    auto_renewal_status = "включено" if subscription.auto_renewal else "отключено"
    status_emoji = "✅" if subscription.auto_renewal else "⏸️"
    
    end_date = subscription.end_date.strftime('%d.%m.%Y %H:%M')
    amount = subscription.amount / 100
    
    status_text = ""
    if subscription.status == SubscriptionStatus.ACTIVE:
        status_text = "✅ Активна"
    elif subscription.status == SubscriptionStatus.AUTO_RENEWAL_OFF:
        status_text = "⏸️ Активна (без автопродления)"
    elif subscription.status == SubscriptionStatus.CANCELLED:
        status_text = "❌ Отменена (действует до окончания)"
    
    management_text = (
        f"🔧 <b>Управление подпиской</b>\n\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"📅 <b>Действует до:</b> {end_date}\n"
        f"💰 <b>Сумма:</b> {amount}₽\n"
        f"🔄 <b>Автопродление:</b> {status_emoji} {auto_renewal_status}\n\n"
    )
    
    if subscription.cancelled_at:
        cancelled_date = subscription.cancelled_at.strftime('%d.%m.%Y %H:%M')
        management_text += f"⚠️ <b>Отменена:</b> {cancelled_date}\n\n"
    
    management_text += "Выберите действие:"
    
    await callback.message.edit_text(
        management_text,
        reply_markup=get_subscription_management_keyboard(subscription.auto_renewal),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.answer("Возвращаемся в главное меню")
    await callback.message.delete()
    
    # Получаем данные пользователя для правильной клавиатуры
    user = await get_user(callback.from_user.id)
    if user:
        from bot.keyboards import get_main_menu_seller, get_main_menu_buyer
        from database.models import UserRole
        
        has_active_subscription = user.subscription_status in [
            SubscriptionStatus.ACTIVE, 
            SubscriptionStatus.AUTO_RENEWAL_OFF, 
            SubscriptionStatus.CANCELLED
        ]
        
        keyboard = get_main_menu_seller(has_active_subscription) if user.role == UserRole.SELLER else get_main_menu_buyer(has_active_subscription)
        
        # Отправляем сообщение о возврате в главное меню с правильной клавиатурой
        await callback.message.answer(
            "🏠 Вы вернулись в главное меню.\n\n"
            "Используйте кнопки ниже для навигации.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "🏠 Вы вернулись в главное меню.\n\n"
            "Используйте кнопки ниже для навигации.",
            parse_mode="HTML"
        ) 