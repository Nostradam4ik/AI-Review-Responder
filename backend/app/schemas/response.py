import uuid
from datetime import datetime

from pydantic import BaseModel


class ResponseBase(BaseModel):
    ai_draft: str
    tone_used: str | None = None
    model_used: str | None = None


class ResponseCreate(BaseModel):
    review_id: uuid.UUID
    tone: str = "warm"


class ResponseEdit(BaseModel):
    final_text: str


class ResponseRead(ResponseBase):
    id: uuid.UUID
    review_id: uuid.UUID
    final_text: str | None = None
    was_edited: bool
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
