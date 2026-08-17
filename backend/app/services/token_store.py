from abc import ABC, abstractmethod
from enum import IntEnum

from jose import JWTError

from app.core.security import decode_token, hash_token
from app.db.redis import redis_client
from app.utils.time import utcnow

REFRESH_PREFIX = "refresh:"   # refresh:<sha256(token)> -> user_id          (active token, TTL)
FAMILY_PREFIX = "family:"     # family:<fid>          -> hash of chain head (TTL)
USED_PREFIX = "used:"         # used:<fid>            -> set of rotated-out token hashes (TTL)
DENY_PREFIX = "deny:"         # deny:<sha256(token)>  -> 1                  (revoked access token, TTL)

# NOTE: the refresh prefix is hardcoded inside the Lua scripts; keep it in sync
# with REFRESH_PREFIX above.

# Atomic rotation + reuse detection. The whole exchange runs in one script so two
# concurrent /refresh calls with the same token can never both succeed: the second
# one sees the old token already rotated out and trips reuse detection.
#
#   KEYS[1] = refresh:<old hash>
#   KEYS[2] = refresh:<new hash>
#   KEYS[3] = family:<fid>        (pointer to the current head of the chain)
#   KEYS[4] = used:<fid>          (hashes of tokens that were rotated out)
#   ARGV[1] = user_id
#   ARGV[2] = old hash
#   ARGV[3] = new hash
#   ARGV[4] = ttl_seconds
#
# Returns 1 = rotated, 2 = reuse detected (family revoked), 0 = invalid.
_ROTATE_SCRIPT = """
local active = redis.call('GET', KEYS[1])
if active == ARGV[1] then
    redis.call('DEL', KEYS[1])
    redis.call('SADD', KEYS[4], ARGV[2])
    redis.call('EXPIRE', KEYS[4], ARGV[4])
    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[4])
    redis.call('SET', KEYS[3], ARGV[3], 'EX', ARGV[4])
    return 1
end
if redis.call('SISMEMBER', KEYS[4], ARGV[2]) == 1 then
    local head = redis.call('GET', KEYS[3])
    if head then
        redis.call('DEL', 'refresh:' .. head)
    end
    redis.call('DEL', KEYS[3])
    redis.call('DEL', KEYS[4])
    return 2
end
return 0
"""

# Logout: revoke the presented refresh token (idempotent, only if it is the active
# one for this user) and remember it in the used set so a later /refresh attempt
# with it trips reuse detection.
#
#   KEYS[1] = refresh:<hash>
#   KEYS[2] = family:<fid>
#   KEYS[3] = used:<fid>
#   ARGV[1] = user_id
#   ARGV[2] = hash
#   ARGV[3] = ttl_seconds
_REVOKE_SCRIPT = """
local active = redis.call('GET', KEYS[1])
if active == ARGV[1] then
    redis.call('DEL', KEYS[1])
    redis.call('SADD', KEYS[3], ARGV[2])
    redis.call('EXPIRE', KEYS[3], ARGV[3])
    if redis.call('GET', KEYS[2]) == ARGV[2] then
        redis.call('DEL', KEYS[2])
    end
end
return 1
"""


class RotationOutcome(IntEnum):
    INVALID = 0
    ROTATED = 1
    REUSE_DETECTED = 2


class AbstractTokenStore(ABC):
    @abstractmethod
    async def store_refresh_token(self, user_id: int, token: str, family_id: str, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def rotate_refresh_token(
        self, user_id: int, old_token: str, new_token: str, family_id: str, ttl_seconds: int
    ) -> RotationOutcome: ...

    @abstractmethod
    async def is_refresh_token_active(self, user_id: int, token: str) -> bool: ...

    @abstractmethod
    async def revoke_refresh_token(self, user_id: int, token: str, family_id: str, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def revoke_access_token(self, token: str) -> None: ...

    @abstractmethod
    async def is_access_token_revoked(self, token: str) -> bool: ...


class RedisTokenStore(AbstractTokenStore):
    def __init__(self, client=redis_client):
        self._client = client
        self._rotate = client.register_script(_ROTATE_SCRIPT)
        self._revoke = client.register_script(_REVOKE_SCRIPT)

    async def store_refresh_token(self, user_id: int, token: str, family_id: str, ttl_seconds: int) -> None:
        token_hash = hash_token(token)
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.set(f"{REFRESH_PREFIX}{token_hash}", user_id, ex=ttl_seconds)
            pipe.set(f"{FAMILY_PREFIX}{family_id}", token_hash, ex=ttl_seconds)
            await pipe.execute()

    async def rotate_refresh_token(
        self, user_id: int, old_token: str, new_token: str, family_id: str, ttl_seconds: int
    ) -> RotationOutcome:
        old_hash, new_hash = hash_token(old_token), hash_token(new_token)
        result = await self._rotate(
            keys=[
                f"{REFRESH_PREFIX}{old_hash}",
                f"{REFRESH_PREFIX}{new_hash}",
                f"{FAMILY_PREFIX}{family_id}",
                f"{USED_PREFIX}{family_id}",
            ],
            args=[user_id, old_hash, new_hash, ttl_seconds],
        )
        return RotationOutcome(result)

    async def is_refresh_token_active(self, user_id: int, token: str) -> bool:
        stored = await self._client.get(f"{REFRESH_PREFIX}{hash_token(token)}")
        return stored == str(user_id)

    async def revoke_refresh_token(self, user_id: int, token: str, family_id: str, ttl_seconds: int) -> None:
        token_hash = hash_token(token)
        await self._revoke(
            keys=[
                f"{REFRESH_PREFIX}{token_hash}",
                f"{FAMILY_PREFIX}{family_id}",
                f"{USED_PREFIX}{family_id}",
            ],
            args=[user_id, token_hash, ttl_seconds],
        )

    async def revoke_access_token(self, token: str) -> None:
        try:
            payload = decode_token(token)
        except JWTError:
            return
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int):
            return
        remaining = expires_at - int(utcnow().timestamp())
        if remaining <= 0:
            return
        await self._client.set(f"{DENY_PREFIX}{hash_token(token)}", "1", ex=remaining)

    async def is_access_token_revoked(self, token: str) -> bool:
        return bool(await self._client.exists(f"{DENY_PREFIX}{hash_token(token)}"))
