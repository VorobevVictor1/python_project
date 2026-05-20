from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.routers.deps import get_task_queue
from app.database import get_db
from app.core.task_queue import TaskQueueProtocol
from app.recommender.service import RecommendationService
from app.recommender.schemas import UserRecommendationsOut


router = APIRouter(tags=["Рекомендации"]) 


def trigger_user_recalculation(user_id: int, queue: TaskQueueProtocol) -> None:
    """
    Вспомогательная функция для постановки задачи в очередь.
    Вызывается из существующих CRUD-эндпоинтов после создания/обновления оценки.
    """
    queue.enqueue("recalculate_user", {"user_id": user_id})


@router.get("/{user_id}", response_model=UserRecommendationsOut)
def get_user_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    Отдаёт предсчитанные рекомендации.
    
    Не блокируется на расчёте: читает только из RecommendationCache.
    Если кэш пуст, возвращает пустой список (батч ещё не отработал).
    """
    service = RecommendationService(db=db)
    cached = service.get_from_cache(user_id)
    
    if not cached:
        # Возвращаем 200 с пустым списком.
        # Альтернатива: 202 Accepted + статус пересчёта.
        return UserRecommendationsOut(user_id=user_id)
    
    return cached