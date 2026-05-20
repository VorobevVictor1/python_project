# tests/integration/test_recommendation_flow.py
from datetime import datetime

from app.auth import get_password_hash
from app.models import Author, Book, ReadingEvent, User
from app.recommender.worker import process_recommendation_task


def test_full_recommendation_flow(client_with_queue, db_session):
    """
    Полный цикл: данные → триггер → воркер → кэш → API.

    :param client_with_queue: фикстура с клиентом и очередью
    :param db_session: фикстура с транзакционной сессией
    """
    client, queue = client_with_queue

    # Создаём пользователей
    target_user = User(
        username="target_user", email="target@test.com", hashed_password=get_password_hash("pass")
    )
    db_session.add(target_user)
    db_session.flush()

    similar_user = User(
        username="similar_user", email="similar@test.com", hashed_password=get_password_hash("pass")
    )
    db_session.add(similar_user)
    db_session.flush()

    # Создаём авторов (обязательно перед книгами!)
    author_a = Author(name="Author A")
    author_b = Author(name="Author B")
    author_c = Author(name="Author C")
    db_session.add_all([author_a, author_b, author_c])
    db_session.flush()  # получаем author.id

    # Создаём книги, привязывая к авторам через author_id ИЛИ author-объект
    book1 = Book(title="Book 1", author_id=author_a.id, year=2020)
    book2 = Book(title="Book 2", author_id=author_b.id, year=2021)
    book3 = Book(title="Book 3", author_id=author_c.id, year=2022)
    book4 = Book(title="Book 4", author_id=author_c.id, year=2023)
    db_session.add_all([book1, book2, book3, book4])
    db_session.flush()

    # Создаём события чтений:
    # - target_user оценил книги 1 и 2
    # - similar_user оценил книги 1, 2 и 3 (высоко)
    # → алгоритм должен порекомендовать книгу 3 target_user
    events = [
        # Целевой пользователь
        ReadingEvent(
            user_id=target_user.id, book_id=book1.id, rating=5.0, completed_at=datetime.utcnow()
        ),
        ReadingEvent(
            user_id=target_user.id, book_id=book2.id, rating=4.0, completed_at=datetime.utcnow()
        ),
        ReadingEvent(
            user_id=target_user.id, book_id=book3.id, rating=3.0, completed_at=datetime.utcnow()
        ),  # ← НОВАЯ
        # Похожий пользователь
        ReadingEvent(
            user_id=similar_user.id, book_id=book1.id, rating=5.0, completed_at=datetime.utcnow()
        ),
        ReadingEvent(
            user_id=similar_user.id, book_id=book2.id, rating=5.0, completed_at=datetime.utcnow()
        ),
        ReadingEvent(
            user_id=similar_user.id, book_id=book4.id, rating=4.5, completed_at=datetime.utcnow()
        ),  # ← кандидат для рекомендации
    ]
    db_session.add_all(events)
    db_session.commit()  # фиксируем данные, чтобы воркер их увидел

    # Сохраняем ID в простые переменные (защита от DetachedInstanceError)
    book4_id = book4.id
    target_user_id = target_user.id

    # === Шаг 1: Триггер пересчёта ===
    queue.enqueue("recalculate_user", {"user_id": target_user_id})
    assert queue.size("recalculate_user") == 1

    # === Шаг 2: Запуск обработки ===
    task = queue.dequeue("recalculate_user")
    process_recommendation_task(task, db_session, queue)

    # === Шаг 3: Проверка через API ===
    response = client.get(f"/recommendations/{target_user_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == target_user_id
    assert "recommendations" in data

    # Проверяем рекомендации через простые значения
    recommended_ids = [r["book_id"] for r in data["recommendations"]]
    assert book4_id in recommended_ids, (
        f"Book {book4_id} should be recommended, got: {recommended_ids}"
    )

    # Проверяем, что прочитанные книги НЕ рекомендуются повторно
    assert book1.id not in recommended_ids
    assert book2.id not in recommended_ids
    assert book3.id not in recommended_ids
