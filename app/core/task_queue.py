from abc import ABC, abstractmethod
from typing import Optional, Any


class TaskQueueProtocol(ABC):
    """
    Абстракция очереди задач.
    
    Принцип: зависимость от абстракции, а не от реализации (Dependency Inversion).
    Позволяет:
    - Тестировать без Redis (мокаем интерфейс)
    - Легко сменить брокер в будущем
    - Явно декларировать контракт
    """
    
    @abstractmethod
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> None:
        """Поместить задачу в очередь."""
        pass
    
    @abstractmethod
    def dequeue(self, task_name: str, timeout: float = 0.0) -> Optional[dict[str, Any]]:
        """
        Получить задачу из очереди.
        
        :param timeout: 0.0 = non-blocking, >0 = ждать до таймаута в секундах
        :return: payload задачи или None, если очередь пуста
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Проверить доступность очереди."""
        pass