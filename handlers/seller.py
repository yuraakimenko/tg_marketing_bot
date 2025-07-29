import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.database import (
    get_user, create_blogger, get_user_bloggers, 
    get_blogger, delete_blogger, update_blogger
)
from database.models import UserRole, SubscriptionStatus, Platform, BlogCategory
from utils.google_sheets import log_blogger_action_to_sheets
from bot.keyboards import (
    get_platform_keyboard, get_category_keyboard, 
    get_yes_no_keyboard, get_blogger_list_keyboard,
    get_blogger_details_keyboard, get_price_stories_keyboard,
    get_price_post_keyboard, get_price_video_keyboard,
    get_platforms_multi_keyboard, get_blogger_success_keyboard,
    get_blogger_addition_navigation_with_back,
    get_blogger_addition_navigation_first_step,
    get_blogger_edit_field_keyboard,
    get_blogger_success_keyboard_enhanced,
    get_delete_confirmation_keyboard,
    get_edit_blogger_keyboard
)
from bot.states import SellerStates
from typing import Union

router = Router()
logger = logging.getLogger(__name__)


# === ОБРАБОТЧИКИ ОСНОВНОГО МЕНЮ ПРОДАЖНИКА ===

@router.message(F.text == "📝 Добавить блогера", StateFilter("*"))
async def universal_add_blogger(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе данных.\n\nИспользуйте /start для регистрации.")
        return
    
    # АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ: если у пользователя нет ролей
    if not user.roles:
        logger.warning(f"У пользователя {message.from_user.id} нет ролей! Автоматически добавляем роль SELLER")
        from database.database import add_user_role
        success = await add_user_role(message.from_user.id, UserRole.SELLER)
        
        if success:
            # Перезагружаем пользователя с новой ролью
            user = await get_user(message.from_user.id)
            logger.info(f"✅ Роль SELLER автоматически добавлена пользователю {message.from_user.id}")
            await message.answer("✅ Роль продажника добавлена автоматически!\n\nТеперь вы можете добавлять блогеров.")
        else:
            logger.error(f"❌ Не удалось автоматически добавить роль пользователю {message.from_user.id}")
            await message.answer("❌ Проблема с ролями пользователя.\n\nИспользуйте /start для переназначения роли.")
            return
    
    if not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.\n\nИспользуйте ⚙️ Настройки → Сменить роль для добавления роли продажника.")
        return
    
    # Проверяем подписку
    has_active_subscription = user.subscription_status in [
        SubscriptionStatus.ACTIVE, 
        SubscriptionStatus.AUTO_RENEWAL_OFF, 
        SubscriptionStatus.CANCELLED
    ]
    
    if not has_active_subscription:
        await message.answer(
            "💳 <b>Требуется подписка</b>\n\n"
            "Для добавления блогеров необходима активная подписка.\n"
            "Стоимость: 500₽/мес\n\n"
            "Оформите подписку в разделе 💳 Подписка",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        "📝 <b>Добавление блогера</b>\n\n"
        "Давайте добавим нового блогера в базу данных.\n\n"
        "🎯 <b>Шаг 1:</b> Выберите платформу:",
        reply_markup=get_platform_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_platform)


@router.message(F.text == "📋 Мои блогеры", StateFilter("*"))
async def universal_my_bloggers(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе данных.\n\nИспользуйте /start для регистрации.")
        return
    
    # АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ: если у пользователя нет ролей
    if not user.roles:
        from database.database import add_user_role
        success = await add_user_role(message.from_user.id, UserRole.SELLER)
        if success:
            user = await get_user(message.from_user.id)
            await message.answer("✅ Роль продажника добавлена автоматически!")
    
    if not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.\n\nИспользуйте ⚙️ Настройки → Сменить роль для добавления роли продажника.")
        return
    
    bloggers = await get_user_bloggers(user.id)
    
    if not bloggers:
        await message.answer(
            "📋 <b>Мои блогеры</b>\n\n"
            "У вас пока нет добавленных блогеров.\n\n"
            "Добавьте первого блогера, используя кнопку 📝 Добавить блогера",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        f"📋 <b>Мои блогеры</b>\n\n"
        f"Найдено блогеров: {len(bloggers)}\n\n"
        "Выберите блогера для просмотра:",
        reply_markup=get_blogger_list_keyboard(bloggers),
        parse_mode="HTML"
    )


@router.message(F.text == "✏️ Редактировать блогера", StateFilter("*"))
async def universal_edit_blogger(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе данных.\n\nИспользуйте /start для регистрации.")
        return
    
    # АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ: если у пользователя нет ролей
    if not user.roles:
        from database.database import add_user_role
        success = await add_user_role(message.from_user.id, UserRole.SELLER)
        if success:
            user = await get_user(message.from_user.id)
            await message.answer("✅ Роль продажника добавлена автоматически!")
    
    if not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.\n\nИспользуйте ⚙️ Настройки → Сменить роль для добавления роли продажника.")
        return
    
    bloggers = await get_user_bloggers(user.id)
    
    if not bloggers:
        await message.answer(
            "✏️ <b>Редактирование блогера</b>\n\n"
            "У вас пока нет добавленных блогеров.\n\n"
            "Добавьте первого блогера, используя кнопку 📝 Добавить блогера",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        f"✏️ <b>Редактирование блогера</b>\n\n"
        f"Найдено блогеров: {len(bloggers)}\n\n"
        "Выберите блогера для редактирования:",
        reply_markup=get_blogger_list_keyboard(bloggers, action="edit"),
        parse_mode="HTML"
    )


# === ОБРАБОТЧИКИ ДОБАВЛЕНИЯ БЛОГЕРА ===

@router.callback_query(F.data.startswith("platform_"))
async def handle_platform_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка множественного выбора платформ"""
    platform_str = callback.data.split("_")[1]
    platform = Platform(platform_str)
    
    data = await state.get_data()
    platforms = data.get('platforms', [])
    
    if platform in platforms:
        # Убираем платформу
        platforms.remove(platform)
        await callback.answer(f"❌ Платформа '{platform.value}' убрана")
    else:
        # Добавляем платформу
        platforms.append(platform)
        await callback.answer(f"✅ Платформа '{platform.value}' добавлена")
    
    await state.update_data(platforms=platforms)
    
    # Обновляем сообщение
    platforms_text = ", ".join([p.value for p in platforms]) if platforms else "Не выбрано"
    
    await callback.message.edit_text(
        f"🎯 <b>Шаг 1:</b> Выберите платформы\n\n"
        f"Выбранные платформы: <b>{platforms_text}</b>\n\n"
        f"Выберите платформы для блогера:",
        reply_markup=get_platform_keyboard(with_navigation=True),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_platforms")
async def confirm_platforms(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора платформ"""
    data = await state.get_data()
    platforms = data.get('platforms', [])
    
    if not platforms:
        await callback.answer("❌ Выберите хотя бы одну платформу")
        return
    
    await callback.answer()
    
    # Устанавливаем основную платформу для совместимости
    main_platform = platforms[0].value
    await state.update_data(platform=main_platform)
    
    await callback.message.edit_text(
        f"🎯 <b>Шаг 2:</b> Введите ссылку на профиль блогера\n\n"
        f"Выбранные платформы: <b>{', '.join([p.value for p in platforms])}</b>\n\n"
        "Примеры ссылок:\n"
        "• Instagram: https://instagram.com/username\n"
        "• YouTube: https://youtube.com/@channel\n"
        "• TikTok: https://tiktok.com/@username\n"
        "• Telegram: https://t.me/username\n"
        "• VK: https://vk.com/username",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_blogger_url)


@router.message(SellerStates.waiting_for_blogger_url)
async def handle_blogger_url(message: Message, state: FSMContext):
    """Обработка ввода ссылки на блогера"""
    url = message.text.strip()
    
    # Расширенная валидация URL
    if not url.startswith(('http://', 'https://')):
        await message.answer(
            "❌ <b>Неверный формат ссылки</b>\n\n"
            "Ссылка должна начинаться с http:// или https://\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    # Получаем выбранные платформы для валидации
    data = await state.get_data()
    platforms = data.get('platforms', [])
    
    # Валидация для конкретных платформ
    platform_validation = {
        'instagram': ['instagram.com/', 'www.instagram.com/'],
        'youtube': ['youtube.com/', 'www.youtube.com/', 'youtu.be/'],
        'tiktok': ['tiktok.com/', 'www.tiktok.com/'],
        'telegram': ['t.me/', 'telegram.me/'],
        'vk': ['vk.com/', 'www.vk.com/', 'm.vk.com/']
    }
    
    # Проверяем URL для хотя бы одной из выбранных платформ
    url_valid = False
    for platform in platforms:
        platform_key = platform.value.lower()
        if platform_key in platform_validation:
            valid_domains = platform_validation[platform_key]
            if any(domain in url.lower() for domain in valid_domains):
                url_valid = True
                break
    
    if platforms and not url_valid:
        platform_names = {
            'instagram': 'Instagram',
            'youtube': 'YouTube', 
            'tiktok': 'TikTok',
            'telegram': 'Telegram',
            'vk': 'VK'
        }
        platform_list = [platform_names.get(p.value.lower(), p.value) for p in platforms]
        await message.answer(
            f"❌ <b>Неверная ссылка для выбранных платформ</b>\n\n"
            f"Выбранные платформы: {', '.join(platform_list)}\n"
            f"URL должен соответствовать одной из выбранных платформ.\n\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(blogger_url=url)
    
    await message.answer(
        "🎯 <b>Шаг 3:</b> Введите имя блогера\n\n"
        "Укажите имя или никнейм блогера:",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_blogger_name)


@router.message(SellerStates.waiting_for_blogger_name)
async def handle_blogger_name(message: Message, state: FSMContext):
    """Обработка ввода имени блогера"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            "❌ <b>Слишком короткое имя</b>\n\n"
            "Имя должно содержать минимум 2 символа.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(blogger_name=name)
    
    # Переходим к статистике
    await message.answer(
        "📊 <b>Статистика блогера</b>\n\n"
        "Укажите количество подписчиков:",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_subscribers_count)


@router.message(SellerStates.waiting_for_subscribers_count)
async def handle_subscribers_count(message: Message, state: FSMContext):
    """Обработка ввода количества подписчиков"""
    try:
        count = int(message.text.strip().replace(',', '').replace(' ', ''))
        if count < 0:
            raise ValueError("Negative count")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число подписчиков (например: 15000).\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(subscribers_count=count)
    
    await message.answer(
        "📖 <b>Охват сторис</b>\n\n"
        "Укажите МИНИМАЛЬНЫЙ охват сторис:\n\n"
        "💡 <b>Важно:</b> Указывайте именно ОХВАТЫ, а не просмотры!",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stories_reach_min)


@router.message(SellerStates.waiting_for_stories_reach_min, F.text)
async def handle_stories_reach_min(message: Message, state: FSMContext):
    """Обработка ввода минимального охвата сторис при добавлении нового блогера"""
    # Проверяем, редактируем ли мы существующего блогера
    data = await state.get_data()
    if 'editing_blogger_id' in data:
        # Это редактирование - передаем управление соответствующему обработчику
        return await handle_edit_stories_reach_min(message, state)
    
    # Это добавление нового блогера
    try:
        reach = int(message.text.strip().replace(',', '').replace(' ', ''))
        if reach < 0:
            raise ValueError("Negative reach")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число минимального охвата сторис.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(stories_reach_min=reach)
    
    await message.answer(
        f"📖 <b>Охват сторис</b>\n\n"
        f"Укажите МАКСИМАЛЬНЫЙ охват сторис:\n\n"
        f"Уже указано: Минимальный охват: {reach:,}",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stories_reach_max)


@router.message(SellerStates.waiting_for_stories_reach_max, F.text)
async def handle_stories_reach_max(message: Message, state: FSMContext):
    """Обработка ввода максимального охвата сторис при добавлении нового блогера"""
    # Проверяем, редактируем ли мы существующего блогера
    data = await state.get_data()
    if 'editing_blogger_id' in data:
        # Это редактирование - передаем управление соответствующему обработчику
        return await handle_edit_stories_reach_max(message, state)
    
    # Это добавление нового блогера
    try:
        reach = int(message.text.strip().replace(',', '').replace(' ', ''))
        if reach < 0:
            raise ValueError("Negative reach")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число максимального охвата сторис.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    min_reach = data.get('stories_reach_min', 0)
    
    if reach < min_reach:
        await message.answer(
            f"❌ <b>Неверное значение</b>\n\n"
            f"Максимальный охват не может быть меньше минимального.\n"
            f"Минимальный охват: {min_reach:,}\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(stories_reach_max=reach)
    
    await message.answer(
        "💰 <b>Цена на 4 истории</b>\n\n"
        "Укажите цену за 4 истории в рублях:",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_stories)


@router.message(SellerStates.waiting_for_price_stories)
async def handle_price_stories(message: Message, state: FSMContext):
    """Обработка ввода цены за 4 истории"""
    try:
        price = int(message.text.strip().replace(',', '').replace(' ', ''))
        if price < 0:
            raise ValueError("Negative price")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите цену в рублях (например: 5000).\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price_stories=price)
    
    await message.answer(
        "🎬 <b>Охват рилс</b>\n\n"
        "Укажите МИНИМАЛЬНЫЙ охват рилс:\n\n"
        "💡 <b>Важно:</b> Указывайте именно ОХВАТЫ, а не просмотры!",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_reels_reach_min)


@router.message(SellerStates.waiting_for_reels_reach_min, F.text)
async def handle_reels_reach_min(message: Message, state: FSMContext):
    """Обработка ввода минимального охвата рилс при добавлении нового блогера"""
    # Проверяем, редактируем ли мы существующего блогера
    data = await state.get_data()
    if 'editing_blogger_id' in data:
        # Это редактирование - передаем управление соответствующему обработчику
        return await handle_edit_reels_reach_min(message, state)
    
    # Это добавление нового блогера
    try:
        reach = int(message.text.strip().replace(',', '').replace(' ', ''))
        if reach < 0:
            raise ValueError("Negative reach")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число минимального охвата рилс.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(reels_reach_min=reach)
    
    await message.answer(
        f"🎬 <b>Охват рилс</b>\n\n"
        f"Укажите МАКСИМАЛЬНЫЙ охват рилс:\n\n"
        f"Уже указано: Минимальный охват: {reach:,}",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_reels_reach_max)


@router.message(SellerStates.waiting_for_reels_reach_max, F.text)
async def handle_reels_reach_max(message: Message, state: FSMContext):
    """Обработка ввода максимального охвата рилс при добавлении нового блогера"""
    # Проверяем, редактируем ли мы существующего блогера
    data = await state.get_data()
    if 'editing_blogger_id' in data:
        # Это редактирование - передаем управление соответствующему обработчику
        return await handle_edit_reels_reach_max(message, state)
    
    # Это добавление нового блогера
    try:
        reach = int(message.text.strip().replace(',', '').replace(' ', ''))
        if reach < 0:
            raise ValueError("Negative reach")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число максимального охвата рилс.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    min_reach = data.get('reels_reach_min', 0)
    
    if reach < min_reach:
        await message.answer(
            f"❌ <b>Неверное значение</b>\n\n"
            f"Максимальный охват не может быть меньше минимального.\n"
            f"Минимальный охват: {min_reach:,}\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(reels_reach_max=reach)
    
    await message.answer(
        "💸 <b>Цена рилс</b>\n\n"
        "Укажите цену за рилс в рублях:",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_reels)


@router.message(SellerStates.waiting_for_price_reels)
async def handle_price_reels(message: Message, state: FSMContext):
    """Обработка ввода цены за рилс"""
    try:
        price = int(message.text.strip().replace(',', '').replace(' ', ''))
        if price < 0:
            raise ValueError("Negative price")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите цену в рублях (например: 8000).\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price_reels=price)
    
    await message.answer(
        "📊 <b>Статистика профиля</b>\n\n"
        "Загрузите скриншоты статистики вашего блога (охваты, аудитория и т.д.).\n"
        "Вы можете отправить несколько фото.\n\n"
        "Когда закончите, нажмите кнопку 'Готово' или напишите 'готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="stats_photos_done")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_price_reels")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stats_photos)


@router.message(SellerStates.waiting_for_stats_photos, F.photo)
async def handle_stats_photo(message: Message, state: FSMContext):
    """Обработка загрузки фото статистики"""
    data = await state.get_data()
    stats_photos = data.get('stats_photos', [])
    
    # Получаем file_id самого большого размера фото
    photo = message.photo[-1]
    stats_photos.append(photo.file_id)
    
    await state.update_data(stats_photos=stats_photos)
    
    # Проверяем, редактируем ли мы существующего блогера
    if 'editing_blogger_id' in data:
        blogger_id = data['editing_blogger_id']
        
        # Отправляем одно сообщение с обновленной информацией
        await message.answer(
            f"📊 <b>Статистика профиля</b>\n\n"
            f"✅ Фото добавлено (всего: {len(stats_photos)})\n\n"
            f"Отправьте еще фото или нажмите 'Готово':",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="edit_stats_photos_done")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_blogger_fields_{blogger_id}")]
            ]),
            parse_mode="HTML"
        )
    else:
        # Это добавление нового блогера
        await message.answer(
            f"📊 <b>Статистика профиля</b>\n\n"
            f"✅ Фото добавлено (всего: {len(stats_photos)})\n\n"
            f"Отправьте еще фото или нажмите 'Готово':",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="stats_photos_done")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_price_reels")]
            ]),
            parse_mode="HTML"
        )


@router.message(SellerStates.waiting_for_stats_photos, F.text.lower() == "готово")
@router.callback_query(F.data == "stats_photos_done", SellerStates.waiting_for_stats_photos)
async def finish_stats_photos(update: Union[Message, CallbackQuery], state: FSMContext):
    """Завершение загрузки фото статистики"""
    if isinstance(update, CallbackQuery):
        await update.answer()
        message = update.message
    else:
        message = update
    
    data = await state.get_data()
    stats_photos = data.get('stats_photos', [])
    
    if not stats_photos:
        text = "⚠️ Вы не загрузили ни одного фото статистики.\n\nПродолжить без фото?"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_without_stats")],
            [InlineKeyboardButton(text="📷 Загрузить фото", callback_data="back_to_stats_upload")]
        ])
        
        if isinstance(update, CallbackQuery):
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Отправляем фотографии и запрашиваем подтверждение
        await send_stats_photos_for_confirmation(message, stats_photos, state)


async def send_stats_photos_for_confirmation(message, stats_photos, state):
    """Отправка загруженных фотографий для подтверждения"""
    # Продублируем сообщение один раз
    await message.answer(
        f"📊 <b>Статистика профиля</b>\n\n"
        f"✅ Фото добавлено (всего: {len(stats_photos)})\n\n"
        f"Отправьте еще фото или нажмите 'Готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="stats_photos_done")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_price_reels")]
        ]),
        parse_mode="HTML"
    )
    
    # Отправляем все загруженные фотографии
    for i, photo_id in enumerate(stats_photos):
        try:
            caption = f"📊 Фото статистики {i+1} из {len(stats_photos)}"
            await message.answer_photo(
                photo=photo_id,
                caption=caption
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото статистики {i+1}: {e}")
            await message.answer(f"❌ Не удалось загрузить фото {i+1}")
    
    # Запрашиваем подтверждение
    await message.answer(
        f"📸 <b>Подтверждение фотографий</b>\n\n"
        f"Вы загрузили {len(stats_photos)} фото статистики.\n\n"
        f"<b>Добавляем именно эти фото или нужно что-то исправить?</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавляем эти фото", callback_data="confirm_stats_photos")],
            [InlineKeyboardButton(text="🔄 Исправить фото", callback_data="retry_stats_photos")]
        ]),
        parse_mode="HTML"
    )
    
    # Переходим в состояние подтверждения
    await state.set_state(SellerStates.waiting_for_stats_photos_confirmation)


@router.callback_query(F.data == "continue_without_stats", SellerStates.waiting_for_stats_photos)
async def continue_without_stats(callback: CallbackQuery, state: FSMContext):
    """Продолжить без фото статистики"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🏷️ <b>Категории блога</b>\n\n"
        "Выберите категории (максимум 3):",
        reply_markup=get_category_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_categories)


@router.callback_query(F.data == "back_to_stats_upload", SellerStates.waiting_for_stats_photos)
async def back_to_stats_upload(callback: CallbackQuery):
    """Вернуться к загрузке фото"""
    await callback.answer()
    await callback.message.edit_text(
        "📊 <b>Статистика профиля</b>\n\n"
        "Загрузите скриншоты статистики вашего блога (охваты, аудитория и т.д.).\n"
        "Вы можете отправить несколько фото.\n\n"
        "Когда закончите, нажмите кнопку 'Готово' или напишите 'готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="stats_photos_done")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_price_reels")]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_price_reels")
async def back_to_price_reels(callback: CallbackQuery, state: FSMContext):
    """Вернуться к вводу цены рилс"""
    await callback.answer()
    await callback.message.edit_text(
        "💸 <b>Цена за рилс</b>\n\n"
        "Укажите цену за один рилс в рублях:",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_reels)


@router.callback_query(F.data.startswith("category_"), SellerStates.waiting_for_categories)
async def handle_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категорий"""
    category_str = callback.data.split("_")[1]
    category = BlogCategory(category_str)
    
    data = await state.get_data()
    categories = data.get('categories', [])
    
    if category in categories:
        # Убираем категорию
        categories.remove(category)
        await callback.answer(f"❌ Категория '{category.get_russian_name()}' убрана")
    else:
        # Добавляем категорию
        if len(categories) >= 3:
            await callback.answer("❌ Максимум 3 категории")
            return
        categories.append(category)
        await callback.answer(f"✅ Категория '{category.get_russian_name()}' добавлена")
    
    await state.update_data(categories=categories)
    
    # Обновляем сообщение
    categories_text = ", ".join([cat.get_russian_name() for cat in categories]) if categories else "Не выбрано"
    
    await callback.message.edit_text(
        f"🏷️ <b>Категории блога</b>\n\n"
        f"Выбранные категории: <b>{categories_text}</b>\n\n"
        f"Выберите категории (максимум 3):",
        reply_markup=get_category_keyboard(with_navigation=True),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_categories", SellerStates.waiting_for_categories)
async def confirm_categories(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора категорий"""
    data = await state.get_data()
    categories = data.get('categories', [])
    
    if not categories:
        await callback.answer("❌ Выберите хотя бы одну категорию")
        return
    
    await callback.answer()
    
    await callback.message.edit_text(
        "📄 <b>Описание блогера</b>\n\n"
        "Напишите краткое описание блогера (или напишите 'пропустить'):",
        reply_markup=get_blogger_addition_navigation_with_back(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_blogger_description)


@router.message(SellerStates.waiting_for_blogger_description)
async def handle_blogger_description(message: Message, state: FSMContext):
    """Обработка ввода описания блогера"""
    description = message.text.strip()
    
    if description.lower() in ['пропустить', 'skip', 'нет', 'no']:
        description = None
    
    await state.update_data(description=description)
    
    # Создаем блогера
    data = await state.get_data()
    user = await get_user(message.from_user.id)
    
    # Проверяем пользователя
    if not user:
        logger.error(f"Пользователь не найден: {message.from_user.id}")
        await message.answer(
            "❌ <b>Ошибка пользователя</b>\n\n"
            "Пользователь не найден в базе данных.\n"
            "Попробуйте выполнить /start для регистрации.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    if not user.id:
        logger.error(f"User ID равно None для пользователя: {message.from_user.id}")
        await message.answer(
            "❌ <b>Ошибка данных пользователя</b>\n\n"
            "Проблема с данными пользователя в базе.\n"
            "Обратитесь в поддержку.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Проверяем обязательные данные
    required_fields = ['blogger_name', 'blogger_url', 'platforms', 'categories']
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
            logger.error(f"Отсутствует поле: {field}, данные: {data.get(field)}")
    
    if missing_fields:
        logger.error(f"Отсутствуют обязательные поля: {missing_fields}")
        await message.answer(
            "❌ <b>Недостаточно данных</b>\n\n"
            "Некоторые обязательные поля не заполнены.\n"
            "Начните процесс добавления блогера заново.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    try:
        logger.info(f"Создание блогера для пользователя {user.id} с данными: {data}")
        logger.info(f"Платформы: {data.get('platforms')}, тип: {type(data.get('platforms'))}")
        logger.info(f"Категории: {data.get('categories')}, тип: {type(data.get('categories'))}")
        
        blogger = await create_blogger(
            seller_id=user.id,
            name=data['blogger_name'],
            url=data['blogger_url'],
            platforms=data['platforms'],
            categories=data['categories'],
            price_stories=data.get('price_stories'),
            price_reels=data.get('price_reels'),
            subscribers_count=data.get('subscribers_count'),
            stories_reach_min=data.get('stories_reach_min'),
            stories_reach_max=data.get('stories_reach_max'),
            reels_reach_min=data.get('reels_reach_min'),
            reels_reach_max=data.get('reels_reach_max'),
            stats_images=data.get('stats_photos', []),
            description=description
        )
        
        # Формируем полную информацию о добавленном блогере
        success_text = f"✅ <b>Блогер успешно добавлен!</b>\n\n"
        success_text += format_full_blogger_info(blogger)
        success_text += f"\n🎉 Теперь блогер доступен для поиска закупщиками."
        
        await message.answer(
            success_text,
            reply_markup=get_blogger_success_keyboard_enhanced(blogger.id),
            parse_mode="HTML"
        )
        
        # Логируем в Google Sheets
        try:
            user_data = {
                'username': user.username,
                'role': 'SELLER',
                'telegram_id': user.telegram_id
            }
            
            blogger_data = {
                'name': blogger.name,
                'url': blogger.url,
                'platforms': blogger.platforms,
                'categories': blogger.categories,
                'subscribers_count': blogger.subscribers_count,
                'price_stories': blogger.price_stories,
                'price_reels': blogger.price_reels,
                'audience_13_17_percent': blogger.audience_13_17_percent,
                'audience_18_24_percent': blogger.audience_18_24_percent,
                'audience_25_35_percent': blogger.audience_25_35_percent
            }
            
            await log_blogger_action_to_sheets(user_data, blogger_data, "add")
            logger.info(f"✅ Данные блогера {blogger.id} записаны в Google Sheets")
        except Exception as e:
            logger.error(f"❌ Ошибка при записи в Google Sheets: {e}")
        
        await state.clear()
        
    except Exception as e:
        import traceback
        logger.error(f"Ошибка при создании блогера: {e}")
        logger.error(f"Полный traceback: {traceback.format_exc()}")
        await message.answer(
            "❌ <b>Ошибка при создании блогера</b>\n\n"
            "Произошла ошибка при сохранении данных.\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            parse_mode="HTML"
        )
        await state.clear()


# === УПРАВЛЕНИЕ БЛОГЕРАМИ ===

@router.message(F.text == "👥 Мои блогеры", StateFilter("*"))
async def show_my_bloggers(message: Message, state: FSMContext):
    """Показать список блогеров пользователя"""
    await state.clear()
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе данных.")
        return
    
    bloggers = await get_user_bloggers(user.id)
    
    if not bloggers:
        await message.answer(
            "📝 <b>У вас пока нет блогеров</b>\n\n"
            "Добавьте первого блогера с помощью кнопки '📝 Добавить блогера'",
            parse_mode="HTML"
        )
        return
    
    for blogger in bloggers:
        info_text = f"📝 <b>Блогер #{blogger.id}</b>\n\n"
        info_text += format_full_blogger_info(blogger)
        
        await message.answer(
            info_text,
            reply_markup=get_blogger_management_keyboard(blogger.id),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("edit_blogger_"))
async def handle_edit_blogger(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования блогера"""
    # Проверяем, какой именно callback пришел
    if callback.data.startswith("edit_blogger_fields_"):
        # Это кнопка "Изменить поля" - передаем управление соответствующему обработчику
        return await handle_edit_blogger_fields(callback, state)
    
    # Это основная кнопка редактирования
    blogger_id = int(callback.data.split("_")[2])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if blogger.seller_id != user.id:
        await callback.answer("❌ Это не ваш блогер")
        return
    
    await callback.answer()
    
    info_text = f"✏️ <b>Редактирование блогера</b>\n\n"
    info_text += format_full_blogger_info(blogger)
    info_text += f"\n\nВыберите, что хотите изменить:"
    
    # Удаляем исходное сообщение и отправляем новое с фото
    await callback.message.delete()
    await send_blogger_info_with_photos(
        callback.message, 
        blogger, 
        info_text, 
        get_edit_blogger_keyboard(blogger.id)
    )


@router.callback_query(F.data.startswith("delete_blogger_"))
async def handle_delete_blogger(callback: CallbackQuery):
    """Удаление блогера"""
    blogger_id = int(callback.data.split("_")[2])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if blogger.seller_id != user.id:
        await callback.answer("❌ Это не ваш блогер")
        return
    
    await callback.answer()
    
    await callback.message.edit_text(
        f"❗ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить блогера:\n"
        f"<b>{blogger.name}</b> ({blogger.url})\n\n"
        f"⚠️ <b>Это действие нельзя отменить!</b>",
        reply_markup=get_delete_confirmation_keyboard(blogger.id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def handle_confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления блогера"""
    blogger_id = int(callback.data.split("_")[2])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if blogger.seller_id != user.id:
        await callback.answer("❌ Это не ваш блогер")
        return
    
    from database.database import delete_blogger
    success = await delete_blogger(blogger_id)
    
    if success:
        # Логируем удаление в Google Sheets
        try:
            user_data = {
                'username': user.username,
                'role': 'SELLER',
                'telegram_id': user.telegram_id
            }
            
            blogger_data = {
                'name': blogger.name,
                'url': blogger.url,
                'platforms': blogger.platforms,
                'categories': blogger.categories,
                'subscribers_count': blogger.subscribers_count,
                'price_stories': blogger.price_stories,
                'price_reels': blogger.price_reels,
                'audience_13_17_percent': blogger.audience_13_17_percent,
                'audience_18_24_percent': blogger.audience_18_24_percent,
                'audience_25_35_percent': blogger.audience_25_35_percent
            }
            
            await log_blogger_action_to_sheets(user_data, blogger_data, "delete")
            logger.info(f"✅ Удаление блогера {blogger.id} записано в Google Sheets")
        except Exception as e:
            logger.error(f"❌ Ошибка при записи удаления в Google Sheets: {e}")
        
        await callback.answer("✅ Блогер удален")
        await callback.message.edit_text(
            f"✅ <b>Блогер удален</b>\n\n"
            f"Блогер <b>{blogger.name}</b> успешно удален из базы данных.",
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка удаления")
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось удалить блогера. Попробуйте еще раз.",
            parse_mode="HTML"
        )


def format_full_blogger_info(blogger) -> str:
    """Формирование информации о блогере согласно новому ТЗ"""
    info_text = f"👤 <b>Имя:</b> {blogger.name}\n"
    
    # Определяем текст для ссылки в зависимости от количества URL (если несколько разделены запятой)
    urls = blogger.url.split(',') if ',' in blogger.url else [blogger.url]
    link_text = "Ссылки на соцсети" if len(urls) > 1 else "Ссылка на соцсети"
    info_text += f"🔗 <b>{link_text}:</b> {blogger.url}\n"
    
    # ===== ПОДПИСЧИКИ =====
    if blogger.subscribers_count:
        info_text += f"👥 <b>Подписчики:</b> {blogger.subscribers_count:,}\n"
    else:
        info_text += f"👥 <b>Подписчики:</b> <i>не указано</i>\n"
    
    # ===== СТАТИСТИКА ПРОФИЛЯ =====
    if blogger.stats_images and len(blogger.stats_images) > 0:
        # Добавляем проверку типа данных
        if isinstance(blogger.stats_images, str):
            try:
                import json
                stats_images_list = json.loads(blogger.stats_images)
                if stats_images_list and len(stats_images_list) > 0:
                    info_text += f"\n📊 <b>Статистика профиля:</b> <i>фото загружены ({len(stats_images_list)} шт.)</i>\n"
                else:
                    info_text += f"\n📊 <b>Статистика профиля:</b> <i>фото не загружены</i>\n"
            except:
                info_text += f"\n📊 <b>Статистика профиля:</b> <i>фото не загружены</i>\n"
        else:
            info_text += f"\n📊 <b>Статистика профиля:</b> <i>фото загружены ({len(blogger.stats_images)} шт.)</i>\n"
    else:
        info_text += f"\n📊 <b>Статистика профиля:</b> <i>фото не загружены</i>\n"
    
    # ===== ОХВАТ СТОРИС (ВИЛКА) =====
    if blogger.stories_reach_min and blogger.stories_reach_max:
        info_text += f"📖 <b>Средний охват сторис:</b> {blogger.stories_reach_min:,} - {blogger.stories_reach_max:,}\n"
    elif blogger.stories_reach_min or blogger.stories_reach_max:
        reach = blogger.stories_reach_min or blogger.stories_reach_max
        info_text += f"📖 <b>Средний охват сторис:</b> ~{reach:,}\n"
    else:
        info_text += f"📖 <b>Средний охват сторис:</b> <i>не указано</i>\n"
    
    # ===== ЦЕНА НА 4 ИСТОРИИ =====
    if blogger.price_stories:
        info_text += f"💰 <b>Цена на 4 истории:</b> {blogger.price_stories:,}₽\n"
    else:
        info_text += f"💰 <b>Цена на 4 истории:</b> <i>не указано</i>\n"
    
    # ===== ОХВАТ РИЛС (ВИЛКА) =====
    if blogger.reels_reach_min and blogger.reels_reach_max:
        info_text += f"🎬 <b>Средний охват рилс:</b> {blogger.reels_reach_min:,} - {blogger.reels_reach_max:,}\n"
    elif blogger.reels_reach_min or blogger.reels_reach_max:
        reach = blogger.reels_reach_min or blogger.reels_reach_max
        info_text += f"🎬 <b>Средний охват рилс:</b> ~{reach:,}\n"
    else:
        info_text += f"🎬 <b>Средний охват рилс:</b> <i>не указано</i>\n"
    
    # ===== ЦЕНА РИЛС =====
    if blogger.price_reels:
        info_text += f"💸 <b>Цена рилс:</b> {blogger.price_reels:,}₽\n"
    else:
        info_text += f"💸 <b>Цена рилс:</b> <i>не указано</i>\n"
    
    # ===== ОПИСАНИЕ (если есть) =====
    if blogger.description and blogger.description.strip():
        info_text += f"\n📄 <b>Описание:</b>\n<i>{blogger.description}</i>\n"
    
    return info_text


def get_blogger_stats_images(blogger) -> list:
    """Получение списка фото статистики блогера"""
    if not blogger.stats_images:
        return []
    
    if isinstance(blogger.stats_images, str):
        try:
            import json
            return json.loads(blogger.stats_images)
        except:
            return []
    else:
        return blogger.stats_images


async def send_blogger_info_with_photos(message, blogger, info_text, reply_markup=None):
    """Отправка информации о блогере с фото статистики"""
    stats_images = get_blogger_stats_images(blogger)
    
    if not stats_images:
        # Если нет фото, отправляем только текст
        await message.answer(
            info_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    # Если есть фото, отправляем первое фото с текстом
    try:
        await message.answer_photo(
            photo=stats_images[0],
            caption=info_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Отправляем остальные фото без подписей
        for i in range(1, len(stats_images)):
            try:
                await message.answer_photo(
                    photo=stats_images[i],
                    caption=f"📊 Фото статистики {i+1} из {len(stats_images)}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке фото статистики {i+1}: {e}")
                await message.answer(f"❌ Не удалось загрузить фото {i+1}")
                
    except Exception as e:
        logger.error(f"Ошибка при отправке основного фото статистики: {e}")
        # Если не удалось отправить с фото, отправляем только текст
        await message.answer(
            info_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        ) 

# === ОБРАБОТЧИКИ НАВИГАЦИИ ===

@router.callback_query(F.data == "blogger_cancel")
async def handle_blogger_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления блогера"""
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        "❌ <b>Добавление блогера отменено</b>\n\n"
        "Вы можете начать заново или вернуться в главное меню.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "blogger_back")
async def handle_blogger_back(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему шагу"""
    await callback.answer()
    
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == SellerStates.waiting_for_blogger_url.state:
        # Возврат к выбору платформ
        platforms = data.get('platforms', [])
        platforms_text = ", ".join([p.value for p in platforms]) if platforms else "Не выбрано"
        
        await callback.message.edit_text(
            f"🎯 <b>Шаг 1:</b> Выберите платформы\n\n"
            f"Выбранные платформы: <b>{platforms_text}</b>\n\n"
            f"Выберите платформы для блогера:",
            reply_markup=get_platform_keyboard(with_navigation=True),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_platform)
        
    elif current_state == SellerStates.waiting_for_blogger_name.state:
        # Возврат к вводу URL
        platforms = data.get('platforms', [])
        await callback.message.edit_text(
            f"🎯 <b>Шаг 2:</b> Введите ссылку на профиль блогера\n\n"
            f"Выбранные платформы: <b>{', '.join([p.value for p in platforms])}</b>\n\n"
            "Примеры ссылок:\n"
            "• Instagram: https://instagram.com/username\n"
            "• YouTube: https://youtube.com/@channel\n"
            "• TikTok: https://tiktok.com/@username\n"
            "• Telegram: https://t.me/username\n"
            "• VK: https://vk.com/username",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_blogger_url)
        
    elif current_state == SellerStates.waiting_for_subscribers_count.state:
        # Возврат к вводу имени
        await callback.message.edit_text(
            "🎯 <b>Шаг 3:</b> Введите имя блогера\n\n"
            "Укажите имя или никнейм блогера:",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_blogger_name)
        
    elif current_state == SellerStates.waiting_for_stories_reach_min.state:
        # Возврат к вводу подписчиков
        await callback.message.edit_text(
            "📊 <b>Статистика блогера</b>\n\n"
            "Укажите количество подписчиков:",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_subscribers_count)
        
    elif current_state == SellerStates.waiting_for_stories_reach_max.state:
        # Возврат к вводу минимального охвата сторис
        await callback.message.edit_text(
            "📖 <b>Охват сторис</b>\n\n"
            "Укажите МИНИМАЛЬНЫЙ охват сторис:\n\n"
            "💡 <b>Важно:</b> Указывайте именно ОХВАТЫ, а не просмотры!",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_stories_reach_min)
        
    elif current_state == SellerStates.waiting_for_price_stories.state:
        # Возврат к вводу максимального охвата сторис
        reach_min = data.get('stories_reach_min', 0)
        await callback.message.edit_text(
            f"📖 <b>Охват сторис</b>\n\n"
            f"Укажите МАКСИМАЛЬНЫЙ охват сторис:\n\n"
            f"Уже указано: Минимальный охват: {reach_min:,}",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_stories_reach_max)
        
    elif current_state == SellerStates.waiting_for_reels_reach_min.state:
        # Возврат к вводу цены сторис
        await callback.message.edit_text(
            "💰 <b>Цена на 4 истории</b>\n\n"
            "Укажите цену за 4 истории в рублях:",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_price_stories)
        
    elif current_state == SellerStates.waiting_for_reels_reach_max.state:
        # Возврат к вводу минимального охвата рилс
        await callback.message.edit_text(
            "🎬 <b>Охват рилс</b>\n\n"
            "Укажите МИНИМАЛЬНЫЙ охват рилс:\n\n"
            "💡 <b>Важно:</b> Указывайте именно ОХВАТЫ, а не просмотры!",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_reels_reach_min)
        
    elif current_state == SellerStates.waiting_for_price_reels.state:
        # Возврат к вводу максимального охвата рилс
        reach_min = data.get('reels_reach_min', 0)
        await callback.message.edit_text(
            f"🎬 <b>Охват рилс</b>\n\n"
            f"Укажите МАКСИМАЛЬНЫЙ охват рилс:\n\n"
            f"Уже указано: Минимальный охват: {reach_min:,}",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_reels_reach_max)
        
    elif current_state == SellerStates.waiting_for_categories.state:
        # Возврат к вводу цены рилс
        await callback.message.edit_text(
            "💸 <b>Цена рилс</b>\n\n"
            "Укажите цену за рилс в рублях:",
            reply_markup=get_blogger_addition_navigation_with_back(),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_price_reels)
        
    elif current_state == SellerStates.waiting_for_blogger_description.state:
        # Возврат к выбору категорий
        categories = data.get('categories', [])
        categories_text = ", ".join([cat.get_russian_name() for cat in categories]) if categories else "Не выбрано"
        
        await callback.message.edit_text(
            f"🏷️ <b>Категории блога</b>\n\n"
            f"Выбранные категории: <b>{categories_text}</b>\n\n"
            f"Выберите категории (максимум 3):",
            reply_markup=get_category_keyboard(with_navigation=True),
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_categories)
        
    else:
        # Если состояние неизвестно, отменяем
        await handle_blogger_cancel(callback, state)


# === БЛОКИРОВКА ДРУГИХ ФУНКЦИЙ ===

@router.message(F.text.in_(["👥 Мои блогеры", "✏️ Редактировать блогера"]), StateFilter(SellerStates))
async def block_during_addition(message: Message, state: FSMContext):
    """Блокировка других функций во время добавления блогера"""
    current_state = await state.get_state()
    if current_state and "waiting_for" in current_state:
        await message.answer(
            "⚠️ <b>Добавление блогера в процессе</b>\n\n"
            "Завершите добавление текущего блогера или нажмите 'Отменить' для доступа к другим функциям.",
            parse_mode="HTML"
        )


# === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ПОЛЕЙ ===

@router.callback_query(F.data.startswith("edit_blogger_fields_"))
async def handle_edit_blogger_fields(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования полей блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if blogger.seller_id != user.id:
        await callback.answer("❌ Это не ваш блогер")
        return
    
    await callback.answer()
    
    info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
    info_text += format_full_blogger_info(blogger)
    info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
    
    # Удаляем исходное сообщение и отправляем новое с фото
    await callback.message.delete()
    await send_blogger_info_with_photos(
        callback.message, 
        blogger, 
        info_text, 
        get_blogger_edit_field_keyboard(blogger.id)
    )


@router.callback_query(F.data == "edit_blogger_done")
async def handle_edit_blogger_done(callback: CallbackQuery):
    """Завершение редактирования блогера"""
    await callback.answer("✅ Редактирование завершено")
    await callback.message.delete()


@router.callback_query(F.data.startswith("view_stats_photos_"))
async def handle_view_stats_photos(callback: CallbackQuery):
    """Просмотр фото статистики блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    
    # Проверяем и преобразуем stats_images если нужно
    stats_images = blogger.stats_images
    if isinstance(stats_images, str):
        try:
            import json
            stats_images = json.loads(stats_images)
        except:
            stats_images = []
    
    if not stats_images or len(stats_images) == 0:
        await callback.message.answer(
            "📊 <b>Статистика профиля</b>\n\n"
            "У этого блогера нет загруженных фото статистики.",
            parse_mode="HTML"
        )
        return
    
    # Отправляем фото статистики
    await callback.message.answer(
        f"📊 <b>Статистика профиля блогера {blogger.name}</b>\n\n"
        f"Всего фото: {len(stats_images)}",
        parse_mode="HTML"
    )
    
    # Отправляем каждое фото
    for i, photo_id in enumerate(stats_images, 1):
        try:
            await callback.message.answer_photo(
                photo=photo_id,
                caption=f"Фото {i} из {len(stats_images)}"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото статистики: {e}")
            await callback.message.answer(f"❌ Не удалось загрузить фото {i}")


@router.callback_query(F.data.startswith("edit_field_stats_photos_"))
async def handle_edit_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Редактирование фото статистики"""
    blogger_id = int(callback.data.split("_")[-1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    
    # Сохраняем ID блогера для обновления
    await state.update_data(editing_blogger_id=blogger_id, stats_photos=[])
    
    # Проверяем и преобразуем stats_images если нужно
    stats_images = blogger.stats_images
    if isinstance(stats_images, str):
        try:
            import json
            stats_images = json.loads(stats_images)
        except:
            stats_images = []
    
    text = "📊 <b>Редактирование фото статистики</b>\n\n"
    if stats_images and len(stats_images) > 0:
        text += f"Текущие фото: {len(stats_images)} шт.\n\n"
        text += "⚠️ Загрузка новых фото заменит все существующие!\n\n"
    
    text += "Загрузите новые скриншоты статистики.\n"
    text += "Когда закончите, нажмите кнопку 'Готово':"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="edit_stats_photos_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_blogger_fields_{blogger_id}")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stats_photos)


@router.callback_query(F.data == "edit_stats_photos_done")
async def finish_edit_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Завершение редактирования фото статистики"""
    await callback.answer()
    
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    stats_photos = data.get('stats_photos', [])
    
    if not blogger_id:
        await callback.message.edit_text("❌ Ошибка: не найден ID блогера")
        return
    
    if not stats_photos:
        # Если нет фото, сразу обновляем блогера
        success = await update_blogger(blogger_id, stats_images=[])
        
        if success:
            await callback.message.edit_text(
                "✅ <b>Фото статистики удалены!</b>",
                parse_mode="HTML"
            )
            
            # Очищаем состояние
            await state.clear()
            
            # Показываем обновленную информацию о блогере
            blogger = await get_blogger(blogger_id)
            if blogger:
                info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
                info_text += format_full_blogger_info(blogger)
                info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
                
                await send_blogger_info_with_photos(
                    callback.message, 
                    blogger, 
                    info_text, 
                    get_blogger_edit_field_keyboard(blogger.id)
                )
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка обновления</b>\n\n"
                "Не удалось обновить фото статистики.",
                parse_mode="HTML"
            )
    else:
        # Отправляем фотографии для подтверждения
        await send_edit_stats_photos_for_confirmation(callback.message, stats_photos, state, blogger_id)


async def send_edit_stats_photos_for_confirmation(message, stats_photos, state, blogger_id):
    """Отправка загруженных фотографий для подтверждения при редактировании"""
    # Продублируем сообщение один раз
    await message.answer(
        f"📊 <b>Статистика профиля</b>\n\n"
        f"✅ Фото добавлено (всего: {len(stats_photos)})\n\n"
        f"Отправьте еще фото или нажмите 'Готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="edit_stats_photos_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_blogger_fields_{blogger_id}")]
        ]),
        parse_mode="HTML"
    )
    
    # Отправляем все загруженные фотографии
    for i, photo_id in enumerate(stats_photos):
        try:
            caption = f"📊 Фото статистики {i+1} из {len(stats_photos)}"
            await message.answer_photo(
                photo=photo_id,
                caption=caption
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото статистики {i+1}: {e}")
            await message.answer(f"❌ Не удалось загрузить фото {i+1}")
    
    # Запрашиваем подтверждение
    await message.answer(
        f"📸 <b>Подтверждение фотографий</b>\n\n"
        f"Вы загрузили {len(stats_photos)} фото статистики.\n\n"
        f"<b>Обновляем именно эти фото или нужно что-то исправить?</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Обновляем эти фото", callback_data="confirm_edit_stats_photos")],
            [InlineKeyboardButton(text="🔄 Исправить фото", callback_data="retry_edit_stats_photos")]
        ]),
        parse_mode="HTML"
    )
    
    # Переходим в состояние подтверждения
    await state.set_state(SellerStates.waiting_for_stats_photos_confirmation)


@router.callback_query(F.data == "add_another_blogger")
async def handle_add_another_blogger(callback: CallbackQuery, state: FSMContext):
    """Добавить еще одного блогера"""
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        "📝 <b>Добавление блогера</b>\n\n"
        "Давайте добавим нового блогера в базу данных.\n\n"
        "🎯 <b>Шаг 1:</b> Выберите платформу:",
        reply_markup=get_platform_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_platform)


@router.callback_query(F.data == "show_my_bloggers")
async def handle_show_my_bloggers_callback(callback: CallbackQuery, state: FSMContext):
    """Показать всех блогеров пользователя"""
    await callback.answer()
    await state.clear()
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден в базе данных.")
        return
    
    bloggers = await get_user_bloggers(user.id)
    
    if not bloggers:
        await callback.message.edit_text(
            "📝 <b>У вас пока нет блогеров</b>\n\n"
            "Добавьте первого блогера с помощью кнопки '📝 Добавить блогера'",
            parse_mode="HTML"
        )
        return
    
    # Удаляем исходное сообщение и отправляем новые
    bot = callback.bot  # Сохраняем ссылку на бота
    chat_id = callback.message.chat.id  # Сохраняем ID чата
    await callback.message.delete()
    
    for blogger in bloggers:
        info_text = f"📝 <b>Блогер #{blogger.id}</b>\n\n"
        info_text += format_full_blogger_info(blogger)
        
        # Временная клавиатура управления
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        management_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_blogger_fields_{blogger.id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_blogger_{blogger.id}")
            ]
        ])
        
        # Создаем временный объект сообщения для передачи в функцию
        temp_message = type('TempMessage', (), {
            'answer': lambda text, reply_markup=None, parse_mode=None: bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode),
            'answer_photo': lambda photo, caption=None, reply_markup=None, parse_mode=None: bot.send_photo(chat_id, photo, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        })()
        
        await send_blogger_info_with_photos(
            temp_message, 
            blogger, 
            info_text, 
            management_keyboard
        )

# === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ОТДЕЛЬНЫХ ПОЛЕЙ ===

@router.callback_query(F.data.startswith("edit_field_name_"))
async def handle_edit_field_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование имени блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="name")
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование имени</b>\n\n"
        f"Текущее имя: <b>{blogger.name}</b>\n\n"
        f"Отправьте новое имя блогера:",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


@router.callback_query(F.data.startswith("edit_field_url_"))
async def handle_edit_field_url(callback: CallbackQuery, state: FSMContext):
    """Редактирование ссылки блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="url")
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование ссылки</b>\n\n"
        f"Текущая ссылка: <b>{blogger.url}</b>\n\n"
        f"Отправьте новую ссылку на профиль блогера:",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


@router.callback_query(F.data.startswith("edit_field_platforms_"))
async def handle_edit_field_platforms(callback: CallbackQuery, state: FSMContext):
    """Редактирование платформ блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="platforms")
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование платформ</b>\n\n"
        f"Текущие платформы: <b>{blogger.platforms}</b>\n\n"
        f"Выберите новые платформы:",
        reply_markup=get_platform_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_platform)


@router.callback_query(F.data.startswith("edit_field_categories_"))
async def handle_edit_field_categories(callback: CallbackQuery, state: FSMContext):
    """Редактирование категорий блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="categories")
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование категорий</b>\n\n"
        f"Текущие категории: <b>{blogger.categories}</b>\n\n"
        f"Выберите новые категории (максимум 3):",
        reply_markup=get_category_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_categories)


@router.callback_query(F.data.startswith("edit_field_subscribers_"))
async def handle_edit_field_subscribers(callback: CallbackQuery, state: FSMContext):
    """Редактирование количества подписчиков"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="subscribers_count")
    
    current_count = blogger.subscribers_count or "не указано"
    await callback.message.edit_text(
        f"✏️ <b>Редактирование количества подписчиков</b>\n\n"
        f"Текущее количество: <b>{current_count}</b>\n\n"
        f"Отправьте новое количество подписчиков (только число):",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


@router.callback_query(F.data.startswith("edit_field_stories_reach_"))
async def handle_edit_field_stories_reach(callback: CallbackQuery, state: FSMContext):
    """Редактирование охвата сторис"""
    blogger_id = int(callback.data.split("_")[-1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="stories_reach")
    
    current_min = blogger.stories_reach_min or "не указано"
    current_max = blogger.stories_reach_max or "не указано"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование охвата сторис</b>\n\n"
        f"Текущий охват: <b>{current_min} - {current_max}</b>\n\n"
        f"Отправьте минимальный охват сторис (только число):",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stories_reach_min)


@router.callback_query(F.data.startswith("edit_field_price_stories_"))
async def handle_edit_field_price_stories(callback: CallbackQuery, state: FSMContext):
    """Редактирование цены сторис"""
    blogger_id = int(callback.data.split("_")[-1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="price_stories")
    
    current_price = blogger.price_stories or "не указано"
    await callback.message.edit_text(
        f"✏️ <b>Редактирование цены сторис</b>\n\n"
        f"Текущая цена: <b>{current_price}</b>\n\n"
        f"Отправьте новую цену за 4 истории (только число):",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


@router.callback_query(F.data.startswith("edit_field_reels_reach_"))
async def handle_edit_field_reels_reach(callback: CallbackQuery, state: FSMContext):
    """Редактирование охвата рилс"""
    blogger_id = int(callback.data.split("_")[-1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="reels_reach")
    
    current_min = blogger.reels_reach_min or "не указано"
    current_max = blogger.reels_reach_max or "не указано"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование охвата рилс</b>\n\n"
        f"Текущий охват: <b>{current_min} - {current_max}</b>\n\n"
        f"Отправьте минимальный охват рилс (только число):",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_reels_reach_min)


@router.callback_query(F.data.startswith("edit_field_price_reels_"))
async def handle_edit_field_price_reels(callback: CallbackQuery, state: FSMContext):
    """Редактирование цены рилс"""
    blogger_id = int(callback.data.split("_")[-1])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="price_reels")
    
    current_price = blogger.price_reels or "не указано"
    await callback.message.edit_text(
        f"✏️ <b>Редактирование цены рилс</b>\n\n"
        f"Текущая цена: <b>{current_price}</b>\n\n"
        f"Отправьте новую цену за рилс (только число):",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


@router.callback_query(F.data.startswith("edit_field_description_"))
async def handle_edit_field_description(callback: CallbackQuery, state: FSMContext):
    """Редактирование описания блогера"""
    blogger_id = int(callback.data.split("_")[3])
    blogger = await get_blogger(blogger_id)
    
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await callback.answer()
    await state.update_data(editing_blogger_id=blogger_id, editing_field="description")
    
    current_desc = blogger.description or "не указано"
    await callback.message.edit_text(
        f"✏️ <b>Редактирование описания</b>\n\n"
        f"Текущее описание: <b>{current_desc}</b>\n\n"
        f"Отправьте новое описание блогера:",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_new_value)


# === ОБРАБОТЧИК НОВЫХ ЗНАЧЕНИЙ ===

@router.message(SellerStates.waiting_for_new_value)
async def handle_new_value(message: Message, state: FSMContext):
    """Обработка нового значения для редактируемого поля"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    editing_field = data.get('editing_field')
    
    if not blogger_id or not editing_field:
        await message.answer("❌ Ошибка: не найдены данные для редактирования")
        await state.clear()
        return
    
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await message.answer("❌ Блогер не найден")
        await state.clear()
        return
    
    # Обновляем соответствующее поле
    update_data = {}
    
    if editing_field == "name":
        update_data["name"] = message.text
    elif editing_field == "url":
        update_data["url"] = message.text
    elif editing_field == "subscribers_count":
        try:
            subscribers = int(message.text.replace(',', '').replace(' ', ''))
            update_data["subscribers_count"] = subscribers
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число")
            return
    elif editing_field == "price_stories":
        try:
            price = int(message.text.replace(',', '').replace(' ', ''))
            update_data["price_stories"] = price
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число")
            return
    elif editing_field == "price_reels":
        try:
            price = int(message.text.replace(',', '').replace(' ', ''))
            update_data["price_reels"] = price
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число")
            return
    elif editing_field == "description":
        update_data["description"] = message.text
    
    # Обновляем блогера
    from database.database import update_blogger
    success = await update_blogger(blogger_id, **update_data)
    
    if success:
        await message.answer(
            f"✅ <b>Поле обновлено!</b>\n\n"
            f"Поле '{editing_field}' успешно изменено.",
            parse_mode="HTML"
        )
        
        # Показываем обновленную информацию о блогере
        updated_blogger = await get_blogger(blogger_id)
        if updated_blogger:
            info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
            info_text += format_full_blogger_info(updated_blogger)
            info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
            
            await send_blogger_info_with_photos(
                message, 
                updated_blogger, 
                info_text, 
                get_blogger_edit_field_keyboard(blogger_id)
            )
    else:
        await message.answer("❌ Ошибка при обновлении поля")
    
    await state.clear()


# === ОБРАБОТЧИКИ ДЛЯ РЕДАКТИРОВАНИЯ ОХВАТОВ ===

async def handle_edit_stories_reach_min(message: Message, state: FSMContext):
    """Обработка минимального охвата сторис при редактировании"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    
    if not blogger_id:
        await message.answer("❌ Ошибка: не найден ID блогера")
        await state.clear()
        return
    
    try:
        min_reach = int(message.text.replace(',', '').replace(' ', ''))
        await state.update_data(stories_reach_min=min_reach)
        
        await message.answer(
            f"✅ Минимальный охват сторис: <b>{min_reach:,}</b>\n\n"
            f"Теперь отправьте максимальный охват сторис (только число):",
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_stories_reach_max)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")


async def handle_edit_stories_reach_max(message: Message, state: FSMContext):
    """Обработка максимального охвата сторис при редактировании"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    min_reach = data.get('stories_reach_min')
    
    if not blogger_id or min_reach is None:
        await message.answer("❌ Ошибка: не найдены данные для редактирования")
        await state.clear()
        return
    
    try:
        max_reach = int(message.text.replace(',', '').replace(' ', ''))
        
        if max_reach < min_reach:
            await message.answer("❌ Максимальный охват не может быть меньше минимального")
            return
        
        # Обновляем блогера
        from database.database import update_blogger
        success = await update_blogger(blogger_id, stories_reach_min=min_reach, stories_reach_max=max_reach)
        
        if success:
            await message.answer(
                f"✅ <b>Охват сторис обновлен!</b>\n\n"
                f"Минимальный: <b>{min_reach:,}</b>\n"
                f"Максимальный: <b>{max_reach:,}</b>",
                parse_mode="HTML"
            )
            
            # Показываем обновленную информацию о блогере
            updated_blogger = await get_blogger(blogger_id)
            if updated_blogger:
                info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
                info_text += format_full_blogger_info(updated_blogger)
                info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
                
                await send_blogger_info_with_photos(
                    message, 
                    updated_blogger, 
                    info_text, 
                    get_blogger_edit_field_keyboard(blogger_id)
                )
        else:
            await message.answer("❌ Ошибка при обновлении охвата сторис")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")


async def handle_edit_reels_reach_min(message: Message, state: FSMContext):
    """Обработка минимального охвата рилс при редактировании"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    
    if not blogger_id:
        await message.answer("❌ Ошибка: не найден ID блогера")
        await state.clear()
        return
    
    try:
        min_reach = int(message.text.replace(',', '').replace(' ', ''))
        await state.update_data(reels_reach_min=min_reach)
        
        await message.answer(
            f"✅ Минимальный охват рилс: <b>{min_reach:,}</b>\n\n"
            f"Теперь отправьте максимальный охват рилс (только число):",
            parse_mode="HTML"
        )
        await state.set_state(SellerStates.waiting_for_reels_reach_max)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")


async def handle_edit_reels_reach_max(message: Message, state: FSMContext):
    """Обработка максимального охвата рилс при редактировании"""
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    min_reach = data.get('reels_reach_min')
    
    if not blogger_id or min_reach is None:
        await message.answer("❌ Ошибка: не найдены данные для редактирования")
        await state.clear()
        return
    
    try:
        max_reach = int(message.text.replace(',', '').replace(' ', ''))
        
        if max_reach < min_reach:
            await message.answer("❌ Максимальный охват не может быть меньше минимального")
            return
        
        # Обновляем блогера
        from database.database import update_blogger
        success = await update_blogger(blogger_id, reels_reach_min=min_reach, reels_reach_max=max_reach)
        
        if success:
            await message.answer(
                f"✅ <b>Охват рилс обновлен!</b>\n\n"
                f"Минимальный: <b>{min_reach:,}</b>\n"
                f"Максимальный: <b>{max_reach:,}</b>",
                parse_mode="HTML"
            )
            
            # Показываем обновленную информацию о блогере
            updated_blogger = await get_blogger(blogger_id)
            if updated_blogger:
                info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
                info_text += format_full_blogger_info(updated_blogger)
                info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
                
                await send_blogger_info_with_photos(
                    message, 
                    updated_blogger, 
                    info_text, 
                    get_blogger_edit_field_keyboard(blogger_id)
                )
        else:
            await message.answer("❌ Ошибка при обновлении охвата рилс")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")


@router.callback_query(F.data == "confirm_stats_photos", SellerStates.waiting_for_stats_photos_confirmation)
async def confirm_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Подтверждение загруженных фотографий"""
    await callback.answer()
    
    await callback.message.edit_text(
        f"✅ <b>Фотографии подтверждены!</b>\n\n"
        f"Переходим к следующему шагу...",
        parse_mode="HTML"
    )
    
    # Переходим к категориям
    await callback.message.answer(
        "🏷️ <b>Категории блога</b>\n\n"
        "Выберите категории (максимум 3):",
        reply_markup=get_category_keyboard(with_navigation=True),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_categories)


@router.callback_query(F.data == "retry_stats_photos", SellerStates.waiting_for_stats_photos_confirmation)
async def retry_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Повторная загрузка фотографий"""
    await callback.answer()
    
    # Очищаем загруженные фотографии
    await state.update_data(stats_photos=[])
    
    await callback.message.edit_text(
        "📊 <b>Статистика профиля</b>\n\n"
        "Загрузите скриншоты статистики вашего блога (охваты, аудитория и т.д.).\n"
        "Вы можете отправить несколько фото.\n\n"
        "Когда закончите, нажмите кнопку 'Готово' или напишите 'готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="stats_photos_done")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_price_reels")]
        ]),
        parse_mode="HTML"
    )
    
    # Возвращаемся к состоянию загрузки фотографий
    await state.set_state(SellerStates.waiting_for_stats_photos)


@router.callback_query(F.data == "confirm_edit_stats_photos", SellerStates.waiting_for_stats_photos_confirmation)
async def confirm_edit_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Подтверждение загруженных фотографий при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    stats_photos = data.get('stats_photos', [])
    
    if not blogger_id:
        await callback.message.edit_text("❌ Ошибка: не найден ID блогера")
        return
    
    # Обновляем блогера
    success = await update_blogger(blogger_id, stats_images=stats_photos)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Фото статистики обновлены!</b>\n\n"
            f"Загружено фото: {len(stats_photos)}",
            parse_mode="HTML"
        )
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем обновленную информацию о блогере
        blogger = await get_blogger(blogger_id)
        if blogger:
            info_text = f"✏️ <b>Редактирование полей блогера</b>\n\n"
            info_text += format_full_blogger_info(blogger)
            info_text += f"\n\n<b>Выберите поле для редактирования:</b>"
            
            await send_blogger_info_with_photos(
                callback.message, 
                blogger, 
                info_text, 
                get_blogger_edit_field_keyboard(blogger.id)
            )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка обновления</b>\n\n"
            "Не удалось обновить фото статистики.",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "retry_edit_stats_photos", SellerStates.waiting_for_stats_photos_confirmation)
async def retry_edit_stats_photos(callback: CallbackQuery, state: FSMContext):
    """Повторная загрузка фотографий при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    blogger_id = data.get('editing_blogger_id')
    
    if not blogger_id:
        await callback.message.edit_text("❌ Ошибка: не найден ID блогера")
        return
    
    # Очищаем загруженные фотографии
    await state.update_data(stats_photos=[])
    
    await callback.message.edit_text(
        "📊 <b>Редактирование фото статистики</b>\n\n"
        "Загрузите новые скриншоты статистики.\n"
        "Когда закончите, нажмите кнопку 'Готово':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="edit_stats_photos_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_blogger_fields_{blogger_id}")]
        ]),
        parse_mode="HTML"
    )
    
    # Возвращаемся к состоянию загрузки фотографий
    await state.set_state(SellerStates.waiting_for_stats_photos)