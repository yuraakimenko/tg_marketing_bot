import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import (
    get_user, create_blogger, get_user_bloggers, 
    get_blogger, delete_blogger, update_blogger
)
from database.models import UserRole, SubscriptionStatus
from bot.keyboards import (
    get_platform_keyboard, get_category_keyboard, 
    get_yes_no_keyboard, get_blogger_list_keyboard,
    get_blogger_details_keyboard
)
from bot.states import SellerStates

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "➕ Добавить блогера")
async def add_blogger_start(message: Message, state: FSMContext):
    """Начать добавление блогера"""
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    
    if user.subscription_status != SubscriptionStatus.ACTIVE:
        await message.answer(
            "❌ Для добавления блогеров необходима активная подписка.\n"
            "💳 Оформите подписку в разделе 'Подписка'."
        )
        return
    
    await message.answer(
        "➕ <b>Добавление блогера</b>\n\n"
        "Шаг 1 из 8\n"
        "📝 Введите имя блогера:",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_blogger_name)


@router.message(SellerStates.waiting_for_blogger_name)
async def process_blogger_name(message: Message, state: FSMContext):
    """Обработка имени блогера"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "Шаг 2 из 8\n"
        "🔗 Введите ссылку на блогера (канал, профиль):"
    )
    await state.set_state(SellerStates.waiting_for_blogger_url)


@router.message(SellerStates.waiting_for_blogger_url)
async def process_blogger_url(message: Message, state: FSMContext):
    """Обработка ссылки блогера"""
    await state.update_data(url=message.text)
    
    await message.answer(
        "Шаг 3 из 8\n"
        "📱 Выберите платформу блогера:",
        reply_markup=get_platform_keyboard()
    )
    await state.set_state(SellerStates.waiting_for_blogger_platform)


@router.callback_query(F.data.startswith("platform_"), SellerStates.waiting_for_blogger_platform)
async def process_blogger_platform(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора платформы"""
    platform = callback.data.split("_")[1]
    
    if platform == "other":
        await callback.answer()
        await callback.message.edit_text(
            "Шаг 3 из 8\n"
            "📱 Введите название платформы:"
        )
        return
    
    await state.update_data(platform=platform)
    await callback.answer()
    
    await callback.message.edit_text(
        "Шаг 4 из 8\n"
        "🎯 Выберите категорию блогера:",
        reply_markup=get_category_keyboard()
    )
    await state.set_state(SellerStates.waiting_for_blogger_category)


@router.callback_query(F.data.startswith("category_"), SellerStates.waiting_for_blogger_category)
async def process_blogger_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    category = callback.data.split("_", 1)[1]
    
    if category == "other":
        await callback.answer()
        await callback.message.edit_text(
            "Шаг 4 из 8\n"
            "🎯 Введите категорию блога:"
        )
        return
    
    await state.update_data(category=category)
    await callback.answer()
    
    await callback.message.edit_text(
        "Шаг 5 из 8\n"
        "👥 Опишите целевую аудиторию блогера:\n"
        "Например: 'Женщины 25-35 лет, интересующиеся здоровьем'"
    )
    await state.set_state(SellerStates.waiting_for_blogger_audience)


@router.message(SellerStates.waiting_for_blogger_audience)
async def process_blogger_audience(message: Message, state: FSMContext):
    """Обработка целевой аудитории"""
    await state.update_data(target_audience=message.text)
    
    await message.answer(
        "Шаг 6 из 8\n"
        "🗣️ Есть ли у блогера отзывы от рекламодателей?",
        reply_markup=get_yes_no_keyboard("reviews")
    )
    await state.set_state(SellerStates.waiting_for_blogger_reviews)


@router.callback_query(F.data.startswith("yes_reviews") | F.data.startswith("no_reviews"), 
                      SellerStates.waiting_for_blogger_reviews)
async def process_blogger_reviews(callback: CallbackQuery, state: FSMContext):
    """Обработка наличия отзывов"""
    has_reviews = callback.data.startswith("yes_")
    await state.update_data(has_reviews=has_reviews)
    
    await callback.answer()
    await callback.message.edit_text(
        "Шаг 7 из 8\n"
        "💰 Введите минимальную цену за рекламу (в рублях):\n"
        "Или введите '0' если цена договорная:"
    )
    await state.set_state(SellerStates.waiting_for_blogger_price_min)


@router.message(SellerStates.waiting_for_blogger_price_min)
async def process_blogger_price_min(message: Message, state: FSMContext):
    """Обработка минимальной цены"""
    try:
        price_min = int(message.text)
        await state.update_data(price_min=price_min if price_min > 0 else None)
        
        await message.answer(
            "Шаг 8 из 8\n"
            "💰 Введите максимальную цену за рекламу (в рублях):\n"
            "Или введите '0' если цена договорная:"
        )
        await state.set_state(SellerStates.waiting_for_blogger_price_max)
    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.message(SellerStates.waiting_for_blogger_price_max)
