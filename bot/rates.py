"""Конвертация валют в USD. Курсы — с frankfurter (ECB), кеш в памяти на 6ч."""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

log = logging.getLogger("rates")

_TTL = 6 * 3600
_cache: dict[str, tuple[float, float]] = {}  # currency -> (rate_to_usd, fetched_at)
_client: httpx.AsyncClient | None = None
_lock = asyncio.Lock()


async def to_usd(amount: float | None, currency: str | None) -> float | None:
    """Переводит сумму из указанной валюты в USD. None — если не получилось."""
    if amount is None or not currency:
        return None
    cur = currency.upper()
    if cur == "USD":
        return float(amount)
    rate = await _get_rate(cur)
    return float(amount) * rate if rate else None


async def _get_rate(cur: str) -> float | None:
    cached = _cache.get(cur)
    if cached and time.time() - cached[1] < _TTL:
        return cached[0]
    async with _lock:
        cached = _cache.get(cur)
        if cached and time.time() - cached[1] < _TTL:
            return cached[0]
        global _client
        if _client is None:
            _client = httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True)
        try:
            r = await _client.get(
                "https://api.frankfurter.dev/v1/latest",
                params={"base": cur, "symbols": "USD"},
            )
            if r.status_code == 200:
                rate = r.json().get("rates", {}).get("USD")
                if rate:
                    _cache[cur] = (float(rate), time.time())
                    return float(rate)
        except Exception as e:  # noqa: BLE001
            log.warning("Курс %s->USD не получен: %s", cur, e)
        # Фолбэк на устаревший кеш, если он есть.
        return cached[0] if cached else None
