"""Tests for the Review Collection Links router.

Public flow: GET /c/{slug} → HTML page; POST /c/{slug}/feedback → save or redirect
Auth flow:   POST /collection/links, GET /collection/links, GET /collection/links/{id}/stats
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection_link import InternalFeedback, ReviewCollectionLink
from app.models.location import Location
from app.models.user import User


# ── Local fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_location(db_session: AsyncSession, test_user: User) -> Location:
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"loc-coll-{uuid.uuid4().hex[:8]}",
        name="Collection Test Restaurant",
        is_active=True,
    )
    db_session.add(loc)
    await db_session.flush()
    return loc


@pytest_asyncio.fixture
async def test_link(db_session: AsyncSession, test_location: Location) -> ReviewCollectionLink:
    link = ReviewCollectionLink(
        id=uuid.uuid4(),
        location_id=test_location.id,
        slug=f"test-slug-{uuid.uuid4().hex[:6]}",
        google_maps_url="https://maps.google.com/test",
        is_active=True,
    )
    db_session.add(link)
    await db_session.flush()
    return link


# ── POST /collection/links ────────────────────────────────────────────────────

async def test_create_collection_link(
    client: AsyncClient,
    db_session: AsyncSession,
    test_location: Location,
):
    """Authenticated user creates a link for their location → 201, slug returned."""
    resp = await client.post("/collection/links", json={
        "location_id": str(test_location.id),
        "google_maps_url": "https://maps.google.com/newlink",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert "slug" in data
    assert data["location_id"] == str(test_location.id)
    assert data["url"].startswith("/c/")


async def test_create_collection_link_wrong_location(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Location belonging to another user → 404."""
    resp = await client.post("/collection/links", json={
        "location_id": str(uuid.uuid4()),
        "google_maps_url": "https://maps.google.com/other",
    })
    assert resp.status_code == 404


async def test_create_collection_link_bad_url(
    client: AsyncClient,
    test_location: Location,
):
    """Non-https google_maps_url → 400."""
    resp = await client.post("/collection/links", json={
        "location_id": str(test_location.id),
        "google_maps_url": "http://maps.google.com/insecure",
    })
    assert resp.status_code == 400


async def test_create_collection_link_missing_url(
    client: AsyncClient,
    test_location: Location,
):
    """Missing google_maps_url field → 422 (Pydantic validation)."""
    resp = await client.post("/collection/links", json={
        "location_id": str(test_location.id),
    })
    assert resp.status_code == 422


# ── GET /collection/links ─────────────────────────────────────────────────────

async def test_list_collection_links_returns_own_links(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
    test_location: Location,
):
    """User sees their own links."""
    resp = await client.get("/collection/links")
    assert resp.status_code == 200
    data = resp.json()
    assert any(lnk["id"] == str(test_link.id) for lnk in data["links"])


async def test_list_collection_links_empty_for_new_user(
    db_session: AsyncSession,
):
    """User with no locations → empty list (no crash)."""
    from app.main import app
    from app.database import get_db
    from app.core.dependencies import get_current_user
    from httpx import AsyncClient, ASGITransport

    new_user = User(
        id=uuid.uuid4(),
        email=f"empty-{uuid.uuid4().hex[:8]}@test.com",
        is_active=True,
        email_verified=True,
    )
    db_session.add(new_user)
    await db_session.flush()

    async def _db():
        yield db_session

    async def _user():
        return new_user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/collection/links")
        assert resp.status_code == 200
        assert resp.json()["links"] == []
    finally:
        app.dependency_overrides.clear()


# ── GET /c/{slug} — public HTML page ─────────────────────────────────────────

