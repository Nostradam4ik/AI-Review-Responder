from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class PlanInfo(BaseModel):
    id: str
    name: str
    price_eur: int
    max_locations: int
    max_responses_per_month: int
    features: dict


class SubscriptionInfo(BaseModel):
    status: str
    plan_id: str | None = None
    trial_end: str | None = None
    current_period_end: str | None = None


class UsageInfo(BaseModel):
    responses_this_month: int
    responses_limit: int


class BillingStatusResponse(BaseModel):
    subscription: dict
    plan: dict | None
    usage: dict
