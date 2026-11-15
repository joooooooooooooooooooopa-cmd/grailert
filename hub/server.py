#!/usr/bin/env python3
"""Контент-дашборд: аналитика площадок и очередь контента для Grailert и Acme.

Один сервис, стандартная библиотека, SQLite на томе. Три части:
  1. Сборщик — раз в 30 минут опрашивает источники и пишет снимки метрик:
     - статистику самих ботов (пользователи, платящие, выручка, источники);
     - подписчиков Telegram-каналов через Bot API;
     - Instagram/Facebook через Graph API — когда появятся токены.
     Источник без настроенного доступа просто пропускается: дашборд живёт
     с первого дня на том, что есть, и «загорается» по мере подключения.
  2. API — JSON для интерфейса + очередь контента (сделан → запланирован →
     опубликован), чтобы было видно, сколько роликов готово и что вышло.
  3. Интерфейс — одна страница со входом по паролю.

Переменные окружения — см. README.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import mimetypes
import os
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
import socketserver

import poster

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    level=logging.INFO)
log = logging.getLogger("hub")

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "3000"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "hub.db"))
FILES_DIR = os.environ.get("FILES_DIR", os.path.join(os.path.dirname(DB_PATH), "files"))
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD", str(120 * 1024 * 1024)))  # 120 МБ
ALLOWED_UPLOAD = {  # тип содержимого -> расширение; ничего другого не принимаем
    "video/mp4": ".mp4", "image/png": ".png", "image/jpeg": ".jpg", "audio/mpeg": ".mp3",
}

HUB_PASSWORD = os.environ.get("HUB_PASSWORD", "")
HUB_SECRET = os.environ.get("HUB_SECRET", "") or HUB_PASSWORD
STATS_TOKEN = os.environ.get("HUB_STATS_TOKEN", "")

GRAILERT_STATS_URL = os.environ.get(
    "GRAILERT_STATS_URL", "http://localhost:8080/hub/stats")
ACME_STATS_URL = os.environ.get(
    "ACME_STATS_URL", "")

GRAILERT_BOT_TOKEN = os.environ.get("GRAILERT_BOT_TOKEN", "")
ACME_BOT_TOKEN = os.environ.get("ACME_BOT_TOKEN", "")
TG_CHANNEL_GRAILERT = os.environ.get("TG_CHANNEL_GRAILERT", "")   # @канал
TG_CHANNEL_ACME = os.environ.get("TG_CHANNEL_ACME", "")

META_TOKEN = os.environ.get("META_TOKEN", "")                     # Graph API
IG_USER_GRAILERT = os.environ.get("IG_USER_GRAILERT", "")         # ig user id
IG_USER_ACME = os.environ.get("IG_USER_ACME", "")
FB_PAGE_GRAILERT = os.environ.get("FB_PAGE_GRAILERT", "")         # page id

COLLECT_EVERY = int(os.environ.get("COLLECT_EVERY", "1800"))

# Публичный адрес пульта — из него собираются подписанные ссылки на файлы для
# Instagram (Graph API забирает видео сам и куку пульта не знает).
PUBLIC_BASE = os.environ.get("PUBLIC_BASE", "").strip().rstrip("/")

# ---------------------------------------------------------------- база

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            ts      INTEGER NOT NULL,
            product TEXT NOT NULL,          -- grailert | acme
            source  TEXT NOT NULL,          -- bot | tg | ig | fb
            metric  TEXT NOT NULL,
            value   REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(product, source, metric, ts);

        CREATE TABLE IF NOT EXISTS media_stats (
            ts       INTEGER NOT NULL,
            product  TEXT NOT NULL,
            platform TEXT NOT NULL,
            media_id TEXT NOT NULL,
            title    TEXT,
            views    INTEGER, likes INTEGER, comments INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_media ON media_stats(product, media_id, ts);

        CREATE TABLE IF NOT EXISTS content (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product      TEXT NOT NULL,
            platform     TEXT NOT NULL,     -- reels | tiktok | tg | fb
            title        TEXT NOT NULL,
            caption      TEXT DEFAULT '',
            status       TEXT DEFAULT 'made',  -- made | scheduled | published
            created_at   INTEGER,
            published_at INTEGER,
            url          TEXT DEFAULT '',
            music        TEXT DEFAULT '',
            filename     TEXT DEFAULT '',
            scheduled_for TEXT DEFAULT '',   -- ГГГГ-ММ-ДД, когда выпускать
            hook         TEXT DEFAULT '',    -- вариант первой секунды, для A/B
            m_views      INTEGER DEFAULT 0,  -- результат за 24ч, вносится руками
            m_likes      INTEGER DEFAULT 0,
            post_time    TEXT DEFAULT '12:00',  -- во сколько выпускать, МСК
            auto         INTEGER DEFAULT 1,     -- публиковать самому
            post_error   TEXT DEFAULT '',       -- почему не вышло в прошлый раз
            attempts     INTEGER DEFAULT 0,     -- сколько раз пробовали отправить
            claimed_at   INTEGER DEFAULT 0      -- когда взяли в работу
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,          -- grailert | acme
            title   TEXT NOT NULL,
            body    TEXT DEFAULT '',        -- JSON: {steps:[...], texts:[{label,value}]}
            done    INTEGER DEFAULT 0,
            ord     INTEGER DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS last_pull (
            source TEXT PRIMARY KEY,
            ts     INTEGER,
            ok     INTEGER,
            note   TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,   -- служебное: подключённые каналы и прочее
            value TEXT
        );
        """)
        # миграция старой базы: досоздаём колонки, если их ещё нет
        cols = {r["name"] for r in _conn.execute("PRAGMA table_info(content)")}
        for col, ddl in (("music", "TEXT DEFAULT ''"), ("filename", "TEXT DEFAULT ''"),
                         ("scheduled_for", "TEXT DEFAULT ''"), ("hook", "TEXT DEFAULT ''"),
                         ("m_views", "INTEGER DEFAULT 0"), ("m_likes", "INTEGER DEFAULT 0"),
                         # автопостинг: во сколько выпускать, публиковать ли самому,
                         # и почему в прошлый раз не вышло
                         ("post_time", "TEXT DEFAULT '12:00'"), ("auto", "INTEGER DEFAULT 1"),
                         ("post_error", "TEXT DEFAULT ''"),
                         # сколько раз пробовали отправить и когда взяли в работу —
                         # без этого повторы кладут в канал дубли, а прерванная
                         # отправка оставляет карточку в 'posting' навсегда
                         ("attempts", "INTEGER DEFAULT 0"), ("claimed_at", "INTEGER DEFAULT 0")):
            if col not in cols:
                _conn.execute(f"ALTER TABLE content ADD COLUMN {col} {ddl}")
        _conn.commit()
        os.makedirs(FILES_DIR, exist_ok=True)
    return _conn


