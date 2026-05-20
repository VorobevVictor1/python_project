from collections import defaultdict, deque
from copy import deepcopy
from typing import Optional, Any
from app.core.task_queue import TaskQueueProtocol


class InMemoryTaskQueue(TaskQueueProtocol):
    """
    In-memory реализация для тестов и разработки.
    
    Не требует внешних зависимостей, детерминирована, быстрая.
    """
    
    def __init__(self):
        self._queues: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> None:
        # deepcopy гарантирует полную изоляцию вложенных структур
        self._queues[task_name].append(deepcopy(payload))
    
    def dequeue(self, task_name: str, timeout: float = 0.0) -> Optional[dict[str, Any]]:
        queue = self._queues.get(task_name)
        if queue and queue:
            return queue.popleft()
        return None
    
    def health_check(self) -> bool:
        return True  # всегда "жива" в памяти
    
    # === Методы только для тестов ===
    def clear(self, task_name: Optional[str] = None) -> None:
        if task_name:
            self._queues[task_name].clear()
        else:
            self._queues.clear()
    
    def size(self, task_name: str) -> int:
        """Вернуть размер очереди (для ассертов в тестах)."""
        return len(self._queues.get(task_name, []))