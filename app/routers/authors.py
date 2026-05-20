from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import (
    create_author,
    delete_author,
    get_author,
    get_authors,
    update_author,
)
from app.database import get_db
from app.schemas import AuthorCreate, AuthorResponse

router = APIRouter()


@router.post("/", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
def create_new_author(author: AuthorCreate, db: Session = Depends(get_db)):
    return create_author(db=db, author=author)


@router.get("/", response_model=list[AuthorResponse])
def read_authors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_authors(db=db, skip=skip, limit=limit)


@router.get("/{author_id}", response_model=AuthorResponse)
def read_author(author_id: int, db: Session = Depends(get_db)):
    db_author = get_author(db, author_id=author_id)
    if db_author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Автор не найден")
    return db_author


@router.put("/{author_id}", response_model=AuthorResponse)
def update_existing_author(author_id: int, author: AuthorCreate, db: Session = Depends(get_db)):
    db_author = update_author(db, author_id=author_id, author=author)
    if db_author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Автор не найден")
    return db_author


@router.delete("/{author_id}", status_code=status.HTTP_200_OK)
def delete_existing_author(author_id: int, db: Session = Depends(get_db)):
    if not delete_author(db, author_id=author_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Автор не найден")
    return {"message": "Автор успешно удалён"}