async def process_blogger_price_max(message: Message, state: FSMContext):
    """Обработка максимальной цены"""
    try:
        price_max = int(message.text)
        await state.update_data(price_max=price_max if price_max > 0 else None)
        
        await message.answer(
            "Финальный шаг!\n"
            "📝 Введите дополнительное описание блогера (необязательно):\n"
            "Или введите 'пропустить' чтобы завершить:"
        )
        await state.set_state(SellerStates.waiting_for_blogger_description)
    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.message(SellerStates.waiting_for_blogger_description)
async def process_blogger_description(message: Message, state: FSMContext):
    """Обработка описания и создание блогера"""
    description = message.text if message.text.lower() != "пропустить" else None
    
    data = await state.get_data()
    user = await get_user(message.from_user.id)
    
    # Создаем блогера
    blogger = await create_blogger(
        seller_id=user.id,
        name=data['name'],
        url=data['url'],
        platform=data['platform'],
        category=data['category'],
        target_audience=data['target_audience'],
        has_reviews=data['has_reviews'],
        price_min=data.get('price_min'),
        price_max=data.get('price_max'),
        description=description
    )
    
    await message.answer(
        f"✅ <b>Блогер успешно добавлен!</b>\n\n"
        f"📝 <b>Имя:</b> {blogger.name}\n"
        f"📱 <b>Платформа:</b> {blogger.platform}\n"
        f"🎯 <b>Категория:</b> {blogger.category}\n"
        f"👥 <b>Аудитория:</b> {blogger.target_audience}\n"
        f"🗣️ <b>Отзывы:</b> {'Есть' if blogger.has_reviews else 'Нет'}\n"
        f"💰 <b>Цена:</b> {blogger.price_min or 'Договорная'}"
        + (f" - {blogger.price_max}" if blogger.price_max else "") + " ₽",
        parse_mode="HTML"
    )
    
    await state.clear()


# === ОБРАБОТЧИКИ ДЛЯ ПРЕРЫВАНИЯ ПРОЦЕССА ДОБАВЛЕНИЯ БЛОГЕРА ===

@router.message(F.text == "📝 Мои блогеры", SellerStates())
async def interrupt_with_my_bloggers(message: Message, state: FSMContext):
    """Прерывание добавления блогера и переход к списку блогеров"""
    await state.clear()
    await show_my_bloggers(message)


@router.message(F.text == "💳 Подписка", SellerStates())
async def interrupt_with_subscription(message: Message, state: FSMContext):
    """Прерывание добавления блогера и переход к подписке"""
    await state.clear()
    await message.answer(
        "❌ Добавление блогера отменено.\n\n"
        "Переходим к разделу подписки..."
    )
    # Будет обработано в handlers/subscription.py


@router.message(F.text == "🔧 Управление подпиской", SellerStates())
async def interrupt_with_subscription_management(message: Message, state: FSMContext):
    """Прерывание добавления блогера и переход к управлению подпиской"""
    await state.clear()
    await message.answer(
        "❌ Добавление блогера отменено.\n\n"
        "Переходим к управлению подпиской..."
    )
    # Будет обработано в handlers/subscription.py


@router.message(F.text == "⚙️ Настройки", SellerStates())
async def interrupt_with_settings(message: Message, state: FSMContext):
    """Прерывание добавления блогера и переход к настройкам"""
    await state.clear()
    await message.answer(
        "❌ Добавление блогера отменено.\n\n"
        "Переходим к настройкам..."
    )
    # Будет обработано в handlers/common.py


@router.message(F.text == "📊 Статистика", SellerStates())
async def interrupt_with_statistics(message: Message, state: FSMContext):
    """Прерывание добавления блогера и переход к статистике"""
    await state.clear()
    await message.answer(
        "❌ Добавление блогера отменено.\n\n"
        "Переходим к статистике..."
    )
    # Будет обработано в handlers/subscription.py


@router.message(F.text == "➕ Добавить блогера", SellerStates())
async def restart_add_blogger(message: Message, state: FSMContext):
    """Перезапуск добавления блогера если уже в процессе"""
    await state.clear()
    await message.answer("🔄 Перезапускаем добавление блогера...")
    await add_blogger_start(message, state)


