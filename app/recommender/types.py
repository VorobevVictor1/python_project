from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ReadingEventDTO:
    """
    Data Transfer Object для события чтения.

    Используем dataclass вместо ORM-модели, чтобы отделить
    доменную логику от SQLAlchemy.
    """

    user_id: int
    book_id: int
    rating: float
    completed_at: datetime


@dataclass(frozen=True)
class Recommendation:
    """Результат рекомендации для одной книги."""

    book_id: int
    score: float  # чем выше, тем релевантнее
    reason: str = ""  # опционально: "похожие пользователи оценили высоко"


@dataclass
class UserRecommendations:
    """Полный результат для пользователя."""

    user_id: int
    recommendations: list[Recommendation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    algorithm_version: str = "cosine_numpy_v1"
