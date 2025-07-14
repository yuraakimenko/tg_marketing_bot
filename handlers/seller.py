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

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать статистику продажника"""
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    
    # Получаем список блогеров
    bloggers = await get_user_bloggers(user.id)
    
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 <b>Роль:</b> продажник\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f}\n"
        f"📝 <b>Отзывов:</b> {user.reviews_count}\n"
        f"📅 <b>В боте с:</b> {user.created_at.strftime('%d.%m.%Y')}\n"
        f"\n📝 <b>Добавлено блогеров:</b> {len(bloggers)}\n"
    )
    
    if user.subscription_end_date:
        stats_text += f"🗓️ <b>Подписка до:</b> {user.subscription_end_date.strftime('%d.%m.%Y')}"
    
    # Статистика по блогерам
    if bloggers:
        platforms = {}
        for blogger in bloggers:
            platforms[blogger.platform] = platforms.get(blogger.platform, 0) + 1
        
        # Топ платформа
        top_platform = max(platforms.items(), key=lambda x: x[1])
        
        stats_text += (
            f"\n\n🎯 <b>Статистика блогеров:</b>\n"
            f"• Топ платформа: {top_platform[0]} ({top_platform[1]})\n"
            f"• С отзывами: {sum(1 for b in bloggers if b.has_reviews)}\n"
            f"• Без отзывов: {sum(1 for b in bloggers if not b.has_reviews)}"
        )
    
    await message.answer(stats_text, parse_mode="HTML")


@router.message(F.text == "➕ Добавить блогера")
async def add_blogger_start(message: Message, state: FSMContext):
    """Начать добавление блогера (новый порядок: сначала платформа)"""
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
        "Шаг 1 из 15\n"
        "📱 Выберите платформы блогера (можно несколько):",
        reply_markup=get_platforms_multi_keyboard(),
        parse_mode="HTML"
    )
    await state.update_data(platforms=[])
    await state.set_state(SellerStates.waiting_for_platform)


@router.callback_query(F.data.startswith("toggle_platform_"), SellerStates.waiting_for_platform)
async def toggle_platform_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора/отмены платформы"""
    platform_code = callback.data.replace("toggle_platform_", "")
    data = await state.get_data()
    platforms = data.get("platforms", [])
    if platform_code in platforms:
        platforms.remove(platform_code)
    else:
        platforms.append(platform_code)
    await state.update_data(platforms=platforms)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=get_platforms_multi_keyboard(platforms))


@router.callback_query(F.data == "finish_platforms_selection", SellerStates.waiting_for_platform)
async def finish_platforms_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    platforms = data.get("platforms", [])
    if not platforms:
        await callback.answer("Выберите хотя бы одну платформу")
        return
    await callback.answer()
    await callback.message.edit_text(
        "Шаг 2 из 15\n"
        "🔗 Введите ссылку на блогера (чистую, без символов после ника):\n\n"
        "<b>Пример: https://instagram.com/username</b>",
        parse_mode="HTML"
    )
    await state.set_state(SellerStates.waiting_for_blogger_url)


@router.message(SellerStates.waiting_for_blogger_url)
async def process_blogger_url(message: Message, state: FSMContext):
    """Обработка ссылки блогера"""
    await state.update_data(url=message.text)
    
    await message.answer(
        "Шаг 3 из 15\n"
        "📝 Введите имя блогера:"
    )
    await state.set_state(SellerStates.waiting_for_blogger_name)


@router.message(SellerStates.waiting_for_blogger_name)
async def process_blogger_name(message: Message, state: FSMContext):
    """Обработка имени блогера"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "Шаг 4 из 15\n"
        "👥 Демография аудитории\n\n"
        "Укажите % аудитории 13-17 лет:\n"
        "(введите число от 0 до 100)"
    )
    await state.set_state(SellerStates.waiting_for_audience_13_17)


@router.message(SellerStates.waiting_for_audience_13_17)
async def process_audience_13_17(message: Message, state: FSMContext):
    """Обработка % аудитории 13-17 лет"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(audience_13_17_percent=percent)
        
        await message.answer(
            "Шаг 5 из 15\n"
            "👥 Укажите % аудитории 18-24 лет:\n"
            "(введите число от 0 до 100)"
        )
        await state.set_state(SellerStates.waiting_for_audience_18_24)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_audience_18_24)
