"""
Review Collection Links — QR/NFC routing pages.

Public flow:
  GET /c/{slug}          — HTML star-rating page (served as inline HTML)
  POST /c/{slug}/feedback — submit a rating (1–5)
    • rating 1–3 → store as InternalFeedback (private)
    • rating 4–5 → redirect to Google Maps review page

Authenticated flow (owner):
  POST /collection/links       — create a link for one of their locations
  GET  /collection/links       — list all links for the authenticated user
  GET  /collection/links/{id}/stats — submission stats for a link
"""
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.collection_link import InternalFeedback, ReviewCollectionLink
from app.models.location import Location
from app.models.user import User

router = APIRouter(tags=["collection"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CreateLinkBody(BaseModel):
    location_id: uuid.UUID
    google_maps_url: str


class FeedbackBody(BaseModel):
    rating: int
    comment: str = ""


# ── Authenticated endpoints ───────────────────────────────────────────────────

@router.post("/collection/links", status_code=201)
async def create_collection_link(
    body: CreateLinkBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a review collection link for one of the user's locations."""
    # Verify location belongs to user
    location = await db.get(Location, body.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(404, "Location not found")

    if not body.google_maps_url.startswith("https://"):
        raise HTTPException(400, "google_maps_url must be a valid https URL")

    slug = secrets.token_urlsafe(8)  # ~11 chars, URL-safe, unique enough

    link = ReviewCollectionLink(
        location_id=body.location_id,
        slug=slug,
        google_maps_url=body.google_maps_url,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "id": str(link.id),
        "slug": link.slug,
        "url": f"/c/{link.slug}",
        "google_maps_url": link.google_maps_url,
        "location_id": str(link.location_id),
        "created_at": link.created_at.isoformat(),
    }


@router.get("/collection/links")
async def list_collection_links(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all review collection links for the authenticated user."""
    # Get user's location IDs
    locs = await db.execute(
        select(Location.id, Location.name).where(Location.user_id == current_user.id)
    )
    loc_map = {row.id: row.name for row in locs.all()}

    if not loc_map:
        return {"links": []}

    result = await db.execute(
        select(ReviewCollectionLink)
        .where(ReviewCollectionLink.location_id.in_(list(loc_map.keys())))
        .order_by(ReviewCollectionLink.created_at.desc())
    )
    links = result.scalars().all()

    return {
        "links": [
            {
                "id": str(lnk.id),
                "slug": lnk.slug,
                "url": f"/c/{lnk.slug}",
                "google_maps_url": lnk.google_maps_url,
                "location_id": str(lnk.location_id),
                "location_name": loc_map.get(lnk.location_id, ""),
                "is_active": lnk.is_active,
                "created_at": lnk.created_at.isoformat(),
            }
            for lnk in links
        ]
    }


@router.get("/collection/links/{link_id}/stats")
async def get_link_stats(
    link_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return submission statistics for a collection link."""
    link = await db.get(ReviewCollectionLink, link_id)
    if not link:
        raise HTTPException(404, "Link not found")

    # Verify ownership via location
    location = await db.get(Location, link.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(403, "Forbidden")

    result = await db.execute(
        select(InternalFeedback).where(InternalFeedback.link_id == link_id)
    )
    feedbacks = result.scalars().all()

    total = len(feedbacks)
    avg_rating = sum(f.rating for f in feedbacks) / total if total else 0.0
    by_rating = {str(i): sum(1 for f in feedbacks if f.rating == i) for i in range(1, 6)}

    return {
        "link_id": str(link_id),
        "total_submissions": total,
        "avg_rating": round(avg_rating, 2),
        "by_rating": by_rating,
    }


# ── Public endpoints ──────────────────────────────────────────────────────────

_STAR_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Donnez votre avis</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f9fafb; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; padding: 1rem; }}
  .card {{ background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.08);
           padding: 2.5rem 2rem; max-width: 420px; width: 100%; text-align: center; }}
  h1 {{ font-size: 1.4rem; color: #111827; margin-bottom: .5rem; }}
  p  {{ color: #6b7280; font-size: .95rem; margin-bottom: 1.5rem; }}
  .stars {{ display: flex; justify-content: center; gap: .5rem; margin-bottom: 1rem; }}
  .star {{ font-size: 2.8rem; cursor: pointer; transition: transform .1s; user-select: none; }}
  .star:hover, .star.active {{ transform: scale(1.15); }}
  textarea {{ width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; padding: .75rem;
              font-size: .9rem; resize: vertical; min-height: 80px; margin-bottom: 1rem; }}
  button {{ background: #2563eb; color: #fff; border: none; border-radius: 8px;
            padding: .8rem 2rem; font-size: 1rem; cursor: pointer; width: 100%; }}
  button:hover {{ background: #1d4ed8; }}
  .hidden {{ display: none; }}
</style>
</head>
<body>
<div class="card">
  <h1>Votre expérience compte !</h1>
  <p>Comment s'est passée votre visite ?</p>
  <div class="stars" id="stars">
    <span class="star" data-v="1">⭐</span>
    <span class="star" data-v="2">⭐</span>
    <span class="star" data-v="3">⭐</span>
    <span class="star" data-v="4">⭐</span>
    <span class="star" data-v="5">⭐</span>
  </div>
  <textarea id="comment" placeholder="Un commentaire ? (optionnel)" class="hidden"></textarea>
  <button id="send" class="hidden" onclick="submit()">Envoyer</button>
</div>
<script>
let selected = 0;
const stars = document.querySelectorAll('.star');
stars.forEach(s => s.addEventListener('click', () => {{
  selected = +s.dataset.v;
  stars.forEach((x, i) => x.classList.toggle('active', i < selected));
  document.getElementById('comment').classList.remove('hidden');
  document.getElementById('send').classList.remove('hidden');
}}));
async function submit() {{
  const comment = document.getElementById('comment').value;
  const r = await fetch('/c/{slug}/feedback', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{rating: selected, comment}})
  }});
  const data = await r.json();
  if (data.redirect) {{ window.location.href = data.redirect; }}
  else {{ document.querySelector('.card').innerHTML = '<h1>Merci !</h1><p>Votre avis a été enregistré.</p>'; }}
}}
</script>
</body>
</html>"""


@router.get("/c/{slug}", response_class=HTMLResponse)
async def collection_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Public star-rating landing page."""
    result = await db.execute(
        select(ReviewCollectionLink).where(
            ReviewCollectionLink.slug == slug,
            ReviewCollectionLink.is_active == True,  # noqa: E712
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Link not found or inactive")

    return HTMLResponse(_STAR_PAGE_TEMPLATE.format(slug=slug))


@router.post("/c/{slug}/feedback")
async def submit_feedback(
    slug: str,
    body: FeedbackBody,
    db: AsyncSession = Depends(get_db),
):
    """Submit a rating.

    - rating 1–3 → store privately as InternalFeedback
    - rating 4–5 → return Google Maps URL for redirect
    """
    if body.rating not in range(1, 6):
        raise HTTPException(400, "rating must be 1–5")

    result = await db.execute(
        select(ReviewCollectionLink).where(
            ReviewCollectionLink.slug == slug,
            ReviewCollectionLink.is_active == True,  # noqa: E712
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Link not found or inactive")

    if body.rating >= 4:
        # Happy customer → send to Google Maps to leave a public review
        return {"redirect": link.google_maps_url}

    # Unhappy customer → capture privately
    db.add(InternalFeedback(
        link_id=link.id,
        rating=body.rating,
        comment=body.comment or None,
    ))
    await db.commit()
    return {"redirect": None}
