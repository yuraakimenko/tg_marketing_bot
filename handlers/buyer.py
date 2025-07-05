import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import get_user, search_bloggers, get_blogger, create_complaint
from database.models import UserRole, SubscriptionStatus
from bot.keyboards import (
    get_category_keyboard, get_yes_no_keyboard, 
    get_search_results_keyboard, get_blogger_selection_keyboard,
    get_main_menu_buyer
)
from bot.states import BuyerStates, ComplaintStates

router = Router()
logger = logging.getLogger(__name__)


# === ОБРАБОТЧИКИ ОСНОВНОГО МЕНЮ ЗАКУПЩИКА ===

@router.message(F.text == "📋 История поиска", state="*")
async def universal_show_search_history(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.BUYER:
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


@router.message(F.text == "📊 Статистика", state="*")
async def universal_show_statistics(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.BUYER:
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


@router.message(F.text == "🔍 Поиск блогеров", state="*")
async def universal_start_search(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or user.role != UserRole.BUYER:
        await message.answer("❌ Эта функция доступна только закупщикам.")
        return
    if user.subscription_status != SubscriptionStatus.ACTIVE:
        await message.answer(
            "❌ Для поиска блогеров необходима активная подписка.\n"
            "💳 Оформите подписку в разделе 'Подписка'."
        )
        return
    await message.answer(
        "🔍 <b>Поиск блогеров</b>\n\n"
        "Шаг 1 из 4\n"
        "🎯 Выберите интересующую категорию:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_category)


@router.callback_query(F.data.startswith("category_"), BuyerStates.waiting_for_category)
async def process_search_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории для поиска"""
    category = callback.data.split("_", 1)[1]
    
    if category == "other":
        await callback.answer()
        await callback.message.edit_text(
            "Шаг 1 из 4\n"
            "🎯 Введите категорию для поиска:"
        )
        return
    
    await state.update_data(category=category)
    await callback.answer()
    
    await callback.message.edit_text(
        "Шаг 2 из 4\n"
        "👥 Опишите целевую аудиторию:\n"
        "Например: 'женщины 25-35 лет' или введите 'любая' для пропуска"
    )
    await state.set_state(BuyerStates.waiting_for_audience)


@router.message(BuyerStates.waiting_for_audience)
async def process_search_audience(message: Message, state: FSMContext):
    """Обработка целевой аудитории для поиска"""
    audience = None if message.text.lower() == "любая" else message.text
    await state.update_data(target_audience=audience)
    
    await message.answer(
        "Шаг 3 из 4\n"
        "🗣️ Важно ли наличие отзывов у блогера?",
        reply_markup=get_yes_no_keyboard("reviews_important")
    )
    await state.set_state(BuyerStates.waiting_for_reviews_preference)


@router.callback_query(F.data.startswith("yes_reviews_important") | F.data.startswith("no_reviews_important"), 
                      BuyerStates.waiting_for_reviews_preference)
async def process_reviews_preference(callback: CallbackQuery, state: FSMContext):
    """Обработка важности отзывов"""
    has_reviews = callback.data.startswith("yes_") if not callback.data.endswith("no_reviews_important") else None
    await state.update_data(has_reviews=has_reviews)
    
    await callback.answer()
    await callback.message.edit_text(
        "Шаг 4 из 4\n"
        "💰 Укажите ваш бюджет:\n"
        "Например: '5000-15000' или '10000' или 'любой' для пропуска"
    )
    await state.set_state(BuyerStates.waiting_for_budget)


@router.message(BuyerStates.waiting_for_budget)
async def process_budget_and_search(message: Message, state: FSMContext):
    """Обработка бюджета и выполнение поиска"""
    budget_text = message.text.lower()
    budget_min = None
    budget_max = None
    
    if budget_text != "любой":
        try:
            if "-" in budget_text:
                # Диапазон: "5000-15000"
                parts = budget_text.split("-")
                budget_min = int(parts[0].strip())
                budget_max = int(parts[1].strip())
            else:
                # Одно число: максимальный бюджет
                budget_max = int(budget_text)
        except ValueError:
            await message.answer("❌ Неверный формат бюджета. Попробуйте еще раз.")
            return
    
    # Получаем параметры поиска
    data = await state.get_data()
    
    # Выполняем поиск
    results = await search_bloggers(
        category=data.get('category'),
        target_audience=data.get('target_audience'),
        has_reviews=data.get('has_reviews'),
        budget_min=budget_min,
        budget_max=budget_max,
        limit=5,
        offset=0
    )
    
    await state.update_data(
        search_results=results,
        search_params={
            'category': data.get('category'),
            'target_audience': data.get('target_audience'),
            'has_reviews': data.get('has_reviews'),
            'budget_min': budget_min,
            'budget_max': budget_max
        },
        current_page=0
    )
    
    if not results:
        await message.answer(
            "😔 <b>По вашим критериям блогеры не найдены</b>\n\n"
            "Попробуйте:\n"
            "• Расширить бюджет\n"
            "• Изменить категорию\n"
            "• Убрать требование к отзывам\n\n"
            "🔍 Начать новый поиск?",
            reply_markup=get_yes_no_keyboard("new_search"),
            parse_mode="HTML"
        )
        await state.set_state(BuyerStates.viewing_results)
        return
    
    # Показываем результаты
    await show_search_results(message, results, 0)
    await state.set_state(BuyerStates.viewing_results)


async def show_search_results(message, results, page=0):
    """Показать результаты поиска"""
    results_text = f"🔍 <b>Найдено блогеров: {len(results)}</b>\n\n"
    
    for i, (blogger, seller) in enumerate(results, 1):
        price_info = "Договорная"
        if blogger.price_min or blogger.price_max:
            if blogger.price_min and blogger.price_max:
                price_info = f"{blogger.price_min}-{blogger.price_max} ₽"
            elif blogger.price_min:
                price_info = f"от {blogger.price_min} ₽"
            elif blogger.price_max:
                price_info = f"до {blogger.price_max} ₽"
        
        results_text += (
            f"<b>{i}. {blogger.name}</b>\n"
            f"📱 {blogger.platform} | 🎯 {blogger.category}\n"
            f"👥 {blogger.target_audience}\n"
            f"💰 {price_info}\n"
            f"🗣️ Отзывы: {'Есть' if blogger.has_reviews else 'Нет'}\n"
            f"⭐ Рейтинг продавца: {seller.rating:.1f}\n\n"
        )
    
    results_text += "Выберите блогера для получения контактов:"
    
    await message.answer(
        results_text,
        reply_markup=get_search_results_keyboard(results, page),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("select_blogger_"), BuyerStates.viewing_results)
async def select_blogger(callback: CallbackQuery, state: FSMContext):
    """Выбор блогера из результатов поиска"""
    blogger_id = int(callback.data.split("_")[2])
    
    # Находим блогера в результатах поиска
    data = await state.get_data()
    results = data.get('search_results', [])
    
    selected_blogger = None
    selected_seller = None
    
    for blogger, seller in results:
        if blogger.id == blogger_id:
            selected_blogger = blogger
            selected_seller = seller
            break
    
    if not selected_blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    # Показываем детали блогера
    price_info = "Договорная"
    if selected_blogger.price_min or selected_blogger.price_max:
        if selected_blogger.price_min and selected_blogger.price_max:
            price_info = f"{selected_blogger.price_min}-{selected_blogger.price_max} ₽"
        elif selected_blogger.price_min:
            price_info = f"от {selected_blogger.price_min} ₽"
        elif selected_blogger.price_max:
            price_info = f"до {selected_blogger.price_max} ₽"
    
    blogger_details = (
        f"📝 <b>Детали блогера</b>\n\n"
        f"👤 <b>Имя:</b> {selected_blogger.name}\n"
        f"🔗 <b>Ссылка:</b> {selected_blogger.url}\n"
        f"📱 <b>Платформа:</b> {selected_blogger.platform}\n"
        f"🎯 <b>Категория:</b> {selected_blogger.category}\n"
        f"👥 <b>Аудитория:</b> {selected_blogger.target_audience}\n"
        f"🗣️ <b>Отзывы:</b> {'Есть' if selected_blogger.has_reviews else 'Нет'}\n"
        f"💰 <b>Цена:</b> {price_info}\n"
        f"⭐ <b>Рейтинг продавца:</b> {selected_seller.rating:.1f}"
    )
    
    if selected_blogger.description:
        blogger_details += f"\n📝 <b>Описание:</b> {selected_blogger.description}"
    
    await callback.answer()
    await callback.message.edit_text(
        blogger_details,
        reply_markup=get_blogger_selection_keyboard(blogger_id, selected_seller.id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("get_contacts_"))
async def get_blogger_contacts(callback: CallbackQuery):
    """Получить контакты продавца блогера"""
    parts = callback.data.split("_")
    blogger_id = int(parts[2])
    seller_id = int(parts[3])
    
    # Здесь можно добавить логику сохранения факта получения контактов
    # Например, в таблицу contacts
    
    # Получаем информацию о продавце
    seller_user = await get_user_by_id(seller_id)
    
    if not seller_user:
        await callback.answer("❌ Продавец не найден")
        return
    
    contact_info = (
        f"📞 <b>Контакты продавца</b>\n\n"
        f"👤 <b>Имя:</b> {seller_user.first_name or 'Не указано'}\n"
    )
    
    if seller_user.username:
        contact_info += f"📱 <b>Telegram:</b> @{seller_user.username}\n"
    else:
        contact_info += f"🆔 <b>ID:</b> {seller_user.telegram_id}\n"
    
    contact_info += (
        f"⭐ <b>Рейтинг:</b> {seller_user.rating:.1f} ({seller_user.reviews_count} отзывов)\n\n"
        "💬 Теперь вы можете связаться с продавцом для обсуждения сотрудничества."
    )
    
    await callback.answer()
    await callback.message.edit_text(
        contact_info,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("search_page_"), BuyerStates.viewing_results)
async def search_pagination(callback: CallbackQuery, state: FSMContext):
    """Пагинация результатов поиска"""
    page = int(callback.data.split("_")[2])
    
    data = await state.get_data()
    search_params = data.get('search_params', {})
    
    # Выполняем поиск для новой страницы
    results = await search_bloggers(
        category=search_params.get('category'),
        target_audience=search_params.get('target_audience'),
        has_reviews=search_params.get('has_reviews'),
        budget_min=search_params.get('budget_min'),
        budget_max=search_params.get('budget_max'),
        limit=5,
        offset=page * 5
    )
    
    if not results:
        await callback.answer("😔 Больше результатов нет")
        return
    
    await state.update_data(search_results=results, current_page=page)
    
    # Обновляем сообщение с новыми результатами
    results_text = f"🔍 <b>Результаты поиска (страница {page + 1})</b>\n\n"
    
    for i, (blogger, seller) in enumerate(results, page * 5 + 1):
        price_info = "Договорная"
        if blogger.price_min or blogger.price_max:
            if blogger.price_min and blogger.price_max:
                price_info = f"{blogger.price_min}-{blogger.price_max} ₽"
            elif blogger.price_min:
                price_info = f"от {blogger.price_min} ₽"
            elif blogger.price_max:
                price_info = f"до {blogger.price_max} ₽"
        
        results_text += (
            f"<b>{i}. {blogger.name}</b>\n"
            f"📱 {blogger.platform} | 🎯 {blogger.category}\n"
            f"👥 {blogger.target_audience}\n"
            f"💰 {price_info}\n"
            f"🗣️ Отзывы: {'Есть' if blogger.has_reviews else 'Нет'}\n"
            f"⭐ Рейтинг продавца: {seller.rating:.1f}\n\n"
        )
    
    results_text += "Выберите блогера для получения контактов:"
    
    await callback.answer()
    await callback.message.edit_text(
        results_text,
        reply_markup=get_search_results_keyboard(results, page),
        parse_mode="HTML"
    )


# === ОБРАБОТЧИКИ ДЛЯ ПРЕРЫВАНИЯ ПРОЦЕССА ПОИСКА ===

@router.message(F.text == "📋 История поиска", BuyerStates())
async def interrupt_with_history(message: Message, state: FSMContext):
    """Прерывание поиска и переход к истории"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "📋 История поиска пока не реализована.\n"
        "Эта функция будет добавлена в следующих обновлениях."
    )


@router.message(F.text == "💳 Подписка", BuyerStates())
async def interrupt_with_subscription_buyer(message: Message, state: FSMContext):
    """Прерывание поиска и переход к подписке"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "Переходим к разделу подписки..."
    )


@router.message(F.text == "🔧 Управление подпиской", BuyerStates())
async def interrupt_with_subscription_management_buyer(message: Message, state: FSMContext):
    """Прерывание поиска и переход к управлению подпиской"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "Переходим к управлению подпиской..."
    )


@router.message(F.text == "⚙️ Настройки", BuyerStates())
async def interrupt_with_settings_buyer(message: Message, state: FSMContext):
    """Прерывание поиска и переход к настройкам"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "Переходим к настройкам..."
    )


@router.message(F.text == "📊 Статистика", BuyerStates())
async def interrupt_with_statistics_buyer(message: Message, state: FSMContext):
    """Прерывание поиска и переход к статистике"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "Переходим к статистике..."
    )


@router.message(F.text == "🔍 Поиск блогеров", BuyerStates())
async def restart_search(message: Message, state: FSMContext):
    """Перезапуск поиска если уже в процессе"""
    await state.clear()
    await message.answer("🔄 Перезапускаем поиск...")
    await universal_start_search(message, state)


# Обработчик для команды отмены
@router.message(F.text.in_({"❌ Отмена", "/cancel", "отмена", "Отмена"}), BuyerStates())
async def cancel_search(message: Message, state: FSMContext):
    """Отмена поиска"""
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.\n\n"
        "Вы можете начать заново или воспользоваться другими функциями."
    )