def snap(product: str, source: str, metric: str, value) -> None:
    if value is None:
        return
    with _lock:
        db().execute("INSERT INTO snapshots (ts,product,source,metric,value) VALUES (?,?,?,?,?)",
                     (int(time.time()), product, source, metric, float(value)))
        db().commit()


def setting(key: str, default: str = "") -> str:
    row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row and row["value"] else default


def set_setting(key: str, value: str) -> None:
    with _lock:
        db().execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
        db().commit()


def mark_pull(source: str, ok: bool, note: str = "") -> None:
    with _lock:
        db().execute("INSERT OR REPLACE INTO last_pull (source,ts,ok,note) VALUES (?,?,?,?)",
                     (source, int(time.time()), 1 if ok else 0, note[:200]))
        db().commit()

# ---------------------------------------------------------------- сборщик


def _get_json(url: str, timeout: int = 20) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        # В путь Telegram кладёт токен бота (/bot<токен>/метод) — в лог нельзя
        # ни query, ни путь целиком.
        safe = re.sub(r"/bot[^/]+/", "/bot***/", url.split("?")[0])
        log.warning("не достучался: %s — %s", safe, e)
        return None


def pull_bot(product: str, url: str) -> None:
    # Адрес статистики второго продукта по умолчанию пуст: не настроен — не опрашиваем.
    if not STATS_TOKEN or not url:
        return
    data = _get_json(f"{url}?token={urllib.parse.quote(STATS_TOKEN)}")
    if not data:
        mark_pull(f"{product}:bot", False, "нет ответа")
        return
    numeric = {k: v for k, v in data.items() if isinstance(v, (int, float))}
    for k, v in numeric.items():
        snap(product, "bot", k, v)
    # Канал, куда бота сделали админом, бот сообщает сам — руками id не вводим.
    channel = data.get("channel")
    if isinstance(channel, dict) and channel.get("id"):
        set_setting(f"channel:{product}", str(channel["id"]))
        set_setting(f"channel_title:{product}", str(channel.get("title") or ""))
    # платящие по источникам — кладём последний список целиком отдельным жанром
    if isinstance(data.get("sources"), list):
        with _lock:
            db().execute("INSERT OR REPLACE INTO last_pull (source,ts,ok,note) VALUES (?,?,?,?)",
                         (f"{product}:sources", int(time.time()), 1,
                          json.dumps(data["sources"], ensure_ascii=False)[:4000]))
            db().commit()
    mark_pull(f"{product}:bot", True)


