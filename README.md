
# Каталог книг — REST API на FastAPI. Проект для ЦК МФТИ. 

## Описание
Веб-сервис для управления каталогом книг с поддержкой авторов, отзывов и рекомендательной аналитики. Реализует полный CRUD, JWT-аутентификацию и алгоритм взвешенного скоринга для рекомендаций.

## Стек
- FastAPI 0.115+, Python 3.10+
- SQLAlchemy 2.0, SQLite
- Pydantic v2 для валидации
- JWT (python-jose), bcrypt/argon2 для хеширования
- pytest + TestClient для тестирования

## Установка и запуск

```bash
# Основной сервис
uv run uvicorn app.main:app --reload

# Воркер (в отдельном терминале)
uv run python -m app.recommender.worker

# С инфраструктурой (Redis)
docker compose up -d redis
uv run uvicorn app.main:app --reload  # в другом терминале
uv run python -m app.recommender.worker  # в третьем
```

База данных `catalog.db` создаётся автоматически при первом запуске.

## Документация API
После запуска сервера:
- Swagger UI: http://127.0.0.1:8000/docs

## Основные эндпоинты

### Авторизация
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | /auth/register | Регистрация пользователя |
| POST | /auth/login | Получение JWT-токена |
| GET | /auth/me | Данные текущего пользователя |

### Авторы
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /authors/ | Список авторов |
| POST | /authors/ | Создать автора |
| GET | /authors/{id} | Получить автора |
| PUT | /authors/{id} | Обновить автора |
| DELETE | /authors/{id} | Удалить автора |

### Книги
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /books/ | Список книг (с фильтрацией ?author_id=N) |
| POST | /books/ | Создать книгу |
| GET | /books/{id} | Получить книгу |
| PUT | /books/{id} | Обновить книгу |
| DELETE | /books/{id} | Удалить книгу |

### Отзывы (требуют авторизации)
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /reviews/ | Список отзывов |
| POST | /reviews/ | Создать отзыв |
| PUT | /reviews/{id} | Обновить свой отзыв |
| DELETE | /reviews/{id} | Удалить свой отзыв |

### Аналитика
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | /analytics/recommend | Рекомендации книг (алгоритм скоринга) |
| GET | /analytics/stats | Статистика каталога |

## Тестирование

```bash
# Запустить все тесты с отчётом о покрытии
uv run pytest --cov=app --cov-report=term-missing

# Запустить без покрытия (быстрее)
uv run pytest --no-cov -v

# HTML-отчёт о покрытии (откроется в браузере)
uv run pytest --cov=app --cov-report=html
```

Текущее покрытие: 81.74%.

## Качество кода

```bash
# Проверка pylint (целевая оценка ≥8.0)
uv run pylint app/ --exit-zero
```
Оценка 9.92.

## Структура проекта
```
book_catalog/
├── app/
│   ├── main.py          # Точка входа, lifespan, роутеры
│   ├── database.py      # SQLite engine, сессии
│   ├── models.py        # SQLAlchemy модели
│   ├── schemas.py       # Pydantic схемы
│   ├── crud.py          # CRUD-функции
│   ├── auth.py          # JWT, хеширование, зависимости
│   └── routers/         # Эндпоинты по сущностям
├── tests/               # Автоматические тесты
├── requirements.txt     # Зависимости
├── .pylintrc           # Конфигурация pylint
└── pytest.ini          # Конфигурация pytest
```

## Автор
Воробьёв Виктор, МФТИ 2026
```
