import pytest
from fastapi import HTTPException

from app.api.deps import rate_limit
from tests.unit.fakes import FakeRateLimiter


@pytest.mark.asyncio
async def test_fake_rate_limiter_allows_up_to_limit():
    limiter = FakeRateLimiter()

    for _ in range(5):
        assert await limiter.is_rate_limited("login:127.0.0.1", limit=5, window_seconds=60) is False

    assert await limiter.is_rate_limited("login:127.0.0.1", limit=5, window_seconds=60) is True



async def test_fake_rate_limiter_tracks_keys_independently():
    limiter = FakeRateLimiter()

    assert await limiter.is_rate_limited("login:a", limit=1, window_seconds=60) is False
    assert await limiter.is_rate_limited("login:a", limit=1, window_seconds=60) is True
    assert await limiter.is_rate_limited("login:b", limit=1, window_seconds=60) is False


class _FakeRequest:
    def __init__(self, host: str = "127.0.0.1", forwarded_for: str | None = None):
        self.client = type("Client", (), {"host": host})()
        self.headers = {}
        if forwarded_for is not None:
            self.headers["X-Forwarded-For"] = forwarded_for



async def test_rate_limit_dependency_raises_after_limit():
    limiter = FakeRateLimiter()
    enforce = rate_limit("login", 2, 60, detail="slow down")

    await enforce(request=_FakeRequest(), rate_limiter=limiter)
    await enforce(request=_FakeRequest(), rate_limiter=limiter)

    with pytest.raises(HTTPException) as exc:
        await enforce(request=_FakeRequest(), rate_limiter=limiter)

    assert exc.value.status_code == 429
    assert exc.value.detail == "slow down"



async def test_rate_limit_dependency_uses_forwarded_for_header():
    limiter = FakeRateLimiter()
    enforce = rate_limit("login", 1, 60)

    await enforce(
        request=_FakeRequest(host="10.0.0.1", forwarded_for="203.0.113.5, 10.0.0.1"),
        rate_limiter=limiter,
    )

    with pytest.raises(HTTPException):
        await enforce(
            request=_FakeRequest(host="10.0.0.1", forwarded_for="203.0.113.5, 10.0.0.1"),
            rate_limiter=limiter,
        )


    await enforce(
        request=_FakeRequest(host="10.0.0.1", forwarded_for="198.51.100.9, 10.0.0.1"),
        rate_limiter=limiter,
    )
