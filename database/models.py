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
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Blogger:
    """Модель блогера"""
    id: int
    seller_id: int
    name: str
    url: str
    platform: str  # youtube, instagram, tiktok, etc.
    category: str  # медицина, отношения, etc.
    target_audience: str  # женщины 25-34 лет, etc.
    has_reviews: bool = False
    review_categories: Optional[str] = None  # JSON список категорий отзывов
    subscribers_count: Optional[int] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchFilter:
    """Модель фильтра поиска для закупщиков"""
    id: int
    buyer_id: int
    target_audience: Optional[str] = None
    category: Optional[str] = None
    has_reviews: Optional[bool] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
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
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Contact:
    """Модель контакта (когда закупщик получает доступ к контактам продавца)"""
    id: int
    buyer_id: int
    seller_id: int
    blogger_id: int
    created_at: datetime = field(default_factory=datetime.now) 