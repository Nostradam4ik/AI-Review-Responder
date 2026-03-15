import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    business_name: str | None = None
    tone_preference: str = "warm"
    language: str = "auto"


class UserCreate(UserBase):
    google_id: str


class UserUpdate(BaseModel):
    business_name: str | None = None
    tone_preference: str | None = None
    language: str | None = None


class UserRead(UserBase):
    id: uuid.UUID
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}
