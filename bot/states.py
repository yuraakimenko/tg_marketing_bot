from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_for_role = State()


class SellerStates(StatesGroup):
    """Состояния для продажника"""
    # Добавление блогера (упрощенный процесс)
    waiting_for_platform = State()  # 1. Выбор платформ
    waiting_for_blogger_url = State()  # 2. Ссылка на профиль
    waiting_for_blogger_name = State()  # 3. Имя блогера
    
    # Категории (максимум 3)
    waiting_for_categories = State()  # Выбор категорий
    
    # Статистика
    waiting_for_subscribers_count = State()  # Количество подписчиков
    
    # Цены
    waiting_for_price_stories = State()  # Цена за сторис
    waiting_for_price_reels = State()  # Цена за пост/рилс
    waiting_for_price_video = State()  # Цена за видео
    
    # Описание
    waiting_for_blogger_description = State()  # Описание блогера
    
    # Редактирование блогера
    editing_blogger = State()
    waiting_for_edit_field = State()
    waiting_for_new_value = State()


class BuyerStates(StatesGroup):
    """Состояния для закупщика"""
    # Поиск блогеров
    waiting_for_platforms = State()  # Выбор платформ
    waiting_for_target_age = State()  # Целевой возраст (минимальный)
    waiting_for_target_age_max = State()  # Целевой возраст (максимальный)
    waiting_for_target_gender = State()  # Целевой пол
    waiting_for_categories = State()  # Категории
    waiting_for_budget = State()  # Бюджет минимальный (кратный 1000)
    waiting_for_budget_max = State()  # Бюджет максимальный (кратный 1000)
    waiting_for_additional_criteria = State()  # Дополнительные критерии
    
    # Просмотр результатов
    viewing_results = State()
    
    # Оценка менеджера
    waiting_for_deal_completion = State()  # Состоялась ли сделка
    waiting_for_manager_rating = State()  # Оценка менеджера


class ReviewStates(StatesGroup):
    """Состояния для отзывов"""
    waiting_for_rating = State()
    waiting_for_comment = State()


class ComplaintStates(StatesGroup):
    """Состояния для жалоб"""
    waiting_for_complaint_reason = State()
    waiting_for_reason = State()  # Альтернативное название для совместимости 