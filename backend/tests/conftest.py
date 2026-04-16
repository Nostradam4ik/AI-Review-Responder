import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Windows: force SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import Base, get_db
from app.main import app
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.core.security import create_access_token, hash_password

# Allow overriding via env var for Docker-based test runners
TEST_DB_URL = os.getenv(
    "PYTEST_DB_URL",
    "postgresql+psycopg://reviewuser:reviewpass@localhost:5432/reviewdb_test",
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ── Schema lifecycle ────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session, drop them on teardown."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_plans(create_tables):
    """Seed static plan rows once per test session (committed to test DB)."""
    async with TestSessionLocal() as session:
        result = await session.execute(select(Plan).where(Plan.id == "starter"))
        if result.scalar_one_or_none() is None:
            session.add_all([
                Plan(
                    id="starter",
                    name="Starter",
                    price_eur=19,
                    max_locations=1,
                    max_responses_per_month=100,
                    features={"export_csv": False, "auto_respond": False, "analytics": False},
                ),
                Plan(
                    id="pro",
                    name="Pro",
                    price_eur=39,
                    max_locations=3,
                    max_responses_per_month=500,
                    features={"export_csv": True, "auto_respond": True, "analytics": True},
                ),
                Plan(
                    id="agency",
                    name="Agency",
                    price_eur=79,
                    max_locations=10,
                    max_responses_per_month=0,
                    features={"export_csv": True, "auto_respond": True, "analytics": True},
                ),
            ])
            await session.commit()


# ── DB session with rollback isolation ─────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """Transactional session that rolls back after each test.

    Using bind=conn so that route-level session.commit() calls only release
    the session-level savepoint — the outer connection transaction is never
    committed to disk and is fully rolled back after the test.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


# ── User fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """A plain (non-admin) user with a unique email per test."""
    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.com",
        business_name="Test Business",
        password_hash=hash_password("password123"),
        email_verified=True,
        is_active=True,
        tone_preference="warm",
        access_token="fake-google-token",
        refresh_token="fake-refresh-token",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """An admin user with a unique email per test."""
    user = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        business_name="Admin",
        password_hash=hash_password("adminpass123"),
        email_verified=True,
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── Subscription fixtures ───────────────────────────────────────────────────

@pytest_asyncio.fixture
async def trial_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="trialing",
        trial_end=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture
async def expired_trial_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="trialing",
        trial_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture
async def active_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="active",
        current_period_start=datetime.now(timezone.utc) - timedelta(days=5),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture
async def pro_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    sub = Subscription(
        user_id=test_user.id,
        plan_id="pro",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


# ── Auth helpers ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


# ── HTTP client fixtures ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User) -> AsyncClient:
    """Client with overridden DB and current-user dependencies."""
    from app.core.dependencies import get_current_user

    async def override_db():
        yield db_session

    async def override_user():
        return test_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession, admin_user: User) -> AsyncClient:
    """Client whose current-user is an admin."""
    from app.core.dependencies import get_current_user

    async def override_db():
        yield db_session

    async def override_admin():
        return admin_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def raw_client(db_session: AsyncSession) -> AsyncClient:
    """Client with only DB overridden — no user injection (for auth tests)."""
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
