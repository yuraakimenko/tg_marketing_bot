import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.database import get_user, create_user, update_user_role
from database.models import UserRole, SubscriptionStatus
from bot.keyboards import (
    get_role_selection_keyboard, 
    get_main_menu_seller, 
    get_main_menu_buyer,
    get_settings_keyboard
)
from bot.states import RegistrationStates

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Обработка команды /start"""
    user = await get_user(message.from_user.id)
    
    if user is None:
        # Новый пользователь - предлагаем выбрать роль
        await message.answer(
            f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
            "🎯 Это бот для поиска и предложения блогеров - своего рода 'Tinder для блогеров'.\n\n"
            "Выберите вашу роль:",
            reply_markup=get_role_selection_keyboard()
        )
        await state.set_state(RegistrationStates.waiting_for_role)
    else:
        # Существующий пользователь
        await show_main_menu(message, user)


@router.callback_query(F.data.startswith("role_"))
async def handle_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора роли"""
    role_str = callback.data.split("_")[1]  # seller или buyer
    role = UserRole.SELLER if role_str == "seller" else UserRole.BUYER
    
    # Создаем пользователя
    user = await create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        role=role
    )
    
    await callback.answer()
    await callback.message.delete()
    
    role_name = "продажник" if role == UserRole.SELLER else "закупщик"
    await callback.message.answer(
        f"✅ Отлично! Вы зарегистрированы как {role_name}.\n\n"
        f"📋 Теперь вам доступны функции {'для размещения блогеров' if role == UserRole.SELLER else 'для поиска блогеров'}.\n\n"
        "💡 Для полного доступа к функциям бота необходима подписка 500₽/мес.",
        reply_markup=get_main_menu_seller(False) if role == UserRole.SELLER else get_main_menu_buyer(False)
    )
    
    await state.clear()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return
    
    role_name = "продажник" if user.role == UserRole.SELLER else "закупщик"
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    
    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"👤 <b>Роль:</b> {role_name}\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f} ({user.reviews_count} отзывов)\n\n"
        "Выберите действие:",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "change_role")
async def change_role(callback: CallbackQuery, state: FSMContext):
    """Смена роли пользователя"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "🔄 Выберите новую роль:\n\n"
        "⚠️ Внимание: при смене роли вы потеряете доступ к функциям предыдущей роли.",
        reply_markup=get_role_selection_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_role)


@router.callback_query(F.data.startswith("role_"), RegistrationStates.waiting_for_role)
async def handle_role_change(callback: CallbackQuery, state: FSMContext):
    """Обработка смены роли"""
    role_str = callback.data.split("_")[1]
    new_role = UserRole.SELLER if role_str == "seller" else UserRole.BUYER
    
    # Обновляем роль пользователя
    success = await update_user_role(callback.from_user.id, new_role)
    
    if success:
        await callback.answer()
        await callback.message.delete()
        
        role_name = "продажник" if new_role == UserRole.SELLER else "закупщик"
        # Получаем обновленные данные пользователя для проверки подписки
        updated_user = await get_user(callback.from_user.id)
        has_active_subscription = updated_user.subscription_status in [
            SubscriptionStatus.ACTIVE, 
            SubscriptionStatus.AUTO_RENEWAL_OFF, 
            SubscriptionStatus.CANCELLED
        ] if updated_user else False
        
        await callback.message.answer(
            f"✅ Роль успешно изменена на {role_name}!",
            reply_markup=get_main_menu_seller(has_active_subscription) if new_role == UserRole.SELLER else get_main_menu_buyer(has_active_subscription)
        )
    else:
        await callback.answer("❌ Ошибка при смене роли")
    
    await state.clear()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    role_name = "продажник" if user.role == UserRole.SELLER else "закупщик"
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    
    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 <b>ID:</b> {user.id}\n"
        f"👤 <b>Имя:</b> {user.first_name or 'Не указано'}\n"
        f"📛 <b>Username:</b> @{user.username or 'Не указано'}\n"
        f"🎭 <b>Роль:</b> {role_name}\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f} ({user.reviews_count} отзывов)\n"
        f"📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y')}"
    )
    
    if user.subscription_end_date:
        profile_text += f"\n🗓️ <b>Подписка до:</b> {user.subscription_end_date.strftime('%d.%m.%Y')}"
    
    await callback.answer()
    await callback.message.edit_text(profile_text, parse_mode="HTML")


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать справку"""
    help_text = (
        "❓ <b>Справка</b>\n\n"
        "🤖 Этот бот поможет вам найти подходящих блогеров или предложить своих.\n\n"
        "<b>Для продажников:</b>\n"
        "• Добавляйте блогеров в базу\n"
        "• Указывайте категории и цены\n"
        "• Получайте заказы от закупщиков\n\n"
        "<b>Для закупщиков:</b>\n"
        "• Ищите блогеров по критериям\n"
        "• Получайте подборки по вашим требованиям\n"
        "• Оценивайте качество сотрудничества\n\n"
        "💳 <b>Подписка:</b> 500₽/мес для доступа ко всем функциям\n\n"
        "📞 <b>Поддержка:</b> @support_username"
    )
    
    await callback.answer()
    await callback.message.edit_text(help_text, parse_mode="HTML")


@router.message(Command("help"))
async def help_command(message: Message):
    """Команда помощи"""
    await show_help(message)


async def show_main_menu(message: Message, user):
    """Показать главное меню для пользователя"""
    # Проверяем наличие активной подписки
    has_active_subscription = user.subscription_status in [
        SubscriptionStatus.ACTIVE, 
        SubscriptionStatus.AUTO_RENEWAL_OFF, 
        SubscriptionStatus.CANCELLED
    ]
    
    if user.role == UserRole.SELLER:
        greeting = (
            f"👋 Добро пожаловать, {user.first_name or 'Продажник'}!\n\n"
            "📋 Здесь вы можете управлять своими блогерами.\n"
            "Выберите действие:"
        )
        keyboard = get_main_menu_seller(has_active_subscription)
    else:
        greeting = (
            f"👋 Добро пожаловать, {user.first_name or 'Закупщик'}!\n\n"
            "🔍 Здесь вы можете найти подходящих блогеров.\n"
            "Выберите действие:"
        )
        keyboard = get_main_menu_buyer(has_active_subscription)
    
    await message.answer(greeting, reply_markup=keyboard) 