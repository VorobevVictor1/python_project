from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.core.task_queue import TaskQueueProtocol
from app.crud import (
    create_review,
    delete_review,
    get_review,
    get_reviews,
    update_review,
)
from app.database import get_db
from app.models import User
from app.routers.deps import get_task_queue
from app.schemas import ReviewCreate, ReviewResponse

router = APIRouter()


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_new_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    queue: TaskQueueProtocol = Depends(get_task_queue), 
):
    # 1. Сохраняем оценку в БД
    created_review = create_review(db=db, review=review, user_id=current_user.id)

    # 2. После успешного коммита ставим задачу в очередь
    queue.enqueue("recalculate_user", {"user_id": current_user.id})

    return created_review


@router.get("/", response_model=list[ReviewResponse])
def read_reviews(
    skip: int = 0,
    limit: int = 100,
    book_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_reviews(db=db, skip=skip, limit=limit, book_id=book_id)


@router.get("/{review_id}", response_model=ReviewResponse)
def read_review(review_id: int, db: Session = Depends(get_db)):
    db_review = get_review(db, review_id=review_id)
    if db_review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отзыв не найден")
    return db_review


@router.put("/{review_id}", response_model=ReviewResponse)
def update_existing_review(
    review_id: int,
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_review = update_review(db, review_id=review_id, review=review, user_id=current_user.id)
    if db_review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден или вы не автор",
        )
    return db_review


@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
def delete_existing_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_review(db, review_id=review_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден или вы не автор",
        )
    return {"message": "Отзыв успешно удалён"}
