import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.database import get_user, create_user, add_user_role, update_user_roles
from database.models import UserRole, SubscriptionStatus
from bot.keyboards import (
    get_role_selection_keyboard, 
    get_main_menu_seller, 
    get_main_menu_buyer,
    get_settings_keyboard,
    get_combined_main_menu
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
async def handle_role_selection_unified(callback: CallbackQuery, state: FSMContext):
    """Унифицированная обработка выбора роли - и для регистрации, и для смены роли"""
    logger.info(f"Получен callback для выбора роли: {callback.data} от пользователя {callback.from_user.id}")
    
    # Получаем пользователя
    user = await get_user(callback.from_user.id)
    
    role_str = callback.data.split("_")[1]  # seller или buyer
    role = UserRole.SELLER if role_str == "seller" else UserRole.BUYER
    
    if not user:
        # НОВЫЙ ПОЛЬЗОВАТЕЛЬ - РЕГИСТРАЦИЯ
        logger.info(f"Создаем нового пользователя с ролью: {callback.data}")
        logger.info(f"Роль определена как: {role}")
        logger.info(f"Данные пользователя: telegram_id={callback.from_user.id}, username={callback.from_user.username}, first_name={callback.from_user.first_name}, last_name={callback.from_user.last_name}")
        
        try:
            # Создаем пользователя с выбранной ролью
            logger.info(f"Начинаем создание пользователя с telegram_id: {callback.from_user.id}")
            
            user = await create_user(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                roles=[role]
            )
            
            if not user:
                logger.error("create_user вернул None")
                await callback.answer("❌ Ошибка при создании пользователя")
                await callback.message.answer("❌ Не удалось создать пользователя. Попробуйте еще раз.")
                return
            
            if not user.id:
                logger.error(f"Пользователь создан, но ID равно None: {user}")
                await callback.answer("❌ Ошибка данных пользователя")
                await callback.message.answer("❌ Проблема с данными пользователя. Обратитесь в поддержку.")
                return
            
            logger.info(f"Пользователь создан успешно: ID={user.id}, telegram_id={user.telegram_id}, роли={[r.value for r in user.roles]}")
            
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
            logger.info("Регистрация завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при регистрации. Попробуйте еще раз.")
            await callback.message.answer(
                "❌ Произошла ошибка при регистрации.\n\n"
                f"Детали ошибки: {str(e)[:100]}\n\n"
                "Попробуйте выполнить /start еще раз или обратитесь в поддержку."
            )
    
    else:
        # СУЩЕСТВУЮЩИЙ ПОЛЬЗОВАТЕЛЬ - ДОБАВЛЕНИЕ РОЛИ
        logger.info(f"Обработка добавления роли существующим пользователем: {callback.data} от пользователя {callback.from_user.id}")
        logger.info(f"Новая роль: {role}")
        logger.info(f"Текущие роли пользователя: {[r.value for r in user.roles]}")
        
        # Проверяем, есть ли уже эта роль
        if user.has_role(role):
            role_name = "продажника" if role == UserRole.SELLER else "закупщика"
            logger.info(f"У пользователя уже есть роль {role_name}")
            await callback.answer(f"ℹ️ У вас уже есть роль {role_name}")
            return
        
        # Добавляем новую роль пользователю
        logger.info(f"Добавляем роль {role} пользователю {callback.from_user.id}")
        success = await add_user_role(callback.from_user.id, role)
        
        if success:
            logger.info("Роль успешно добавлена")
            await callback.answer("✅ Роль успешно добавлена!")
            
            # Получаем обновленные данные пользователя для проверки подписки
            updated_user = await get_user(callback.from_user.id)
            has_active_subscription = updated_user.subscription_status in [
                SubscriptionStatus.ACTIVE, 
                SubscriptionStatus.AUTO_RENEWAL_OFF, 
                SubscriptionStatus.CANCELLED
            ] if updated_user else False
            
            # Формируем список всех ролей
            all_roles = []
            if updated_user.has_role(UserRole.SELLER):
                all_roles.append("продажник")
            if updated_user.has_role(UserRole.BUYER):
                all_roles.append("закупщик")
            
            roles_text = ", ".join(all_roles)
            
            # Обновляем сообщение с новыми ролями
            await callback.message.edit_text(
                f"✅ <b>Роль успешно добавлена!</b>\n\n"
                f"🎭 Ваши роли: <b>{roles_text}</b>\n"
                f"💳 Подписка: {'сохранена' if has_active_subscription else 'неактивна'}\n\n"
                f"🚀 Теперь вам доступны функции для всех ваших ролей.",
                reply_markup=get_combined_main_menu(updated_user, has_active_subscription),
                parse_mode="HTML"
            )
            
            logger.info("Роль добавлена успешно")
            
        else:
            logger.error("Ошибка при добавлении роли")
            await callback.answer("❌ Ошибка при добавлении роли")
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Произошла ошибка при добавлении роли.\n"
                "Пожалуйста, попробуйте еще раз или обратитесь в поддержку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Вернуться в настройки", callback_data="back_to_settings")]
                ]),
                parse_mode="HTML"
            )


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return
    
    # Формируем список ролей
    role_names = []
    if user.has_role(UserRole.SELLER):
        role_names.append("продажник")
    if user.has_role(UserRole.BUYER):
        role_names.append("закупщик")
    
    roles_text = ", ".join(role_names) if role_names else "не указана"
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    
    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"👤 <b>Роли:</b> {roles_text}\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f} ({user.reviews_count} отзывов)\n\n"
        "Выберите действие:",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "change_role")