async def test_public_page_valid_slug_returns_html(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
):
    """Valid active slug → 200 with HTML content type."""
    resp = await client.get(f"/c/{test_link.slug}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<title>" in resp.text


async def test_public_page_invalid_slug_returns_404(client: AsyncClient):
    """Unknown slug → 404."""
    resp = await client.get("/c/this-slug-does-not-exist-xyz")
    assert resp.status_code == 404


async def test_public_page_inactive_link_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Inactive link → 404."""
    test_link.is_active = False
    await db_session.flush()

    resp = await client.get(f"/c/{test_link.slug}")
    assert resp.status_code == 404


# ── POST /c/{slug}/feedback ───────────────────────────────────────────────────

async def test_feedback_low_rating_saves_internally(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Rating 1–3 → InternalFeedback row created, redirect=None."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={
        "rating": 2,
        "comment": "Not great",
    })

    assert resp.status_code == 200
    assert resp.json()["redirect"] is None

    result = await db_session.execute(
        select(InternalFeedback).where(InternalFeedback.link_id == test_link.id)
    )
    feedbacks = result.scalars().all()
    assert len(feedbacks) == 1
    assert feedbacks[0].rating == 2
    assert feedbacks[0].comment == "Not great"


async def test_feedback_high_rating_redirects_to_google(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Rating 4–5 → redirect URL returned, no InternalFeedback saved."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 5})

    assert resp.status_code == 200
    assert resp.json()["redirect"] == "https://maps.google.com/test"

    result = await db_session.execute(
        select(InternalFeedback).where(InternalFeedback.link_id == test_link.id)
    )
    assert result.scalars().all() == []


async def test_feedback_boundary_rating_3_is_internal(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Rating 3 (boundary) → captured internally, NOT redirected."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 3})
    assert resp.status_code == 200
    assert resp.json()["redirect"] is None


async def test_feedback_boundary_rating_4_is_redirect(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
):
    """Rating 4 (boundary) → redirect URL returned."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 4})
    assert resp.status_code == 200
    assert resp.json()["redirect"] is not None


async def test_feedback_invalid_rating_zero(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
):
    """Rating 0 → 400 (out of range 1–5)."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 0})
    assert resp.status_code == 400


async def test_feedback_invalid_rating_six(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
):
    """Rating 6 → 400 (out of range 1–5)."""
    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 6})
    assert resp.status_code == 400


async def test_feedback_inactive_link_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Feedback on inactive link → 404."""
    test_link.is_active = False
    await db_session.flush()

    resp = await client.post(f"/c/{test_link.slug}/feedback", json={"rating": 3})
    assert resp.status_code == 404


# ── GET /collection/links/{id}/stats ─────────────────────────────────────────

async def test_stats_all_zeros_for_new_link(
    client: AsyncClient,
    test_link: ReviewCollectionLink,
):
    """Fresh link → total_submissions=0, avg_rating=0."""
    resp = await client.get(f"/collection/links/{test_link.id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_submissions"] == 0
    assert data["avg_rating"] == 0.0


async def test_stats_counts_internal_feedback(
    client: AsyncClient,
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Stats reflect the actual InternalFeedback rows."""
    db_session.add_all([
        InternalFeedback(link_id=test_link.id, rating=1),
        InternalFeedback(link_id=test_link.id, rating=2),
        InternalFeedback(link_id=test_link.id, rating=3),
    ])
    await db_session.flush()

    resp = await client.get(f"/collection/links/{test_link.id}/stats")
    data = resp.json()
    assert data["total_submissions"] == 3
    assert data["avg_rating"] == 2.0
    assert data["by_rating"]["1"] == 1
    assert data["by_rating"]["2"] == 1
    assert data["by_rating"]["3"] == 1


async def test_stats_forbidden_for_other_user(
    db_session: AsyncSession,
    test_link: ReviewCollectionLink,
):
    """Stats for a link owned by another user → 403."""
    from app.main import app
    from app.database import get_db
    from app.core.dependencies import get_current_user
    from httpx import AsyncClient, ASGITransport
    from app.core.security import hash_password

    other = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pw"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(other)
    await db_session.flush()

    async def _db():
        yield db_session

    async def _other():
        return other

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _other

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/collection/links/{test_link.id}/stats")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
