from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.review import Review

GMB_BASE_URL = "https://mybusinessbusinessinformation.googleapis.com/v1"
GMB_REVIEWS_URL = "https://mybusiness.googleapis.com/v4"


class GMBService:
    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_locations(self) -> list[dict]:
        """Fetch all GMB business locations for the authenticated user."""
        async with httpx.AsyncClient() as client:
            # First get accounts
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
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GMB_REVIEWS_URL}/{location.gmb_location_id}/reviews",
                headers=self.headers,
            )
            if resp.status_code != 200:
                return []

            reviews_data = resp.json().get("reviews", [])

        for review_data in reviews_data:
            gmb_review_id = review_data["reviewId"]

            # Check if already exists
            result = await db.execute(
                select(Review).where(Review.gmb_review_id == gmb_review_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                continue

            # Parse rating
            rating_map = {
                "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5
            }
            rating_str = review_data.get("starRating", "THREE")
            rating = rating_map.get(rating_str, 3)

            # Parse date
            create_time = review_data.get("createTime")
            review_date = None
            if create_time:
                try:
                    review_date = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                except ValueError:
                    review_date = datetime.now(timezone.utc)

            review = Review(
                location_id=location.id,
                gmb_review_id=gmb_review_id,
                author_name=review_data.get("reviewer", {}).get("displayName"),
                rating=rating,
                comment=review_data.get("comment", ""),
                review_date=review_date,
                status="pending",
            )
            db.add(review)
            new_reviews.append(review)

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
