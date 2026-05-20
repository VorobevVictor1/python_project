import json
import redis
from typing import Optional, Any
from app.core.task_queue import TaskQueueProtocol


class RedisTaskQueue(TaskQueueProtocol):
    """
    Redis-реализация через LIST (простой паттерн "queue").
    
    Для учебного проекта используем blocking pop — достаточно надёжно.
    В продакшене можно доработать до Streams с consumer groups.
    """
    
    def __init__(self, redis_url: str, key_prefix: str = "task:"):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix
    
    def _key(self, task_name: str) -> str:
        return f"{self._prefix}{task_name}"
    
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> None:
        """LPUSH: добавляем в голову списка."""
        self._redis.lpush(self._key(task_name), json.dumps(payload))
    
    def dequeue(self, task_name: str, timeout: float = 0.0) -> Optional[dict[str, Any]]:
        """
        BRPOP: blocking pop с таймаутом.
        Если timeout=0 — возвращаем сразу (non-blocking).
        """
        key = self._key(task_name)
        if timeout > 0:
            result = self._redis.brpop([key], timeout=timeout)
            if result:
                _, raw_payload = result
                return json.loads(raw_payload)
            return None
        else:
            # Non-blocking: RPOP
            raw_payload = self._redis.rpop(key)
            return json.loads(raw_payload) if raw_payload else None
    
    def health_check(self) -> bool:
        try:
            return self._redis.ping()
        except redis.ConnectionError:
            return False
    
    def close(self) -> None:
        self._redis.close()