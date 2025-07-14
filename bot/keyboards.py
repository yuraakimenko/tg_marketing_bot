from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Продажник", callback_data="role_seller")],
        [InlineKeyboardButton(text="🧑‍💼 Закупщик", callback_data="role_buyer")]
    ])


def get_main_menu_seller(has_active_subscription: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню для продажника"""
    keyboard = [
        [KeyboardButton(text="➕ Добавить блогера")],
        [KeyboardButton(text="📝 Мои блогеры"), KeyboardButton(text="📊 Статистика")]
    ]
    
    # Если есть активная подписка, добавляем кнопку управления
    if has_active_subscription:
        keyboard.append([KeyboardButton(text="💳 Подписка"), KeyboardButton(text="🔧 Управление подпиской")])
    else:
        keyboard.append([KeyboardButton(text="💳 Подписка")])
    
    keyboard.append([KeyboardButton(text="⚙️ Настройки")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )


def get_main_menu_buyer(has_active_subscription: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню для закупщика"""
    keyboard = [
        [KeyboardButton(text="🔍 Поиск блогеров")],
        [KeyboardButton(text="📋 История поиска"), KeyboardButton(text="📊 Статистика")]
    ]
    
    # Если есть активная подписка, добавляем кнопку управления
    if has_active_subscription:
        keyboard.append([KeyboardButton(text="💳 Подписка"), KeyboardButton(text="🔧 Управление подпиской")])
    else:
        keyboard.append([KeyboardButton(text="💳 Подписка")])
    
    keyboard.append([KeyboardButton(text="⚙️ Настройки")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 1 месяц - 500₽", callback_data="pay_monthly")],
        [InlineKeyboardButton(text="💎 3 месяца - 1350₽ (-10%)", callback_data="pay_quarterly")],
        [InlineKeyboardButton(text="👑 12 месяцев - 5000₽ (-17%)", callback_data="pay_yearly")],
        [InlineKeyboardButton(text="ℹ️ Подробнее о подписке", callback_data="subscription_info")]
    ])


def get_subscription_management_keyboard(auto_renewal: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура управления подпиской (обновленная - только автопродление)"""
    keyboard = []
    
    if auto_renewal:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Отключить автоПРОДЛЕНИЕ", 
            callback_data="toggle_auto_renewal"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Включить автоПРОДЛЕНИЕ", 
            callback_data="toggle_auto_renewal"
        )])
    
    keyboard.append([InlineKeyboardButton(text="📊 История платежей", callback_data="payment_history")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы (обновленная)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton(text="📺 YouTube", callback_data="platform_youtube")],
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="🎵 TikTok", callback_data="platform_tiktok")],
        [InlineKeyboardButton(text="🌐 VK", callback_data="platform_vk")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_platforms_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформ для поиска (множественный выбор)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Instagram", callback_data="select_platform_instagram")],
        [InlineKeyboardButton(text="📺 YouTube", callback_data="select_platform_youtube")],
        [InlineKeyboardButton(text="📱 Telegram", callback_data="select_platform_telegram")],
        [InlineKeyboardButton(text="🎵 TikTok", callback_data="select_platform_tiktok")],
        [InlineKeyboardButton(text="🌐 VK", callback_data="select_platform_vk")],
        [InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_platforms_selection")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории (обновленная с новыми категориями)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💃 Лайфстайл", callback_data="category_lifestyle")],
        [InlineKeyboardButton(text="🏃‍♀️ Спорт", callback_data="category_sport")],
        [InlineKeyboardButton(text="🥗 Питание", callback_data="category_nutrition")],
        [InlineKeyboardButton(text="🏥 Медицина", callback_data="category_medicine")],
        [InlineKeyboardButton(text="💕 Отношения", callback_data="category_relationships")],
        [InlineKeyboardButton(text="💄 Красота", callback_data="category_beauty")],
        [InlineKeyboardButton(text="👗 Мода", callback_data="category_fashion")],
        [InlineKeyboardButton(text="✈️ Путешествия", callback_data="category_travel")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="category_business")],
        [InlineKeyboardButton(text="📚 Образование", callback_data="category_education")],
        [InlineKeyboardButton(text="🎬 Развлечения", callback_data="category_entertainment")],
        [InlineKeyboardButton(text="💻 Технологии", callback_data="category_technology")],
        [InlineKeyboardButton(text="👶 Родительство", callback_data="category_parenting")],
        [InlineKeyboardButton(text="💰 Финансы", callback_data="category_finance")],
        [InlineKeyboardButton(text="❓ Неважно", callback_data="category_not_important")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_categories_selection_keyboard(selected_categories: list = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора категорий для поиска (множественный выбор)"""
    if selected_categories is None:
        selected_categories = []
    
    keyboard = []
    categories = [
        ("💃 Лайфстайл", "category_lifestyle"),
        ("🏃‍♀️ Спорт", "category_sport"),
        ("🥗 Питание", "category_nutrition"),
        ("🏥 Медицина", "category_medicine"),
        ("💕 Отношения", "category_relationships"),
        ("💄 Красота", "category_beauty"),
        ("👗 Мода", "category_fashion"),
        ("✈️ Путешествия", "category_travel"),
        ("💼 Бизнес", "category_business"),
        ("📚 Образование", "category_education"),
        ("🎬 Развлечения", "category_entertainment"),
        ("💻 Технологии", "category_technology"),
        ("👶 Родительство", "category_parenting"),
        ("💰 Финансы", "category_finance"),
        ("❓ Неважно", "category_not_important")
    ]
    
    for name, value in categories:
        if value in selected_categories:
            keyboard.append([InlineKeyboardButton(text=f"✅ {name}", callback_data=f"toggle_category_{value}")])
        else:
            keyboard.append([InlineKeyboardButton(text=f"⬜ {name}", callback_data=f"toggle_category_{value}")])
    
    keyboard.append([InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_categories_selection")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_budget_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора бюджета (кратный 1000)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 4,000₽", callback_data="budget_4000")],
        [InlineKeyboardButton(text="💰 10,000₽", callback_data="budget_10000")],
        [InlineKeyboardButton(text="💰 20,000₽", callback_data="budget_20000")],
        [InlineKeyboardButton(text="💰 50,000₽", callback_data="budget_50000")],
        [InlineKeyboardButton(text="💰 100,000₽", callback_data="budget_100000")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="budget_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_budget_range_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора диапазона бюджета"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 4,000₽ - 10,000₽", callback_data="budget_range_4000_10000")],
        [InlineKeyboardButton(text="💰 10,000₽ - 20,000₽", callback_data="budget_range_10000_20000")],
        [InlineKeyboardButton(text="💰 20,000₽ - 50,000₽", callback_data="budget_range_20000_50000")],
        [InlineKeyboardButton(text="💰 50,000₽ - 100,000₽", callback_data="budget_range_50000_100000")],
        [InlineKeyboardButton(text="💰 100,000₽+", callback_data="budget_range_100000_plus")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="budget_range_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_price_stories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за 4 истории (кратная 1000)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 4,000₽", callback_data="price_stories_4000")],
        [InlineKeyboardButton(text="💰 10,000₽", callback_data="price_stories_10000")],
        [InlineKeyboardButton(text="💰 20,000₽", callback_data="price_stories_20000")],
        [InlineKeyboardButton(text="💰 50,000₽", callback_data="price_stories_50000")],
        [InlineKeyboardButton(text="💰 100,000₽", callback_data="price_stories_100000")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="price_stories_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_price_post_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за пост (кратная 1000)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 4,000₽", callback_data="price_post_4000")],
        [InlineKeyboardButton(text="💰 10,000₽", callback_data="price_post_10000")],
        [InlineKeyboardButton(text="💰 20,000₽", callback_data="price_post_20000")],
        [InlineKeyboardButton(text="💰 50,000₽", callback_data="price_post_50000")],
        [InlineKeyboardButton(text="💰 100,000₽", callback_data="price_post_100000")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="price_post_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_price_video_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за видео (кратная 1000)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 4,000₽", callback_data="price_video_4000")],
        [InlineKeyboardButton(text="💰 10,000₽", callback_data="price_video_10000")],
        [InlineKeyboardButton(text="💰 20,000₽", callback_data="price_video_20000")],
        [InlineKeyboardButton(text="💰 50,000₽", callback_data="price_video_50000")],
        [InlineKeyboardButton(text="💰 100,000₽", callback_data="price_video_100000")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="price_video_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_yes_no_keyboard(action: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура Да/Нет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"yes_{action}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"no_{action}")
        ]
    ])


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура оценки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rating_1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rating_2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating_3"),
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating_4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating_5")
        ]
    ])


