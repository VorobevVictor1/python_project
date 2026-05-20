"""Тесты эндпоинтов аутентификации."""

from fastapi import status


def test_register_success(client):
    """Успешная регистрация нового пользователя."""
    response = client.post(
        "/auth/register",
        json={"username": "newuser", "email": "new@example.com", "password": "securepass123"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # Пароль не должен возвращаться


def test_register_duplicate_username(client, test_user):
    """Регистрация с существующим username должна вернуть 400."""
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",  # Уже существует
            "email": "another@example.com",
            "password": "pass1234",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_invalid_email(client):
    """Регистрация с невалидным email должна вернуть 422."""
    response = client.post(
        "/auth/register",
        json={
            "username": "baduser",
            "email": "not-an-email",  # Некорректный email
            "password": "pass123",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client, test_user):
    """Успешный вход возвращает JWT-токен."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass123"},  # form-data!
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_login_wrong_password(client, test_user):
    """Вход с неверным паролем должен вернуть 401."""
    response = client.post("/auth/login", data={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_authenticated(client, test_user):
    """Получение профиля текущего пользователя с токеном."""
    response = client.get("/auth/me", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_me_unauthenticated(client):
    """Запрос /me без токена должен вернуть 401."""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
