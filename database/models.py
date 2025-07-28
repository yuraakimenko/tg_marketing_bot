from dataclasses import dataclass, field
from typing import Optional, List, Set
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
    
    def get_russian_name(self) -> str:
        """Получить русское название категории"""
        names = {
            "lifestyle": "Лайфстайл",
            "sport": "Спорт",
            "nutrition": "Питание",
            "medicine": "Медицина",
            "relationships": "Отношения",
            "beauty": "Красота",
            "fashion": "Мода",
            "travel": "Путешествия",
            "business": "Бизнес",
            "education": "Образование",
            "entertainment": "Развлечения",
            "technology": "Технологии",
            "parenting": "Родительство",
            "finance": "Финансы",
            "not_important": "Неважно"
        }
        return names.get(self.value, self.value)


@dataclass
class User:
    """Модель пользователя с поддержкой множественных ролей"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: Set[UserRole] = field(default_factory=set)  # Множество ролей вместо одной роли
    subscription_status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    subscription_end_date: Optional[datetime] = None
    subscription_start_date: Optional[datetime] = None  # Добавляем дату начала подписки
    rating: float = 0.0
    reviews_count: int = 0
    is_vip: bool = False  # VIP статус для менеджеров
    penalty_amount: int = 0  # Сумма штрафов
    is_blocked: bool = False  # Блокировка за штрафы
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def has_role(self, role: UserRole) -> bool:
        """Проверяет, есть ли у пользователя указанная роль"""
        return role in self.roles
    
    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Проверяет, есть ли у пользователя хотя бы одна из указанных ролей"""
        return bool(self.roles.intersection(set(roles)))
    
    def add_role(self, role: UserRole) -> None:
        """Добавляет роль пользователю"""
        self.roles.add(role)
    
    def remove_role(self, role: UserRole) -> None:
        """Удаляет роль у пользователя"""
        self.roles.discard(role)
    
    def get_primary_role(self) -> Optional[UserRole]:
        """Возвращает основную роль (первую добавленную) для обратной совместимости"""
        return next(iter(self.roles)) if self.roles else None
    
    def can_complain(self) -> bool:
        """Проверяет, может ли пользователь подавать жалобы (только закупщики)"""
        return UserRole.BUYER in self.roles
    
    def can_edit_bloggers(self) -> bool:
        """Проверяет, может ли пользователь редактировать блогеров (продажники и закупщики)"""
        return bool(self.roles)  # Любая роль может редактировать блогеров


@dataclass
class Blogger:
    """Модель блогера"""
    id: int
    seller_id: int
    name: str
    url: str
    platforms: List[Platform] = field(default_factory=list)  # Множественный выбор платформ
    
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
    price_stories: Optional[int] = None  # Цена за сторис
    price_post: Optional[int] = None  # Цена за пост
    price_video: Optional[int] = None  # Цена за видео
    
    # Статистика
    subscribers_count: Optional[int] = None
    avg_views: Optional[int] = None
    avg_likes: Optional[int] = None
    engagement_rate: Optional[float] = None
    
    # Дополнительные поля
    has_reviews: bool = False
    is_registered_rkn: bool = False
    official_payment_possible: bool = False

    # Ссылки на изображения со статистикой
    stats_images: List[str] = field(default_factory=list)
    
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_price_summary(self) -> str:
        """Получить сводку по ценам"""
        prices = []
        if self.price_stories:
            prices.append(f"Сторис: {self.price_stories:,} ₽")
        if self.price_post:
            prices.append(f"Пост: {self.price_post:,} ₽")
        if self.price_video:
            prices.append(f"Видео: {self.price_video:,} ₽")
        return "\n".join(prices) if prices else "Не указано"
    
    def get_platforms_summary(self) -> str:
        """Получить сводку по платформам"""
        return ", ".join([platform.value for platform in self.platforms]) if self.platforms else "Не указано"


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