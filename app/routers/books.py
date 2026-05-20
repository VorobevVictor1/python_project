from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import create_book, delete_book, get_book, get_books, update_book
from app.database import get_db
from app.schemas import BookCreate, BookResponse

router = APIRouter()


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_new_book(book: BookCreate, db: Session = Depends(get_db)):
    return create_book(db=db, book=book)


@router.get("/", response_model=list[BookResponse])
def read_books(
    skip: int = 0,
    limit: int = 100,
    author_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_books(db=db, skip=skip, limit=limit, author_id=author_id)


@router.get("/{book_id}", response_model=BookResponse)
def read_book(book_id: int, db: Session = Depends(get_db)):
    db_book = get_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")
    return db_book


@router.put("/{book_id}", response_model=BookResponse)
def update_existing_book(book_id: int, book: BookCreate, db: Session = Depends(get_db)):
    db_book = update_book(db, book_id=book_id, book=book)
    if db_book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")
    return db_book


@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
def delete_existing_book(book_id: int, db: Session = Depends(get_db)):
    if not delete_book(db, book_id=book_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")
    return {"message": "Книга успешно удалена"}
