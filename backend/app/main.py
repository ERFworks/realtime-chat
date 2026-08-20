import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.adapters.file_storage import ensure_bucket_exists
from app.api.v1 import auth, conversations, friends, messages, profiles, users
from app.core.config import settings
from app.db.redis import redis_client
from app.websocket import router as ws_router
from app.websocket.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(ensure_bucket_exists)
    listener_task = asyncio.create_task(manager.start_listener())
    yield

    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    await manager.disconnect_all()
    await redis_client.aclose()

app = FastAPI(title="Realtime Chat App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(conversations.router, prefix="/api/v1/conversations")
app.include_router(messages.router, prefix="/api/v1/conversations")
app.include_router(friends.router, prefix="/api/v1/friends")
app.include_router(profiles.router, prefix="/api/v1/profile")
app.include_router(ws_router.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1/users")


@app.get("/health")
async def health():
    return {"status": "OK"}