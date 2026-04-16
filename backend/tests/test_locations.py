"""Tests for locations router — sync persistence, deduplication, and error handling."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gmb_location(gmb_id: str | None = None, name: str = "Test Location") -> dict:
    return {
        "gmb_location_id": gmb_id or f"accounts/123/locations/{uuid.uuid4().hex[:8]}",
        "name": name,
        "address": "1 Main St, Paris",
    }


async def _mock_get_gmb_service(gmb_locations: list[dict]):
    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=gmb_locations)
    return mock_gmb


# ── list_locations ─────────────────────────────────────────────────────────────

async def test_list_locations_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/locations/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_locations_returns_saved(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    test_user,
):
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/1/locations/existing",
        name="My Restaurant",
        address="2 Rue Rivoli",
        is_active=True,
    )
    db_session.add(loc)
    await db_session.flush()

    resp = await client.get("/locations/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Restaurant"


# ── sync_locations ─────────────────────────────────────────────────────────────

async def test_sync_locations_no_google_token(client: AsyncClient, auth_headers, test_user):
    """Sync without Google token → returns message, no crash."""
    test_user.access_token = None
    resp = await client.post("/locations/sync", headers=auth_headers)
    assert resp.status_code == 200
    assert "No Google account" in resp.json()["message"]


async def test_sync_locations_persists_after_commit(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    test_user,
    trial_subscription,
):
    """Synced locations are committed to DB, not just flushed (Bug 2 regression)."""
    gmb_id = f"accounts/123/locations/{uuid.uuid4().hex[:8]}"
    locations = [_gmb_location(gmb_id=gmb_id, name="La Belle Vue")]

    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["new"] == 1
    assert "La Belle Vue" in data["locations"]

    # Verify the location exists in the DB session (after commit)
    result = await db_session.execute(
        select(Location).where(Location.gmb_location_id == gmb_id)
    )
    saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.name == "La Belle Vue"
    assert saved.user_id == test_user.id


async def test_sync_locations_no_duplicates(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    test_user,
    trial_subscription,
):
    """Syncing the same GMB location twice → only 1 record in DB (no duplicate)."""
    gmb_id = f"accounts/123/locations/{uuid.uuid4().hex[:8]}"
    locations = [_gmb_location(gmb_id=gmb_id, name="Café Dupont")]

    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        await client.post("/locations/sync", headers=auth_headers)

    # Second sync — same location, updated name
    locations[0]["name"] = "Café Dupont Updated"
    mock_gmb.get_locations = AsyncMock(return_value=locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 200
    # new=0 because location already existed
    assert resp.json()["new"] == 0

    result = await db_session.execute(
        select(Location).where(Location.gmb_location_id == gmb_id)
    )
    all_locs = result.scalars().all()
    assert len(all_locs) == 1
    assert all_locs[0].name == "Café Dupont Updated"


async def test_sync_locations_gmb_api_error(
    client: AsyncClient,
    auth_headers,
    test_user,
    trial_subscription,
):
    """GMB API error during sync → 502 with error message."""
    with patch("app.routers.locations.get_gmb_service", side_effect=Exception("GMB timeout")):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 502
    assert "GMB API error" in resp.json()["detail"]


async def test_sync_locations_respects_starter_plan_limit(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    test_user,
    active_subscription,
):
    """Starter plan (max_locations=1 from plan.max_locations column) enforced during sync."""
    # Starter plan has max_locations=1 as a column on Plan (not in features dict)
    existing = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"accounts/1/locations/existing-{uuid.uuid4().hex[:4]}",
        name="Existing",
        is_active=True,
    )
    db_session.add(existing)
    await db_session.flush()

    # Try to sync 2 new locations (plan only allows 1, and 1 already exists)
    two_locations = [
        _gmb_location(name="New Loc 1"),
        _gmb_location(name="New Loc 2"),
    ]

    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=two_locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    # Should be 402 location_limit_reached
    assert resp.status_code == 402
    assert "location_limit_reached" in resp.json()["detail"]


async def test_sync_locations_pro_plan_allows_three(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    test_user,
    pro_subscription,
):
    """Pro plan (max_locations=3 from plan.max_locations column) allows 3, blocks 4th."""
    three_locations = [_gmb_location(name=f"Loc {i}") for i in range(3)]

    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=three_locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["new"] == 3

    # A 4th location must be blocked
    mock_gmb.get_locations = AsyncMock(return_value=[_gmb_location(name="Loc 3")])

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 402
    assert "location_limit_reached" in resp.json()["detail"]


async def test_sync_locations_trial_user_unlimited(
    client: AsyncClient,
    auth_headers,
    test_user,
    trial_subscription,
):
    """Trial users have unlimited location slots."""
    locations = [_gmb_location(name=f"Loc {i}") for i in range(5)]

    mock_gmb = AsyncMock()
    mock_gmb.get_locations = AsyncMock(return_value=locations)

    with patch("app.routers.locations.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/locations/sync", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["new"] == 5