def get_complaint_reasons_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура причин жалобы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Некачественный контент", callback_data="complaint_reason_low_quality")],
        [InlineKeyboardButton(text="💰 Завышенные цены", callback_data="complaint_reason_high_price")],
        [InlineKeyboardButton(text="⏰ Нарушение сроков", callback_data="complaint_reason_deadline")],
        [InlineKeyboardButton(text="🤥 Несоответствие описанию", callback_data="complaint_reason_misleading")],
        [InlineKeyboardButton(text="📞 Плохая коммуникация", callback_data="complaint_reason_communication")],
        [InlineKeyboardButton(text="📝 Другое", callback_data="complaint_reason_other")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])


def get_blogger_action_keyboard(blogger_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с блогером"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подходит", callback_data=f"blogger_suitable_{blogger_id}")],
        [InlineKeyboardButton(text="❌ Не подходит", callback_data=f"blogger_not_suitable_{blogger_id}")],
        [InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"blogger_complaint_{blogger_id}")]
    ])


def get_blogger_list_keyboard(bloggers, page=0) -> InlineKeyboardMarkup:
    """Клавиатура списка блогеров"""
    keyboard = []
    
    start = page * 5
    end = start + 5
    
    for i, blogger in enumerate(bloggers[start:end], start):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{blogger.name} ({blogger.platform})",
                callback_data=f"blogger_{blogger.id}"
            )
        ])
    
    # Навигация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bloggers_page_{page-1}"))
    if end < len(bloggers):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bloggers_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_blogger_details_keyboard(blogger_id: int) -> InlineKeyboardMarkup:
    """Клавиатура деталей блогера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_blogger_{blogger_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_blogger_{blogger_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_bloggers")]
    ])


def get_search_results_keyboard(results, page=0) -> InlineKeyboardMarkup:
    """Клавиатура результатов поиска"""
    keyboard = []
    
    for i, (blogger, seller) in enumerate(results):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{blogger.name} - {blogger.platform}",
                callback_data=f"select_blogger_{blogger.id}"
            )
        ])
    
    # Кнопки навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Предыдущие", callback_data=f"search_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(text="🔄 Показать еще", callback_data=f"search_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(text="🔍 Новый поиск", callback_data="new_search")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_blogger_selection_keyboard(blogger_id: int, seller_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора блогера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Получить контакты", callback_data=f"get_contacts_{blogger_id}_{seller_id}")],
        [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"review_{seller_id}")],
        [InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complaint_{blogger_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="back_to_results")]
    ])


def get_payment_confirmation_keyboard(payment_data: dict) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения платежа"""
    keyboard = []
    
    # Если это mock-платеж, добавляем кнопку имитации оплаты
    if payment_data.get('is_mock'):
        keyboard.append([InlineKeyboardButton(
            text="✅ Имитировать успешную оплату", 
            callback_data=f"mock_payment_success_{payment_data['invoice_id']}"
        )])
        keyboard.append([InlineKeyboardButton(
            text="❌ Имитировать неудачную оплату", 
            callback_data=f"mock_payment_failure_{payment_data['invoice_id']}"
        )])
    else:
        # Для реальных платежей - ссылка на оплату
        keyboard.append([InlineKeyboardButton(
            text="💳 Перейти к оплате", 
            url=payment_data['payment_url']
        )])
        keyboard.append([InlineKeyboardButton(
            text="🔄 Проверить статус", 
            callback_data=f"check_payment_{payment_data['invoice_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_subscription_cancel_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отменить", callback_data="confirm_cancel_subscription")],
        [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="keep_subscription")]
    ])


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить роль", callback_data="change_role")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="help")],
        [InlineKeyboardButton(text="📞 Поддержка", callback_data="support")]
    ]) 