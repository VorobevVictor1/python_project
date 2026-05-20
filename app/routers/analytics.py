"""Бизнес-логика и аналитические эндпоинты."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import get_books
from app.database import get_db
from app.models import Book
from app.schemas import BookResponse, RecommendationRequest

router = APIRouter()


@router.post("/recommend", response_model=list[BookResponse])
def recommend_books(req: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Алгоритм рекомендации книг на основе взвешенного скоринга.

    Параметры:
    - min_year: минимальный год издания книги
    - max_rating: максимальный рейтинг для нормализации
    - limit: количество рекомендаций к возврату

    Алгоритм:
    1. Фильтрация книг по году
    2. Расчёт скоринга: новизна + рейтинг
    3. Сортировка по убыванию скоринга
    4. Возврат топ-N результатов
    """
    # Получаем книги из БД (можно добавить кэширование для продакшена)
    books = get_books(db, skip=0, limit=200)

    if not books:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет книг для рекомендации"
        )

    current_year = datetime.now().year
    scored = []

    for book in books:
        # Пропускаем книги старше минимального года
        if book.year < req.min_year:
            continue

        # Алгоритм взвешенного скоринга:
        # 1. Recency score: чем новее книга, тем выше балл (0.0–1.0)
        recency_score = 1.0 / (current_year - book.year + 1)

        # 2. Rating normalization: нормализуем входной параметр
        rating_factor = req.max_rating / 5.0

        # 3. Финальный скор: взвешенная сумма
        # Веса подобраны эмпирически: новизна важнее, но не доминирует
        final_score = (0.6 * recency_score) + (0.4 * rating_factor)

        scored.append((book, final_score))

    # Сортируем по убыванию скоринга
    scored.sort(key=lambda x: x[1], reverse=True)

    # Возвращаем топ-N книг (только объекты Book для автоматической сериализации)
    return [book for book, _ in scored[: req.limit]]


@router.get("/stats")
def get_catalog_stats(db: Session = Depends(get_db)):
    """Простая статистика каталога — пример дополнительного аналитического эндпоинта."""
    from sqlalchemy import func

    from app.models import Review

    total_books = db.query(func.count(Book.id)).scalar()
    avg_year = db.query(func.avg(Book.year)).scalar()
    total_reviews = db.query(func.count(Review.id)).scalar()

    return {
        "total_books": total_books,
        "average_publication_year": round(avg_year, 1) if avg_year else None,
        "total_reviews": total_reviews,
        "algorithm_version": "weighted_greedy_v1",
    }