# Обработчик для команды отмены
@router.message(F.text.in_({"❌ Отмена", "/cancel", "отмена", "Отмена"}), SellerStates())
async def cancel_adding_blogger(message: Message, state: FSMContext):
    """Отмена добавления блогера"""
    await state.clear()
    await message.answer(
        "❌ Добавление блогера отменено.\n\n"
        "Вы можете начать заново или воспользоваться другими функциями."
    )


# Обработчик кнопки "Отмена" в inline клавиатурах
@router.callback_query(F.data == "cancel_action", SellerStates())
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия через inline кнопку"""
    await state.clear()
    await callback.answer("❌ Действие отменено")
    await callback.message.edit_text(
        "❌ Добавление блогера отменено.\n\n"
        "Вы можете начать заново или воспользоваться другими функциями."
    )


@router.message(F.text == "📝 Мои блогеры")
async def show_my_bloggers(message: Message):
    """Показать список блогеров пользователя"""
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    
    bloggers = await get_user_bloggers(user.id)
    
    if not bloggers:
        await message.answer(
            "📝 У вас пока нет добавленных блогеров.\n"
            "Используйте кнопку 'Добавить блогера' для начала."
        )
        return
    
    await message.answer(
        f"📝 <b>Ваши блогеры ({len(bloggers)}):</b>\n\n"
        "Выберите блогера для просмотра деталей:",
        reply_markup=get_blogger_list_keyboard(bloggers),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("blogger_"))
async def show_blogger_details(callback: CallbackQuery):
    """Показать детали блогера"""
    blogger_id = int(callback.data.split("_")[1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    # Проверяем, что это блогер текущего пользователя
    user = await get_user(callback.from_user.id)
    if not user or blogger.seller_id != user.id:
        await callback.answer("❌ Нет доступа к этому блогеру")
        return
    
    details_text = (
        f"📝 <b>Детали блогера</b>\n\n"
        f"👤 <b>Имя:</b> {blogger.name}\n"
        f"🔗 <b>Ссылка:</b> {blogger.url}\n"
        f"📱 <b>Платформа:</b> {blogger.platform}\n"
        f"🎯 <b>Категория:</b> {blogger.category}\n"
        f"👥 <b>Аудитория:</b> {blogger.target_audience}\n"
        f"🗣️ <b>Отзывы:</b> {'Есть' if blogger.has_reviews else 'Нет'}\n"
        f"💰 <b>Цена:</b> {blogger.price_min or 'Договорная'}"
        + (f" - {blogger.price_max}" if blogger.price_max else "") + " ₽\n"
        f"📅 <b>Добавлен:</b> {blogger.created_at.strftime('%d.%m.%Y')}"
    )
    
    if blogger.description:
        details_text += f"\n📝 <b>Описание:</b> {blogger.description}"
    
    await callback.answer()
    await callback.message.edit_text(
        details_text,
        reply_markup=get_blogger_details_keyboard(blogger_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_blogger_"))
async def confirm_delete_blogger(callback: CallbackQuery):
    """Подтвердить удаление блогера"""
    blogger_id = int(callback.data.split("_")[2])
    
    await callback.answer()
    await callback.message.edit_text(
        "🗑️ Вы уверены, что хотите удалить этого блогера?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_yes_no_keyboard(f"delete_confirm_{blogger_id}")
    )


@router.callback_query(F.data.startswith("yes_delete_confirm_"))
async def delete_blogger_confirmed(callback: CallbackQuery):
    """Удалить блогера после подтверждения"""
    blogger_id = int(callback.data.split("_")[3])
    user = await get_user(callback.from_user.id)
    
    success = await delete_blogger(blogger_id, user.id)
    
    if success:
        await callback.answer("✅ Блогер удален")
        await callback.message.edit_text("✅ Блогер успешно удален из базы.")
    else:
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data.startswith("no_delete_confirm_"))
async def cancel_delete_blogger(callback: CallbackQuery):
    """Отменить удаление блогера"""
    await callback.answer("Удаление отменено")
    await callback.message.edit_text("❌ Удаление отменено.")


@router.callback_query(F.data == "back_to_bloggers")
async def back_to_bloggers_list(callback: CallbackQuery):
    """Вернуться к списку блогеров"""
    user = await get_user(callback.from_user.id)
    bloggers = await get_user_bloggers(user.id)
    
    await callback.answer()
    await callback.message.edit_text(
        f"📝 <b>Ваши блогеры ({len(bloggers)}):</b>\n\n"
        "Выберите блогера для просмотра деталей:",
        reply_markup=get_blogger_list_keyboard(bloggers),
        parse_mode="HTML"
    )


# === ОБРАБОТЧИКИ ДЛЯ РЕДАКТИРОВАНИЯ БЛОГЕРА ===

@router.callback_query(F.data.startswith("edit_blogger_"))
async def start_edit_blogger(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование блогера"""
    blogger_id = int(callback.data.split("_")[2])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    # Проверяем, что это блогер текущего пользователя
    user = await get_user(callback.from_user.id)
    if not user or blogger.seller_id != user.id:
        await callback.answer("❌ Нет доступа к этому блогеру")
        return
    
    # Сохраняем ID блогера в состояние
    await state.update_data(editing_blogger_id=blogger_id)
    await state.set_state(SellerStates.editing_blogger)
    
    edit_menu = (
        f"✏️ <b>Редактирование блогера: {blogger.name}</b>\n\n"
        "Выберите, что хотите изменить:\n\n"
        "1️⃣ Имя блогера\n"
        "2️⃣ Ссылка на блогера\n"
        "3️⃣ Платформа\n"
        "4️⃣ Категория\n"
        "5️⃣ Целевая аудитория\n"
        "6️⃣ Минимальная цена\n"
        "7️⃣ Максимальная цена\n"
        "8️⃣ Описание\n\n"
        "Введите номер поля (1-8) или 'отмена' для выхода:"
    )
    
    await callback.answer()
    await callback.message.edit_text(edit_menu, parse_mode="HTML")


