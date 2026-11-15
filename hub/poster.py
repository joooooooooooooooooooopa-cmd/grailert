# -*- coding: utf-8 -*-
"""Автопостинг из очереди пульта: Telegram сейчас, Instagram — когда дадут токен.

Смысл: оператор не должен ходить и выкладывать руками. Карточка в очереди с датой
и временем публикуется сама, статус в пульте меняется на «опубликовано», ссылка
на пост подставляется туда же.

Как устроено:
  • раз в минуту смотрим, чему пора выйти (время московское, как и вся сетка);
  • карточку сначала ЗАБИРАЕМ (status='posting' одним UPDATE с условием) и только
    потом отправляем — иначе два прохода подряд опубликуют один ролик дважды;
  • не получилось — возвращаем в очередь с текстом ошибки, а не теряем молча.

Канал не задаём руками: боты сами запоминают канал, куда их сделали админом, и
отдают его в своей статистике. Env-переменная TG_CHANNEL_* остаётся как ручной
перекрыватель.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

log = logging.getLogger("poster")

MSK = timezone(timedelta(hours=3))
TG_FILE_LIMIT = 50 * 1024 * 1024      # предел Bot API на загрузку файла
CHECK_EVERY = 60
# Насколько старой может быть просроченная карточка, чтобы её ещё имело смысл
# выпускать. Иначе подключение площадки задним числом вывалит в канал весь
# накопившийся хвост разом.
STALE_DAYS = 2
# Сколько постов одного продукта выпускаем за проход: лента не должна получать
# три ролика в одну минуту, даже если очередь просрочена.
MAX_PER_RUN = 1
# Сколько неудачных попыток на продукт делаем за проход: если площадка отвечает
# ошибкой, не надо перебирать всю очередь подряд — подождём следующей минуты.
MAX_TRIES_PER_RUN = 3
# Сколько раз всего пробуем отправить одну карточку. Дальше не трогаем и ждём
# человека: «отправилось, но ответ не дошёл» неотличимо от «не отправилось»,
# и бесконечные повторы кладут в канал дубли.
MAX_ATTEMPTS = 3
# Через сколько секунд карточка в статусе 'posting' считается брошенной
# (сервис перезапустили посреди отправки).
STUCK_SECONDS = 15 * 60
# Минимальный зазор между постами одного продукта. Без него очередь, набранная
# за прошлые дни, выходит пачкой по посту в минуту.
MIN_GAP_SECONDS = 30 * 60

_deps: dict = {}


def setup(deps: dict) -> None:
    """deps: db, lock, files_dir, token_for(product), channel_for(product),
    ig_user_for(product), meta_token(), public_url(filename)."""
    global _deps
    _deps = deps


def _db():
    return _deps["db"]()


def _lock():
    return _deps["lock"]


# --- расписание ---------------------------------------------------------------

def now_msk() -> datetime:
    return datetime.now(MSK)


def due_rows(now: datetime | None = None) -> list:
    """Карточки, которым пора выйти: дата прошла или сегодня и время наступило.

    Слишком старое не берём: если площадку подключили через неделю, канал не
    должен получить весь хвост очереди одной пачкой.
    """
    now = now or now_msk()
    today = now.strftime("%Y-%m-%d")
    hhmm = now.strftime("%H:%M")
    floor = (now - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%d")
    cur = _db().execute(
        "SELECT * FROM content WHERE auto=1 AND status IN ('made','scheduled') "
        "AND COALESCE(attempts,0) < ? AND scheduled_for >= ? AND ("
        "  scheduled_for < ? OR (scheduled_for = ? AND COALESCE(post_time,'12:00') <= ?)"
        ") ORDER BY scheduled_for, id",
        (MAX_ATTEMPTS, floor, today, today, hhmm),
    )
    return list(cur.fetchall())


def last_post_ts(product: str) -> int:
    """Когда этот продукт публиковался в последний раз."""
    cur = _db().execute(
        "SELECT MAX(published_at) t FROM content WHERE product=? AND status='published'",
        (product,))
    row = cur.fetchone()
    return int((row["t"] if row and row["t"] else 0) or 0)


def stale_rows(now: datetime | None = None) -> list:
    """Просроченное настолько, что публиковать само уже не станем."""
    now = now or now_msk()
    floor = (now - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%d")
    cur = _db().execute(
        "SELECT * FROM content WHERE auto=1 AND status IN ('made','scheduled') "
        "AND scheduled_for != '' AND scheduled_for < ?", (floor,))
    return list(cur.fetchall())


def exhausted_rows() -> list:
    """Карточки, исчерпавшие попытки отправки."""
    cur = _db().execute(
        "SELECT * FROM content WHERE auto=1 AND status IN ('made','scheduled') "
        "AND COALESCE(attempts,0) >= ?", (MAX_ATTEMPTS,))
    return list(cur.fetchall())


def claim(row_id: int) -> bool:
    """Забирает карточку под публикацию. False — её уже кто-то забрал."""
    with _lock():
        cur = _db().execute(
            "UPDATE content SET status='posting', attempts=COALESCE(attempts,0)+1, "
            "claimed_at=? WHERE id=? AND status IN ('made','scheduled')",
            (int(time.time()), row_id))
        _db().commit()
    return cur.rowcount > 0


def unstick() -> int:
    """Возвращает в очередь карточки, застрявшие в 'posting'.

    Сервис могли перезапустить (деплой) прямо во время отправки — тогда
    карточка осталась бы в 'posting' навсегда: её не берёт ни расписание, ни
    кнопка «опубликовать сейчас».
    """
    threshold = int(time.time()) - STUCK_SECONDS
    with _lock():
        cur = _db().execute(
            "UPDATE content SET status='scheduled', "
            "post_error='отправка прервалась, проверь канал перед повтором' "
            "WHERE status='posting' AND COALESCE(claimed_at,0) < ?", (threshold,))
        _db().commit()
    if cur.rowcount:
        log.warning("Вернул в очередь застрявших карточек: %d", cur.rowcount)
    return cur.rowcount


def finish(row_id: int, url: str) -> None:
    with _lock():
        _db().execute(
            "UPDATE content SET status='published', published_at=?, url=?, post_error='' WHERE id=?",
            (int(time.time()), url, row_id))
        _db().commit()


def fail(row_id: int, reason: str) -> None:
    with _lock():
        _db().execute(
            "UPDATE content SET status='scheduled', post_error=? WHERE id=?",
            (reason[:300], row_id))
        _db().commit()


def note(row_id: int, text: str) -> None:
    """Пишет причину, не трогая статус: карточку мы даже не пробовали отправить."""
    with _lock():
        _db().execute("UPDATE content SET post_error=? WHERE id=? AND COALESCE(post_error,'') != ?",
                      (text[:300], row_id, text[:300]))
        _db().commit()


def target_ready(row) -> tuple[bool, str]:
    """Есть ли куда публиковать эту карточку. Пусто — причина словами."""
    platform = row["platform"]
    if platform == "tg":
        if not _deps["token_for"](row["product"]):
            return False, "нет токена бота"
        if not _deps["channel_for"](row["product"]):
            return False, "канал не подключён: добавь бота админом в канал"
        return True, ""
    if platform in ("reels", "ig"):
        if not _deps["meta_token"]():
            return False, "Instagram не подключён: нет токена"
        if not _deps["ig_user_for"](row["product"]):
            return False, "Instagram не подключён: нет id аккаунта"
        return True, ""
    return False, f"площадка {platform} не поддержана автопостингом"


# --- HTTP ---------------------------------------------------------------------

def _post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    return _read(req, timeout)


def _read(req, timeout: int) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": str(e)}


def _multipart(url: str, fields: dict, file_field: str, filename: str, blob: bytes,
               timeout: int = 300) -> dict:
    """Загрузка файла в Telegram. Тело собираем сами — сторонних библиотек тут нет."""
    boundary = "----hub" + uuid.uuid4().hex
    out = bytearray()
    for key, value in fields.items():
        if value is None:
            continue
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        out += str(value).encode() + b"\r\n"
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    out += f"--{boundary}\r\n".encode()
    out += f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    out += f"Content-Type: {ctype}\r\n\r\n".encode()
    out += blob + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=bytes(out),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return _read(req, timeout)


def _safe(url: str) -> str:
    """Токен бота живёт в ПУТИ ссылки Telegram — в лог его пускать нельзя."""
    return re.sub(r"/bot[^/]+/", "/bot***/", url.split("?")[0])


# --- Telegram -----------------------------------------------------------------

def post_telegram(row) -> tuple[bool, str]:
    """Публикует карточку в канал продукта. Возвращает (успех, ссылка или причина)."""
    product = row["product"]
    token = _deps["token_for"](product)
    channel = _deps["channel_for"](product)
    if not token:
        return False, "нет токена бота"
    if not channel:
        return False, "канал не подключён: добавь бота админом в канал"

    api = f"https://api.telegram.org/bot{token}/"
    caption = (row["caption"] or row["title"] or "")[:1024]
    filename = row["filename"] or ""
    path = os.path.join(_deps["files_dir"], filename) if filename else ""

    if filename and os.path.exists(path):
        size = os.path.getsize(path)
        if size > TG_FILE_LIMIT:
            return False, f"файл {size // 1024 // 1024} МБ, Bot API берёт до 50 МБ"
        with open(path, "rb") as f:
            blob = f.read()
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".mp4":
            res = _multipart(api + "sendVideo",
                             {"chat_id": channel, "caption": caption,
                              "supports_streaming": "true", "parse_mode": "HTML"},
                             "video", filename, blob)
        elif ext in (".png", ".jpg", ".jpeg"):
            res = _multipart(api + "sendPhoto",
                             {"chat_id": channel, "caption": caption, "parse_mode": "HTML"},
                             "photo", filename, blob)
        else:
            res = _multipart(api + "sendDocument",
                             {"chat_id": channel, "caption": caption, "parse_mode": "HTML"},
                             "document", filename, blob)
    else:
        text = (row["caption"] or row["title"] or "").strip()
        if not text:
            return False, "нечего публиковать: ни файла, ни текста"
        res = _post_json(api + "sendMessage",
                         {"chat_id": channel, "text": text[:4096], "parse_mode": "HTML",
                          "disable_web_page_preview": True})

    if not res.get("ok"):
        return False, str(res.get("description") or "Telegram отказал")[:200]
    msg = res.get("result") or {}
    return True, _msg_link(channel, msg)


def _msg_link(channel: str, msg: dict) -> str:
    mid = msg.get("message_id")
    chat = msg.get("chat") or {}
    if chat.get("username"):
        return f"https://t.me/{chat['username']}/{mid}"
    cid = str(chat.get("id") or channel)
    if cid.startswith("-100"):
        return f"https://t.me/c/{cid[4:]}/{mid}"
    return ""


# --- Instagram ----------------------------------------------------------------

def post_instagram(row) -> tuple[bool, str]:
    """Публикация Reels через Graph API.

    Instagram забирает файл сам по ссылке, поэтому нужен публичный адрес — его
    даёт подписанная ссылка пульта. Пока нет токена и ig-аккаунта, ветка молчит.
    """
    token = _deps["meta_token"]()
    ig_user = _deps["ig_user_for"](row["product"])
    if not (token and ig_user):
        return False, "Instagram не подключён: нет токена или id аккаунта"
    filename = row["filename"] or ""
    if not filename:
        return False, "нет файла"
    media_url = _deps["public_url"](filename)
    if not media_url:
        return False, "нет публичного адреса файла"

    ext = os.path.splitext(filename)[1].lower()
    base = f"https://graph.facebook.com/v21.0/{ig_user}"
    caption = (row["caption"] or row["title"] or "")[:2200]
    if ext == ".mp4":
        params = {"media_type": "REELS", "video_url": media_url,
                  "caption": caption, "access_token": token}
    else:
        params = {"image_url": media_url, "caption": caption, "access_token": token}

    created = _post_form(f"{base}/media", params)
    cid = created.get("id")
    if not cid:
        return False, str(created.get("error") or created)[:200]

    # Видео контейнер готовится не мгновенно: публиковать раньше времени нельзя.
    for _ in range(30):
        st = _read(urllib.request.Request(
            f"https://graph.facebook.com/v21.0/{cid}?fields=status_code"
            f"&access_token={urllib.parse.quote(token)}"), 30)
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            return False, "Instagram не смог обработать файл"
        time.sleep(5)
    else:
        return False, "Instagram слишком долго обрабатывает файл"

    pub = _post_form(f"{base}/media_publish", {"creation_id": cid, "access_token": token})
    if not pub.get("id"):
        return False, str(pub.get("error") or pub)[:200]
    # media_publish отдаёт числовой id, а адрес поста строится из shortcode —
    # ссылку берём у самого Graph, иначе в пульте будет 404 на каждом посте.
    link = _read(urllib.request.Request(
        f"https://graph.facebook.com/v21.0/{pub['id']}?fields=permalink"
        f"&access_token={urllib.parse.quote(token)}"), 30).get("permalink")
    return True, link or f"https://www.instagram.com/ (media {pub['id']})"


def _post_form(url: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    return _read(req, 120)


# --- цикл ---------------------------------------------------------------------

PLATFORM_SENDERS = {
    "tg": post_telegram,
    "reels": post_instagram,
    "ig": post_instagram,
}


def publish_row(row) -> tuple[bool, str]:
    sender = PLATFORM_SENDERS.get(row["platform"])
    if not sender:
        return False, f"площадка {row['platform']} не поддержана автопостингом"
    return sender(row)


def run_once() -> int:
    """Публикует то, чему пора. Возвращает число опубликованных.

    За проход берём не больше MAX_PER_RUN на продукт: очередь может быть
    просрочена, но лента от этого не должна получить пачку роликов подряд.
    """
    done = 0
    used: dict[str, int] = {}
    unstick()
    # Отставшее помечаем один раз, чтобы было видно в пульте, и не публикуем.
    for row in stale_rows():
        if not (row["post_error"] or "").startswith("просрочено"):
            fail(row["id"], f"просрочено больше {STALE_DAYS} дней — публикуй кнопкой вручную")
    # Исчерпавшие попытки тоже объясняем один раз и оставляем человеку.
    for row in exhausted_rows():
        if not (row["post_error"] or "").startswith("не вышло"):
            fail(row["id"], f"не вышло {MAX_ATTEMPTS} раза подряд — проверь и публикуй кнопкой")

    now_ts = int(time.time())
    tries: dict[str, int] = {}
    for row in due_rows():
        product = row["product"]
        if used.get(product, 0) >= MAX_PER_RUN or tries.get(product, 0) >= MAX_TRIES_PER_RUN:
            continue
        # Зазор между постами: очередь за прошлые дни не должна выходить пачкой.
        if now_ts - last_post_ts(product) < MIN_GAP_SECONDS:
            continue

        # Площадка не подключена — карточку даже не трогаем. Иначе она каждую
        # минуту занимала бы слот продукта и загораживала те, что реально могут
        # выйти: очередь стояла бы намертво из-за одного неподключённого канала.
        ready, why = target_ready(row)
        if not ready:
            note(row["id"], why)
            continue

        if not claim(row["id"]):
            continue
        tries[product] = tries.get(product, 0) + 1
        try:
            ok, info = publish_row(row)
        except Exception as e:  # noqa: BLE001
            log.exception("автопостинг упал на #%s", row["id"])
            ok, info = False, str(e)[:200]
        if ok:
            # Слот тратим только на настоящую публикацию: сорвавшаяся отправка
            # не должна отбирать очередь у следующей карточки.
            used[product] = used.get(product, 0) + 1
            finish(row["id"], info)
            done += 1
            log.info("опубликовано #%s (%s/%s) → %s",
                     row["id"], row["product"], row["platform"], info)
        else:
            fail(row["id"], info)
            log.warning("не опубликовано #%s: %s", row["id"], info)
    return done


def post_now(row_id: int) -> tuple[bool, str]:
    """Ручная публикация из пульта, мимо расписания."""
    cur = _db().execute("SELECT * FROM content WHERE id=?", (row_id,))
    row = cur.fetchone()
    if not row:
        return False, "карточка не найдена"
    if row["status"] == "published":
        return False, "уже опубликовано"
    if row["status"] == "posting":
        # Могло застрять после перезапуска сервиса — тогда отпускаем и берём заново.
        unstick()
        row = _db().execute("SELECT * FROM content WHERE id=?", (row_id,)).fetchone()
    # Кнопка — это решение человека, счётчик автоматических попыток ей не помеха.
    with _lock():
        _db().execute("UPDATE content SET attempts=0 WHERE id=?", (row_id,))
        _db().commit()
    if not claim(row_id):
        return False, "публикуется прямо сейчас"
    try:
        ok, info = publish_row(row)
    except Exception as e:  # noqa: BLE001
        ok, info = False, str(e)[:200]
    if ok:
        finish(row_id, info)
    else:
        fail(row_id, info)
    return ok, info


def loop() -> None:
    time.sleep(20)
    while True:
        try:
            run_once()
        except Exception:  # noqa: BLE001
            log.exception("цикл автопостинга упал")
        time.sleep(CHECK_EVERY)


def start() -> None:
    threading.Thread(target=loop, daemon=True, name="poster").start()
    log.info("автопостинг включён, проверка раз в %d с", CHECK_EVERY)
