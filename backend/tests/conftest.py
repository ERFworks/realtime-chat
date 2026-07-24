import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)


TEST_DATABSE_URL = (
    "postgresql+asyncpg://chat_test:chat_test@localhost:5433/chat_test"   
)

os.environ["SQLALCHEMY_DATABASE_URL"] = TEST_DATABSE_URL

os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin123"
os.environ["MINIO_BUCKET_NAME"] = "realtime-chat-test"
os.environ["MINIO_USE_SSL"] = "false"

os.environ["SECRET_KEY"] = "test-secret-key-only-for-tests"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"


from app.db.base import Base  
from app.db.session import get_db  
from app.main import app  

test_engine = create_async_engine(
    TEST_DATABSE_URL,
    poolclass=NullPool
)


TestSessionLocal = async_sessionmaker(
    bind = test_engine,
    class_ = AsyncSession,
    expire_on_commit = False,
    autoflush = False
)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()



async def register_user(
    client: AsyncClient,
    username: str = "erf",
    password: str = "strong-password-123",
):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "first_name": "erfan",
            "last_name": None,
        },
    )

async def login_user(
    client: AsyncClient,
    username: str = "erf",
    password: str = "strong-password-123",
):
    return await client.post(
        "/api/v1/auth/login",
        data={
            "username": username,
            "password" : password
        }
    ) 