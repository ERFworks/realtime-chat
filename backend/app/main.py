from fastapi import FastAPI

from app.api.v1 import auth, conversations, messages, friends

from app.db import base

app = FastAPI(title="Raeltime Chat App")

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(conversations.router, prefix="/api/v1/conversations")
app.include_router(messages.router, prefix="/api/v1/conversations")
app.include_router(friends.router, prefix="/api/v1/friends")

@app.get("/health")
async def health():
    return {"status": "OK"}