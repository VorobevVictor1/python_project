# Dockerfile
FROM python:3.14-slim

WORKDIR /app

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем только зависимости сначала (кэширование слоёв)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

# Копируем исходный код
COPY . .

# Переменная для выбора режима очереди
ENV USE_IN_MEMORY_QUEUE=false
ENV REDIS_URL=redis://redis:6379/0
ENV DATABASE_URL=sqlite:///./data/catalog.db

# Создаём папку для БД
RUN mkdir -p /app/data

# Экспортируем порты (только для API)
EXPOSE 8000

# Команда по умолчанию — запуск API
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]