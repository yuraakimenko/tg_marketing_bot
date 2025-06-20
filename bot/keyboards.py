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
                text=f"{blogger.name} - {blogger.category}",
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
        [InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="back_to_results")]
    ])


def get_yes_no_keyboard(action: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура Да/Нет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"yes_{action}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"no_{action}")
        ]
    ])


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 YouTube", callback_data="platform_youtube")],
        [InlineKeyboardButton(text="📸 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton(text="🎵 TikTok", callback_data="platform_tiktok")],
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="🌐 Другое", callback_data="platform_other")]
    ])


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏥 Медицина", callback_data="category_медицина")],
        [InlineKeyboardButton(text="💕 Отношения", callback_data="category_отношения")],
        [InlineKeyboardButton(text="👶 Дети", callback_data="category_дети")],
        [InlineKeyboardButton(text="🏠 Дом и быт", callback_data="category_дом")],
        [InlineKeyboardButton(text="💄 Красота", callback_data="category_красота")],
        [InlineKeyboardButton(text="🍳 Кулинария", callback_data="category_кулинария")],
        [InlineKeyboardButton(text="🎮 Развлечения", callback_data="category_развлечения")],
        [InlineKeyboardButton(text="📚 Образование", callback_data="category_образование")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="category_бизнес")],
        [InlineKeyboardButton(text="🌐 Другое", callback_data="category_other")]
    ])


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура оценки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1⭐", callback_data="rating_1"),
            InlineKeyboardButton(text="2⭐", callback_data="rating_2"),
            InlineKeyboardButton(text="3⭐", callback_data="rating_3"),
            InlineKeyboardButton(text="4⭐", callback_data="rating_4"),
            InlineKeyboardButton(text="5⭐", callback_data="rating_5")
        ]
    ])


def get_subscription_management_keyboard(auto_renewal: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура управления подпиской"""
    keyboard = []
    
    if auto_renewal:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Отключить автообновление", 
            callback_data="disable_auto_renewal"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Включить автообновление", 
            callback_data="enable_auto_renewal"
        )])
    
    keyboard.extend([
        [InlineKeyboardButton(
            text="⏸️ Приостановить до окончания", 
            callback_data="suspend_subscription"
        )],
        [InlineKeyboardButton(
            text="❌ Отменить подписку полностью", 
            callback_data="cancel_subscription_full"
        )],
        [InlineKeyboardButton(
            text="📊 История платежей", 
            callback_data="payment_history"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="back_to_main"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_subscription_cancel_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, отменить подписку", 
            callback_data="confirm_cancel_subscription"
        )],
        [InlineKeyboardButton(
            text="❌ Нет, оставить как есть", 
            callback_data="cancel_subscription_cancel"
        )]
    ])


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить роль", callback_data="change_role")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]) 