def pull_tg(product: str, bot_token: str, channel: str) -> None:
    if not (bot_token and channel):
        return
    data = _get_json(
        f"https://api.telegram.org/bot{bot_token}/getChatMemberCount?chat_id={urllib.parse.quote(channel)}")
    if data and data.get("ok"):
        snap(product, "tg", "subscribers", data["result"])
        mark_pull(f"{product}:tg", True)
    else:
        mark_pull(f"{product}:tg", False, str((data or {}).get("description", "нет ответа")))


def pull_ig(product: str, ig_user: str) -> None:
    if not (META_TOKEN and ig_user):
        return
    base = f"https://graph.facebook.com/v21.0/{ig_user}"
    prof = _get_json(f"{base}?fields=followers_count,media_count&access_token={META_TOKEN}")
    if not prof or "error" in prof:
        mark_pull(f"{product}:ig", False, str((prof or {}).get("error", "нет ответа"))[:150])
        return
    snap(product, "ig", "followers", prof.get("followers_count"))
    snap(product, "ig", "media_count", prof.get("media_count"))
    media = _get_json(
        f"{base}/media?fields=id,caption,like_count,comments_count,media_type,timestamp"
        f"&limit=25&access_token={META_TOKEN}")
    now = int(time.time())
    for m in (media or {}).get("data", []):
        views = None
        ins = _get_json(
            f"https://graph.facebook.com/v21.0/{m['id']}/insights?metric=views&access_token={META_TOKEN}")
        for row in (ins or {}).get("data", []):
            vals = row.get("values") or []
            if vals:
                views = vals[0].get("value")
        with _lock:
            db().execute(
                "INSERT INTO media_stats (ts,product,platform,media_id,title,views,likes,comments) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (now, product, "ig", m["id"], (m.get("caption") or "")[:120],
                 views, m.get("like_count"), m.get("comments_count")))
            db().commit()
    mark_pull(f"{product}:ig", True)


def pull_fb(product: str, page_id: str) -> None:
    if not (META_TOKEN and page_id):
        return
    data = _get_json(
        f"https://graph.facebook.com/v21.0/{page_id}?fields=followers_count,fan_count&access_token={META_TOKEN}")
    if not data or "error" in data:
        mark_pull(f"{product}:fb", False, str((data or {}).get("error", ""))[:150])
        return
    snap(product, "fb", "followers", data.get("followers_count") or data.get("fan_count"))
    mark_pull(f"{product}:fb", True)


def token_for(product: str) -> str:
    return GRAILERT_BOT_TOKEN if product == "grailert" else ACME_BOT_TOKEN


def channel_for(product: str) -> str:
    """Куда постить: сперва то, что задано руками, иначе — что запомнил бот."""
    manual = TG_CHANNEL_GRAILERT if product == "grailert" else TG_CHANNEL_ACME
    return manual or setting(f"channel:{product}")


def ig_user_for(product: str) -> str:
    return IG_USER_GRAILERT if product == "grailert" else IG_USER_ACME


def public_url(filename: str) -> str:
    """Подписанная ссылка на файл для Instagram: он забирает видео сам, извне.

    Кука пульта ему недоступна, а раздавать файлы всем подряд нельзя — поэтому
    ссылка со своей подписью и без права листать каталог.
    """
    if not (PUBLIC_BASE and filename):
        return ""
    return f"{PUBLIC_BASE}/pub/{sign('file:' + filename)}/{urllib.parse.quote(filename)}"


