import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from database.database import get_user, search_bloggers, get_blogger, create_complaint
from database.models import UserRole, SubscriptionStatus
from bot.keyboards import (
    get_category_keyboard, get_yes_no_keyboard, 
    get_search_results_keyboard, get_blogger_selection_keyboard,
    get_main_menu_buyer
)
from bot.states import BuyerStates, ComplaintStates
from utils.google_sheets import log_complaint_to_sheets

router = Router()
logger = logging.getLogger(__name__)


# === ОБРАБОТЧИКИ ОСНОВНОГО МЕНЮ ЗАКУПЩИКА ===

@router.message(F.text == "📋 История поиска", StateFilter("*"))
async def universal_show_search_history(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.has_role(UserRole.BUYER):
        await message.answer("❌ Эта функция доступна только закупщикам.")
        return
    await message.answer(
        "📋 <b>История поиска</b>\n\n"
        "📊 Функция находится в разработке.\n\n"
        "Скоро здесь будет отображаться:\n"
        "• История ваших поисков\n"
        "• Сохраненные результаты\n"
        "• Избранные блогеры\n\n"
        "🔍 Пока вы можете использовать поиск блогеров.",
        parse_mode="HTML"
    )


@router.message(F.text == "📊 Статистика", StateFilter("*"))
async def universal_show_statistics(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.has_role(UserRole.BUYER):
        await message.answer("❌ Эта функция доступна только закупщикам.")
        return
    subscription_status = "активна" if user.subscription_status == SubscriptionStatus.ACTIVE else "неактивна"
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 <b>Роль:</b> закупщик\n"
        f"💳 <b>Подписка:</b> {subscription_status}\n"
        f"⭐ <b>Рейтинг:</b> {user.rating:.1f}\n"
        f"📝 <b>Отзывов:</b> {user.reviews_count}\n"
        f"📅 <b>В боте с:</b> {user.created_at.strftime('%d.%m.%Y')}\n"
    )
    if user.subscription_end_date:
        stats_text += f"\n🗓️ <b>Подписка до:</b> {user.subscription_end_date.strftime('%d.%m.%Y')}"
    stats_text += (
        f"\n\n🔍 <b>Статистика поиска:</b>\n"
        f"• Поисков выполнено: В разработке\n"
        f"• Контактов получено: В разработке\n"
        f"• Избранных блогеров: В разработке"
    )
    await message.answer(stats_text, parse_mode="HTML")


@router.message(F.text == "🔍 Поиск блогеров", StateFilter("*"))
async def universal_search_bloggers(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.has_role(UserRole.BUYER):
        await message.answer("❌ Эта функция доступна только закупщикам.")
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
            "Для поиска блогеров необходима активная подписка.\n"
            "Стоимость: 500₽/мес\n\n"
            "Оформите подписку в разделе 💳 Подписка",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        "🔍 <b>Поиск блогеров</b>\n\n"
        "Давайте найдем подходящих блогеров для вашего проекта.\n\n"
        "🎯 <b>Шаг 1:</b> Выберите платформы:",
        reply_markup=get_platform_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_platforms)


# === ОБРАБОТЧИКИ ПОИСКА БЛОГЕРОВ ===

@router.callback_query(F.data.startswith("platform_"), BuyerStates.waiting_for_platforms)
async def handle_platform_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора платформ для поиска"""
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
        f"Выберите платформы для поиска:",
        reply_markup=get_platform_selection_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_platforms", BuyerStates.waiting_for_platforms)
async def confirm_platforms(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора платформ"""
    data = await state.get_data()
    platforms = data.get('platforms', [])
    
    if not platforms:
        await callback.answer("❌ Выберите хотя бы одну платформу")
        return
    
    await callback.answer()
    
    await callback.message.edit_text(
        f"👥 <b>Целевая аудитория</b>\n\n"
        f"Укажите минимальный возраст целевой аудитории:\n\n"
        f"💡 <b>Важно:</b> Укажите возраст в годах (например: 18, 25, 35)",
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_target_age)


@router.message(BuyerStates.waiting_for_target_age)
async def handle_target_age(message: Message, state: FSMContext):
    """Обработка ввода целевого возраста"""
    try:
        age = int(message.text.strip())
        if age < 13 or age > 65:
            raise ValueError("Invalid age")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите возраст от 13 до 65 лет.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(target_age_min=age)
    
    await message.answer(
        f"👥 Укажите максимальный возраст целевой аудитории:\n\n"
        f"Уже указано: Минимальный возраст: {age} лет\n\n"
        f"💡 <b>Важно:</b> Максимальный возраст должен быть больше минимального",
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_target_age_max)


@router.message(BuyerStates.waiting_for_target_age_max)
async def handle_target_age_max(message: Message, state: FSMContext):
    """Обработка ввода максимального целевого возраста"""
    try:
        age_max = int(message.text.strip())
        if age_max < 13 or age_max > 65:
            raise ValueError("Invalid age")
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите возраст от 13 до 65 лет.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    age_min = data.get('target_age_min', 0)
    
    if age_max <= age_min:
        await message.answer(
            f"❌ <b>Неверный возраст</b>\n\n"
            f"Максимальный возраст ({age_max}) должен быть больше минимального ({age_min}).\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(target_age_max=age_max)
    
    await message.answer(
        f"👥 <b>Пол целевой аудитории</b>\n\n"
        f"Выберите пол целевой аудитории:",
        reply_markup=get_gender_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_target_gender)


@router.callback_query(F.data.startswith("gender_"), BuyerStates.waiting_for_target_gender)
async def handle_target_gender(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора пола целевой аудитории"""
    gender = callback.data.split("_")[1]
    
    await state.update_data(target_gender=gender)
    await callback.answer()
    
    await callback.message.edit_text(
        f"🏷️ <b>Категории блогов</b>\n\n"
        f"Выберите интересующие категории:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_categories)


@router.callback_query(F.data.startswith("category_"), BuyerStates.waiting_for_categories)
async def handle_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категорий для поиска"""
    category_str = callback.data.split("_")[1]
    category = BlogCategory(category_str)
    
    data = await state.get_data()
    categories = data.get('categories', [])
    
    if category in categories:
        # Убираем категорию
        categories.remove(category)
        await callback.answer(f"❌ Категория '{category.value}' убрана")
    else:
        # Добавляем категорию
        categories.append(category)
        await callback.answer(f"✅ Категория '{category.value}' добавлена")
    
    await state.update_data(categories=categories)
    
    # Обновляем сообщение
    categories_text = ", ".join([cat.value for cat in categories]) if categories else "Не выбрано"
    
    await callback.message.edit_text(
        f"🏷️ <b>Категории блогов</b>\n\n"
        f"Выбранные категории: <b>{categories_text}</b>\n\n"
        f"Выберите интересующие категории:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_categories", BuyerStates.waiting_for_categories)
async def confirm_categories(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора категорий"""
    data = await state.get_data()
    categories = data.get('categories', [])
    
    if not categories:
        await callback.answer("❌ Выберите хотя бы одну категорию")
        return
    
    await callback.answer()
    
    await callback.message.edit_text(
        f"💰 <b>Бюджет</b>\n\n"
        f"Укажите минимальный бюджет (в рублях):\n\n"
        f"💡 <b>Важно:</b> Бюджет должен быть кратен 1000",
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_budget)


@router.message(BuyerStates.waiting_for_budget)
async def handle_budget(message: Message, state: FSMContext):
    """Обработка ввода бюджета"""
    try:
        budget = int(message.text.strip())
        if budget < 0:
            raise ValueError("Negative budget")
        if budget % 1000 != 0:
            await message.answer(
                "❌ <b>Бюджет должен быть кратен 1000</b>\n\n"
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
    
    await state.update_data(budget_min=budget)
    
    await message.answer(
        f"💰 Укажите максимальный бюджет (в рублях):\n\n"
        f"Уже указано: Минимальный бюджет: {budget}₽\n\n"
        f"💡 <b>Важно:</b> Максимальный бюджет должен быть больше минимального",
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_budget_max)


@router.message(BuyerStates.waiting_for_budget_max)
async def handle_budget_max(message: Message, state: FSMContext):
    """Обработка ввода максимального бюджета"""
    try:
        budget_max = int(message.text.strip())
        if budget_max < 0:
            raise ValueError("Negative budget")
        if budget_max % 1000 != 0:
            await message.answer(
                "❌ <b>Бюджет должен быть кратен 1000</b>\n\n"
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
    
    data = await state.get_data()
    budget_min = data.get('budget_min', 0)
    
    if budget_max <= budget_min:
        await message.answer(
            f"❌ <b>Неверный бюджет</b>\n\n"
            f"Максимальный бюджет ({budget_max}₽) должен быть больше минимального ({budget_min}₽).\n"
            f"Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(budget_max=budget_max)
    
    await message.answer(
        f"📋 <b>Дополнительные критерии</b>\n\n"
        f"У блогера должны быть отзывы от других заказчиков?",
        reply_markup=get_yes_no_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_additional_criteria)


@router.callback_query(F.data.startswith("yes_no_"), BuyerStates.waiting_for_additional_criteria)
async def handle_additional_criteria(callback: CallbackQuery, state: FSMContext):
    """Обработка дополнительных критериев"""
    has_reviews = callback.data == "yes_no_yes"
    await state.update_data(has_reviews=has_reviews)
    
    await callback.answer()
    
    # Выполняем поиск
    data = await state.get_data()
    
    try:
        # Преобразуем данные для поиска
        platforms = [p.value for p in data.get('platforms', [])]
        categories = [c.value for c in data.get('categories', [])]
        
        results = await search_bloggers(
            platforms=platforms,
            categories=categories,
            target_age_min=data.get('target_age_min'),
            target_age_max=data.get('target_age_max'),
            target_gender=data.get('target_gender'),
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
            has_reviews=data.get('has_reviews'),
            limit=10
        )
        
        if not results:
            await callback.message.edit_text(
                "🔍 <b>Результаты поиска</b>\n\n"
                "😔 По вашему запросу ничего не найдено.\n\n"
                "Попробуйте:\n"
                "• Расширить критерии поиска\n"
                "• Увеличить бюджет\n"
                "• Выбрать другие категории",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        await callback.message.edit_text(
            f"🔍 <b>Результаты поиска</b>\n\n"
            f"Найдено блогеров: {len(results)}\n\n"
            f"Выберите блогера для просмотра:",
            reply_markup=get_search_results_keyboard(results),
            parse_mode="HTML"
        )
        await state.set_state(BuyerStates.viewing_results)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске блогеров: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при поиске</b>\n\n"
            "Произошла ошибка при выполнении поиска.\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            parse_mode="HTML"
        )
        await state.clear()


# === ОБРАБОТЧИКИ ПРОСМОТРА РЕЗУЛЬТАТОВ ===

@router.callback_query(F.data.startswith("blogger_"), BuyerStates.viewing_results)
async def handle_blogger_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора блогера из результатов поиска"""
    blogger_id = int(callback.data.split("_")[1])
    
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
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
    
    info_text += f"\n🏷️ <b>Категории:</b> {', '.join([cat.value for cat in blogger.categories])}\n"
    
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
    
    await callback.answer()
    await callback.message.edit_text(
        info_text,
        reply_markup=get_blogger_selection_keyboard(blogger),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("contact_"))
async def handle_contact_request(callback: CallbackQuery, state: FSMContext):
    """Обработка запроса контактов блогера"""
    blogger_id = int(callback.data.split("_")[1])
    
    user = await get_user(callback.from_user.id)
    if not user or not user.has_role(UserRole.BUYER):
        await callback.answer("❌ Доступ запрещен")
        return
    
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    # Здесь должна быть логика получения контактов продавца
    # Пока что просто показываем сообщение
    await callback.answer("✅ Запрос отправлен")
    await callback.message.edit_text(
        f"📞 <b>Запрос контактов</b>\n\n"
        f"Ваш запрос на получение контактов блогера <b>{blogger.name}</b> отправлен.\n\n"
        f"Продавец свяжется с вами в ближайшее время.\n\n"
        f"💡 <b>Совет:</b> Будьте вежливы и четко опишите ваш проект.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("complain_"))
async def handle_complaint_request(callback: CallbackQuery, state: FSMContext):
    """Обработка запроса на жалобу"""
    blogger_id = int(callback.data.split("_")[1])
    
    user = await get_user(callback.from_user.id)
    if not user or not user.can_complain():
        await callback.answer("❌ Только закупщики могут подавать жалобы")
        return
    
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    await state.update_data(complaint_blogger_id=blogger_id, complaint_blogger_name=blogger.name)
    
    await callback.answer()
    await callback.message.edit_text(
        f"⚠️ <b>Подача жалобы</b>\n\n"
        f"Вы собираетесь подать жалобу на блогера <b>{blogger.name}</b>.\n\n"
        f"Опишите причину жалобы:",
        parse_mode="HTML"
    )
    await state.set_state(ComplaintStates.waiting_for_reason)


@router.message(ComplaintStates.waiting_for_reason)
async def handle_complaint_reason(message: Message, state: FSMContext):
    """Обработка причины жалобы"""
    reason = message.text.strip()
    
    if len(reason) < 10:
        await message.answer(
            "❌ <b>Слишком короткое описание</b>\n\n"
            "Опишите причину жалобы подробнее (минимум 10 символов).\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    blogger_id = data.get('complaint_blogger_id')
    blogger_name = data.get('complaint_blogger_name')
    
    user = await get_user(message.from_user.id)
    
    try:
        success = await create_complaint(
            blogger_id=blogger_id,
            blogger_name=blogger_name,
            user_id=user.id,
            username=user.username or "Неизвестно",
            reason=reason
        )
        
        if success:
            await message.answer(
                f"✅ <b>Жалоба подана</b>\n\n"
                f"Ваша жалоба на блогера <b>{blogger_name}</b> принята.\n\n"
                f"Мы рассмотрим её в ближайшее время.",
                parse_mode="HTML"
            )
            
            # Логируем в Google Sheets
            await log_complaint_to_sheets(user, blogger_name, reason)
        else:
            await message.answer(
                "❌ <b>Ошибка при подаче жалобы</b>\n\n"
                "Не удалось отправить жалобу.\n"
                "Попробуйте еще раз или обратитесь в поддержку.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Ошибка при создании жалобы: {e}")
        await message.answer(
            "❌ <b>Ошибка при подаче жалобы</b>\n\n"
            "Произошла ошибка при отправке жалобы.\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            parse_mode="HTML"
        )
    
    await state.clear()


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_platform_selection_keyboard():
    """Клавиатура выбора платформ для поиска"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton(text="📺 YouTube", callback_data="platform_youtube")],
        [InlineKeyboardButton(text="📱 TikTok", callback_data="platform_tiktok")],
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="📱 VK", callback_data="platform_vk")],
        [InlineKeyboardButton(text="✅ Подтвердить выбор", callback_data="confirm_platforms")]
    ])


def get_gender_selection_keyboard():
    """Клавиатура выбора пола"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩 Женщины", callback_data="gender_female")],
        [InlineKeyboardButton(text="👨 Мужчины", callback_data="gender_male")],
        [InlineKeyboardButton(text="👥 Любой", callback_data="gender_any")]
    ])


# Вспомогательная функция для получения пользователя по ID
async def get_user_by_id(user_id: int):
    """Получить пользователя по внутреннему ID"""
    # Эту функцию нужно добавить в database.py
    import aiosqlite
    from database.database import DATABASE_PATH
    from database.models import User, UserRole, SubscriptionStatus
    from datetime import datetime
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            # Получаем роли пользователя
            cursor = await db.execute("""
                SELECT role FROM user_roles WHERE user_id = ?
            """, (row['id'],))
            
            role_rows = await cursor.fetchall()
            roles = {UserRole(role_row['role']) for role_row in role_rows}
            
            return User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                roles=roles,
                subscription_status=SubscriptionStatus(row['subscription_status']) if row['subscription_status'] else SubscriptionStatus.INACTIVE,
                subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                subscription_start_date=datetime.fromisoformat(row['subscription_start_date']) if row['subscription_start_date'] else None,
                rating=row['rating'],
                reviews_count=row['reviews_count'],
                is_vip=bool(row['is_vip']),
                penalty_amount=row['penalty_amount'],
                is_blocked=bool(row['is_blocked']),
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
            )
        return None 