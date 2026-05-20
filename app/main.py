from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import analytics, auth, authors, books, recommendations, reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаёт таблицы SQLite при первом запуске (если их ещё нет)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Каталог книг",
    description="REST-сервис для управления каталогом книг с авторизацией и аналитикой",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключение роутеров
app.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
app.include_router(authors.router, prefix="/authors", tags=["Авторы"])
app.include_router(books.router, prefix="/books", tags=["Книги"])
app.include_router(reviews.router, prefix="/reviews", tags=["Отзывы"])
app.include_router(analytics.router, prefix="/analytics", tags=["Аналитика"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Рекомендации"])


@app.get("/")
def root():
    return {"status": "ok", "message": "API каталога книг запущен"}
