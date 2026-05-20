from app.infrastructure.in_memory_queue import InMemoryTaskQueue


def test_in_memory_queue_basic():
    queue = InMemoryTaskQueue()

    # Enqueue / Dequeue
    queue.enqueue("recalc", {"user_id": 42})
    task = queue.dequeue("recalc")

    assert task == {"user_id": 42}
    assert queue.dequeue("recalc") is None  # очередь пуста


def test_in_memory_queue_isolation():
    """Проверяем, что copy() защищает от мутаций."""
    queue = InMemoryTaskQueue()
    payload = {"user_id": 1, "meta": {"cnt": 1}}

    queue.enqueue("test", payload)
    payload["meta"]["cnt"] = 999  # мутируем оригинал

    retrieved = queue.dequeue("test")
    assert retrieved["meta"]["cnt"] == 1  # в очереди — копия!
