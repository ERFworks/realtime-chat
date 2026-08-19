from abc import ABC, abstractmethod

from app.db.redis import redis_client

_INCR_WITH_EXPIRE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class AbstractRateLimiter(ABC):
    @abstractmethod
    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool: ...


class RedisRateLimiter(AbstractRateLimiter):
    def __init__(self, client=redis_client):
        self._client = client
        self._incr_script = self._client.register_script(_INCR_WITH_EXPIRE_SCRIPT)

    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        current_count = await self._incr_script(keys=[key], args=[window_seconds])
        return int(current_count) > limit
