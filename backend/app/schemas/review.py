import uuid
from datetime import datetime

from pydantic import BaseModel


class ReviewBase(BaseModel):
    author_name: str | None = None
    rating: int
    comment: str | None = None
    language: str | None = None


class ReviewRead(ReviewBase):
    id: uuid.UUID
    location_id: uuid.UUID
    gmb_review_id: str
    review_date: datetime | None = None
    status: str
    synced_at: datetime

    model_config = {"from_attributes": True}


class ReviewList(BaseModel):
    reviews: list[ReviewRead]
    total: int
