from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    reading_events = relationship("ReadingEvent", back_populates="user")


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    books = relationship("Book", back_populates="author")


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    year = Column(Integer)
    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="books")
    reviews = relationship("Review", back_populates="book")
    reading_events = relationship("ReadingEvent", back_populates="book")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Float)
    comment = Column(String, nullable=True)
    book = relationship("Book", back_populates="reviews")


class ReadingEvent(Base):
    """Событие: пользователь прочитал книгу и поставил оценку.

    Это сырые данные для алгоритма рекомендаций.
    Не путать с Review — это внутренняя аналитическая сущность.
    """

    __tablename__ = "reading_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    rating = Column(Float, nullable=False)  # 1.0 - 5.0
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи для удобной навигации
    user = relationship("User", back_populates="reading_events")
    book = relationship("Book", back_populates="reading_events")

    # Уникальность: один пользователь — одна запись на книгу (последняя оценка)
    __table_args__ = (Index("idx_user_book_unique", "user_id", "book_id", unique=True),)


class RecommendationCache(Base):
    """Кэш предсчитанных рекомендаций.

    Заполняется батч-воркером, читается API.
    """

    __tablename__ = "recommendation_cache"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    recommended_book_ids = Column(String, nullable=False)  # JSON-список: "[1,5,23]"
    scores = Column(String, nullable=False)  # JSON-список скоров: "[0.92,0.87,0.81]"
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
