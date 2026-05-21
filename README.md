# Каталог книг — REST API на FastAPI

Веб-сервис для управления каталогом книг с поддержкой авторов, отзывов и рекомендательной аналитики. Реализует полный CRUD, JWT-аутентификацию и алгоритм коллаборативной фильтрации для рекомендаций.

## Стек
- FastAPI 0.115+, Python 3.11+
- SQLAlchemy 2.0, SQLite / PostgreSQL
- Pydantic v2 для валидации
- JWT (python-jose), bcrypt/argon2 для хеширования
- pytest + TestClient для тестирования
- numpy для векторных вычислений в рекомендациях
- Redis (опционально) для очереди задач

## Установка и запуск

### Локальная разработка
```bash
# Клонировать репозиторий
git clone <repo_url>
cd python_project

# Создать виртуальное окружение и установить зависимости
uv venv
uv sync

# Запустить сервер разработки
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
База данных `catalog.db` создаётся автоматически при первом запуске.

### Запуск с инфраструктурой (Redis)
```bash
# Запустить Redis и сервисы через Docker Compose
docker compose up -d

# API доступен на http://127.0.0.1:8000
# Воркер запускается автоматически в отдельном контейнере
```

### Запуск батч-воркера отдельно
Если не используется Docker Compose, воркер можно запустить вручную в отдельном терминале:
```bash
# С in-memory очередью (для тестов)
uv run python -m app.recommender

# С Redis (предварительно запустить: docker compose up -d redis)
export USE_IN_MEMORY_QUEUE=false
export REDIS_URL=redis://localhost:6379/0
uv run python -m app.recommender
```

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

### Рекомендации
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /recommendations/{user_id} | Получить рекомендации для пользователя |

Рекомендации пересчитываются асинхронно в батч-режиме. После создания отзыва задача на пересчёт попадает в очередь, воркер обрабатывает её в фоне и сохраняет результат в кэш. Эндпоинт `GET /recommendations/{user_id}` мгновенно возвращает данные из кэша.

### Аналитика
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /analytics/stats | Статистика каталога |

## Архитектура рекомендаций

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────────┐
│   FastAPI App   │     │   Queue     │     │  Batch Worker   │
│                 │     │ (In-Mem/    │     │ (отдельный      │
│ • Принимает     │────►│   Redis)    │◄────│   процесс)      │
│   события       │     │             │     │                 │
│ • Отдаёт кэш    │◄────│             │────►│ • Читает задачи │
│   рекомендаций  │     │             │     │ • Считает рек-ции│
└─────────────────┘     └─────────────┘     │ • Пишет в кэш   │
                                            └─────────────────┘
```

**Алгоритм**: косинусное сходство оценок пользователей.
**Реализация**: `app/recommender/engine.py` (numpy для векторных операций).
**Кэширование**: результаты сохраняются в таблицу `recommendation_cache`.

## Тестирование

```bash
# Запустить все тесты с отчётом о покрытии
uv run pytest --cov=app --cov-report=term-missing

# Запустить без покрытия (быстрее)
uv run pytest --no-cov -v

# HTML-отчёт о покрытии
uv run pytest --cov=app --cov-report=html
```

### Демо-скрипт и автопроверка
Скрипт генерирует тестовые данные и проверяет логику рекомендаций:

```bash
# Локальный запуск
uv run python scripts/demo_and_test.py

# С подробным выводом
uv run python scripts/demo_and_test.py --verbose

# Сохранить данные после теста (для ручной проверки)
uv run python scripts/demo_and_test.py --no-cleanup

# В Docker (если контейнеры запущены)
docker compose exec api uv run python scripts/demo_and_test.py --verbose --no-cleanup
```

**Аргументы скрипта**:
- `--no-cleanup` — не удалять тестовые данные после проверки
- `--verbose`, `-v` — подробный вывод
- `--use-redis` — использовать Redis для очереди (по умолчанию: in-memory)

## Качество кода

```bash
# Проверка pylint (целевая оценка ≥8.0)
uv run pylint app/ --exit-zero
```

## Структура проекта
```
.
├── app/
│   ├── main.py                 # Точка входа FastAPI
│   ├── database.py            # Настройки БД
│   ├── models.py              # SQLAlchemy модели
│   ├── schemas.py             # Pydantic схемы
│   ├── crud.py                # CRUD-функции
│   ├── auth.py                # JWT, хеширование
│   ├── core/
│   │   ├── config.py          # Настройки через pydantic-settings
│   │   └── task_queue.py      # Абстракция очереди задач
│   ├── infrastructure/
│   │   ├── in_memory_queue.py # Реализация очереди для тестов
│   │   └── redis_queue.py     # Реализация очереди для Redis
│   ├── recommender/
│   │   ├── engine.py          # Ядро алгоритма (numpy)
│   │   ├── service.py         # Сервисный слой (БД)
│   │   ├── schemas.py         # Pydantic-схемы для API
│   │   ├── types.py           # Dataclass DTO
│   │   ├── worker.py          # Логика батч-воркера
│   │   └── __main__.py        # Точка входа для запуска воркера
│   └── routers/
│       ├── auth.py
│       ├── authors.py
│       ├── books.py
│       ├── reviews.py         # Триггерит пересчёт рекомендаций
│       ├── analytics.py
│       └── recommendations.py # Эндпоинты рекомендаций
├── scripts/
│   └── demo_and_test.py       # Демо-данные и автопроверка
├── tests/
│   ├── unit/                  # Юнит-тесты
│   └── integration/           # Интеграционные тесты
├── docker-compose.yml         # Инфраструктура для разработки
├── pyproject.toml            # Зависимости и метаданные
├── .env.example              # Шаблон конфигурации
└── README.md                 # Этот файл
```

## Конфигурация
Переменные окружения (или файл `.env`):
```env
# Database
DATABASE_URL=sqlite:///./catalog.db

# Queue
USE_IN_MEMORY_QUEUE=true      # true для тестов, false для Redis
REDIS_URL=redis://localhost:6379/0

# Recommendations
RECOMMENDATION_TOP_N=10       # Количество рекомендаций в ответе
RECOMMENDATION_MIN_RATINGS=3  # Мин. оценок пользователя для расчёта
```

## Автор
Воробьёв Виктор, МФТИ 2026Ы