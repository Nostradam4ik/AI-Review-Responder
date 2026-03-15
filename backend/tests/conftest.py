import asyncio
import sys
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Windows: force SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import create_access_token

# ── Test database ──────────────────────────────────────────────────────────
TEST_DB_URL = "postgresql+psycopg://reviewuser:reviewpass@localhost:5432/reviewdb_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per session, drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """Provide a transactional session that rolls back after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the test DB."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        business_name="Test Business",
        google_id="google-test-123",
        access_token="fake-google-token",
        refresh_token="fake-refresh-token",
        tone_preference="warm",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Return Bearer token headers for the test user."""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User) -> AsyncClient:
    """HTTP test client with overridden DB and auth dependencies."""
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
