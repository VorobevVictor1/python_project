import logging
import time

from sqlalchemy.orm import Session

from app.core.task_queue import TaskQueueProtocol
from app.recommender.service import RecommendationService

logger = logging.getLogger(__name__)


def process_recommendation_task(task: dict, db: Session, queue: TaskQueueProtocol) -> None:
    """
    Обрабатывает одну задачу из очереди.

    Вынесена в отдельную функцию для упрощения тестирования:
    тесты вызывают её напрямую, не запуская бесконечный цикл.
    """
    user_id = task.get("user_id")
    if not user_id:
        logger.warning("Task missing user_id, skipping.")
        return

    logger.info(f"Processing recommendations for user {user_id}")

    # 1. Генерируем рекомендации (чтение из БД, расчёт через numpy)
    service = RecommendationService(db=db)
    result = service.generate_for_user(user_id)

    # 2. Сохраняем в кэш
    service.save_to_cache(result)

    logger.info(f"Done. Cached {len(result.recommendations)} recommendations for user {user_id}")


def run_worker_loop(
    db: Session,
    queue: TaskQueueProtocol,
    task_name: str = "recalculate_user",
    poll_timeout: float = 5.0,
) -> None:
    """
    Бесконечный цикл воркера.

    Использует blocking dequeue: процесс спит, пока нет задач,
    не нагружая CPU холостыми циклами.
    """
    logger.info(f"Starting recommendation worker. Polling '{task_name}' queue...")

    while True:
        try:
            task = queue.dequeue(task_name, timeout=poll_timeout)
            if task:
                process_recommendation_task(task, db, queue)
        except Exception as e:
            logger.error(f"Worker error processing task: {e}")
            time.sleep(10)
