from __future__ import annotations

import time

import redis.asyncio as aioredis
from fastapi import HTTPException, Request

from ..config import settings

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


async def rate_limit(request: Request, limit: int, window_seconds: int = 60) -> None:
    r = _get_redis()
    api_key = request.headers.get("X-API-Key", "")
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    key_base = api_key if api_key else client_ip
    key = f"ratelimit:{key_base}:{int(time.time()) // window_seconds}"

    current = await r.incr(key)
    if current == 1:
        await r.expire(key, window_seconds)

    if current > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window_seconds)},
        )
