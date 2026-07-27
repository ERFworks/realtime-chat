from jose import JWTError

from app.core.security import decode_token

def authenticate_websocket_token(token: str | None) -> int | None:

    if not token:
        return None

    try:
        payload = decode_token(token)
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    try:
        return int(sub)
    except (TypeError, ValueError):
        return None