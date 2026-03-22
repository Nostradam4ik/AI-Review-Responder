"""User profile endpoints."""
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


class UpdateProfileRequest(BaseModel):
    business_name: str | None = None
    tone_preference: str | None = None
    language: str | None = None
    onboarding_done: bool | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        business_name=current_user.business_name,
        tone_preference=current_user.tone_preference,
        language=current_user.language,
        email_verified=current_user.email_verified,
        onboarding_done=current_user.onboarding_done,
    )


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

    await db.commit()
    await db.refresh(current_user)

    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        business_name=current_user.business_name,
        tone_preference=current_user.tone_preference,
        language=current_user.language,
        email_verified=current_user.email_verified,
        onboarding_done=current_user.onboarding_done,
    )


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