async def process_audience_18_24(message: Message, state: FSMContext):
    """Обработка % аудитории 18-24 лет"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(audience_18_24_percent=percent)
        
        await message.answer(
            "Шаг 6 из 15\n"
            "👥 Укажите % аудитории 25-35 лет:\n"
            "(введите число от 0 до 100)"
        )
        await state.set_state(SellerStates.waiting_for_audience_25_35)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_audience_25_35)
async def process_audience_25_35(message: Message, state: FSMContext):
    """Обработка % аудитории 25-35 лет"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(audience_25_35_percent=percent)
        
        await message.answer(
            "Шаг 7 из 15\n"
            "👥 Укажите % аудитории 35+ лет:\n"
            "(введите число от 0 до 100)"
        )
        await state.set_state(SellerStates.waiting_for_audience_35_plus)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_audience_35_plus)
async def process_audience_35_plus(message: Message, state: FSMContext):
    """Обработка % аудитории 35+ лет"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(audience_35_plus_percent=percent)
        
        await message.answer(
            "Шаг 8 из 15\n"
            "👥 Пол аудитории\n\n"
            "Укажите % женской аудитории:\n"
            "(введите число от 0 до 100)"
        )
        await state.set_state(SellerStates.waiting_for_female_percent)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_female_percent)
async def process_female_percent(message: Message, state: FSMContext):
    """Обработка % женской аудитории"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(female_percent=percent)
        
        await message.answer(
            "Шаг 9 из 15\n"
            "👥 Укажите % мужской аудитории:\n"
            "(введите число от 0 до 100)"
        )
        await state.set_state(SellerStates.waiting_for_male_percent)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_male_percent)
async def process_male_percent(message: Message, state: FSMContext):
    """Обработка % мужской аудитории"""
    try:
        percent = int(message.text)
        if percent < 0 or percent > 100:
            await message.answer("❌ Введите число от 0 до 100")
            return
        
        await state.update_data(male_percent=percent)
        
        await message.answer(
            "Шаг 10 из 15\n"
            "🎯 Выберите основную категорию блога:",
            reply_markup=get_category_keyboard()
        )
        await state.set_state(SellerStates.waiting_for_categories)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.callback_query(F.data.startswith("category_"), SellerStates.waiting_for_categories)
