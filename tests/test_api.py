"""Тесты CRUD-операций и бизнес-эндпоинтов."""
import pytest
from fastapi import status


# ==================== AUTHORS ====================

def test_create_author(client):
    """Создание автора."""
    response = client.post("/authors/", json={"name": "Test Author"})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Author"
    assert data["id"] == 1


def test_get_authors(client):
    """Получение списка авторов."""
    # Сначала создадим автора
    client.post("/authors/", json={"name": "Author One"})
    client.post("/authors/", json={"name": "Author Two"})
    
    response = client.get("/authors/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert all("name" in author for author in data)


def test_get_author_not_found(client):
    """Запрос несуществующего автора."""
    response = client.get("/authors/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== BOOKS ====================

def test_create_book(client, db_session):
    """Создание книги (требуется существующий автор)."""
    # Создаём автора
    author_response = client.post("/authors/", json={"name": "Book Author"})
    author_id = author_response.json()["id"]
    
    # Создаём книгу
    response = client.post("/books/", json={
        "title": "Test Book",
        "year": 2024,
        "author_id": author_id
    })
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["year"] == 2024


def test_get_books_with_filter(client, db_session):
    """Фильтрация книг по author_id."""
    # Создаём двух авторов и книги для каждого
    author1 = client.post("/authors/", json={"name": "Author A"}).json()["id"]
    author2 = client.post("/authors/", json={"name": "Author B"}).json()["id"]
    
    client.post("/books/", json={"title": "Book A1", "year": 2020, "author_id": author1})
    client.post("/books/", json={"title": "Book A2", "year": 2021, "author_id": author1})
    client.post("/books/", json={"title": "Book B1", "year": 2022, "author_id": author2})
    
    # Фильтруем по author1
    response = client.get(f"/books/?author_id={author1}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert all(book["author_id"] == author1 for book in data)


def test_update_book(client, db_session):
    """Обновление книги."""
    author_id = client.post("/authors/", json={"name": "Updater"}).json()["id"]
    book = client.post("/books/", json={
        "title": "Old Title", "year": 2000, "author_id": author_id
    }).json()
    
    response = client.put(f"/books/{book['id']}", json={
        "title": "New Title", "year": 2025, "author_id": author_id
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "New Title"
    assert data["year"] == 2025


def test_delete_book(client, db_session):
    """Удаление книги."""
    author_id = client.post("/authors/", json={"name": "Deleter"}).json()["id"]
    book = client.post("/books/", json={
        "title": "ToDelete", "year": 1999, "author_id": author_id
    }).json()
    
    response = client.delete(f"/books/{book['id']}")
    assert response.status_code == status.HTTP_200_OK
    
    # Проверяем, что книга действительно удалена
    response = client.get(f"/books/{book['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== REVIEWS (с авторизацией) ====================

def test_create_review_requires_auth(client, db_session):
    """Создание отзыва без токена должно вернуть 401."""
    response = client.post("/reviews/", json={
        "book_id": 1, "rating": 5.0, "comment": "Great!"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_review_success(client, db_session, test_user):
    """Успешное создание отзыва с авторизацией."""
    # Создаём автора и книгу
    author_id = client.post("/authors/", json={"name": "Review Author"}).json()["id"]
    book = client.post("/books/", json={
        "title": "Reviewable Book", "year": 2023, "author_id": author_id
    }).json()
    
    # Создаём отзыв
    response = client.post("/reviews/", json={
        "book_id": book["id"],
        "rating": 4.5,
        "comment": "Excellent book!"
    }, headers=test_user["headers"])
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["rating"] == 4.5
    assert data["book_id"] == book["id"]


def test_review_rating_validation(client, db_session, test_user):
    """Валидация рейтинга: должен быть от 1.0 до 5.0."""
    # Рейтинг ниже минимума
    response = client.post("/reviews/", json={
        "book_id": 1, "rating": 0.5, "comment": "Bad"
    }, headers=test_user["headers"])
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Рейтинг выше максимума
    response = client.post("/reviews/", json={
        "book_id": 1, "rating": 6.0, "comment": "Too good?"
    }, headers=test_user["headers"])
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==================== ANALYTICS (бизнес-логика) ====================

def test_recommend_endpoint_success(client, db_session):
    """Тест бизнес-эндпоинта рекомендаций."""
    # Создаём тестовые данные
    author_id = client.post("/authors/", json={"name": "Analytics Author"}).json()["id"]
    
    # Книги разных лет
    client.post("/books/", json={"title": "Old Book", "year": 1990, "author_id": author_id})
    client.post("/books/", json={"title": "Recent Book", "year": 2024, "author_id": author_id})
    client.post("/books/", json={"title": "Very Recent", "year": 2025, "author_id": author_id})
    
    # Запрос рекомендаций
    response = client.post("/analytics/recommend", json={
        "min_year": 2000,
        "max_rating": 5.0,
        "limit": 2
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 2  # limit=2
    # Проверяем, что возвращены только книги >= min_year
    assert all(book["year"] >= 2000 for book in data)


def test_recommend_empty_database(client):
    """Рекомендации при пустой базе должны вернуть 404."""
    response = client.post("/analytics/recommend", json={})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_analytics_stats_endpoint(client, db_session):
    """Тест эндпоинта статистики."""
    response = client.get("/analytics/stats")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_books" in data
    assert "average_publication_year" in data
    assert "algorithm_version" in data