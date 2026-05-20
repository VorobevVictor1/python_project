from app.models import ReadingEvent, RecommendationCache
from app.database import Base, engine


def test_models_create_tables():
    """Проверяем, что новые модели корректно определяются SQLAlchemy."""
    # Это не создаёт таблицы в БД, просто проверяет метаданные
    assert "reading_events" in Base.metadata.tables
    assert "recommendation_cache" in Base.metadata.tables
    
    # Проверяем колонки
    reading_events = Base.metadata.tables["reading_events"]
    assert "user_id" in reading_events.c
    assert "book_id" in reading_events.c
    assert "rating" in reading_events.c
    
    cache = Base.metadata.tables["recommendation_cache"]
    assert "user_id" in cache.c
    assert "recommended_book_ids" in cache.c