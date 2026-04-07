import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    from jose import JWTError

    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account deactivated")
    return user


def require_plan_feature(feature: str):
    """
    Returns a FastAPI dependency that:
    - 402 'trial_expired' if trial ended and no active subscription
    - 402 'feature_not_available' if plan does not include the feature
    - During active trial: all features unlocked
    """
    async def _check(
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from sqlalchemy import select
        from app.models.subscription import Subscription
        from app.models.plan import Plan

        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
        )
        sub = sub_result.scalar_one_or_none()

        if not sub:
            raise HTTPException(status_code=402, detail="subscription_required")

        now = datetime.now(timezone.utc)

        # Trial expired with no paid plan
        if sub.status == "trialing" and (not sub.trial_end or sub.trial_end < now):
            raise HTTPException(status_code=402, detail="trial_expired")

        if sub.status not in ("active", "trialing"):
            raise HTTPException(status_code=402, detail="subscription_required")

        # Active trial → all features unlocked
        if sub.status == "trialing":
            return current_user

        # Manually set expiry on active subscription
        now = datetime.now(timezone.utc)
        if sub.status == "active" and sub.current_period_end and sub.current_period_end < now:
            raise HTTPException(status_code=402, detail="subscription_expired")

        # Paid subscription → check plan features
        plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
        plan = plan_result.scalar_one_or_none()

        if not plan or not plan.features.get(feature, False):
            raise HTTPException(status_code=402, detail="feature_not_available")

        return current_user

    return _check
