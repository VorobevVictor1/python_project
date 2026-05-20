from sqlalchemy.orm import Session
from app.models import Author, Book, Review
from app.schemas import AuthorCreate, BookCreate, ReviewCreate

# ==================== AUTHORS ====================


def create_author(db: Session, author: AuthorCreate) -> Author:
    db_author = Author(**author.model_dump())
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    return db_author


def get_authors(db: Session, skip: int = 0, limit: int = 100) -> list[Author]:
    return db.query(Author).offset(skip).limit(limit).all()


def get_author(db: Session, author_id: int) -> Author | None:
    return db.query(Author).filter(Author.id == author_id).first()


def update_author(db: Session, author_id: int, author: AuthorCreate) -> Author | None:
    db_author = get_author(db, author_id)
    if not db_author:
        return None
    for key, value in author.model_dump().items():
        setattr(db_author, key, value)
    db.commit()
    db.refresh(db_author)
    return db_author


def delete_author(db: Session, author_id: int) -> bool:
    db_author = get_author(db, author_id)
    if not db_author:
        return False
    db.delete(db_author)
    db.commit()
    return True


# ==================== BOOKS ====================


def create_book(db: Session, book: BookCreate) -> Book:
    db_book = Book(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_books(
    db: Session, skip: int = 0, limit: int = 100, author_id: int | None = None
) -> list[Book]:
    query = db.query(Book)
    if author_id is not None:
        query = query.filter(Book.author_id == author_id)
    return query.offset(skip).limit(limit).all()


def get_book(db: Session, book_id: int) -> Book | None:
    return db.query(Book).filter(Book.id == book_id).first()


def update_book(db: Session, book_id: int, book: BookCreate) -> Book | None:
    db_book = get_book(db, book_id)
    if not db_book:
        return None
    for key, value in book.model_dump().items():
        setattr(db_book, key, value)
    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int) -> bool:
    db_book = get_book(db, book_id)
    if not db_book:
        return False
    db.delete(db_book)
    db.commit()
    return True


# ==================== REVIEWS ====================


def create_review(db: Session, review: ReviewCreate, user_id: int) -> Review:
    db_review = Review(**review.model_dump(), user_id=user_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_reviews(
    db: Session, skip: int = 0, limit: int = 100, book_id: int | None = None
) -> list[Review]:
    query = db.query(Review)
    if book_id is not None:
        query = query.filter(Review.book_id == book_id)
    return query.offset(skip).limit(limit).all()


def get_review(db: Session, review_id: int) -> Review | None:
    return db.query(Review).filter(Review.id == review_id).first()


def update_review(
    db: Session, review_id: int, review: ReviewCreate, user_id: int
) -> Review | None:
    # Пользователь может обновить только свой отзыв
    db_review = (
        db.query(Review)
        .filter(Review.id == review_id, Review.user_id == user_id)
        .first()
    )
    if not db_review:
        return None
    for key, value in review.model_dump().items():
        setattr(db_review, key, value)
    db.commit()
    db.refresh(db_review)
    return db_review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    db_review = (
        db.query(Review)
        .filter(Review.id == review_id, Review.user_id == user_id)
        .first()
    )
    if not db_review:
        return False
    db.delete(db_review)
    db.commit()
    return True
