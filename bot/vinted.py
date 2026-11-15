"""Клиент внутреннего API Vinted + парсинг ссылок и форматирование уведомлений.

У Vinted нет публичного API. Используем внутренний /api/v2/catalog/items,
который требует сессионных кук (access_token_web и т.п. + токен Datadome).
Куки получаем, зайдя на главную домена обычным User-Agent'ом, и переиспользуем.
При 401/403 — пересеваем сессию. Между запросами держим зазор (анти-бан).
"""
from __future__ import annotations

import asyncio
import html
import logging
import time
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse

import httpx

import config

log = logging.getLogger("vinted")

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": DESKTOP_UA,
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/plain, */*",
}

WEB_TO_API = {
    "catalog[]": "catalog_ids",
    "status[]": "status_ids",
    "brand_ids[]": "brand_ids",
    "size_ids[]": "size_ids",
    "color_ids[]": "color_ids",
    "material_ids[]": "material_ids",
    "video_game_rating_ids[]": "video_game_rating_ids",
}

DROP_PARAMS = {"page", "time", "disabled_personalization"}


def parse_search_url(url: str) -> tuple[str, dict]:
    """vinted.pl/catalog?... -> (host, params для API).

    Хост вне белого списка заменяем на домен по умолчанию: сюда попадают и
    старые записи из базы, и всё, что могло проскочить мимо проверок выше —
    ходить на чужой адрес мы не должны ни при каких входных данных.
    """
    parsed = urlparse(url.strip())
    host = host_of(url) or config.DEFAULT_HOST
    if not is_allowed_host(host):
        log.warning("Хост %s не из белого списка — беру домен по умолчанию", host)
        host = config.DEFAULT_HOST
    raw = parse_qs(parsed.query, keep_blank_values=False)

    params: dict[str, str] = {}
    for key, values in raw.items():
        if key in DROP_PARAMS:
            continue
        api_key = WEB_TO_API.get(key) or (key[:-2] if key.endswith("[]") else key)
        joined = ",".join(values)
        params[api_key] = (params[api_key] + "," + joined) if params.get(api_key) else joined

    params["order"] = "newest_first"
    params.setdefault("per_page", str(config.PER_PAGE))
    return host, params


# Домены, на которые нам вообще можно ходить. Список один и тот же, что в
# клавиатуре выбора страны — держим его здесь, чтобы проверка была рядом с местом,
# где строится запрос.
ALLOWED_HOSTS = {
    "vinted.pl", "vinted.de", "vinted.fr", "vinted.it", "vinted.es", "vinted.nl",
    "vinted.co.uk", "vinted.cz", "vinted.lt", "vinted.pt", "vinted.be", "vinted.sk",
    "vinted.com", "vinted.at", "vinted.hu", "vinted.ro", "vinted.gr", "vinted.fi",
    "vinted.se", "vinted.dk", "vinted.ie", "vinted.lu", "vinted.hr", "vinted.si",
}


def host_of(url: str) -> str:
    """Голый хост ссылки без www."""
    netloc = (urlparse(url.strip()).netloc or "").split("@")[-1].split(":")[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def is_allowed_host(host: str) -> bool:
    return (host or "").lower() in ALLOWED_HOSTS


def looks_like_vinted_url(url: str) -> bool:
    """Ссылка ведёт именно на Vinted.

    Проверка точная, а не по подстроке: «vinted.» встречается и в
    vinted.evil.com, а по такой ссылке бот ходил бы на чужой хост вечно —
    и отдавал бы его ответ обратно в пульт.
    """
    p = urlparse(url.strip())
    return p.scheme in ("http", "https") and is_allowed_host(host_of(url))


def build_search_url(keyword: str, host: str | None = None) -> str:
    """Строит ссылку поиска по всему сайту для произвольного ключевого слова."""
    host = host or config.DEFAULT_HOST
    return f"https://www.{host}/catalog?search_text={quote_plus(keyword.strip())}&order=newest_first"


# --- Фильтр цены в ссылке поиска ---------------------------------------------
# Vinted и в вебе, и в API понимает price_from/price_to, поэтому фильтр храним
# прямо в URL подписки — без миграций БД, и пульт/экспорт видят его автоматически.

def price_filter_of(url: str) -> tuple[float | None, float | None]:
    """(мин, макс) из ссылки поиска; None — грань не задана."""
    raw = parse_qs(urlparse(url.strip()).query)

    def _num(key: str) -> float | None:
        try:
            return float(raw[key][0])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    return _num("price_from"), _num("price_to")


def set_price_filter(url: str, pmin: float | None, pmax: float | None) -> str:
    """Возвращает URL с обновлёнными price_from/price_to (None — грань убрать)."""
    parsed = urlparse(url.strip())
    raw = parse_qs(parsed.query, keep_blank_values=False)
    raw.pop("price_from", None)
    raw.pop("price_to", None)
    if pmin is not None:
        raw["price_from"] = [f"{pmin:g}"]
    if pmax is not None:
        raw["price_to"] = [f"{pmax:g}"]
    query = urlencode(raw, doseq=True)
    return urlunparse(parsed._replace(query=query))


def parse_price_range(text: str) -> tuple[float | None, float | None] | None:
    """«10-50» / «-50» / «10-» / «-» → (мин, макс); None — ввод не распознан."""
    s = (text or "").strip().replace(",", ".").replace("–", "-")
    if s == "-":
        return (None, None)
    if s.count("-") != 1:
        return None
    left, right = (part.strip() for part in s.split("-"))

    def _num(part: str) -> float | None:
        if not part:
            return None
        try:
            v = float(part)
        except ValueError:
            raise _BadRange
        if v < 0 or v > 1_000_000:
            raise _BadRange
        return v

    try:
        pmin, pmax = _num(left), _num(right)
    except _BadRange:
        return None
    if pmin is None and pmax is None:
        return None
    if pmin is not None and pmax is not None and pmin > pmax:
        pmin, pmax = pmax, pmin
    return (pmin, pmax)


class _BadRange(Exception):
    pass


def pretty_price_range(pmin: float | None, pmax: float | None) -> str:
    if pmin is not None and pmax is not None:
        return f"{pmin:g}–{pmax:g}"
    if pmin is not None:
        return f"≥ {pmin:g}"
    if pmax is not None:
        return f"≤ {pmax:g}"
    return ""


class VintedClient:
    """Одна сессия на домен. Лениво сеет куки, пересевает при бане, троттлит запросы."""

    def __init__(self, host: str):
        self.host = host
        self.base = f"https://www.{host}"
        self._client: httpx.AsyncClient | None = None
        self._seeded = False
        self._lock = asyncio.Lock()
        self._last_req = 0.0

    async def _throttle(self) -> None:
        gap = config.REQUEST_GAP - (time.monotonic() - self._last_req)
        if gap > 0:
            await asyncio.sleep(gap)
        self._last_req = time.monotonic()

    async def _ensure(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=BASE_HEADERS,
                timeout=httpx.Timeout(25.0),
                follow_redirects=True,
                proxy=config.VINTED_PROXY,
            )
        if not self._seeded:
            try:
                await self._throttle()
                await self._client.get(
                    self.base + "/",
                    headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                )
            except Exception as e:  # noqa: BLE001
                log.warning("Не удалось засеять сессию %s: %s", self.host, e)
            self._seeded = True

    async def get_items(self, params: dict) -> list[dict] | None:
        """Список объявлений. None — если запрос не удался/забанен (а не «пусто»)."""
        async with self._lock:
            await self._ensure()
            url = f"{self.base}/api/v2/catalog/items"
            headers = {"X-Requested-With": "XMLHttpRequest", "Referer": self.base + "/catalog"}
            for attempt in range(2):
                try:
                    await self._throttle()
                    r = await self._client.get(url, params=params, headers=headers)
                except Exception as e:  # noqa: BLE001
                    log.warning("Ошибка запроса каталога %s: %s", self.host, e)
                    return None
                if r.status_code == 200:
                    try:
                        return r.json().get("items", []) or []
                    except Exception:  # noqa: BLE001
                        return None
                if r.status_code in (401, 403, 419) and attempt == 0:
                    log.info("Vinted %s -> %s, пересеваю сессию", self.host, r.status_code)
                    self._seeded = False
                    await self._ensure()
                    continue
                if r.status_code == 429:
                    log.warning("Vinted %s -> 429 (rate limit)", self.host)
                    await asyncio.sleep(5)
                    return None
                log.warning("Каталог %s -> HTTP %s", self.host, r.status_code)
                return None
            return None

    async def check(self) -> dict:
        """Быстрая проверка доступности домена для диагностики."""
        items = await self.get_items({"per_page": "1", "order": "newest_first"})
        return {
            "ok": items is not None,
            "count": len(items) if items is not None else 0,
            "host": self.host,
            "proxy": bool(config.VINTED_PROXY),
        }


# Пул сессий на домен: один клиент с локом сериализует все поиски юзеров,
# и при росте базы очередь на домен растёт линейно. N независимых сессий
# (свои куки и свой троттлинг у каждой) раздаются раунд-робином.
_pools: dict[str, list[VintedClient]] = {}
_rr: dict[str, int] = {}
_registry_lock = asyncio.Lock()


async def get_client(host: str) -> VintedClient:
    async with _registry_lock:
        pool = _pools.get(host)
        if pool is None:
            pool = [VintedClient(host) for _ in range(max(1, config.VINTED_POOL))]
            _pools[host] = pool
            _rr[host] = 0
        _rr[host] = (_rr[host] + 1) % len(pool)
        return pool[_rr[host]]


# --- Фильтр по ключевым словам ----------------------------------------------

def passes_keywords(title: str, include: str, exclude: str) -> bool:
    t = (title or "").lower()
    if exclude:
        if any(w.strip() and w.strip().lower() in t for w in exclude.split(",")):
            return False
    if include:
        words = [w.strip().lower() for w in include.split(",") if w.strip()]
        if words and not any(w in t for w in words):
            return False
    return True


# --- Извлечение полей и форматирование --------------------------------------

def price_amount(item: dict) -> tuple[float | None, str]:
    """Возвращает (сумма, код валюты) из объявления."""
    p = item.get("price")
    if isinstance(p, dict):
        amount, cur = p.get("amount"), p.get("currency_code") or item.get("currency") or ""
    else:
        amount, cur = p, item.get("currency") or ""
    try:
        return (float(amount), cur) if amount is not None else (None, cur)
    except (TypeError, ValueError):
        return (None, cur)


def item_price(item: dict) -> str:
    amount, cur = price_amount(item)
    if amount is None:
        return "—"
    return f"{amount:g} {cur}".strip()


def total_price(item: dict) -> str | None:
    p = item.get("total_item_price")
    if isinstance(p, dict) and p.get("amount") is not None:
        try:
            return f"{float(p['amount']):g} {p.get('currency_code') or ''}".strip()
        except (TypeError, ValueError):
            return None
    return None


def photo_urls(detail: dict | None, fallback_item: dict) -> list[str]:
    urls: list[str] = []
    # Галерея: сперва из деталей, иначе прямо из каталога (там тоже есть photos[]).
    gallery = (detail or {}).get("photos") or fallback_item.get("photos") or []
    for ph in gallery:
        if isinstance(ph, dict):
            u = ph.get("full_size_url") or ph.get("url")
            if u:
                urls.append(u)
    # Последний фолбэк — одиночное фото.
    if not urls:
        ph = fallback_item.get("photo")
        if isinstance(ph, dict):
            u = ph.get("full_size_url") or ph.get("url")
            if u:
                urls.append(u)
    return urls[: config.MAX_PHOTOS]


def format_caption(sub_name: str, item: dict, usd: float | None = None,
                   lang: str = "ru", deal: bool = False) -> str:
    # Импорт здесь, а не сверху: i18n ни от чего не зависит, но так vinted
    # остаётся импортируемым в тестах без инициализации всех строк.
    from i18n import t

    title = html.escape(item.get("title") or t(lang, "cap_untitled"))
    size = html.escape(item.get("size_title") or "—")
    brand = html.escape(item.get("brand_title") or "")
    status = html.escape(item.get("status") or "")
    url = item.get("url") or ""
    price = html.escape(item_price(item))
    total = total_price(item)

    usd_part = f" ≈ <b>${usd:,.2f}</b>" if usd else ""
    protection = t(lang, "cap_protect", v=html.escape(total)) if total else ""

    lines = [
        f"🔎 <b>{html.escape(sub_name)}</b>",
        "",
        f"🆕 <b>{title}</b>",
        f"💶 <b>{price}</b>{usd_part}{protection}",
        t(lang, "cap_size", v=size),
    ]
    if deal:
        lines.insert(2, "<b>" + t(lang, "deal_badge") + "</b>")
    if brand:
        lines.append(f"🏷 {brand}")
    if status:
        lines.append(f"✨ {status}")
    seller = item.get("user") or {}
    if isinstance(seller, dict) and seller.get("login"):
        lines.append(f"👤 {html.escape(str(seller['login']))}")
    if url:
        lines.append(f'\n<a href="{html.escape(url, quote=True)}">{t(lang, "cap_open")}</a>')
    return "\n".join(lines)


def deal_median(items: list[dict]) -> float | None:
    """Медиана цен пачки объявлений — «рынок» для бейджа 🔥. None, если данных мало."""
    prices = sorted(a for a, _ in (price_amount(i) for i in items) if a is not None and a > 0)
    if len(prices) < config.DEAL_MIN_SAMPLES:
        return None
    n = len(prices)
    mid = n // 2
    return prices[mid] if n % 2 else (prices[mid - 1] + prices[mid]) / 2


def is_deal(item: dict, median: float | None) -> bool:
    if median is None:
        return False
    amount, _ = price_amount(item)
    return amount is not None and 0 < amount <= median * config.DEAL_RATIO
