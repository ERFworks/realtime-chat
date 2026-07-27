from app.websocket import router as ws_router

from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, conversations, messages, friends, profiles
from app.core.config import settings
from app.utils.file_storage import ensure_bucket_exists

@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(ensure_bucket_exists)
    yield

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

@app.get("/health")
async def health():
    return {"status": "OK"}