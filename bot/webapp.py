# -*- coding: utf-8 -*-
"""HTTP-слой Grailert: пульт (Telegram Mini App) и статистика для дашборда.

Бот — воркер на поллинге, веб тут нужен ради двух вещей:
  • `/app` — пульт: поиски, живая лента объявлений, тариф и касса в одном экране;
  • `/hub/stats` — цифры для контент-дашборда (раньше жил в отдельном statsd.py).

Сервер стоит на stdlib в отдельном потоке, как и раньше. Всё, что должно
происходить внутри бота (опрос Vinted, планировщик джоб, счета), уезжает в
event loop PTB через `run_coroutine_threadsafe` — трогать job_queue из чужого
потока нельзя.

Функции бота приходят сюда хуками при старте: webapp не импортирует bot.py,
иначе получилось бы кольцо импортов.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, parse_qsl, urlsplit

import config
import db
import plans
import ui
import vinted
from app_i18n import strings as app_strings

log = logging.getLogger("webapp")

HUB_STATS_TOKEN = os.getenv("HUB_STATS_TOKEN", "").strip()
HUB_PORT = int(os.getenv("HUB_PORT", "8080"))
# Сколько живёт подпись initData. Утёкшая строка не должна открывать пульт вечно.
INIT_DATA_MAX_AGE = 24 * 3600

# Замок на операции «проверил лимит и записал». Сервер многопоточный, а лимиты
# тарифа должны выдерживать два одновременных запроса с одного аккаунта.
_write_lock = threading.Lock()

_loop: asyncio.AbstractEventLoop | None = None
_hooks: dict = {}
_page_cache: tuple[float, bytes] | None = None

PAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html")


# --- авторизация -------------------------------------------------------------

def validate_init_data(init_data: str, max_age: int = INIT_DATA_MAX_AGE) -> int | None:
    """Проверка подписи Telegram WebApp. Возвращает user_id или None.

    Поле `signature` (Bot API 9.0) в хеш не входит — если его не исключить,
    подпись не сойдётся никогда.
    """
    if not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:  # noqa: BLE001
        return None
    provided = pairs.pop("hash", "")
    pairs.pop("signature", None)
    if not provided:
        return None
    data_check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        return None
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError:
        return None
    if not auth_date or time.time() - auth_date > max_age:
        return None
    try:
        # parse_qsl уже раскодировал значение. Второй unquote ломал бы JSON у
        # людей, у кого в имени встречается «%22» или «%5C», — и пульт для них
        # был бы мёртв навсегда при полностью верной подписи.
        return int(json.loads(pairs.get("user", "{}")).get("id") or 0) or None
    except Exception:  # noqa: BLE001
        return None


# --- мост в event loop бота --------------------------------------------------

def call_bot(coro, timeout: float = 40):
    """Выполняет корутину в петле бота и ждёт результат. None — если не вышло."""
    if _loop is None:
        raise RuntimeError("webapp не запущен из бота")
    fut = asyncio.run_coroutine_threadsafe(coro, _loop)
    return fut.result(timeout=timeout)


async def _schedule(sub) -> None:
    _hooks["schedule"](_hooks["job_queue"](), sub)


async def _unschedule(sid: int) -> None:
    _hooks["unschedule"](_hooks["job_queue"](), sid)


# --- сборка ответов ----------------------------------------------------------

def _plan_info(uid: int) -> tuple[str, int | None]:
    return _hooks["plan_of"](uid)


def _sub_json(sub, lang: str) -> dict:
    host, _ = vinted.parse_search_url(sub["url"])
    plan, _unused = _plan_info(sub["user_id"])
    real = plans.allowed_interval(plan, sub["interval_sec"])
    pmin, pmax = vinted.price_filter_of(sub["url"])
    return {
        "id": sub["id"],
        "name": sub["name"],
        "url": sub["url"],
        "host": host,
        # Показываем частоту, с которой опрос идёт НА САМОМ ДЕЛЕ: расписание
        # подтягивает интервал до тарифного, и «30 сек» на карточке у free —
        # это обещание, которого продукт не выполняет.
        "interval": real,
        "interval_text": ui.pretty_interval(real, lang),
        "active": bool(sub["active"]),
        "kw_include": sub["kw_include"] or "",
        "kw_exclude": sub["kw_exclude"] or "",
        "price_min": pmin,
        "price_max": pmax,
        "last_check": sub["last_check"],
        "last_status": sub["last_status"] or "",
        "seen": db.seen_count(sub["id"]),
    }


def _price_bound(value) -> float | None:
    """Число из поля цены пульта; мусор и отрицательное → None (грань не задана)."""
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v if 0 < v <= 1_000_000 else None


def _apply_price(sid: int, url: str, body: dict) -> None:
    pmin = _price_bound(body.get("price_min"))
    pmax = _price_bound(body.get("price_max"))
    if pmin is not None and pmax is not None and pmin > pmax:
        pmin, pmax = pmax, pmin
    db.set_url(sid, vinted.set_price_filter(url, pmin, pmax))


def session_payload(uid: int) -> dict:
    lang = _hooks["lang_of"](uid)
    plan, until = _plan_info(uid)
    subs = db.list_subscriptions(uid)
    stats = db.user_stats(uid)
    crypto_on = _hooks["crypto_enabled"]()
    products = []
    for code, p in plans.PRODUCTS.items():
        products.append({
            "code": code,
            "plan": p["plan"],
            "plan_name": _hooks["plan_name"](lang, p["plan"]),
            "days": p["days"],
            "stars": p["stars"],
            "usdt": p["usdt"],
        })
    return {
        "user_id": uid,
        "lang": lang,
        "t": app_strings(lang),
        "plan": plan,
        "plan_name": _hooks["plan_name"](lang, plan),
        "plan_until": _hooks["fmt_date"](until) if until else None,
        "limits": {
            "searches": plans.search_limit(plan),
            "min_interval": plans.min_interval(plan),
        },
        "intervals": [
            {"sec": s, "text": ui.pretty_interval(s, lang),
             "locked": s < plans.min_interval(plan),
             "need_plan": _hooks["plan_name"](lang, plans.plan_for_interval(s))}
            for s in (30, 60, 120, 300, 900, 1800, 3600)
        ],
        "hosts": [{"label": lbl, "host": h} for lbl, h in ui.DOMAINS],
        "default_host": ui.LANG_DEFAULT_HOST.get(lang, config.DEFAULT_HOST),
        "searches": [_sub_json(s, lang) for s in subs],
        "stats": {
            "total": stats.get("total", len(subs)),
            "active": stats.get("active", 0),
            "paused": stats.get("paused", 0),
            "notif_total": stats.get("notif_total", 0),
            "notif_today": stats.get("notif_today", 0),
        },
        "products": products,
        "crypto_on": crypto_on,
        "bot": config.BOT_USERNAME,
        "presets": ui.PRESETS,
    }


def _item_json(item: dict) -> dict:
    photos = vinted.photo_urls(None, item)
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "price": vinted.item_price(item),
        "total": vinted.total_price(item),
        "size": item.get("size_title") or "",
        "brand": item.get("brand_title") or "",
        "status": item.get("status") or "",
        "url": item.get("url") or "",
        "photo": photos[0] if photos else "",
    }


# --- обработчики API ---------------------------------------------------------

def api_session(uid: int, _body: dict) -> dict:
    return session_payload(uid)


def api_add(uid: int, body: dict) -> dict:
    # Сервер многопоточный: «посчитал и вставил» без замка позволяет двумя
    # одновременными запросами создать два поиска при лимите в один.
    with _write_lock:
        return _api_add(uid, body)


def _api_add(uid: int, body: dict) -> dict:
    plan, _ = _plan_info(uid)
    if not plans.can_add_search(plan, db.count_subscriptions(uid)):
        return {"error": "limit", "limit": plans.search_limit(plan)}

    raw = str(body.get("query") or "").strip()
    if not raw:
        return {"error": "empty"}
    host = str(body.get("host") or "").strip() or config.DEFAULT_HOST
    if vinted.looks_like_vinted_url(raw):
        url = raw
    else:
        if host not in {h for _, h in ui.DOMAINS}:
            return {"error": "bad_host"}
        url = vinted.build_search_url(raw, host)

    interval = plans.allowed_interval(plan, max(config.MIN_INTERVAL, _int(body.get("interval"), config.DEFAULT_INTERVAL)))
    name = (str(body.get("name") or "").strip() or raw)[:64]

    sid = db.add_subscription(uid, name, url, interval)
    inc = str(body.get("kw_include") or "")[:200]
    exc = str(body.get("kw_exclude") or "")[:200]
    if inc or exc:
        db.set_keywords(sid, inc, exc)
    if body.get("price_min") is not None or body.get("price_max") is not None:
        _apply_price(sid, url, body)
    sub = db.get_subscription(sid)
    call_bot(_schedule(sub))
    return {"ok": True, "search": _sub_json(sub, _hooks["lang_of"](uid))}


def api_save(uid: int, body: dict) -> dict:
    with _write_lock:
        return _api_save(uid, body)


def _api_save(uid: int, body: dict) -> dict:
    sub = _own_sub(uid, body)
    if not sub:
        return {"error": "not_found"}
    sid = sub["id"]
    plan, _ = _plan_info(uid)

    # Сначала ВСЕ проверки, потом записи. Иначе имя и фильтры уже сохранены, а
    # ответ — ошибка: пульт показывает старое значение, а в базе новое.
    want_interval = None
    if "interval" in body:
        want = max(config.MIN_INTERVAL, _int(body["interval"], sub["interval_sec"]))
        # Запрос ровно с тем интервалом, что уже стоит в базе, — это не попытка
        # ускориться, а обычное сохранение имени: пульт шлёт форму целиком.
        if want < plans.min_interval(plan) and want != sub["interval_sec"]:
            return {"error": "interval_locked",
                    "need_plan": _hooks["plan_name"](_hooks["lang_of"](uid),
                                                     plans.plan_for_interval(want))}
        want_interval = plans.allowed_interval(plan, want)

    if "name" in body:
        db.set_name(sid, str(body["name"]).strip()[:64] or sub["name"])
    if "kw_include" in body or "kw_exclude" in body:
        db.set_keywords(sid,
                        str(body.get("kw_include", sub["kw_include"] or ""))[:200],
                        str(body.get("kw_exclude", sub["kw_exclude"] or ""))[:200])
    if want_interval is not None:
        db.set_interval(sid, want_interval)
    if "active" in body:
        want_on = bool(body["active"])
        if want_on and not _can_activate(uid, sid, plan):
            return {"error": "limit", "limit": plans.search_limit(plan)}
        db.set_active(sid, want_on)
    if "price_min" in body or "price_max" in body:
        _apply_price(sid, db.get_subscription(sid)["url"], body)

    fresh = db.get_subscription(sid)
    if fresh["active"]:
        call_bot(_schedule(fresh))
    else:
        call_bot(_unschedule(sid))
    return {"ok": True, "search": _sub_json(fresh, _hooks["lang_of"](uid))}


def _can_activate(uid: int, sid: int, plan: str) -> bool:
    """Включать поиск можно, только пока активных меньше лимита тарифа."""
    limit = plans.search_limit(plan)
    if not limit:
        return True
    active = sum(1 for s in db.list_subscriptions(uid) if s["active"] and s["id"] != sid)
    return active < limit


def api_toggleall(uid: int, body: dict) -> dict:
    with _write_lock:
        return _api_toggleall(uid, body)


def _api_toggleall(uid: int, body: dict) -> dict:
    """Мастер-тумблер пульта: пауза/запуск всех поисков разом.

    При включении поднимаем поиски по порядку, пока позволяет лимит тарифа —
    как кнопка «Запустить все» в боте.
    """
    want_on = bool(body.get("on"))
    plan, _ = _plan_info(uid)
    limit = plans.search_limit(plan)
    # Считаем от УЖЕ активных, а не с нуля: иначе включение «всех» при части
    # активных поисков поднимало их сверх лимита тарифа.
    enabled = sum(1 for s in db.list_subscriptions(uid) if s["active"]) if want_on else 0
    for sub in db.list_subscriptions(uid):
        if want_on and sub["active"]:
            continue
        sid = sub["id"]
        if want_on:
            if limit and enabled >= limit:
                break
            db.set_active(sid, True)
            call_bot(_schedule(db.get_subscription(sid)))
            enabled += 1
        else:
            db.set_active(sid, False)
            call_bot(_unschedule(sid))
    lang = _hooks["lang_of"](uid)
    return {"ok": True,
            "searches": [_sub_json(s, lang) for s in db.list_subscriptions(uid)]}


def api_delete(uid: int, body: dict) -> dict:
    sub = _own_sub(uid, body)
    if not sub:
        return {"error": "not_found"}
    call_bot(_unschedule(sub["id"]))
    db.delete_subscription(sub["id"])
    return {"ok": True}


# Когда пользователь в последний раз жал «проверить сейчас». Держим в памяти
# процесса: переживать рестарт этой отметке незачем.
_last_manual: dict[int, float] = {}


def manual_cooldown(plan: str) -> int:
    """Пауза между ручными проверками. Треть тарифного интервала, но не меньше 20 с.

    Без неё кнопка «проверить сейчас» полностью обходит тариф: free крутил бы
    опрос раз в две секунды вместо 15 минут, попутно занимая клиент Vinted и
    отодвигая плановые опросы всех остальных.
    """
    return max(20, plans.min_interval(plan) // 3)


def api_check(uid: int, body: dict) -> dict:
    sub = _own_sub(uid, body)
    if not sub:
        return {"error": "not_found"}
    plan, _ = _plan_info(uid)
    wait = manual_cooldown(plan)
    left = wait - (time.time() - _last_manual.get(uid, 0))
    if left > 0:
        return {"error": "cooldown", "seconds": int(left) + 1}
    _last_manual[uid] = time.time()
    sent = call_bot(_hooks["run_poll"](_hooks["bot"](), sub, True), timeout=90)
    fresh = db.get_subscription(sub["id"])
    return {"ok": True, "sent": sent, "search": _sub_json(fresh, _hooks["lang_of"](uid))}


def api_feed(uid: int, body: dict) -> dict:
    """Живая лента: что продаётся по этому поиску прямо сейчас.

    id="all" — сводная лента по всем поискам (до 4 первых, чтобы не упереться
    в троттлинг клиента Vinted): по 6 свежих с каждого, вперемешку по новизне.
    """
    if body.get("id") == "all":
        subs = db.list_subscriptions(uid)[:4]
        if not subs:
            return {"ok": True, "items": []}
        merged: list[tuple[int, dict]] = []
        alive = False
        for sub in subs:
            items = call_bot(_fetch_items(sub["url"]), timeout=60)
            if items is None:
                continue          # источник не ответил — это не «пусто»
            alive = True
            if not items:
                continue
            inc, exc = sub["kw_include"] or "", sub["kw_exclude"] or ""
            good = [i for i in items if vinted.passes_keywords(i.get("title", ""), inc, exc)]
            merged.extend((i.get("id") or 0, i) for i in good[:6])
        if not alive:
            return {"error": "vinted_down"}
        merged.sort(key=lambda p: p[0], reverse=True)  # id монотонный — свежие сверху
        return {"ok": True, "items": [_item_json(i) for _, i in merged[:24]]}

    sub = _own_sub(uid, body)
    if not sub:
        return {"error": "not_found"}
    items = call_bot(_fetch_items(sub["url"]), timeout=60)
    if items is None:
        return {"error": "vinted_down"}
    inc, exc = sub["kw_include"] or "", sub["kw_exclude"] or ""
    good = [i for i in items if vinted.passes_keywords(i.get("title", ""), inc, exc)]
    return {"ok": True, "items": [_item_json(i) for i in good[:24]]}


async def _fetch_items(url: str):
    host, params = vinted.parse_search_url(url)
    client = await vinted.get_client(host)
    return await client.get_items(params)


def api_preview(uid: int, body: dict) -> dict:
    """Сколько объявлений сейчас под запрос — показываем до сохранения поиска."""
    raw = str(body.get("query") or "").strip()
    if not raw:
        return {"error": "empty"}
    host = str(body.get("host") or "").strip() or config.DEFAULT_HOST
    if vinted.looks_like_vinted_url(raw):
        url = raw
    else:
        # Тот же белый список, что и при сохранении поиска: без него сюда можно
        # подставить любой хост и получить его ответ обратно в пульт.
        if host not in {h for _, h in ui.DOMAINS}:
            return {"error": "bad_host"}
        url = vinted.build_search_url(raw, host)
    try:
        items = call_bot(_fetch_items(url), timeout=45)
    except Exception:  # noqa: BLE001
        items = None
    if items is None:
        return {"ok": True, "down": True, "items": [], "count": 0}
    return {"ok": True, "down": False, "count": len(items),
            "items": [_item_json(i) for i in items[:12]]}


def api_buy(uid: int, body: dict) -> dict:
    code = str(body.get("code") or "")
    if code not in plans.PRODUCTS:
        return {"error": "bad_product"}
    method = body.get("method")
    if method not in ("stars", "crypto"):
        method = "stars"
    if method == "crypto" and not _hooks["crypto_enabled"]():
        return {"error": "crypto_off"}
    lang = _hooks["lang_of"](uid)
    try:
        return call_bot(_hooks["make_invoice"](uid, lang, code, method), timeout=45)
    except Exception:  # noqa: BLE001
        log.exception("Пульт: счёт не создался")
        return {"error": "payment_failed"}


def api_paystatus(uid: int, body: dict) -> dict:
    pid = _int(body.get("id"), 0)
    payment = db.get_payment(pid) if pid else None
    if not payment or payment["user_id"] != uid:
        return {"error": "not_found"}
    if payment["status"] == "paid":
        return {"phase": "paid"}
    try:
        phase = call_bot(_hooks["check_payment"](payment), timeout=45)
    except Exception:  # noqa: BLE001
        return {"phase": "pending"}
    return {"phase": phase}


def _own_sub(uid: int, body: dict):
    """Поиск по id, но только свой — чужой id не должен ничего открывать."""
    sub = db.get_subscription(_int(body.get("id"), 0))
    if not sub or sub["user_id"] != uid:
        return None
    return sub


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


ROUTES = {
    "/app/api/session": api_session,
    "/app/api/add": api_add,
    "/app/api/save": api_save,
    "/app/api/delete": api_delete,
    "/app/api/toggleall": api_toggleall,
    "/app/api/check": api_check,
    "/app/api/feed": api_feed,
    "/app/api/preview": api_preview,
    "/app/api/buy": api_buy,
    "/app/api/paystatus": api_paystatus,
}


# --- HTTP --------------------------------------------------------------------

def _page() -> bytes:
    """Страница пульта. В проде читается один раз, в разработке — по mtime."""
    global _page_cache
    mtime = os.path.getmtime(PAGE_PATH)
    if _page_cache and _page_cache[0] == mtime:
        return _page_cache[1]
    with open(PAGE_PATH, "rb") as f:
        body = f.read()
    _page_cache = (mtime, body)
    return body


class _Handler(BaseHTTPRequestHandler):
    server_version = "grailert"
    # Без таймаута чтение тела висит вечно: клиент объявил Content-Length и
    # замолчал, поток занят, потоки не ограничены — так кладут весь процесс.
    timeout = 15

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, data: dict, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(),
                   "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802
        parts = urlsplit(self.path)
        path = parts.path
        if path == "/healthz":
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return
        if path == "/hub/stats":
            token = (parse_qs(parts.query).get("token") or [""])[0]
            if not HUB_STATS_TOKEN or not hmac.compare_digest(
                    token.encode("utf-8", "ignore"), HUB_STATS_TOKEN.encode()):
                self.send_error(401)
                return
            data = db.global_stats()
            data.update(db.revenue_stats())
            data["sources"] = db.sources_report()
            data["growth"] = db.growth_report()
            # Канал, куда бота сделали админом: по нему пульт контента постит сам.
            data["channel"] = db.get_channel()
            self._json(data)
            return
        if path in ("/app", "/app/"):
            self._send(200, _page(), "text/html; charset=utf-8")
            return
        self.send_error(404)

    def do_POST(self):  # noqa: N802
        path = urlsplit(self.path).path
        handler = ROUTES.get(path)
        if not handler:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 64 * 1024:
            self._json({"error": "too_big"}, 413)
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except Exception:  # noqa: BLE001
            self._json({"error": "bad_json"}, 400)
            return

        uid = validate_init_data(str(body.get("initData") or ""))
        if not uid:
            self._json({"error": "auth"}, 401)
            return
        if not db.is_activated(uid):
            self._json({"error": "not_activated"}, 403)
            return
        # Закрытый тест: пульт тоже только для белого списка (и админов).
        if config.INVITE_ONLY and uid not in config.ADMIN_IDS and not db.is_whitelisted(uid):
            self._json({"error": "invite_only"}, 403)
            return
        try:
            self._json(handler(uid, body))
        except Exception:  # noqa: BLE001
            log.exception("Пульт: ошибка в %s", path)
            self._json({"error": "server"}, 500)

    def log_message(self, fmt, *args):
        log.info("webapp: " + fmt, *args)


class _V6Server(socketserver.ThreadingTCPServer):
    # Внутренняя сеть хостинга — IPv6; публичный прокси приходит туда же.
    import socket as _s
    address_family = _s.AF_INET6
    allow_reuse_address = True
    daemon_threads = True


def start(hooks: dict) -> None:
    """Запускает сервер. Зовётся из on_startup, когда петля бота уже крутится."""
    global _loop, _hooks
    _loop = asyncio.get_running_loop()
    _hooks = hooks

    def run():
        try:
            with _V6Server(("::", HUB_PORT), _Handler) as srv:
                log.info("webapp: слушаю [::]:%d (пульт /app)", HUB_PORT)
                srv.serve_forever()
        except Exception:  # noqa: BLE001
            log.exception("webapp: сервер упал")

    threading.Thread(target=run, daemon=True, name="webapp").start()