@router.message(SellerStates.editing_blogger)
async def process_edit_field_selection(message: Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    
    if message.text.lower() in ['отмена', 'cancel', '/cancel']:
        await state.clear()
        await message.answer("❌ Редактирование отменено.")
        return
    
    # Маппинг номеров на поля
    field_mapping = {
        '1': ('name', 'имя блогера'),
        '2': ('url', 'ссылку на блогера'),
        '3': ('platform', 'платформу'),
        '4': ('category', 'категорию'),
        '5': ('target_audience', 'целевую аудиторию'),
        '6': ('price_min', 'минимальную цену'),
        '7': ('price_max', 'максимальную цену'),
        '8': ('description', 'описание')
    }
    
    if message.text not in field_mapping:
        await message.answer(
            "❌ Неверный выбор. Введите номер от 1 до 8 или 'отмена'."
        )
        return
    
    field_name, field_display = field_mapping[message.text]
    
    # Получаем текущие данные блогера
    blogger = await get_blogger(blogger_id)
    current_value = getattr(blogger, field_name)
    
    await state.update_data(editing_field=field_name)
    await state.set_state(SellerStates.waiting_for_new_value)
    
    await message.answer(
        f"✏️ <b>Редактирование: {field_display}</b>\n\n"
        f"Текущее значение: {current_value or 'Не указано'}\n\n"
        "Введите новое значение или 'отмена' для выхода:"
    )


@router.message(SellerStates.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    """Обработка нового значения поля"""
    if message.text.lower() in ['отмена', 'cancel', '/cancel']:
        await state.clear()
        await message.answer("❌ Редактирование отменено.")
        return
    
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    field_name = data.get('editing_field')
    new_value = message.text
    
    # Специальная обработка для цен
    if field_name in ['price_min', 'price_max']:
        try:
            new_value = int(new_value) if new_value != '0' else None
        except ValueError:
            await message.answer("❌ Введите корректное число или '0' для договорной цены.")
            return
    
    # Обновляем блогера в базе данных
    user = await get_user(message.from_user.id)
    success = await update_blogger(blogger_id, user.id, **{field_name: new_value})
    
    if success:
        await message.answer("✅ Поле успешно обновлено!")
        
        # Показываем обновленные детали блогера
        blogger = await get_blogger(blogger_id)
        details_text = (
            f"📝 <b>Обновленные детали блогера</b>\n\n"
            f"👤 <b>Имя:</b> {blogger.name}\n"
            f"🔗 <b>Ссылка:</b> {blogger.url}\n"
            f"📱 <b>Платформа:</b> {blogger.platform}\n"
            f"🎯 <b>Категория:</b> {blogger.category}\n"
            f"👥 <b>Аудитория:</b> {blogger.target_audience}\n"
            f"🗣️ <b>Отзывы:</b> {'Есть' if blogger.has_reviews else 'Нет'}\n"
            f"💰 <b>Цена:</b> {blogger.price_min or 'Договорная'}"
            + (f" - {blogger.price_max}" if blogger.price_max else "") + " ₽\n"
            f"📅 <b>Добавлен:</b> {blogger.created_at.strftime('%d.%m.%Y')}"
        )
        
        if blogger.description:
            details_text += f"\n📝 <b>Описание:</b> {blogger.description}"
        
        await message.answer(
            details_text,
            reply_markup=get_blogger_details_keyboard(blogger_id),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка при обновлении данных.")
    
    await state.clear() 