from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_for_role = State()


class SellerStates(StatesGroup):
    """Состояния для продажника"""
    # Добавление блогера
    waiting_for_blogger_name = State()
    waiting_for_blogger_url = State()
    waiting_for_blogger_platform = State()
    waiting_for_blogger_category = State()
    waiting_for_blogger_audience = State()
    waiting_for_blogger_reviews = State()
    waiting_for_blogger_price_min = State()
    waiting_for_blogger_price_max = State()
    waiting_for_blogger_description = State()
    
    # Редактирование блогера
    editing_blogger = State()
    waiting_for_edit_field = State()
    waiting_for_new_value = State()


class BuyerStates(StatesGroup):
    """Состояния для закупщика"""
    # Поиск блогеров
    waiting_for_category = State()
    waiting_for_audience = State()
    waiting_for_reviews_preference = State()
    waiting_for_budget = State()
    
    # Просмотр результатов
    viewing_results = State()


class ReviewStates(StatesGroup):
    """Состояния для отзывов"""
    waiting_for_rating = State()
    waiting_for_comment = State() 