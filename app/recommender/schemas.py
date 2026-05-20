from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationOut(BaseModel):
    book_id: int
    score: float


class UserRecommendationsOut(BaseModel):
    user_id: int
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    generated_at: datetime | None = None
    algorithm_version: str = "cosine_numpy_v1"