# Обработчик кнопки "Отмена" в inline клавиатурах
@router.callback_query(F.data == "cancel_action", BuyerStates())
async def cancel_action_callback_buyer(callback: CallbackQuery, state: FSMContext):
    """Отмена действия через inline кнопку"""
    await state.clear()
    await callback.answer("❌ Действие отменено")
    await callback.message.edit_text(
        "❌ Поиск отменен.\n\n"
        "Вы можете начать заново или воспользоваться другими функциями."
    )


@router.callback_query(F.data == "new_search")
async def new_search(callback: CallbackQuery, state: FSMContext):
    """Начать новый поиск"""
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "🔍 <b>Новый поиск блогеров</b>\n\n"
        "Шаг 1 из 4\n"
        "🎯 Выберите интересующую категорию:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_category)


@router.callback_query(F.data == "back_to_results")
async def back_to_results(callback: CallbackQuery, state: FSMContext):
    """Вернуться к результатам поиска"""
    data = await state.get_data()
    results = data.get('search_results', [])
    page = data.get('current_page', 0)
    
    if not results:
        await callback.answer("❌ Нет результатов для отображения")
        return
    
    await callback.answer()
    await show_search_results(callback.message, results, page)


@router.callback_query(F.data == "yes_new_search")
async def yes_new_search(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[DEBUG] yes_new_search handler called. callback.data={callback.data}, user_id={callback.from_user.id}")
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "🔍 <b>Новый поиск блогеров</b>\n\n"
        "Шаг 1 из 4\n"
        "🎯 Выберите интересующую категорию:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BuyerStates.waiting_for_category)


@router.callback_query(F.data == "no_new_search")
async def no_new_search(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[DEBUG] no_new_search handler called. callback.data={callback.data}, user_id={callback.from_user.id}")
    await state.clear()
    user = await get_user(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu_buyer(user.subscription_status == SubscriptionStatus.ACTIVE),
        parse_mode="HTML"
    )


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
            return User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=UserRole(row['role']),
                subscription_status=SubscriptionStatus(row['subscription_status']),
                subscription_end_date=datetime.fromisoformat(row['subscription_end_date']) if row['subscription_end_date'] else None,
                rating=row['rating'],
                reviews_count=row['reviews_count'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        return None


@router.callback_query(F.data.startswith("complaint_"))
async def start_complaint(callback: CallbackQuery, state: FSMContext):
    """Начать процесс подачи жалобы на блогера"""
    blogger_id = int(callback.data.split("_")[1])
    
    # Получаем информацию о блогере
    blogger = await get_blogger(blogger_id)
    if not blogger:
        await callback.answer("❌ Блогер не найден")
        return
    
    # Сохраняем ID блогера в состояние
    await state.update_data(complaint_blogger_id=blogger_id, complaint_blogger_name=blogger.name)
    await state.set_state(ComplaintStates.waiting_for_complaint_reason)
    
    await callback.answer()
    await callback.message.edit_text(
        f"⚠️ <b>Подача жалобы на блогера</b>\n\n"
        f"📝 <b>Блогер:</b> {blogger.name}\n"
        f"📱 <b>Платформа:</b> {blogger.platform}\n\n"
        f"💬 <b>Напишите причину жалобы:</b>\n"
        f"Опишите подробно, что вас беспокоит в этом блогере "
        f"(например: подозрение на накрутку, фейковые подписчики, неактуальная информация и т.д.)\n\n"
        f"Или напишите 'отмена' для выхода.",
        parse_mode="HTML"
    )


@router.message(ComplaintStates.waiting_for_complaint_reason)
async def process_complaint_reason(message: Message, state: FSMContext):
    """Обработка причины жалобы"""
    if message.text.lower() in ['отмена', 'cancel', '/cancel']:
        await state.clear()
        await message.answer("❌ Подача жалобы отменена.")
        return
    
    reason = message.text.strip()
    if len(reason) < 10:
        await message.answer(
            "⚠️ Причина жалобы слишком короткая. "
            "Пожалуйста, опишите проблему подробнее (минимум 10 символов)."
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    blogger_id = data.get('complaint_blogger_id')
    blogger_name = data.get('complaint_blogger_name')
    
    user = await get_user(message.from_user.id)
    username = message.from_user.username or f"{message.from_user.first_name or 'Пользователь'}"
    
    # Сохраняем жалобу в базу данных
    success = await create_complaint(
        blogger_id=blogger_id,
        blogger_name=blogger_name,
        user_id=user.id,
        username=username,
        reason=reason
    )
    
    await state.clear()
    
    if success:
        await message.answer(
            f"✅ <b>Жалоба успешно отправлена!</b>\n\n"
            f"📝 <b>Блогер:</b> {blogger_name}\n"
            f"💬 <b>Причина:</b> {reason[:100]}{'...' if len(reason) > 100 else ''}\n\n"
            f"🔍 Ваша жалоба будет рассмотрена модератором в ближайшее время.\n"
            f"📊 Все жалобы автоматически записываются в систему учета для анализа.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при отправке жалобы</b>\n\n"
            "Попробуйте еще раз позже или обратитесь в поддержку.",
            parse_mode="HTML"
        ) 