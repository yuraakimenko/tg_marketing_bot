from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(Enum):
    SELLER = "seller"
    BUYER = "buyer"


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"  # Отменена пользователем
    AUTO_RENEWAL_OFF = "auto_renewal_off"  # Активна, но без автопродления


class Platform(Enum):
    """Платформы социальных сетей"""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TELEGRAM = "telegram"
    TIKTOK = "tiktok"
    VK = "vk"


class BlogCategory(Enum):
    """Категории блогов"""
    LIFESTYLE = "lifestyle"
    SPORT = "sport"
    NUTRITION = "nutrition"
    MEDICINE = "medicine"
    RELATIONSHIPS = "relationships"
    BEAUTY = "beauty"
    FASHION = "fashion"
    TRAVEL = "travel"
    BUSINESS = "business"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    TECHNOLOGY = "technology"
    PARENTING = "parenting"
    FINANCE = "finance"
    NOT_IMPORTANT = "not_important"  # "неважно"


@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.SELLER
    subscription_status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    subscription_end_date: Optional[datetime] = None
    rating: float = 0.0
    reviews_count: int = 0
    is_vip: bool = False  # VIP статус для менеджеров
    penalty_amount: int = 0  # Сумма штрафов
    is_blocked: bool = False  # Блокировка за штрафы
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Blogger:
    """Модель блогера"""
    id: int
    seller_id: int
    name: str
    url: str
    platform: Platform  # Платформа (instagram, youtube, telegram, etc.)
    
    # Демография аудитории
    audience_13_17_percent: Optional[int] = None  # % аудитории 13-17 лет
    audience_18_24_percent: Optional[int] = None  # % аудитории 18-24 лет
    audience_25_35_percent: Optional[int] = None  # % аудитории 25-35 лет
    audience_35_plus_percent: Optional[int] = None  # % аудитории 35+ лет
    
    # Пол аудитории
    female_percent: Optional[int] = None  # % женской аудитории
    male_percent: Optional[int] = None  # % мужской аудитории
    
    # Категории (максимум 3)
    categories: List[BlogCategory] = field(default_factory=list)  # Список категорий
    
    # Цены
    price_stories: Optional[int] = None  # Цена за 4 истории
    price_post: Optional[int] = None  # Цена за пост
    price_video: Optional[int] = None  # Цена за видео
    
    # Дополнительная информация
    has_reviews: bool = False
    is_registered_rkn: bool = False  # Зарегистрирован в РКН
    official_payment_possible: bool = False  # Возможна офиц. оплата (СЗ/ИП)
    
    # Статистика (будет разной для разных платформ)
    subscribers_count: Optional[int] = None
    avg_views: Optional[int] = None  # Средние просмотры
    avg_likes: Optional[int] = None  # Средние лайки
    engagement_rate: Optional[float] = None  # Процент вовлеченности
    
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchFilter:
    """Модель фильтра поиска для закупщиков"""
    id: int
    buyer_id: int
    platforms: List[Platform] = field(default_factory=list)  # Выбранные платформы
    
    # Демография
    target_age_min: Optional[int] = None  # Минимальный возраст ЦА
    target_age_max: Optional[int] = None  # Максимальный возраст ЦА
    target_gender: Optional[str] = None  # "male", "female", "any"
    
    # Категории
    categories: List[BlogCategory] = field(default_factory=list)
    
    # Бюджет (кратный 1000)
    budget_min: Optional[int] = None  # Минимальный бюджет
    budget_max: Optional[int] = None  # Максимальный бюджет
    
    # Дополнительные критерии
    has_reviews: Optional[bool] = None
    is_registered_rkn: Optional[bool] = None
    official_payment_required: Optional[bool] = None
    
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Review:
    """Модель отзыва"""
    id: int
    reviewer_id: int  # ID того, кто оставляет отзыв
    reviewed_id: int  # ID того, о ком отзыв
    rating: int  # от 1 до 5
    comment: Optional[str] = None
    blogger_id: Optional[int] = None  # ID блогера, если отзыв о сотрудничестве
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Subscription:
    """Модель подписки"""
    id: int
    user_id: int
    start_date: datetime
    end_date: datetime
    amount: int  # в копейках
    status: SubscriptionStatus
    payment_id: Optional[str] = None
    auto_renewal: bool = True  # Автопродление включено по умолчанию
    cancelled_at: Optional[datetime] = None  # Дата отмены
    promo_code: Optional[str] = None  # Промокод для бесплатной подписки
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Contact:
    """Модель контакта (когда закупщик получает доступ к контактам продавца)"""
    id: int
    buyer_id: int
    seller_id: int
    blogger_id: int
    deal_completed: Optional[bool] = None  # Состоялась ли сделка
    rating_given: Optional[int] = None  # Оценка коммуникации с менеджером
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Complaint:
    """Модель жалобы на блогера"""
    id: int
    blogger_id: int
    blogger_name: str
    user_id: int
    username: str
    reason: str
    status: str = "open"  # open, reviewed, resolved
    penalty_applied: bool = False  # Был ли применен штраф
    created_at: datetime = field(default_factory=datetime.now) 