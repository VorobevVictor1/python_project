from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RecommendationOut(BaseModel):
    book_id: int
    score: float


class UserRecommendationsOut(BaseModel):
    user_id: int
    recommendations: List[RecommendationOut] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
    algorithm_version: str = "cosine_numpy_v1"