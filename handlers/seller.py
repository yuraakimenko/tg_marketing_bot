import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from database.database import (
    get_user, create_blogger, get_user_bloggers, 
    get_blogger, delete_blogger, update_blogger
)
from database.models import UserRole, SubscriptionStatus, Platform, BlogCategory
from bot.keyboards import (
    get_platform_keyboard, get_category_keyboard, 
    get_yes_no_keyboard, get_blogger_list_keyboard,
    get_blogger_details_keyboard, get_price_stories_keyboard,
    get_price_post_keyboard, get_price_video_keyboard,
    get_platforms_multi_keyboard, get_blogger_success_keyboard
)
from bot.states import SellerStates

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
        reply_markup=get_platform_keyboard(),
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
        reply_markup=get_platform_keyboard(),
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
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stories_reach_min)


@router.message(SellerStates.waiting_for_stories_reach_min)
async def handle_stories_reach_min(message: Message, state: FSMContext):
    """Обработка ввода минимального охвата сторис"""
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
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_stories_reach_max)


@router.message(SellerStates.waiting_for_stories_reach_max)
async def handle_stories_reach_max(message: Message, state: FSMContext):
    """Обработка ввода максимального охвата сторис"""
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
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_reels_reach_min)


@router.message(SellerStates.waiting_for_reels_reach_min)
async def handle_reels_reach_min(message: Message, state: FSMContext):
    """Обработка ввода минимального охвата рилс"""
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
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_reels_reach_max)


@router.message(SellerStates.waiting_for_reels_reach_max)
async def handle_reels_reach_max(message: Message, state: FSMContext):
    """Обработка ввода максимального охвата рилс"""
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
        "🏷️ <b>Категории блога</b>\n\n"
        "Выберите категории (максимум 3):",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_categories)


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
        reply_markup=get_category_keyboard(),
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
            description=description
        )
        
        # Формируем полную информацию о добавленном блогере
        success_text = f"✅ <b>Блогер успешно добавлен!</b>\n\n"
        success_text += format_full_blogger_info(blogger)
        success_text += f"\n🎉 Теперь блогер доступен для поиска закупщиками."
        
        await message.answer(
            success_text,
            reply_markup=get_blogger_success_keyboard(blogger.id),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при создании блогера: {e}")
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
    
    await callback.message.edit_text(
        info_text,
        reply_markup=get_edit_blogger_keyboard(blogger.id),
        parse_mode="HTML"
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
    info_text += f"🔗 <b>Чистая ссылка:</b> {blogger.url}\n"
    
    # ===== ПОДПИСЧИКИ =====
    if blogger.subscribers_count:
        info_text += f"👥 <b>Подписчики:</b> {blogger.subscribers_count:,}\n"
    else:
        info_text += f"👥 <b>Подписчики:</b> <i>не указано</i>\n"
    
    # ===== СТАТИСТИКА ПРОФИЛЯ =====
    info_text += f"\n📊 <b>Статистика профиля:</b> <i>фотки должны быть</i>\n"
    
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