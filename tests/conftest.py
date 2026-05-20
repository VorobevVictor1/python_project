"""Фикстуры и конфигурация для тестов."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_password_hash
from app.database import Base, get_db
from app.infrastructure.in_memory_queue import InMemoryTaskQueue
from app.main import app
from app.models import User
from app.routers.deps import get_task_queue

# Используем in-memory SQLite для полной изоляции тестов
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Важно для in-memory БД
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Фикстура: чистая сессия БД для каждого теста."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Фикстура: TestClient с переопределённой зависимостью get_db."""

    def override_get_db():
        # Просто отдаём сессию, не закрывая её после каждого запроса
        # Жизненным циклом сессии управляет фикстура db_session
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Очищаем зависимости после теста
    app.dependency_overrides.clear()
    # Сессия закроется в фикстуре db_session (в её finally-блоке)


@pytest.fixture(scope="function")
def test_user(db_session):
    """Фикстура: тестовый пользователь с токеном."""
    from app.auth import create_access_token

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": user.username})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="function")
def task_queue():
    """Фикстура: in-memory очередь для тестов."""
    queue = InMemoryTaskQueue()
    yield queue
    queue.clear()  # очистка после теста для изоляции


@pytest.fixture(scope="function")
def client_with_queue(client, task_queue):
    """
    Комбинированная фикстура: TestClient + переопределённая очередь.

    Используется в интеграционных тестах, где нужно проверять
    и API, и постановку задач в очередь.
    """
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    yield client, task_queue
    app.dependency_overrides.pop(get_task_queue, None)
