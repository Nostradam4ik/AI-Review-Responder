from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from app.services.billing_service import (
    create_checkout_session,
    create_portal_session,
    get_billing_status,
    handle_webhook,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for plan upgrade."""
    from app.config import settings
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    url = await create_checkout_session(current_user, body.plan_id, db)
    return CheckoutResponse(checkout_url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events. Does NOT require auth (called by Stripe)."""
    if stripe_signature is None:
        raise HTTPException(400, "Missing stripe-signature header")
    payload = await request.body()
    await handle_webhook(payload, stripe_signature, db)
    return {"status": "ok"}


@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current plan, usage, and subscription details."""
    return await get_billing_status(current_user, db)


@router.post("/portal", response_model=PortalResponse)
async def billing_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Customer Portal session for managing billing."""
    from app.config import settings
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    url = await create_portal_session(current_user, db)
    return PortalResponse(portal_url=url)