async def change_role(callback: CallbackQuery, state: FSMContext):
    """Смена роли пользователя"""
    logger.info(f"Запрос на смену роли от пользователя {callback.from_user.id}")
    
    user = await get_user(callback.from_user.id)
    if not user:
        logger.error(f"Пользователь {callback.from_user.id} не найден при запросе смены роли")
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Формируем список текущих ролей
    current_roles = []
    if user.has_role(UserRole.SELLER):
        current_roles.append("продажник")
    if user.has_role(UserRole.BUYER):
        current_roles.append("закупщик")
    
    current_roles_text = ", ".join(current_roles) if current_roles else "не указана"
    logger.info(f"Текущие роли пользователя {callback.from_user.id}: {current_roles_text}")
    
    await callback.answer()
    await callback.message.edit_text(
        f"🔄 <b>Управление ролями</b>\n\n"
        f"📋 Текущие роли: <b>{current_roles_text}</b>\n\n"
        f"Выберите действие:\n\n"
        f"ℹ️ <b>Важно:</b> Подписка сохранится при изменении ролей.",
        reply_markup=get_role_management_keyboard(),
        parse_mode="HTML"
    )
    logger.info(f"Отображено меню управления ролями для пользователя {callback.from_user.id}")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    """Возврат в настройки"""
    await callback.answer()
    await settings_menu(callback.message)


async def show_main_menu(message: Message, user: User):
    """Показать главное меню в зависимости от ролей пользователя"""
    has_active_subscription = user.subscription_status in [
        SubscriptionStatus.ACTIVE, 
        SubscriptionStatus.AUTO_RENEWAL_OFF, 
        SubscriptionStatus.CANCELLED
    ]
    
    if user.has_role(UserRole.SELLER) and user.has_role(UserRole.BUYER):
        # Пользователь с двумя ролями
        keyboard = get_combined_main_menu(user, has_active_subscription)
        await message.answer(
            f"👋 Добро пожаловать обратно, {user.first_name or 'пользователь'}!\n\n"
            f"🎭 Ваши роли: продажник, закупщик\n"
            f"💳 Подписка: {'активна' if has_active_subscription else 'неактивна'}\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    elif user.has_role(UserRole.SELLER):
        # Только продажник
        keyboard = get_main_menu_seller(has_active_subscription)
        await message.answer(
            f"👋 Добро пожаловать обратно, {user.first_name or 'пользователь'}!\n\n"
            f"🎭 Ваша роль: продажник\n"
            f"💳 Подписка: {'активна' if has_active_subscription else 'неактивна'}\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    elif user.has_role(UserRole.BUYER):
        # Только закупщик
        keyboard = get_main_menu_buyer(has_active_subscription)
        await message.answer(
            f"👋 Добро пожаловать обратно, {user.first_name or 'пользователь'}!\n\n"
            f"🎭 Ваша роль: закупщик\n"
            f"💳 Подписка: {'активна' if has_active_subscription else 'неактивна'}\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    else:
        # Пользователь без ролей (ошибка)
        await message.answer(
            "❌ <b>Проблема с ролями</b>\n\n"
            "У вас не назначена ни одна роль.\n"
            "Выберите роль для продолжения:",
            reply_markup=get_role_selection_keyboard(),
            parse_mode="HTML"
        )


async def update_main_menu_keyboard(message: Message, user_id: int):
    """Обновить клавиатуру главного меню для пользователя"""
    user = await get_user(user_id)
    if not user:
        return
    
    has_active_subscription = user.subscription_status in [
        SubscriptionStatus.ACTIVE, 
        SubscriptionStatus.AUTO_RENEWAL_OFF, 
        SubscriptionStatus.CANCELLED
    ]
    
    keyboard = get_combined_main_menu(user, has_active_subscription)
    
    await message.answer(
        "🔄 Главное меню обновлено!\n\n"
        "Теперь вам доступны актуальные функции.",
        reply_markup=keyboard
    )


def get_role_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления ролями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить роль продажника", callback_data="role_seller")],
        [InlineKeyboardButton(text="➕ Добавить роль закупщика", callback_data="role_buyer")],
        [InlineKeyboardButton(text="⚙️ Вернуться в настройки", callback_data="back_to_settings")]
    ])


def get_combined_main_menu(user, has_active_subscription: bool) -> InlineKeyboardMarkup:
    """Комбинированное главное меню для пользователей с несколькими ролями"""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    keyboard_buttons = []
    
    # Функции продажника
    if user.has_role(UserRole.SELLER):
        keyboard_buttons.extend([
            [KeyboardButton(text="📝 Добавить блогера")],
            [KeyboardButton(text="📋 Мои блогеры")],
            [KeyboardButton(text="✏️ Редактировать блогера")]
        ])
    
    # Функции закупщика
    if user.has_role(UserRole.BUYER):
        keyboard_buttons.extend([
            [KeyboardButton(text="🔍 Поиск блогеров")],
            [KeyboardButton(text="📋 История поиска")],
            [KeyboardButton(text="📊 Статистика")]
        ])
    
    # Общие функции
    keyboard_buttons.extend([
        [KeyboardButton(text="💳 Подписка")],
        [KeyboardButton(text="⚙️ Настройки")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    ) 