from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_for_role = State()


class SellerStates(StatesGroup):
    """Состояния для продажника"""
    # Добавление блогера (новый порядок)
    waiting_for_platform = State()  # 1. Сначала соцсеть
    waiting_for_blogger_url = State()  # 2. Потом ссылка
    waiting_for_blogger_name = State()  # 3. Имя блогера
    
    # Демография аудитории
    waiting_for_audience_13_17 = State()  # % аудитории 13-17 лет
    waiting_for_audience_18_24 = State()  # % аудитории 18-24 лет
    waiting_for_audience_25_35 = State()  # % аудитории 25-35 лет
    waiting_for_audience_35_plus = State()  # % аудитории 35+ лет
    
    # Пол аудитории
    waiting_for_female_percent = State()  # % женской аудитории
    waiting_for_male_percent = State()  # % мужской аудитории
    
    # Категории (максимум 3)
    waiting_for_categories = State()  # Выбор категорий
    waiting_for_additional_category = State()  # Дополнительная категория
    
    # Цены (кратные 1000)
    waiting_for_price_stories = State()  # Цена за 4 истории
    waiting_for_price_post = State()  # Цена за пост
    waiting_for_price_video = State()  # Цена за видео
    
    # Дополнительная информация
    waiting_for_has_reviews = State()  # Наличие отзывов
    waiting_for_is_registered_rkn = State()  # Регистрация в РКН
    waiting_for_official_payment = State()  # Возможна офиц. оплата
    
    # Статистика (загрузка)
    waiting_for_statistics = State()  # Загрузка статистики
    
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
    waiting_for_target_age = State()  # Целевой возраст
    waiting_for_target_gender = State()  # Целевой пол
    waiting_for_categories = State()  # Категории
    waiting_for_budget = State()  # Бюджет (кратный 1000)
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