from datetime import datetime, timedelta

import numpy as np

from app.recommender.engine import RecommenderEngine
from app.recommender.types import ReadingEventDTO


def _make_event(user: int, book: int, rating: float, days_ago: int = 0) -> ReadingEventDTO:
    """Хелпер для создания тестовых событий."""
    return ReadingEventDTO(
        user_id=user,
        book_id=book,
        rating=rating,
        completed_at=datetime.utcnow() - timedelta(days=days_ago),
    )


def test_engine_empty_events():
    """Пустые данные → пустой результат."""
    engine = RecommenderEngine(top_n=5)
    result = engine.predict_for_user(user_id=1, events=[], all_book_ids={1, 2, 3})
    assert result.user_id == 1
    assert len(result.recommendations) == 0


def test_engine_not_enough_ratings():
    """Меньше min_ratings оценок → пустой результат."""
    engine = RecommenderEngine(top_n=5, min_ratings=3)
    events = [
        _make_event(1, 10, 5.0),
        _make_event(1, 11, 4.0),  # всего 2 оценки, нужно 3
    ]
    result = engine.predict_for_user(user_id=1, events=events, all_book_ids={10, 11, 12})
    assert len(result.recommendations) == 0


def test_engine_simple_collaborative():
    """Базовый тест: похожие пользователи → похожие рекомендации."""
    # Пользователь 1: любит книги 1,2
    # Пользователь 2: любит книги 1,2,3 → должен порекомендовать 3 пользователю 1
    events = [
        _make_event(1, 1, 5.0),
        _make_event(1, 2, 4.0),
        _make_event(2, 1, 5.0),
        _make_event(2, 2, 5.0),
        _make_event(2, 3, 4.5),  # книга 3 — кандидат для пользователя 1
    ]

    engine = RecommenderEngine(top_n=3, min_ratings=2, min_similarity=0.0)
    result = engine.predict_for_user(user_id=1, events=events, all_book_ids={1, 2, 3, 4})

    assert len(result.recommendations) >= 1
    assert result.recommendations[0].book_id == 3
    assert result.recommendations[0].score > 0


def test_engine_excludes_read_books():
    """Прочитанные книги не рекомендуются повторно."""
    events = [
        _make_event(1, 1, 5.0),  # пользователь 1 уже прочитал книгу 1
        _make_event(2, 1, 5.0),
        _make_event(2, 2, 4.0),
    ]

    engine = RecommenderEngine(top_n=5, min_similarity=0.0)
    result = engine.predict_for_user(user_id=1, events=events, all_book_ids={1, 2})

    # Книга 1 не должна быть в рекомендациях
    recommended_ids = {r.book_id for r in result.recommendations}
    assert 1 not in recommended_ids


def test_engine_numpy_cosine_similarity():
    """Проверка, что косинусное сходство считается корректно."""
    from app.recommender.engine import RecommenderEngine

    engine = RecommenderEngine()

    # Тестовая матрица: 3 пользователя × 4 книги
    # NaN = нет оценки
    matrix = np.array(
        [
            [5.0, 4.0, np.nan, np.nan],  # user 0
            [5.0, 4.0, 4.5, np.nan],  # user 1 — похож на user 0
            [np.nan, np.nan, 1.0, 2.0],  # user 2 — не похож
        ]
    )

    similarities = engine._cosine_similarity_matrix(matrix)

    # user 0 и user 1 должны иметь высокое сходство (общие оценки 5,4)
    assert similarities[0, 1] > 0.9

    # user 0 и user 2 не имеют общих оценок → сходство 0
    assert similarities[0, 2] == 0.0

    # Диагональ = 1
    assert np.allclose(np.diag(similarities), 1.0)


def test_engine_predict_scores_numpy():
    """Проверка предсказания скоров."""
    from app.recommender.engine import RecommenderEngine

    engine = RecommenderEngine(min_similarity=0.0)  # отключаем порог для теста

    # Простая матрица: 2 пользователя, 3 книги
    matrix = np.array(
        [
            [5.0, 4.0, np.nan],  # user 0: прочитал 1,2
            [5.0, 4.0, 4.5],  # user 1: прочитал 1,2,3
        ]
    )

    # user_read_mask: какие книги уже прочитал user 0
    user_read_mask = np.array([True, True, False])

    # Вычисляем сходства вручную для теста
    similarities = np.array([[1.0, 0.99], [0.99, 1.0]])

    scores = engine._predict_scores(
        user_idx=0, rating_matrix=matrix, similarities=similarities, user_read_mask=user_read_mask
    )

    # Книга 2 (индекс 2) должна получить высокий скор от user 1
    assert scores[2] > 4.0  # взвешенное среднее ~4.5


def test_engine_handles_numpy_edge_cases():
    """Проверка устойчивости к краевым случаям."""
    from app.recommender.engine import RecommenderEngine

    engine = RecommenderEngine()

    # Пустая матрица
    empty = np.array([]).reshape(0, 0)
    sim = engine._cosine_similarity_matrix(empty)
    assert sim.shape == (0, 0)

    # Один пользователь
    single = np.array([[5.0, np.nan, 4.0]])
    sim = engine._cosine_similarity_matrix(single)
    assert sim.shape == (1, 1)
    assert sim[0, 0] == 1.0
