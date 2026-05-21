"""
Точка входа для запуска батч-воркера.
"""

import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database import Base
from app.recommender.worker import run_worker_loop
from app.routers.deps import get_task_queue

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting recommendation worker...")

    # Создаём engine
    worker_engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )

    # Создаём таблицы, если их нет (идемпотентная операция)
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=worker_engine)
    logger.info("Database initialized")

    Session = sessionmaker(bind=worker_engine)
    queue = get_task_queue()

    try:
        with Session() as db:
            run_worker_loop(db=db, queue=queue)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    finally:
        if hasattr(queue, "close"):
            queue.close()


if __name__ == "__main__":
    main()
