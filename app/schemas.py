"""Pydantic схемы для валидации запросов и ответов API."""


from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ==================== AUTH ====================


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[\w.@+-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)


# ==================== AUTHORS ====================


class AuthorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class AuthorResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


# ==================== BOOKS ====================


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    year: int = Field(..., ge=1000, le=2026)
    author_id: int


class BookResponse(BaseModel):
    id: int
    title: str
    year: int
    author_id: int
    model_config = ConfigDict(from_attributes=True)


# ==================== REVIEWS ====================


class ReviewCreate(BaseModel):
    book_id: int
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: str | None = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    book_id: int
    user_id: int
    rating: float
    comment: str | None = None
    model_config = ConfigDict(from_attributes=True)


# ==================== ANALYTICS ====================


class RecommendationRequest(BaseModel):
    min_year: int = Field(default=1900, ge=1000, le=2026)
    max_rating: float = Field(default=5.0, ge=1.0, le=5.0)
    limit: int = Field(default=5, ge=1, le=50)
