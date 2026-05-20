import json

from sqlalchemy.orm import Session

from app.models import Book, ReadingEvent, RecommendationCache
from app.recommender.engine import RecommenderEngine
from app.recommender.types import ReadingEventDTO, UserRecommendations


class RecommendationService:
    """
    Сервисный слой: связывает доменную логику (engine) с инфраструктурой (БД).

    Принцип: тонкий слой, который только преобразует данные и вызывает engine.
    """

    def __init__(self, db: Session, engine: RecommenderEngine | None = None):
        self.db = db
        self.engine = engine or RecommenderEngine()

    def _fetch_events(self) -> list[ReadingEventDTO]:
        """Загружаем все события из БД и конвертируем в DTO."""
        events = self.db.query(ReadingEvent).all()
        return [
            ReadingEventDTO(
                user_id=e.user_id, book_id=e.book_id, rating=e.rating, completed_at=e.completed_at
            )
            for e in events
        ]

    def _fetch_all_book_ids(self) -> set[int]:
        """Множество всех доступных book_id."""
        return {book.id for book in self.db.query(Book.id).all()}

    def generate_for_user(self, user_id: int) -> UserRecommendations:
        """Сгенерировать рекомендации для пользователя (синхронно)."""
        events = self._fetch_events()
        all_books = self._fetch_all_book_ids()
        return self.engine.predict_for_user(user_id=user_id, events=events, all_book_ids=all_books)

    def save_to_cache(self, result: UserRecommendations) -> RecommendationCache:
        """Сохранить результат в кэш-таблицу."""
        # Конвертируем списки в JSON-строки
        book_ids_json = json.dumps([r.book_id for r in result.recommendations])
        scores_json = json.dumps([r.score for r in result.recommendations])

        # Upsert: если есть запись — обновляем, иначе создаём
        existing = (
            self.db.query(RecommendationCache)
            .filter(RecommendationCache.user_id == result.user_id)
            .first()
        )

        if existing:
            existing.recommended_book_ids = book_ids_json
            existing.scores = scores_json
            existing.generated_at = result.generated_at
            cache_obj = existing
        else:
            cache_obj = RecommendationCache(
                user_id=result.user_id,
                recommended_book_ids=book_ids_json,
                scores=scores_json,
                generated_at=result.generated_at,
            )
            self.db.add(cache_obj)

        self.db.commit()
        self.db.refresh(cache_obj)
        return cache_obj

    def get_from_cache(self, user_id: int) -> UserRecommendations | None:
        """Получить рекомендации из кэша (для API)."""
        from app.recommender.types import Recommendation  # локальный импорт

        cache = (
            self.db.query(RecommendationCache)
            .filter(RecommendationCache.user_id == user_id)
            .first()
        )

        if not cache:
            return None

        # Парсим JSON обратно в объекты
        book_ids = json.loads(cache.recommended_book_ids)
        scores = json.loads(cache.scores)

        recommendations = [
            Recommendation(book_id=bid, score=scr) for bid, scr in zip(book_ids, scores, strict=True)
        ]

        return UserRecommendations(
            user_id=cache.user_id,
            recommendations=recommendations,
            generated_at=cache.generated_at,
            algorithm_version="cosine_numpy_v1",  # обновляем версию
        )
