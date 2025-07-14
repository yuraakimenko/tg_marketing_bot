from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Продажник", callback_data="role_seller")],
        [InlineKeyboardButton(text="🧑‍💼 Закупщик", callback_data="role_buyer")]
    ])


def get_main_menu_seller(has_active_subscription: bool) -> ReplyKeyboardMarkup:
    """Главное меню для продажника"""
    keyboard_buttons = [
        [KeyboardButton(text="📝 Добавить блогера")],
        [KeyboardButton(text="📋 Мои блогеры")],
        [KeyboardButton(text="✏️ Редактировать блогера")]
    ]
    
    keyboard_buttons.extend([
        [KeyboardButton(text="💳 Подписка")],
        [KeyboardButton(text="⚙️ Настройки")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_main_menu_buyer(has_active_subscription: bool) -> ReplyKeyboardMarkup:
    """Главное меню для закупщика"""
    keyboard_buttons = [
        [KeyboardButton(text="🔍 Поиск блогеров")],
        [KeyboardButton(text="📋 История поиска")],
        [KeyboardButton(text="📊 Статистика")]
    ]
    
    keyboard_buttons.extend([
        [KeyboardButton(text="💳 Подписка")],
        [KeyboardButton(text="⚙️ Настройки")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить роли", callback_data="change_role")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton(text="📺 YouTube", callback_data="platform_youtube")],
        [InlineKeyboardButton(text="📱 TikTok", callback_data="platform_tiktok")],
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="📱 VK", callback_data="platform_vk")]
    ])


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категорий"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Образ жизни", callback_data="category_lifestyle")],
        [InlineKeyboardButton(text="⚽ Спорт", callback_data="category_sport")],
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
        [InlineKeyboardButton(text="✅ Подтвердить выбор", callback_data="confirm_categories")]
    ])


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура да/нет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="yes_no_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="yes_no_no")]
    ])


def get_blogger_list_keyboard(bloggers, action="view") -> InlineKeyboardMarkup:
    """Клавиатура списка блогеров"""
    buttons = []
    for blogger in bloggers:
        button_text = f"📝 {blogger.name}"
        callback_data = f"blogger_{blogger.id}_{action}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_blogger_details_keyboard(blogger, action="view") -> InlineKeyboardMarkup:
    """Клавиатура деталей блогера"""
    buttons = []
    
    if action == "edit":
        buttons.extend([
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_blogger_{blogger.id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_blogger_{blogger.id}")]
        ])
    else:
        buttons.extend([
            [InlineKeyboardButton(text="📞 Получить контакты", callback_data=f"contact_{blogger.id}")],
            [InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complain_{blogger.id}")]
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_bloggers")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_search_results_keyboard(results) -> InlineKeyboardMarkup:
    """Клавиатура результатов поиска"""
    buttons = []
    for blogger, seller in results:
        button_text = f"📝 {blogger.name} ({seller.rating:.1f}⭐)"
        callback_data = f"blogger_{blogger.id}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_blogger_selection_keyboard(blogger) -> InlineKeyboardMarkup:
    """Клавиатура выбора блогера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Получить контакты", callback_data=f"contact_{blogger.id}")],
        [InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complain_{blogger.id}")],
        [InlineKeyboardButton(text="🔙 Назад к результатам", callback_data="back_to_results")]
    ])


def get_price_stories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за истории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 000₽", callback_data="price_stories_5000")],
        [InlineKeyboardButton(text="10 000₽", callback_data="price_stories_10000")],
        [InlineKeyboardButton(text="15 000₽", callback_data="price_stories_15000")],
        [InlineKeyboardButton(text="20 000₽", callback_data="price_stories_20000")],
        [InlineKeyboardButton(text="Другая цена", callback_data="price_stories_custom")]
    ])


def get_price_post_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за пост"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 000₽", callback_data="price_post_10000")],
        [InlineKeyboardButton(text="20 000₽", callback_data="price_post_20000")],
        [InlineKeyboardButton(text="30 000₽", callback_data="price_post_30000")],
        [InlineKeyboardButton(text="50 000₽", callback_data="price_post_50000")],
        [InlineKeyboardButton(text="Другая цена", callback_data="price_post_custom")]
    ])


def get_price_video_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цены за видео"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="20 000₽", callback_data="price_video_20000")],
        [InlineKeyboardButton(text="50 000₽", callback_data="price_video_50000")],
        [InlineKeyboardButton(text="100 000₽", callback_data="price_video_100000")],
        [InlineKeyboardButton(text="200 000₽", callback_data="price_video_200000")],
        [InlineKeyboardButton(text="Другая цена", callback_data="price_video_custom")]
    ])


def get_platforms_multi_keyboard(selected_platforms=None) -> InlineKeyboardMarkup:
    """Клавиатура множественного выбора платформ"""
    if selected_platforms is None:
        selected_platforms = []
    
    buttons = []
    platforms = [
        ("📱 Instagram", "instagram"),
        ("📺 YouTube", "youtube"),
        ("📱 TikTok", "tiktok"),
        ("📱 Telegram", "telegram"),
        ("📱 VK", "vk")
    ]
    
    for name, platform in platforms:
        if platform in selected_platforms:
            button_text = f"✅ {name}"
        else:
            button_text = f"❌ {name}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"toggle_platform_{platform}")])
    
    buttons.append([InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_platforms_selection")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) 