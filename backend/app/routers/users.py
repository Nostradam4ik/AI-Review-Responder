"""User profile endpoints."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    id: str
    email: str
    business_name: str | None
    tone_preference: str
    language: str
    email_verified: bool
    onboarding_done: bool
    has_password: bool
    telegram_connected: bool
    auto_publish: bool
    response_instructions: str | None
    is_admin: bool


class UpdateProfileRequest(BaseModel):
    business_name: str | None = None
    tone_preference: str | None = None
    language: str | None = None
    onboarding_done: bool | None = None
    auto_publish: bool | None = None
    response_instructions: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _profile(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        business_name=user.business_name,
        tone_preference=user.tone_preference,
        language=user.language,
        email_verified=user.email_verified,
        onboarding_done=user.onboarding_done,
        has_password=bool(user.password_hash),
        telegram_connected=bool(user.telegram_chat_id),
        auto_publish=bool(user.auto_publish),
        response_instructions=user.response_instructions,
        is_admin=bool(user.is_admin),
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return _profile(current_user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.business_name is not None:
        current_user.business_name = body.business_name
    if body.tone_preference is not None:
        current_user.tone_preference = body.tone_preference
    if body.language is not None:
        current_user.language = body.language
    if body.onboarding_done is not None:
        current_user.onboarding_done = body.onboarding_done
    if body.auto_publish is not None:
        current_user.auto_publish = body.auto_publish
    if body.response_instructions is not None:
        instructions = re.sub(r'[\x00-\x1f\x7f]', '', body.response_instructions.strip())
        if len(instructions) > 1000:
            raise HTTPException(422, "response_instructions must be 1000 characters or fewer")
        current_user.response_instructions = instructions or None

    await db.commit()
    await db.refresh(current_user)
    return _profile(current_user)


@router.post("/me/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.password_hash:
        raise HTTPException(400, "This account uses Google sign-in — password change not applicable")
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


@router.get("/me/telegram-status")
async def telegram_status(current_user: User = Depends(get_current_user)):
    return {"connected": bool(current_user.telegram_chat_id)}


@router.delete("/me/telegram")
async def disconnect_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.telegram_chat_id = None
    await db.commit()
    return {"disconnected": True}