def collect() -> None:
    pull_bot("grailert", GRAILERT_STATS_URL)
    pull_bot("acme", ACME_STATS_URL)
    pull_tg("grailert", GRAILERT_BOT_TOKEN, channel_for("grailert"))
    pull_tg("acme", ACME_BOT_TOKEN, channel_for("acme"))
    pull_ig("grailert", IG_USER_GRAILERT)
    pull_ig("acme", IG_USER_ACME)
    pull_fb("grailert", FB_PAGE_GRAILERT)


def collector_loop() -> None:
    time.sleep(5)
    while True:
        try:
            collect()
            log.info("сбор метрик завершён")
        except Exception:  # noqa: BLE001
            log.exception("сбор метрик упал")
        time.sleep(COLLECT_EVERY)

# ---------------------------------------------------------------- auth


def sign(value: str) -> str:
    return hmac.new(HUB_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def same_secret(given: str, expected: str) -> bool:
    """Сравнение секретов без падения на не-ASCII.

    `hmac.compare_digest` на строках требует ASCII и иначе бросает TypeError —
    строка запроса приходит от кого угодно, и запрос с кириллицей в токене
    ронял обработчик вместо честного 401.
    """
    return hmac.compare_digest((given or "").encode("utf-8", "ignore"),
                               (expected or "").encode("utf-8", "ignore"))


def make_cookie() -> str:
    exp = str(int(time.time()) + 30 * 86400)
    return f"{exp}.{sign(exp)}"


def check_cookie(raw: str | None) -> bool:
    """Кука приходит от кого угодно — ни подпись, ни срок не должны ронять сервер."""
    if not raw or "." not in raw:
        return False
    exp, sig = raw.rsplit(".", 1)
    if not same_secret(sig, sign(exp)):
        return False
    try:
        return int(exp) > time.time()
    except ValueError:
        return False

# ---------------------------------------------------------------- api-данные


def series(product: str, source: str, metric: str, days: int = 30) -> list:
    rows = db().execute(
        "SELECT ts, value FROM snapshots WHERE product=? AND source=? AND metric=? "
        "AND ts>=? ORDER BY ts", (product, source, metric, int(time.time()) - days * 86400),
    ).fetchall()
    # прореживаем до одного значения в час, чтобы график не пух
    out, last_h = [], None
    for r in rows:
        h = r["ts"] // 3600
        if h != last_h:
            out.append([r["ts"], r["value"]])
            last_h = h
    return out


def latest(product: str, source: str, metric: str):
    row = db().execute(
        "SELECT value FROM snapshots WHERE product=? AND source=? AND metric=? "
        "ORDER BY ts DESC LIMIT 1", (product, source, metric)).fetchone()
    return row["value"] if row else None


def overview() -> dict:
    out = {"generated": int(time.time()), "products": {}, "pulls": []}
    for r in db().execute("SELECT * FROM last_pull ORDER BY source"):
        if r["source"].endswith(":sources"):
            continue
        out["pulls"].append({"source": r["source"], "ts": r["ts"], "ok": bool(r["ok"]),
                             "note": r["note"] or ""})
    for product in ("grailert", "acme"):
        p = {"tiles": {}, "series": {}, "sources": [], "media": [], "queue": {}}
        for src, metric in (("bot", "users"), ("bot", "paying"), ("bot", "usdt"),
                            ("bot", "stars"), ("bot", "revenue"), ("bot", "subs"),
                            ("bot", "paid_cnt"), ("tg", "subscribers"),
                            ("ig", "followers"), ("fb", "followers")):
            v = latest(product, src, metric)
            if v is not None:
                p["tiles"][f"{src}.{metric}"] = v
        p["series"]["bot.users"] = series(product, "bot", "users")
        p["series"]["tg.subscribers"] = series(product, "tg", "subscribers")
        p["series"]["ig.followers"] = series(product, "ig", "followers")
        row = db().execute("SELECT note FROM last_pull WHERE source=?",
                           (f"{product}:sources",)).fetchone()
        if row and row["note"]:
            try:
                p["sources"] = json.loads(row["note"])
            except ValueError:
                pass
        # свежайший снимок по каждому посту
        p["media"] = [dict(r) for r in db().execute(
            """SELECT m.* FROM media_stats m
               JOIN (SELECT media_id, MAX(ts) mt FROM media_stats WHERE product=?
                     GROUP BY media_id) x
               ON m.media_id=x.media_id AND m.ts=x.mt
               WHERE m.product=? ORDER BY m.ts DESC LIMIT 25""",
            (product, product))]
        q = {}
        for r in db().execute(
                "SELECT status, COUNT(*) c FROM content WHERE product=? GROUP BY status",
                (product,)):
            q[r["status"]] = r["c"]
        p["queue"] = q
        # Автопостинг: куда постим и готовы ли вообще
        chan = channel_for(product)
        p["channel"] = {
            "id": chan,
            "title": setting(f"channel_title:{product}"),
            "ready": bool(chan and token_for(product)),
        }
        p["ig_ready"] = bool(META_TOKEN and ig_user_for(product))
        out["products"][product] = p
    out["content"] = [dict(r) for r in db().execute(
        "SELECT * FROM content ORDER BY id DESC LIMIT 100")]
    out["tasks"] = [dict(r) for r in db().execute(
        "SELECT * FROM tasks ORDER BY done, ord, id")]
    return out

# ---------------------------------------------------------------- http

STATIC = os.path.join(BASE, "static")

LOGIN_PAGE = """<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Вход — Пульт</title>
<link rel="icon" href="/favicon.ico">
<style>body{font-family:system-ui;background:#101216;color:#e8eaee;display:grid;place-items:center;min-height:100vh;margin:0}
form{background:#191c22;border:1px solid #2a2e37;border-radius:10px;padding:34px;display:flex;flex-direction:column;gap:14px;width:290px}
h1{font-size:19px;margin:0 0 6px}input{font:inherit;padding:11px;border-radius:6px;border:1px solid #343945;background:#101216;color:inherit}
button{font:inherit;font-weight:600;padding:11px;border-radius:6px;border:0;background:#e4572e;color:#fff;cursor:pointer}
.err{color:#ef8a73;font-size:13px}</style>
<form method="post" action="/login"><h1>Пульт контента</h1>
{err}<input type="password" name="password" placeholder="Пароль" autofocus>
<button>Войти</button></form>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "hub"

    # --- утилиты ---
    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(),
                   "application/json; charset=utf-8")

    def _authed(self) -> bool:
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            if part.strip().startswith("hub="):
                return check_cookie(part.strip()[4:])
        return False

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n)) if n else {}
        except Exception:  # noqa: BLE001
            return {}

    def _serve_file(self, name: str, inline: bool, head_only: bool = False) -> None:
        """Отдача файла с поддержкой Range: без него Safari на iPhone не играет видео.

        head_only — ответить одними заголовками: качалки (в том числе загрузчик
        Instagram) часто сперва спрашивают HEAD, а stdlib его сам не умеет.
        """
        full = os.path.join(FILES_DIR, name)
        if not os.path.isfile(full) or "/" in name or name.startswith("."):
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        size = os.path.getsize(full)

        start, end = 0, size - 1
        rng = self.headers.get("Range", "")
        partial = False
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip()) if rng else None
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:  # bytes=-N — последние N байт
                start = max(0, size - int(m.group(2)))
            if start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            end = min(end, size - 1)
            partial = True

        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if not inline:
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self.end_headers()
        if head_only:
            return
        with open(full, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1 << 20, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return  # плеер оборвал соединение — это норма для видео
                remaining -= len(chunk)

    # --- маршруты ---
    def do_HEAD(self):  # noqa: N802
        """Только для файлов: остальным HEAD не нужен, а гадать не надо."""
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/pub/"):
            parts = path[len("/pub/"):].split("/", 1)
            if len(parts) == 2:
                sig, name = parts[0], os.path.basename(urllib.parse.unquote(parts[1]))
                if same_secret(sig, sign("file:" + name)):
                    self._serve_file(name, True, head_only=True)
                    return
            self.send_error(404)
            return
        if path == "/healthz":
            self._send(200, b"", "text/plain")
            return
        if not self._authed():
            self.send_error(401)
            return
        if path.startswith("/file/"):
            self._serve_file(os.path.basename(path[len("/file/"):]), True, head_only=True)
            return
        self.send_error(404)

    def do_GET(self):  # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        if path == "/healthz":
            self._send(200, b"ok", "text/plain")
            return
        # Иконки нужны и на форме входа — секрета в них нет.
        if path in ("/favicon.ico", "/apple-touch-icon.png"):
            full = os.path.join(STATIC, path.lstrip("/"))
            if os.path.isfile(full):
                with open(full, "rb") as f:
                    self._send(200, f.read(), mimetypes.guess_type(full)[0] or "image/x-icon",
                               {"Cache-Control": "public, max-age=86400"})
                return
        # Подписанная ссылка на файл: по ней Instagram забирает видео сам.
        # Кука ему недоступна, а листать каталог по такой ссылке нельзя.
        if path.startswith("/pub/"):
            parts = path[len("/pub/"):].split("/", 1)
            if len(parts) == 2:
                sig, name = parts[0], os.path.basename(urllib.parse.unquote(parts[1]))
                if same_secret(sig, sign("file:" + name)):
                    self._serve_file(name, True)
                    return
            self.send_error(404)
            return
        if not self._authed():
            self._send(200, LOGIN_PAGE.replace("{err}", "").encode(), "text/html; charset=utf-8")
            return
        if path == "/api/overview":
            self._json(overview())
            return
        if path.startswith("/file/"):
            self._serve_file(os.path.basename(path[len("/file/"):]),
                             "inline=1" in (urllib.parse.urlsplit(self.path).query or ""))
            return
        if path == "/" or path == "/index.html":
            path = "/ui.html"
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if full.startswith(STATIC) and os.path.isfile(full):
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            with open(full, "rb") as f:
                self._send(200, f.read(), ctype)
            return
        self.send_error(404)

    def do_POST(self):  # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        if path == "/login":
            n = int(self.headers.get("Content-Length", "0"))
            form = urllib.parse.parse_qs(self.rfile.read(n).decode())
            pw = (form.get("password") or [""])[0]
            if HUB_PASSWORD and same_secret(pw, HUB_PASSWORD):
                self._send(302, b"", "text/plain", {
                    "Location": "/",
                    "Set-Cookie": f"hub={make_cookie()}; Path=/; HttpOnly; Secure; Max-Age=2592000; SameSite=Lax",
                })
            else:
                time.sleep(1.0)  # лёгкий тормоз перебору
                self._send(200, LOGIN_PAGE.replace(
                    "{err}", '<div class="err">Не подошло</div>').encode(),
                    "text/html; charset=utf-8")
            return
        if not self._authed():
            self._json({"error": "auth"}, 401)
            return
        if path == "/api/refresh":
            threading.Thread(target=collect, daemon=True).start()
            self._json({"ok": True})
            return
        if path == "/api/queue/add":
            b = self._body()
            if not b.get("title") or b.get("product") not in ("grailert", "acme"):
                self._json({"error": "нужны product и title"}, 400)
                return
            with _lock:
                db().execute(
                    "INSERT INTO content (product,platform,title,caption,music,status,created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (b["product"], b.get("platform", "reels"), b["title"][:200],
                     b.get("caption", "")[:2000], b.get("music", "")[:300],
                     "made", int(time.time())))
                db().commit()
            self._json({"ok": True})
            return
        if path == "/api/queue/edit":
            b = self._body()
            row = db().execute("SELECT id FROM content WHERE id=?", (b.get("id"),)).fetchone()
            if not row:
                self._json({"error": "нет такой записи"}, 404)
                return
            sched = str(b.get("scheduled_for", ""))[:10]
            if sched and not re.match(r"^\d{4}-\d{2}-\d{2}$", sched):
                self._json({"error": "дата должна быть ГГГГ-ММ-ДД"}, 400)
                return
            def _num(x):
                try:
                    return max(0, int(x))
                except (TypeError, ValueError):
                    return 0
            ptime = str(b.get("post_time", "") or "12:00")[:5]
            if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", ptime):
                self._json({"error": "время должно быть ЧЧ:ММ"}, 400)
                return
            auto = 0 if str(b.get("auto", "1")) in ("0", "false", "False") else 1
            with _lock:
                db().execute(
                    "UPDATE content SET title=?, caption=?, music=?, url=?, "
                    "scheduled_for=?, hook=?, m_views=?, m_likes=?, post_time=?, auto=? WHERE id=?",
                    (str(b.get("title", ""))[:200], str(b.get("caption", ""))[:2000],
                     str(b.get("music", ""))[:300], str(b.get("url", ""))[:500],
                     sched, str(b.get("hook", ""))[:120],
                     _num(b.get("m_views")), _num(b.get("m_likes")), ptime, auto, b["id"]))
                db().commit()
            self._json({"ok": True})
            return
        if path == "/api/queue/post_now":
            b = self._body()
            try:
                cid = int(b.get("id"))
            except (TypeError, ValueError):
                self._json({"error": "плохой id"}, 400)
                return
            ok, info = poster.post_now(cid)
            self._json({"ok": ok, "info": info}, 200 if ok else 400)
            return
        if path == "/api/queue/delete":
            b = self._body()
            row = db().execute("SELECT filename FROM content WHERE id=?", (b.get("id"),)).fetchone()
            if row:
                if row["filename"]:
                    try:
                        os.remove(os.path.join(FILES_DIR, row["filename"]))
                    except OSError:
                        pass
                with _lock:
                    db().execute("DELETE FROM content WHERE id=?", (b["id"],))
                    db().commit()
            self._json({"ok": True})
            return
        if path.startswith("/api/upload/"):
            try:
                cid = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._json({"error": "плохой id"}, 400)
                return
            row = db().execute("SELECT id FROM content WHERE id=?", (cid,)).fetchone()
            if not row:
                self._json({"error": "нет такой записи"}, 404)
                return
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            ext = ALLOWED_UPLOAD.get(ctype)
            if not ext:
                self._json({"error": f"тип {ctype or 'неизвестен'} не принимается"}, 415)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_UPLOAD:
                self._json({"error": "файл пустой или больше 120 МБ"}, 413)
                return
            # имя файла строим сами из id — пользовательские имена не доверяем
            fname = f"{cid}{ext}"
            tmp = os.path.join(FILES_DIR, f"{fname}.{os.getpid()}.{int(time.time()*1000)}.part")
            written = 0
            with open(tmp, "wb") as f:
                while written < length:
                    chunk = self.rfile.read(min(1 << 20, length - written))
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
            if written != length:
                os.remove(tmp)
                self._json({"error": "файл пришёл не целиком"}, 400)
                return
            os.replace(tmp, os.path.join(FILES_DIR, fname))
            with _lock:
                db().execute("UPDATE content SET filename=? WHERE id=?", (fname, cid))
                db().commit()
            self._json({"ok": True, "filename": fname})
            return
        if path == "/api/task/toggle":
            if not self._authed():
                return self._json({"error": "auth"}, 401)
            b = self._body()
            db().execute("UPDATE tasks SET done=? WHERE id=?",
                         (1 if b.get("done") else 0, int(b.get("id", 0))))
            db().commit()
            return self._json({"ok": True})

        if path == "/api/task/add":
            if not self._authed():
                return self._json({"error": "auth"}, 401)
            b = self._body()
            title = (b.get("title") or "").strip()[:200]
            if not title:
                return self._json({"error": "title"}, 400)
            product = b.get("product") if b.get("product") in ("grailert", "acme") else "grailert"
            db().execute("INSERT INTO tasks(product,title,body) VALUES(?,?,?)",
                         (product, title, b.get("body") or ""))
            db().commit()
            return self._json({"ok": True})

        if path == "/api/queue/status":
            b = self._body()
            if b.get("status") not in ("made", "scheduled", "published"):
                self._json({"error": "плохой статус"}, 400)
                return
            with _lock:
                db().execute(
                    "UPDATE content SET status=?, url=COALESCE(NULLIF(?,''),url), "
                    "published_at=CASE WHEN ?='published' THEN ? ELSE published_at END WHERE id=?",
                    (b["status"], b.get("url", ""), b["status"], int(time.time()), b.get("id")))
                db().commit()
            self._json({"ok": True})
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        log.info(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    if not HUB_PASSWORD:
        raise SystemExit("HUB_PASSWORD обязателен — дашборд без пароля не поднимаем")
    db()
    threading.Thread(target=collector_loop, daemon=True).start()
    # Автопостинг: карточка с датой и временем уходит в канал сама.
    poster.setup({
        "db": db, "lock": _lock, "files_dir": FILES_DIR,
        "token_for": token_for, "channel_for": channel_for,
        "ig_user_for": ig_user_for, "meta_token": lambda: META_TOKEN,
        "public_url": public_url,
    })
    poster.start()
    log.info("Пульт на :%d", PORT)
    with Server(("", PORT), Handler) as httpd:
        httpd.serve_forever()
