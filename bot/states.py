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
    
    # Категории (максимум 3)
    waiting_for_categories = State()  # Выбор категорий
    waiting_for_additional_category = State()  # Дополнительная категория
    
    # Статистика
    waiting_for_subscribers_count = State()  # Количество подписчиков
    
    # Охваты сторис (вилка)
    waiting_for_stories_reach_min = State()  # Минимальный охват сторис
    waiting_for_stories_reach_max = State()  # Максимальный охват сторис
    
    # Цена за 4 истории
    waiting_for_price_stories = State()  # Цена за 4 истории
    
    # Охваты рилс (вилка)
    waiting_for_reels_reach_min = State()  # Минимальный охват рилс
    waiting_for_reels_reach_max = State()  # Максимальный охват рилс
    
    # Цена рилс
    waiting_for_price_reels = State()  # Цена за рилс
    
    # Статистика - фото пруфы
    waiting_for_stats_photos = State()  # Загрузка фото статистики
    waiting_for_stats_photos_confirmation = State()  # Подтверждение загруженных фото
    
    # Описание
    waiting_for_blogger_description = State()  # Описание блогера
    
    # Редактирование блогера
    editing_blogger = State()
    waiting_for_edit_field = State()
    waiting_for_new_value = State()
    
    # Новые состояния для статистики по платформам
    waiting_for_platform_stats = State()  # Выбор платформы для добавления статистики
    waiting_for_platform_subscribers = State()  # Подписчики для платформы
    waiting_for_platform_engagement = State()  # Вовлеченность для платформы
    waiting_for_platform_avg_views = State()  # Средние просмотры для платформы
    waiting_for_platform_avg_likes = State()  # Средние лайки для платформы
    
    # Демография для платформы
    waiting_for_platform_age_13_17 = State()  # % аудитории 13-17 лет
    waiting_for_platform_age_18_24 = State()  # % аудитории 18-24 лет
    waiting_for_platform_age_25_35 = State()  # % аудитории 25-35 лет
    waiting_for_platform_age_35_plus = State()  # % аудитории 35+ лет
    
    # Пол аудитории для платформы
    waiting_for_platform_female_percent = State()  # % женской аудитории
    
    # Цены для платформы
    waiting_for_platform_price_stories = State()  # Цена за истории
    waiting_for_platform_price_reels = State()  # Цена за рилс
    waiting_for_platform_price_post = State()  # Цена за пост
    
    # Охваты для платформы
    waiting_for_platform_stories_reach_min = State()  # Минимальный охват сторис
    waiting_for_platform_stories_reach_max = State()  # Максимальный охват сторис
    waiting_for_platform_reels_reach_min = State()  # Минимальный охват рилс
    waiting_for_platform_reels_reach_max = State()  # Максимальный охват рилс
    
    # Фото статистики для платформы
    waiting_for_platform_stats_photos = State()  # Загрузка фото статистики для платформы
    waiting_for_platform_stats_photos_confirmation = State()  # Подтверждение фото для платформы


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