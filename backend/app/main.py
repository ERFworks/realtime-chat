from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, conversations, messages, friends
from app.core.config import settings
from app.db import base

app = FastAPI(title="Raeltime Chat App")

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

@app.get("/health")
async def health():
    return {"status": "OK"}