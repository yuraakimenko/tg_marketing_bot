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
    get_platforms_multi_keyboard # добавлен импорт
)
from bot.states import SellerStates

router = Router()
logger = logging.getLogger(__name__)


# === ОБРАБОТЧИКИ ОСНОВНОГО МЕНЮ ПРОДАЖНИКА ===

@router.message(F.text == "📝 Добавить блогера", StateFilter("*"))
async def universal_add_blogger(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.")
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
    if not user or not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.")
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
    if not user or not user.has_role(UserRole.SELLER):
        await message.answer("❌ Эта функция доступна только продажникам.")
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
    
    # Переходим к демографии
    await message.answer(
        "📊 <b>Демография аудитории</b>\n\n"
        "Укажите процент аудитории в возрасте 13-17 лет:\n\n"
        "💡 <b>Важно:</b> Сумма всех возрастных категорий должна равняться 100%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_audience_13_17)


@router.message(SellerStates.waiting_for_audience_13_17)
async def handle_audience_13_17(message: Message, state: FSMContext):
    """Обработка ввода процента аудитории 13-17 лет"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(audience_13_17_percent=percent)
    
    await message.answer(
        f"📊 Укажите процент аудитории в возрасте 18-24 лет:\n\n"
        f"Уже указано: 13-17 лет: {percent}%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_audience_18_24)


@router.message(SellerStates.waiting_for_audience_18_24)
async def handle_audience_18_24(message: Message, state: FSMContext):
    """Обработка ввода процента аудитории 18-24 лет"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(audience_18_24_percent=percent)
    
    data = await state.get_data()
    total = data.get('audience_13_17_percent', 0) + percent
    
    await message.answer(
        f"📊 Укажите процент аудитории в возрасте 25-35 лет:\n\n"
        f"Уже указано: 13-17 лет: {data.get('audience_13_17_percent', 0)}%, "
        f"18-24 лет: {percent}%\n"
        f"Всего: {total}%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_audience_25_35)


@router.message(SellerStates.waiting_for_audience_25_35)
async def handle_audience_25_35(message: Message, state: FSMContext):
    """Обработка ввода процента аудитории 25-35 лет"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(audience_25_35_percent=percent)
    
    data = await state.get_data()
    total = (data.get('audience_13_17_percent', 0) + 
             data.get('audience_18_24_percent', 0) + percent)
    
    await message.answer(
        f"📊 Укажите процент аудитории в возрасте 35+ лет:\n\n"
        f"Уже указано: 13-17 лет: {data.get('audience_13_17_percent', 0)}%, "
        f"18-24 лет: {data.get('audience_18_24_percent', 0)}%, "
        f"25-35 лет: {percent}%\n"
        f"Всего: {total}%\n\n"
        f"Осталось указать: {100 - total}%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_audience_35_plus)


@router.message(SellerStates.waiting_for_audience_35_plus)
async def handle_audience_35_plus(message: Message, state: FSMContext):
    """Обработка ввода процента аудитории 35+ лет"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    total = (data.get('audience_13_17_percent', 0) + 
             data.get('audience_18_24_percent', 0) + 
             data.get('audience_25_35_percent', 0) + percent)
    
    if total != 100:
        await message.answer(
            f"❌ <b>Неверная сумма процентов</b>\n\n"
            f"Сумма всех возрастных категорий должна равняться 100%.\n"
            f"Текущая сумма: {total}%\n\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(audience_35_plus_percent=percent)
    
    await message.answer(
        "👥 <b>Пол аудитории</b>\n\n"
        "Укажите процент женской аудитории:\n\n"
        "💡 <b>Важно:</b> Сумма мужской и женской аудитории должна равняться 100%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_female_percent)


@router.message(SellerStates.waiting_for_female_percent)
async def handle_female_percent(message: Message, state: FSMContext):
    """Обработка ввода процента женской аудитории"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(female_percent=percent)
    
    await message.answer(
        f"👥 Укажите процент мужской аудитории:\n\n"
        f"Уже указано: Женская аудитория: {percent}%\n"
        f"Осталось указать: {100 - percent}%",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_male_percent)


@router.message(SellerStates.waiting_for_male_percent)
async def handle_male_percent(message: Message, state: FSMContext):
    """Обработка ввода процента мужской аудитории"""
    try:
        percent = int(message.text.strip())
        if percent < 0 or percent > 100:
            raise ValueError("Invalid percentage")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    total = data.get('female_percent', 0) + percent
    
    if total != 100:
        await message.answer(
            f"❌ <b>Неверная сумма процентов</b>\n\n"
            f"Сумма мужской и женской аудитории должна равняться 100%.\n"
            f"Текущая сумма: {total}%\n\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(male_percent=percent)
    
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
        f"💰 <b>Цены</b>\n\n"
        f"Укажите цену за 4 истории (в рублях):\n\n"
        f"💡 <b>Важно:</b> Цена должна быть кратна 1000",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_stories)


@router.message(SellerStates.waiting_for_price_stories)
async def handle_price_stories(message: Message, state: FSMContext):
    """Обработка ввода цены за истории"""
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError("Negative price")
        if price % 1000 != 0:
            await message.answer(
                "❌ <b>Цена должна быть кратна 1000</b>\n\n"
                "Примеры: 5000, 10000, 15000\n"
                "Попробуйте еще раз:",
                parse_mode="HTML"
            )
            return
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое число, кратное 1000.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price_stories=price)
    
    await message.answer(
        f"💰 Укажите цену за пост (в рублях):\n\n"
        f"Уже указано: Истории: {price}₽\n\n"
        f"💡 <b>Важно:</b> Цена должна быть кратна 1000",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_post)


@router.message(SellerStates.waiting_for_price_post)
async def handle_price_post(message: Message, state: FSMContext):
    """Обработка ввода цены за пост"""
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError("Negative price")
        if price % 1000 != 0:
            await message.answer(
                "❌ <b>Цена должна быть кратна 1000</b>\n\n"
                "Примеры: 5000, 10000, 15000\n"
                "Попробуйте еще раз:",
                parse_mode="HTML"
            )
            return
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое число, кратное 1000.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price_post=price)
    
    data = await state.get_data()
    
    await message.answer(
        f"💰 Укажите цену за видео (в рублях):\n\n"
        f"Уже указано: Истории: {data.get('price_stories', 0)}₽, "
        f"Пост: {price}₽\n\n"
        f"💡 <b>Важно:</b> Цена должна быть кратна 1000",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_price_video)


@router.message(SellerStates.waiting_for_price_video)
async def handle_price_video(message: Message, state: FSMContext):
    """Обработка ввода цены за видео"""
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError("Negative price")
        if price % 1000 != 0:
            await message.answer(
                "❌ <b>Цена должна быть кратна 1000</b>\n\n"
                "Примеры: 5000, 10000, 15000\n"
                "Попробуйте еще раз:",
                parse_mode="HTML"
            )
            return
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое число, кратное 1000.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price_video=price)
    
    await message.answer(
        "📝 <b>Дополнительная информация</b>\n\n"
        "У блогера есть отзывы от других заказчиков?",
        reply_markup=get_yes_no_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_has_reviews)


@router.callback_query(F.data.startswith("yes_no_"), SellerStates.waiting_for_has_reviews)
async def handle_has_reviews(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа о наличии отзывов"""
    has_reviews = callback.data == "yes_no_yes"
    await state.update_data(has_reviews=has_reviews)
    
    await callback.answer()
    
    await callback.message.edit_text(
        "📋 <b>Регистрация в РКН</b>\n\n"
        "Блогер зарегистрирован в Роскомнадзоре?",
        reply_markup=get_yes_no_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_is_registered_rkn)


@router.callback_query(F.data.startswith("yes_no_"), SellerStates.waiting_for_is_registered_rkn)
async def handle_is_registered_rkn(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа о регистрации в РКН"""
    is_registered_rkn = callback.data == "yes_no_yes"
    await state.update_data(is_registered_rkn=is_registered_rkn)
    
    await callback.answer()
    
    await callback.message.edit_text(
        "💼 <b>Официальная оплата</b>\n\n"
        "Возможна ли официальная оплата (СЗ/ИП)?",
        reply_markup=get_yes_no_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_official_payment)


@router.callback_query(F.data.startswith("yes_no_"), SellerStates.waiting_for_official_payment)
async def handle_official_payment(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа о возможности официальной оплаты"""
    official_payment_possible = callback.data == "yes_no_yes"
    await state.update_data(official_payment_possible=official_payment_possible)
    
    await callback.answer()
    
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\n"
        "Укажите количество подписчиков:",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_statistics)


@router.message(SellerStates.waiting_for_statistics)
async def handle_statistics(message: Message, state: FSMContext):
    """Обработка ввода статистики"""
    input_text = message.text.strip()
    logger.info(f"Получен ввод статистики: '{input_text}' (длина: {len(input_text)})")
    
    try:
        # Убираем возможные пробелы и нечисловые символы
        clean_input = ''.join(filter(str.isdigit, input_text))
        
        if not clean_input:
            raise ValueError("No digits found")
            
        subscribers = int(clean_input)
        logger.info(f"Преобразованное число подписчиков: {subscribers}")
        
        if subscribers < 0:
            raise ValueError("Negative subscribers")
            
        if subscribers > 1000000000:  # 1 миллиард - разумный лимит
            await message.answer(
                "❌ <b>Слишком большое число</b>\n\n"
                "Максимальное количество подписчиков: 1,000,000,000\n"
                "Попробуйте еще раз:",
                parse_mode="HTML"
            )
            return
            
    except ValueError as e:
        logger.error(f"Ошибка валидации статистики: {e}, ввод: '{input_text}'")
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое положительное число.\n"
            f"Ваш ввод: '{input_text}'\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(subscribers_count=subscribers)
    
    await message.answer(
        f"📊 Укажите средние просмотры:\n\n"
        f"Уже указано: Подписчики: {subscribers}",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_avg_views)


@router.message(SellerStates.waiting_for_avg_views)
async def handle_avg_views(message: Message, state: FSMContext):
    """Обработка ввода средних просмотров"""
    input_text = message.text.strip()
    
    try:
        # Убираем возможные пробелы и нечисловые символы
        clean_input = ''.join(filter(str.isdigit, input_text))
        
        if not clean_input:
            raise ValueError("No digits found")
            
        avg_views = int(clean_input)
        
        if avg_views < 0:
            raise ValueError("Negative views")
            
    except ValueError as e:
        logger.error(f"Ошибка валидации просмотров: {e}, ввод: '{input_text}'")
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое положительное число.\n"
            f"Ваш ввод: '{input_text}'\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(avg_views=avg_views)
    
    await message.answer(
        f"📊 Укажите средние лайки:\n\n"
        f"Уже указано: Просмотры: {avg_views}",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_avg_likes)


@router.message(SellerStates.waiting_for_avg_likes)
async def handle_avg_likes(message: Message, state: FSMContext):
    """Обработка ввода средних лайков"""
    input_text = message.text.strip()
    
    try:
        # Убираем возможные пробелы и нечисловые символы
        clean_input = ''.join(filter(str.isdigit, input_text))
        
        if not clean_input:
            raise ValueError("No digits found")
            
        avg_likes = int(clean_input)
        
        if avg_likes < 0:
            raise ValueError("Negative likes")
            
    except ValueError as e:
        logger.error(f"Ошибка валидации лайков: {e}, ввод: '{input_text}'")
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите целое положительное число.\n"
            f"Ваш ввод: '{input_text}'\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(avg_likes=avg_likes)
    
    await message.answer(
        f"📊 Укажите процент вовлеченности (от 0 до 100):\n\n"
        f"Уже указано: Лайки: {avg_likes}",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_engagement_rate)


@router.message(SellerStates.waiting_for_engagement_rate)
async def handle_engagement_rate(message: Message, state: FSMContext):
    """Обработка ввода процента вовлеченности"""
    try:
        engagement_rate = float(message.text.strip())
        if engagement_rate < 0 or engagement_rate > 100:
            raise ValueError("Invalid engagement rate")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите число от 0 до 100.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(engagement_rate=engagement_rate)
    
    await message.answer(
        "📝 <b>Описание</b>\n\n"
        "Добавьте описание блогера (необязательно):\n\n"
        "Можно указать:\n"
        "• Особенности контента\n"
        "• Стиль подачи\n"
        "• Дополнительную информацию\n\n"
        "Или отправьте 'пропустить' для пропуска этого шага.",
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
            platforms=data['platforms'],  # Теперь используем множественные платформы
            categories=data['categories'],
            audience_13_17_percent=data.get('audience_13_17_percent'),
            audience_18_24_percent=data.get('audience_18_24_percent'),
            audience_25_35_percent=data.get('audience_25_35_percent'),
            audience_35_plus_percent=data.get('audience_35_plus_percent'),
            female_percent=data.get('female_percent'),
            male_percent=data.get('male_percent'),
            price_stories=data.get('price_stories'),
            price_post=data.get('price_post'),
            price_video=data.get('price_video'),
            has_reviews=data.get('has_reviews', False),
            is_registered_rkn=data.get('is_registered_rkn', False),
            official_payment_possible=data.get('official_payment_possible', False),
            subscribers_count=data.get('subscribers_count'),
            avg_views=data.get('avg_views'),
            avg_likes=data.get('avg_likes'),
            engagement_rate=data.get('engagement_rate'),
            description=description
        )
        
        await message.answer(
            f"✅ <b>Блогер успешно добавлен!</b>\n\n"
            f"📝 <b>Имя:</b> {blogger.name}\n"
            f"🔗 <b>Ссылка:</b> {blogger.url}\n"
            f"📊 <b>Подписчиков:</b> {blogger.subscribers_count:,}\n\n"
            f"Теперь блогер доступен для поиска закупщиками.",
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


# === ОБРАБОТЧИКИ ПРОСМОТРА И РЕДАКТИРОВАНИЯ БЛОГЕРОВ ===

@router.callback_query(F.data.startswith("blogger_"))
async def handle_blogger_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора блогера"""
    parts = callback.data.split("_")
    blogger_id = int(parts[1])
    action = parts[2] if len(parts) > 2 else "view"
    
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if not user or not user.has_role(UserRole.SELLER):
        await callback.answer("❌ Доступ запрещен")
        return
    
    # Проверяем, что блогер принадлежит пользователю
    if blogger.seller_id != user.id:
        await callback.answer("❌ Это не ваш блогер")
        return
    
    if action == "edit":
        await state.update_data(editing_blogger_id=blogger_id)
        await state.set_state(SellerStates.editing_blogger)
        
        await callback.answer()
        await callback.message.edit_text(
            f"✏️ <b>Редактирование блогера</b>\n\n"
            f"📝 <b>Имя:</b> {blogger.name}\n"
            f"🔗 <b>Ссылка:</b> {blogger.url}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_blogger_details_keyboard(blogger, action="edit"),
            parse_mode="HTML"
        )
    else:
        # Просмотр блогера
        await callback.answer()
        
        # Формируем подробную информацию о блогере
        info_text = f"📝 <b>Информация о блогере</b>\n\n"
        info_text += f"👤 <b>Имя:</b> {blogger.name}\n"
        info_text += f"🔗 <b>Ссылка:</b> {blogger.url}\n"
        info_text += f"📱 <b>Платформы:</b> {blogger.get_platforms_summary()}\n\n"
        
        if blogger.subscribers_count:
            info_text += f"📊 <b>Подписчиков:</b> {blogger.subscribers_count:,}\n"
        if blogger.avg_views:
            info_text += f"👁️ <b>Средние просмотры:</b> {blogger.avg_views:,}\n"
        if blogger.avg_likes:
            info_text += f"❤️ <b>Средние лайки:</b> {blogger.avg_likes:,}\n"
        if blogger.engagement_rate:
            info_text += f"📈 <b>Вовлеченность:</b> {blogger.engagement_rate:.1f}%\n"
        
        info_text += f"\n👥 <b>Демография:</b>\n"
        info_text += f"• Возраст: {blogger.get_age_categories_summary()}\n"
        info_text += f"• Пол: Женщины {blogger.female_percent}%, Мужчины {blogger.male_percent}%\n"
        
        info_text += f"\n🏷️ <b>Категории:</b> {', '.join([cat.get_russian_name() for cat in blogger.categories])}\n"
        
        info_text += f"\n💰 <b>Цены:</b>\n"
        if blogger.price_stories:
            info_text += f"• Истории: {blogger.price_stories:,}₽\n"
        if blogger.price_post:
            info_text += f"• Пост: {blogger.price_post:,}₽\n"
        if blogger.price_video:
            info_text += f"• Видео: {blogger.price_video:,}₽\n"
        
        info_text += f"\n📋 <b>Дополнительно:</b>\n"
        info_text += f"• Отзывы: {'✅' if blogger.has_reviews else '❌'}\n"
        info_text += f"• РКН: {'✅' if blogger.is_registered_rkn else '❌'}\n"
        info_text += f"• Офиц. оплата: {'✅' if blogger.official_payment_possible else '❌'}\n"
        
        if blogger.description:
            info_text += f"\n📝 <b>Описание:</b>\n{blogger.description}"
        
        await callback.message.edit_text(
            info_text,
            reply_markup=get_blogger_details_keyboard(blogger),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("delete_blogger_"))
async def handle_delete_blogger(callback: CallbackQuery):
    """Обработка удаления блогера"""
    blogger_id = int(callback.data.split("_")[2])
    
    user = await get_user(callback.from_user.id)
    if not user or not user.has_role(UserRole.SELLER):
        await callback.answer("❌ Доступ запрещен")
        return
    
    success = await delete_blogger(blogger_id, user.id)
    
    if success:
        await callback.answer("✅ Блогер удален")
        await callback.message.edit_text(
            "✅ <b>Блогер успешно удален</b>\n\n"
            "Блогер больше не будет отображаться в поиске.",
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при удалении")
        await callback.message.edit_text(
            "❌ <b>Ошибка при удалении</b>\n\n"
            "Не удалось удалить блогера.\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            parse_mode="HTML"
        ) 