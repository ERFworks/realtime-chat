import hashlib
import uuid
from datetime import timedelta

from jose import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.utils.time import utcnow

password_hash = PasswordHash.recommended() 



def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, family_id: str | None = None):
    expire = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()

    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    if family_id:
        to_encode["fid"] = family_id
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()