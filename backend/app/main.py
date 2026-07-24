from fastapi import FastAPI
from app.api.v1 import auth

from app.db import base

app = FastAPI(title="Raeltime Chat App")

app.include_router(auth.router, prefix="/api/v1/auth")

@app.get("/health")
async def health():
    return {"status": "OK"}