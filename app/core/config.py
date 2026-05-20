from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./catalog.db"

    # Queue
    USE_IN_MEMORY_QUEUE: bool = False  # переключать через env для тестов
    REDIS_URL: str = "redis://localhost:6379/0"

    # Recommendations
    RECOMMENDATION_TOP_N: int = 10
    RECOMMENDATION_MIN_RATINGS: int = 3  # мин. оценок пользователя для расчёта

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