async def process_categories(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категорий"""
    category_str = callback.data.split("_", 1)[1]
    
    # Преобразуем строку в enum
    category_map = {
        "lifestyle": BlogCategory.LIFESTYLE,
        "sport": BlogCategory.SPORT,
        "nutrition": BlogCategory.NUTRITION,
        "medicine": BlogCategory.MEDICINE,
        "relationships": BlogCategory.RELATIONSHIPS,
        "beauty": BlogCategory.BEAUTY,
        "fashion": BlogCategory.FASHION,
        "travel": BlogCategory.TRAVEL,
        "business": BlogCategory.BUSINESS,
        "education": BlogCategory.EDUCATION,
        "entertainment": BlogCategory.ENTERTAINMENT,
        "technology": BlogCategory.TECHNOLOGY,
        "parenting": BlogCategory.PARENTING,
        "finance": BlogCategory.FINANCE,
        "not_important": BlogCategory.NOT_IMPORTANT
    }
    
    if category_str not in category_map:
        await callback.answer("❌ Неизвестная категория")
        return
    
    category = category_map[category_str]
    await state.update_data(categories=[category])
    await callback.answer()
    
    await callback.message.edit_text(
        "Шаг 11 из 15\n"
        "💰 Выберите цену за 4 истории (кратную 1000):",
        reply_markup=get_price_stories_keyboard()
    )
    await state.set_state(SellerStates.waiting_for_price_stories)


@router.callback_query(F.data.startswith("price_stories_"), SellerStates.waiting_for_price_stories)
async def process_price_stories(callback: CallbackQuery, state: FSMContext):
    """Обработка цены за 4 истории"""
    price_str = callback.data.split("_")[2]
    
    if price_str == "custom":
        await callback.answer()
        await callback.message.edit_text(
            "💰 Введите цену за 4 истории (кратную 1000):\n"
            "Например: 4000, 10000, 20000"
        )
        return
    
    try:
        price = int(price_str)
        await state.update_data(price_stories=price)
        await callback.answer()
        
        await callback.message.edit_text(
            "Шаг 12 из 15\n"
            "💰 Выберите цену за пост (кратную 1000):",
            reply_markup=get_price_post_keyboard()
        )
        await state.set_state(SellerStates.waiting_for_price_post)
    except ValueError:
        await callback.answer("❌ Неверная цена")


@router.callback_query(F.data.startswith("price_post_"), SellerStates.waiting_for_price_post)
async def process_price_post(callback: CallbackQuery, state: FSMContext):
    """Обработка цены за пост"""
    price_str = callback.data.split("_")[2]
    
    if price_str == "custom":
        await callback.answer()
        await callback.message.edit_text(
            "💰 Введите цену за пост (кратную 1000):\n"
            "Например: 4000, 10000, 20000"
        )
        return
    
    try:
        price = int(price_str)
        await state.update_data(price_post=price)
        await callback.answer()
        
        await callback.message.edit_text(
            "Шаг 13 из 15\n"
            "💰 Выберите цену за видео (кратную 1000):",
            reply_markup=get_price_video_keyboard()
        )
        await state.set_state(SellerStates.waiting_for_price_video)
    except ValueError:
        await callback.answer("❌ Неверная цена")


@router.callback_query(F.data.startswith("price_video_"), SellerStates.waiting_for_price_video)
async def process_price_video(callback: CallbackQuery, state: FSMContext):
    """Обработка цены за видео"""
    price_str = callback.data.split("_")[2]
    
    if price_str == "custom":
        await callback.answer()
        await callback.message.edit_text(
            "💰 Введите цену за видео (кратную 1000):\n"
            "Например: 4000, 10000, 20000"
        )
        return
    
    try:
        price = int(price_str)
        await state.update_data(price_video=price)
        await callback.answer()
        
        await callback.message.edit_text(
            "Шаг 14 из 15\n"
            "🗣️ Есть ли у блогера отзывы от рекламодателей?",
            reply_markup=get_yes_no_keyboard("reviews")
        )
        await state.set_state(SellerStates.waiting_for_has_reviews)
    except ValueError:
        await callback.answer("❌ Неверная цена")


@router.callback_query(F.data.startswith("yes_reviews") | F.data.startswith("no_reviews"), 
                      SellerStates.waiting_for_has_reviews)
async def process_has_reviews(callback: CallbackQuery, state: FSMContext):
    """Обработка наличия отзывов"""
    has_reviews = callback.data.startswith("yes_")
    await state.update_data(has_reviews=has_reviews)
    
    await callback.answer()
    await callback.message.edit_text(
        "Шаг 15 из 15\n"
        "📝 Введите дополнительное описание блогера (необязательно):\n"
        "Или введите 'пропустить' чтобы завершить:"
    )
    await state.set_state(SellerStates.waiting_for_blogger_description)


# === ОБРАБОТЧИКИ ДЛЯ КАСТОМНЫХ ЦЕН ===

@router.message(SellerStates.waiting_for_price_stories)
async def process_custom_price_stories(message: Message, state: FSMContext):
    """Обработка кастомной цены за 4 истории"""
    try:
        price = int(message.text)
        if price % 1000 != 0:
            await message.answer("❌ Цена должна быть кратна 1000")
            return
        
        await state.update_data(price_stories=price)
        
        await message.answer(
            "Шаг 12 из 15\n"
            "💰 Выберите цену за пост (кратную 1000):",
            reply_markup=get_price_post_keyboard()
        )
        await state.set_state(SellerStates.waiting_for_price_post)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_price_post)
async def process_custom_price_post(message: Message, state: FSMContext):
    """Обработка кастомной цены за пост"""
    try:
        price = int(message.text)
        if price % 1000 != 0:
            await message.answer("❌ Цена должна быть кратна 1000")
            return
        
        await state.update_data(price_post=price)
        
        await message.answer(
            "Шаг 13 из 15\n"
            "💰 Выберите цену за видео (кратную 1000):",
            reply_markup=get_price_video_keyboard()
        )
        await state.set_state(SellerStates.waiting_for_price_video)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(SellerStates.waiting_for_price_video)
async def process_custom_price_video(message: Message, state: FSMContext):
    """Обработка кастомной цены за видео"""
    try:
        price = int(message.text)
        if price % 1000 != 0:
            await message.answer("❌ Цена должна быть кратна 1000")
            return
        
        await state.update_data(price_video=price)
        
        await message.answer(
            "Шаг 14 из 15\n"
            "🗣️ Есть ли у блогера отзывы от рекламодателей?",
            reply_markup=get_yes_no_keyboard("reviews")
        )
        await state.set_state(SellerStates.waiting_for_has_reviews)
    except ValueError:
        await message.answer("❌ Введите корректное число")


# === ФИНАЛЬНЫЙ ОБРАБОТЧИК СОЗДАНИЯ БЛОГЕРА ===

@router.message(SellerStates.waiting_for_blogger_description)
async def process_blogger_description(message: Message, state: FSMContext):
    """Обработка описания и создание блогера"""
    description = message.text if message.text.lower() != "пропустить" else None
    
    data = await state.get_data()
    user = await get_user(message.from_user.id)
    
    # Валидация возрастных категорий
    age_total = (
        data.get('audience_13_17_percent', 0) +
        data.get('audience_18_24_percent', 0) +
        data.get('audience_25_35_percent', 0) +
        data.get('audience_35_plus_percent', 0)
    )
    
    if age_total != 100:
        await message.answer(
            f"❌ <b>Ошибка валидации!</b>\n\n"
            f"Сумма процентов возрастных категорий должна быть 100%.\n"
            f"Текущая сумма: {age_total}%\n\n"
            f"Пожалуйста, исправьте данные и попробуйте снова.",
            parse_mode="HTML"
        )
        return
    
    # Валидация процентов по полу
    gender_total = data.get('female_percent', 0) + data.get('male_percent', 0)
    if gender_total != 100:
        await message.answer(
            f"❌ <b>Ошибка валидации!</b>\n\n"
            f"Сумма процентов по полу должна быть 100%.\n"
            f"Текущая сумма: {gender_total}%\n\n"
            f"Пожалуйста, исправьте данные и попробуйте снова.",
            parse_mode="HTML"
        )
        return
    
    # Преобразуем платформы в enum
    platforms = []
    for platform_code in data.get('platforms', []):
        try:
            platforms.append(Platform(platform_code))
        except ValueError:
            await message.answer(f"❌ Неизвестная платформа: {platform_code}")
            return
    
    # Создаем блогера с новыми полями
    blogger = await create_blogger(
        seller_id=user.id,
        name=data['name'],
        url=data['url'],
        platforms=platforms,
        categories=data['categories'],
        audience_13_17_percent=data['audience_13_17_percent'],
        audience_18_24_percent=data['audience_18_24_percent'],
        audience_25_35_percent=data['audience_25_35_percent'],
        audience_35_plus_percent=data['audience_35_plus_percent'],
        female_percent=data['female_percent'],
        male_percent=data['male_percent'],
        price_stories=data['price_stories'],
        price_post=data['price_post'],
        price_video=data['price_video'],
        has_reviews=data['has_reviews'],
        description=description
    )
    
    # Логируем в Google Sheets
    from utils.google_sheets import log_blogger_action_to_sheets
    
    user_data = {
        'username': user.username,
        'role': user.role.value,
        'subscription_start_date': user.subscription_start_date,
        'subscription_end_date': user.subscription_end_date
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
    
    await log_blogger_action_to_sheets(user_data, blogger_data, "add")
    
    await message.answer(
        f"✅ <b>Блогер успешно добавлен!</b>\n\n"
        f"📝 <b>Имя:</b> {blogger.name}\n"
        f"📱 <b>Платформы:</b> {', '.join([p.value for p in blogger.platforms])}\n"
        f"🎯 <b>Категории:</b> {', '.join([cat.value for cat in blogger.categories])}\n"
        f"👥 <b>Аудитория:</b> {blogger.female_percent}%♀️ {blogger.male_percent}%♂️\n"
        f"📊 <b>Возрастные категории:</b> {blogger.get_age_categories_summary()}\n"
        f"🗣️ <b>Отзывы:</b> {'Есть' if blogger.has_reviews else 'Нет'}\n"
        f"💰 <b>Цены:</b>\n"
        f"• 4 истории: {blogger.price_stories}₽\n"
        f"• Пост: {blogger.price_post}₽\n"
        f"• Видео: {blogger.price_video}₽",
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
    try:
        blogger_id = int(callback.data.split("_")[1])
        blogger = await get_blogger(blogger_id)
        if not blogger:
            await callback.answer("❌ Блогер не найден")
            return
        user = await get_user(callback.from_user.id)
        if not user or blogger.seller_id != user.id:
            await callback.answer("❌ Нет доступа к этому блогеру")
            return
        # Платформы
        platforms_str = blogger.get_platforms_summary()
        # Категории
        categories = blogger.categories if hasattr(blogger, 'categories') else []
        categories_str = ", ".join([c.value if hasattr(c, 'value') else str(c) for c in categories])
        # Цены
        price_stories = getattr(blogger, 'price_stories', None)
        price_post = getattr(blogger, 'price_post', None)
        price_video = getattr(blogger, 'price_video', None)
        price_text = ""
        if price_stories:
            price_text += f"4 истории: {price_stories}₽\n"
        if price_post:
            price_text += f"Пост: {price_post}₽\n"
        if price_video:
            price_text += f"Видео: {price_video}₽\n"
        if not price_text:
            price_text = "Договорная"
        # Аудитория
        female = getattr(blogger, 'female_percent', None)
        male = getattr(blogger, 'male_percent', None)
        audience_str = f"{female or 0}%♀️ {male or 0}%♂️"
        details_text = (
            f"📝 <b>Детали блогера</b>\n\n"
            f"👤 <b>Имя:</b> {blogger.name}\n"
            f"🔗 <b>Ссылка:</b> {blogger.url}\n"
            f"📱 <b>Платформы:</b> {platforms_str}\n"
            f"🎯 <b>Категории:</b> {categories_str}\n"
            f"👥 <b>Аудитория:</b> {audience_str}\n"
            f"🗣️ <b>Отзывы:</b> {'Есть' if blogger.has_reviews else 'Нет'}\n"
            f"💰 <b>Цены:</b>\n{price_text}"
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
    except Exception as e:
        logger.error(f"Ошибка в show_blogger_details: {e}")
        await callback.answer("❌ Ошибка при отображении блогера")
        await callback.message.edit_text("❌ Ошибка при отображении блогера. Попробуйте позже.")


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
            f"📱 <b>Платформа:</b> {', '.join([p.value for p in blogger.platform])} (множество)\n" # Display multiple platforms
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


# Универсальные хэндлеры для меню продавца (работают из любого состояния)
@router.message(F.text == "➕ Добавить блогера", StateFilter("*"))
async def universal_add_blogger(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    from handlers.seller import add_blogger_start
    await add_blogger_start(message, state)

@router.message(F.text == "📝 Мои блогеры", StateFilter("*"))
async def universal_my_bloggers(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    from handlers.seller import show_my_bloggers
    await show_my_bloggers(message)

@router.message(F.text == "📊 Статистика", StateFilter("*"))
async def universal_show_statistics_seller(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.SELLER:
        await message.answer("❌ Эта функция доступна только продажникам.")
        return
    from handlers.seller import show_statistics
    await show_statistics(message)

@router.message(F.text == "💳 Подписка", StateFilter("*"))
async def universal_subscription_seller(message: Message, state: FSMContext):
    await state.clear()
    from handlers.subscription import subscription_menu
    await subscription_menu(message)

@router.message(F.text == "🔧 Управление подпиской", StateFilter("*"))
async def universal_subscription_management_seller(message: Message, state: FSMContext):
    await state.clear()
    from handlers.subscription import subscription_management_menu
    await subscription_management_menu(message)

@router.message(F.text == "⚙️ Настройки", StateFilter("*"))
async def universal_settings_seller(message: Message, state: FSMContext):
    await state.clear()
    from handlers.common import settings_menu
    await settings_menu(message) 