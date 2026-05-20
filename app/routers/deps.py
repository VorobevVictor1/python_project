from functools import lru_cache
from app.core.task_queue import TaskQueueProtocol
from app.infrastructure.in_memory_queue import InMemoryTaskQueue
from app.infrastructure.redis_queue import RedisTaskQueue
from app.core.config import settings


@lru_cache
def get_task_queue() -> TaskQueueProtocol:
    """
    Factory для очереди задач.
    
    В тестах переопределяется через dependency_overrides.
    """
    if settings.USE_IN_MEMORY_QUEUE:
        return InMemoryTaskQueue()
    
    return RedisTaskQueue(redis_url=settings.REDIS_URL)