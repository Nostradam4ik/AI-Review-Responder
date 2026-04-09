import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_token, encrypt_token
from app.models.location import Location
from app.models.review import Review

GMB_BASE_URL = "https://mybusinessbusinessinformation.googleapis.com/v1"
GMB_REVIEWS_URL = "https://mybusinessreviews.googleapis.com/v1"

logger = logging.getLogger(__name__)


def _calc_priority(rating: int, comment: str) -> int:
    """Return a priority score for a review (0–10).

    10 — 1-star (very negative, needs urgent response)
    7  — 2-star
    4  — 3-star
    2  — 4/5-star with a long comment (>100 chars, worth engaging)
    0  — 4/5-star with short/no comment
    """
    if rating == 1:
        return 10
    if rating == 2:
        return 7
    if rating == 3:
        return 4
    if len(comment or "") > 100:
        return 2
    return 0


async def refresh_google_token(user, db: AsyncSession) -> None:
    """Refresh the user's Google access token if expired or within 5 minutes of expiry.

    Updates user.access_token and user.token_expires_at and commits to DB.
    Raises ValueError if refresh fails (caller should skip this user).
    """
    from app.config import settings

    now = datetime.now(timezone.utc)
    if user.token_expires_at and user.token_expires_at > now + timedelta(minutes=5):
        return  # Still valid

    if not user.refresh_token:
        raise ValueError(f"No refresh token for user {user.id} — cannot refresh access token")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": decrypt_token(user.refresh_token),
            },
        )

    if resp.status_code != 200:
        raise ValueError(
            f"Failed to refresh Google token for user {user.id}: "
            f"{resp.status_code} {resp.text[:200]}"
        )

    data = resp.json()
    user.access_token = encrypt_token(data["access_token"])
    expires_in = data.get("expires_in", 3600)
    user.token_expires_at = now + timedelta(seconds=expires_in)
    await db.commit()
    logger.info("Refreshed Google token for user %s", user.id)


async def get_gmb_service(user, db: AsyncSession) -> "GMBService":
    """Return a GMBService with a valid access token, refreshing if needed."""
    await refresh_google_token(user, db)
    return GMBService(decrypt_token(user.access_token))


class GMBService:
    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_locations(self) -> list[dict]:
        """Fetch all GMB business locations for the authenticated user."""
        async with httpx.AsyncClient() as client:
            accounts_resp = await client.get(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                headers=self.headers,
            )
            accounts_resp.raise_for_status()
            accounts = accounts_resp.json().get("accounts", [])

            locations = []
            for account in accounts:
                account_name = account["name"]
                locs_resp = await client.get(
                    f"{GMB_BASE_URL}/{account_name}/locations",
                    headers=self.headers,
                    params={"readMask": "name,title,storefrontAddress"},
                )
                if locs_resp.status_code == 200:
                    for loc in locs_resp.json().get("locations", []):
                        address_parts = loc.get("storefrontAddress", {})
                        address_lines = address_parts.get("addressLines", [])
                        locality = address_parts.get("locality", "")
                        address = ", ".join(address_lines + ([locality] if locality else []))
                        locations.append({
                            "gmb_location_id": loc["name"],
                            "name": loc.get("title", ""),
                            "address": address,
                        })
            return locations

    async def sync_reviews(
        self,
        location: Location,
        db: AsyncSession,
    ) -> list[Review]:
        """Fetch reviews from GMB and upsert into DB. Returns newly added reviews."""
        new_reviews = []
        next_page_token = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params: dict = {"pageSize": 50}
                if next_page_token:
                    params["pageToken"] = next_page_token

                resp = await client.get(
                    f"{GMB_REVIEWS_URL}/{location.gmb_location_id}/reviews",
                    headers=self.headers,
                    params=params,
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                reviews_data = data.get("reviews", [])

                for review_data in reviews_data:
                    gmb_review_id = review_data["reviewId"]

                    result = await db.execute(
                        select(Review).where(Review.gmb_review_id == gmb_review_id)
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        if review_data.get("reviewReply") and existing.status != "responded":
                            existing.status = "responded"
                        continue

                    rating_map = {
                        "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5
                    }
                    rating_str = review_data.get("starRating", "THREE")
                    rating = rating_map.get(rating_str, 3)

                    create_time = review_data.get("createTime")
                    review_date = None
                    if create_time:
                        try:
                            review_date = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                        except ValueError:
                            review_date = datetime.now(timezone.utc)

                    comment_text = review_data.get("comment", "")
                    priority_score = _calc_priority(rating, comment_text)

                    review = Review(
                        location_id=location.id,
                        gmb_review_id=gmb_review_id,
                        author_name=review_data.get("reviewer", {}).get("displayName"),
                        rating=rating,
                        comment=comment_text,
                        language=review_data.get("languageCode", "fr"),
                        review_date=review_date,
                        status="pending",
                        priority_score=priority_score,
                    )
                    db.add(review)
                    new_reviews.append(review)

                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break

        await db.flush()
        return new_reviews

    async def publish_response(
        self,
        gmb_location_id: str,
        review_id: str,
        response_text: str,
    ) -> bool:
        """Publish a reply to a GMB review."""
        url = f"{GMB_REVIEWS_URL}/{gmb_location_id}/reviews/{review_id}/reply"
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                url,
                headers=self.headers,
                json={"comment": response_text},
            )
            return resp.status_code in (200, 201)
