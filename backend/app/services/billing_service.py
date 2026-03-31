"""
Stripe billing service — checkout, portal, webhook handling.
Uses stripe 7.x module-level API (stripe.api_key).
"""
import asyncio
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User


def _init_stripe() -> None:
    """Set stripe.api_key from settings (called lazily before each Stripe call)."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        raise HTTPException(503, "Stripe not configured — set STRIPE_SECRET_KEY in .env")


def _price_id_for_plan(plan_id: str) -> str:
    mapping = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "pro": settings.STRIPE_PRICE_PRO,
        "agency": settings.STRIPE_PRICE_AGENCY,
    }
    price = mapping.get(plan_id, "")
    if not price:
        raise HTTPException(400, f"Stripe price not configured for plan '{plan_id}'")
    return price


async def create_checkout_session(user: User, plan_id: str, db: AsyncSession) -> str:
    """Create Stripe Checkout Session and return the URL."""
    _init_stripe()

    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    if plan_result.scalar_one_or_none() is None:
        raise HTTPException(400, "Invalid plan_id")

    price_id = _price_id_for_plan(plan_id)

    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_result.scalar_one_or_none()
    customer_id = sub.stripe_customer_id if sub else None

    if not customer_id:
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer["id"]

    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.APP_URL}/dashboard/billing?success=1",
        cancel_url=f"{settings.APP_URL}/dashboard/billing?cancelled=1",
        metadata={"user_id": str(user.id), "plan_id": plan_id},
    )
    return session["url"]


async def create_portal_session(user: User, db: AsyncSession) -> str:
    """Create Stripe Customer Portal session and return the URL."""
    _init_stripe()

    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise HTTPException(400, "No Stripe billing account found. Please subscribe first.")

    session = await asyncio.to_thread(
        stripe.billing_portal.Session.create,
        customer=sub.stripe_customer_id,
        return_url=f"{settings.APP_URL}/dashboard/billing",
    )
    return session["url"]


async def get_billing_status(user: User, db: AsyncSession) -> dict:
    """Return subscription status, plan info, and current month usage."""
    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_result.scalar_one_or_none()

    if not sub:
        return {
            "subscription": {"status": "none"},
            "plan": None,
            "usage": {"responses_this_month": 0, "responses_limit": 0},
            "is_trial": False,
            "trial_days_remaining": None,
            "pro_features_available": False,
        }

    plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
    plan = plan_result.scalar_one_or_none()

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    usage_result = await db.execute(
        select(func.count()).where(
            UsageLog.user_id == user.id,
            UsageLog.billing_period == period,
        )
    )
    responses_used = usage_result.scalar() or 0

    now = datetime.now(timezone.utc)
    is_trial = sub.status == "trialing"
    trial_active = is_trial and sub.trial_end is not None and sub.trial_end > now
    trial_days_remaining: int | None = None
    if trial_active and sub.trial_end:
        trial_days_remaining = max(0, (sub.trial_end - now).days)

    # Pro features available if: active trial OR paid plan with pro/agency features
    pro_features_available = trial_active or (
        sub.status == "active" and plan is not None and plan.features.get("auto_respond", False)
    )

    return {
        "subscription": {
            "status": sub.status,
            "plan_id": sub.plan_id,
            "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "price_eur": plan.price_eur,
            "max_locations": plan.max_locations,
            "max_responses_per_month": plan.max_responses_per_month,
            "features": plan.features,
        } if plan else None,
        "usage": {
            "responses_this_month": responses_used,
            "responses_limit": plan.max_responses_per_month if plan else 0,
        },
        "is_trial": is_trial and trial_active,
        "trial_days_remaining": trial_days_remaining,
        "pro_features_available": pro_features_available,
    }


async def handle_webhook(payload: bytes, sig_header: str, db: AsyncSession) -> None:
    """Process incoming Stripe webhook event."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(400, "Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid Stripe signature")

    event_type = event["type"]
    data = event["data"]["object"]

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        plan_id = data.get("metadata", {}).get("plan_id", "starter")
        customer_id = data.get("customer")
        stripe_sub_id = data.get("subscription")

        if not (user_id and stripe_sub_id):
            return

        stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
        period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
        period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)

        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            return
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_uuid))
        sub = result.scalar_one_or_none()

        if sub:
            sub.plan_id = plan_id
            sub.stripe_subscription_id = stripe_sub_id
            sub.stripe_customer_id = customer_id
            sub.status = "active"
            sub.current_period_start = period_start
            sub.current_period_end = period_end
            sub.trial_end = None
        else:
            db.add(Subscription(
                user_id=user_id,
                plan_id=plan_id,
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=customer_id,
                status="active",
                current_period_start=period_start,
                current_period_end=period_end,
            ))
        await db.commit()

    elif event_type == "invoice.payment_succeeded":
        stripe_sub_id = data.get("subscription")
        if not stripe_sub_id:
            return
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
            sub.status = "active"
            sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
            sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)
            await db.commit()

    elif event_type == "invoice.payment_failed":
        stripe_sub_id = data.get("subscription")
        if not stripe_sub_id:
            return
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "past_due"
            await db.commit()

    elif event_type == "customer.subscription.deleted":
        stripe_sub_id = data.get("id")
        if not stripe_sub_id:
            return
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "cancelled"
            await db.commit()
