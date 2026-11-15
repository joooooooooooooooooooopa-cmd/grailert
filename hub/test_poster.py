# -*- coding: utf-8 -*-
"""Тесты автопостинга: расписание, защита от дублей, отправка, ошибки.

Запуск: python3 test_poster.py
Сеть не нужна — Telegram и Graph API подменяются заглушками.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta

TMP = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(TMP, "hub.db")
os.environ["FILES_DIR"] = os.path.join(TMP, "files")
os.environ["HUB_PASSWORD"] = "test"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poster  # noqa: E402

PASS = FAIL = 0
FAILS: list[str] = []


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  ❌ {name}   {extra}")


# --- окружение теста ---------------------------------------------------------

CONN: sqlite3.Connection | None = None
LOCK = threading.Lock()
FILES = os.path.join(TMP, "files")
SENT: list[dict] = []
CHANNEL = {"grailert": "-1001234567890", "acme": ""}
BREAK = {"send": False}
META = {"token": ""}


def conn() -> sqlite3.Connection:
    global CONN
    if CONN is None:
        os.makedirs(FILES, exist_ok=True)
        CONN = sqlite3.connect(os.path.join(TMP, "hub.db"), check_same_thread=False)
        CONN.row_factory = sqlite3.Row
        CONN.executescript("""
        CREATE TABLE content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT, platform TEXT, title TEXT, caption TEXT DEFAULT '',
            status TEXT DEFAULT 'made', created_at INTEGER, published_at INTEGER,
            url TEXT DEFAULT '', music TEXT DEFAULT '', filename TEXT DEFAULT '',
            scheduled_for TEXT DEFAULT '', hook TEXT DEFAULT '',
            m_views INTEGER DEFAULT 0, m_likes INTEGER DEFAULT 0,
            post_time TEXT DEFAULT '12:00', auto INTEGER DEFAULT 1, post_error TEXT DEFAULT '',
            attempts INTEGER DEFAULT 0, claimed_at INTEGER DEFAULT 0
        );""")
        CONN.commit()
    return CONN


def add(product="grailert", platform="tg", title="Пост", caption="Текст",
        filename="", when=None, ptime="00:00", auto=1, status="scheduled") -> int:
    when = when if when is not None else datetime.now().strftime("%Y-%m-%d")
    cur = conn().execute(
        "INSERT INTO content (product,platform,title,caption,filename,scheduled_for,"
        "post_time,auto,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (product, platform, title, caption, filename, when, ptime, auto, status,
         int(time.time())))
    conn().commit()
    return cur.lastrowid


def row(cid):
    return conn().execute("SELECT * FROM content WHERE id=?", (cid,)).fetchone()


def install():
    poster.MIN_GAP_SECONDS = 0   # зазор проверяется отдельным тестом
    poster.setup({
        "db": conn, "lock": LOCK, "files_dir": FILES,
        "token_for": lambda p: "111:TOKEN",
        "channel_for": lambda p: CHANNEL.get(p, ""),
        "ig_user_for": lambda p: "",
        "meta_token": lambda: META["token"],
        "public_url": lambda f: f"https://hub.example/pub/sig/{f}",
    })

    def fake_multipart(url, fields, file_field, filename, blob, timeout=300):
        SENT.append({"url": url, "fields": fields, "file": filename, "size": len(blob)})
        return {"ok": True, "result": {"message_id": 42,
                                       "chat": {"id": int(fields["chat_id"]), "username": "grails"}}}

    def fake_post_json(url, payload, timeout=60):
        SENT.append({"url": url, "fields": payload})
        if BREAK["send"]:
            return {"ok": False, "description": "Bad Gateway"}
        return {"ok": True, "result": {"message_id": 43,
                                       "chat": {"id": -1001234567890, "username": "grails"}}}

    poster._multipart = fake_multipart
    poster._post_json = fake_post_json


# --- тесты -------------------------------------------------------------------

def test_schedule():
    print("\n[A] Кому пора выходить")
    now = datetime(2026, 9, 6, 12, 30)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    a = add(when=today, ptime="12:00")
    b = add(when=today, ptime="23:00")
    c = add(when=yesterday, ptime="23:00")
    d = add(when=tomorrow, ptime="00:01")
    e = add(when=today, ptime="09:00", auto=0)
    f = add(when="", ptime="09:00")
    g = add(when=today, ptime="09:00", status="published")

    old = add(when="2026-08-01", ptime="09:00")

    due = {r["id"] for r in poster.due_rows(now)}
    check("время наступило — берём", a in due)
    check("время ещё не пришло — не берём", b not in due)
    check("вчерашнее просроченное берём", c in due)
    check("завтрашнее не берём", d not in due)
    check("выключенный автопостинг не берём", e not in due)
    check("без даты не берём", f not in due)
    check("уже опубликованное не берём", g not in due)
    check("давно просроченное само не выходит", old not in due)
    check("оно попадает в отставшие", old in {r["id"] for r in poster.stale_rows(now)})


def test_claim():
    print("\n[B] Защита от двойной публикации")
    cid = add()
    check("первый забор проходит", poster.claim(cid) is True)
    check("второй забор не проходит", poster.claim(cid) is False)
    check("статус стал posting", row(cid)["status"] == "posting")
    poster.finish(cid, "https://t.me/x/1")
    check("после публикации статус published", row(cid)["status"] == "published")
    check("ссылка сохранена", row(cid)["url"] == "https://t.me/x/1")
    check("опубликованное больше не забрать", poster.claim(cid) is False)


def test_send_text():
    print("\n[C] Текстовый пост")
    SENT.clear()
    cid = add(caption="Привет из очереди")
    ok, info = poster.post_telegram(row(cid))
    check("отправлено", ok, info)
    check("ушло через sendMessage", SENT and SENT[-1]["url"].endswith("sendMessage"))
    check("текст тот самый", SENT[-1]["fields"]["text"] == "Привет из очереди")
    check("ссылка на пост собрана", info == "https://t.me/grails/43", info)


def test_send_video():
    print("\n[D] Видео и картинка")
    SENT.clear()
    path = os.path.join(FILES, "12.mp4")
    with open(path, "wb") as f:
        f.write(b"x" * 2048)
    cid = add(filename="12.mp4", caption="Ролик")
    ok, info = poster.post_telegram(row(cid))
    check("видео отправлено", ok, info)
    check("ушло через sendVideo", SENT[-1]["url"].endswith("sendVideo"))
    check("файл приложен целиком", SENT[-1]["size"] == 2048)
    check("подпись приехала", SENT[-1]["fields"]["caption"] == "Ролик")

    with open(os.path.join(FILES, "13.png"), "wb") as f:
        f.write(b"y" * 100)
    cid2 = add(filename="13.png")
    poster.post_telegram(row(cid2))
    check("картинка идёт через sendPhoto", SENT[-1]["url"].endswith("sendPhoto"))


def test_errors():
    print("\n[E] Отказы")
    CHANNEL["acme"] = ""
    cid = add(product="acme")
    ok, info = poster.post_telegram(row(cid))
    check("без канала не публикуем", not ok and "канал" in info, info)

    cid2 = add(caption="", title="")
    ok2, info2 = poster.post_telegram(row(cid2))
    check("пустую карточку не публикуем", not ok2, info2)

    big = os.path.join(FILES, "99.mp4")
    with open(big, "wb") as f:
        f.seek(poster.TG_FILE_LIMIT + 10)
        f.write(b"\0")
    cid3 = add(filename="99.mp4")
    ok3, info3 = poster.post_telegram(row(cid3))
    check("слишком большой файл не шлём", not ok3 and "50 МБ" in info3, info3)
    os.remove(big)

    cid4 = add(platform="tiktok")
    ok4, info4 = poster.publish_row(row(cid4))
    check("неизвестная площадка не падает", not ok4 and "tiktok" in info4, info4)

    cid5 = add(product="acme")
    poster.fail(cid5, "канал не подключён")
    check("после отказа карточка возвращается в очередь", row(cid5)["status"] == "scheduled")
    check("причина отказа записана", "канал" in row(cid5)["post_error"])


def test_run_once():
    print("\n[F] Полный проход")
    SENT.clear()
    conn().execute("DELETE FROM content")
    conn().commit()
    ready = add(caption="Выйдет", ptime="00:00")
    later = add(caption="Не выйдет", ptime="23:59",
                when=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
    done = poster.run_once()
    check("опубликована одна карточка", done == 1, done)
    check("нужная опубликована", row(ready)["status"] == "published")
    check("будущая не тронута", row(later)["status"] == "scheduled")

    again = poster.run_once()
    check("повторный проход ничего не дублирует", again == 0, again)

    # Очередь просрочена: за проход уходит один пост на продукт, а не пачка
    conn().execute("DELETE FROM content")
    conn().commit()
    y = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    ids = [add(caption=f"пост {i}", when=y, ptime="00:00") for i in range(3)]
    check("за проход уходит один пост", poster.run_once() == 1)
    published = [i for i in ids if row(i)["status"] == "published"]
    check("остальные ждут следующего прохода", len(published) == 1, published)

    # Совсем старое не выходит вовсе, но объясняет почему
    conn().execute("DELETE FROM content")
    conn().commit()
    ancient = add(caption="древний", when="2026-01-01", ptime="00:00")
    check("древнюю карточку не публикуем", poster.run_once() == 0)
    check("статус вернулся в очередь", row(ancient)["status"] == "scheduled")
    check("причина видна в пульте", "просрочено" in (row(ancient)["post_error"] or ""))


def test_blocked_platform_does_not_hog_queue():
    print("\n[G0] Неподключённая площадка не держит очередь")
    conn().execute("DELETE FROM content")
    conn().commit()
    SENT.clear()
    META["token"] = ""            # Instagram выключен
    y = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    blocked = add(platform="reels", filename="12.mp4", when=y, ptime="00:00")
    okcard = add(platform="tg", caption="этот может выйти", when=y, ptime="00:00")

    done = poster.run_once()
    check("публикуемая карточка вышла, несмотря на застрявшую", done == 1, done)
    check("вышла именно она", row(okcard)["status"] == "published")
    check("застрявшая осталась в очереди", row(blocked)["status"] == "scheduled")
    check("и объясняет причину", "Instagram" in (row(blocked)["post_error"] or ""))
    check("но не переводилась в posting зря", row(blocked)["status"] != "posting")

    # Сорвавшаяся отправка не должна отбирать слот у следующей
    conn().execute("DELETE FROM content")
    conn().commit()
    CHANNEL["acme"] = "-100999"
    bad = add(product="acme", filename="нет-такого.mp4", caption="", title="", when=y, ptime="00:00")
    good = add(product="acme", caption="а этот выйдет", when=y, ptime="00:00")
    done2 = poster.run_once()
    check("после сбоя следующая карточка того же продукта пробует сразу", done2 == 1, done2)
    check("вышла вторая", row(good)["status"] == "published")
    check("первая с причиной в очереди", row(bad)["status"] == "scheduled")
    CHANNEL["acme"] = ""


def test_attempts_and_stuck():
    print("\n[G1] Повторы, застревание и зазор")
    conn().execute("DELETE FROM content")
    conn().commit()
    SENT.clear()
    CHANNEL["acme"] = "-100777"    # канал есть, но Telegram отвечает ошибкой
    BREAK["send"] = True
    y = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    cid = add(product="acme", caption="упрямая", when=y, ptime="00:00")

    for _ in range(5):
        poster.run_once()
    BREAK["send"] = False
    r = row(cid)
    check("больше MAX_ATTEMPTS попыток не делаем",
          r["attempts"] <= poster.MAX_ATTEMPTS, r["attempts"])
    check("после исчерпания попыток объясняем человеку",
          "не вышло" in (r["post_error"] or ""), r["post_error"])
    check("и в очередь на автопостинг она больше не попадает",
          cid not in {x["id"] for x in poster.due_rows()})

    # Кнопка «опубликовать сейчас» сбрасывает счётчик — это решение человека
    ok, info = poster.post_now(cid)
    check("кнопкой публикуется даже после исчерпанных попыток", ok, info)
    CHANNEL["acme"] = ""

    # Прерванная отправка не оставляет карточку в posting навсегда
    conn().execute("DELETE FROM content")
    conn().commit()
    stuck = add(caption="прервалась", when=y, ptime="00:00")
    poster.claim(stuck)
    conn().execute("UPDATE content SET claimed_at=? WHERE id=?",
                   (int(time.time()) - poster.STUCK_SECONDS - 10, stuck))
    conn().commit()
    check("до разлипания карточка невидима", stuck not in {x["id"] for x in poster.due_rows()})
    poster.unstick()
    check("застрявшая вернулась в очередь", row(stuck)["status"] == "scheduled")
    check("и объясняет, что отправка прервалась",
          "прерв" in (row(stuck)["post_error"] or ""), row(stuck)["post_error"])
    check("свежая posting не трогается", poster.claim(stuck) and poster.unstick() == 0)

    # Зазор между постами одного продукта
    conn().execute("DELETE FROM content")
    conn().commit()
    poster.MIN_GAP_SECONDS = 1800
    try:
        a = add(caption="первый", when=y, ptime="00:00")
        b = add(caption="второй", when=y, ptime="00:00")
        check("первый пост уходит", poster.run_once() == 1)
        check("второй ждёт зазора", poster.run_once() == 0)
        check("он всё ещё в очереди", row(b)["status"] == "scheduled")
        conn().execute("UPDATE content SET published_at=? WHERE id=?",
                       (int(time.time()) - 1801, a))
        conn().commit()
        check("после зазора выходит", poster.run_once() == 1)
    finally:
        poster.MIN_GAP_SECONDS = 0


def test_post_now():
    print("\n[G] Публикация по кнопке")
    SENT.clear()
    cid = add(caption="Срочно", when="", ptime="23:59", auto=0)
    ok, info = poster.post_now(cid)
    check("публикуется мимо расписания", ok, info)
    check("статус published", row(cid)["status"] == "published")
    ok2, info2 = poster.post_now(cid)
    check("повторно опубликовать нельзя", not ok2 and "уже" in info2, info2)
    ok3, _ = poster.post_now(999999)
    check("несуществующая карточка не падает", not ok3)


def test_instagram_off():
    print("\n[H] Instagram без токена")
    cid = add(platform="reels", filename="12.mp4")
    ok, info = poster.publish_row(row(cid))
    check("без токена молчит и объясняет", not ok and "Instagram" in info, info)


def main():
    install()
    test_schedule()
    test_claim()
    test_send_text()
    test_send_video()
    test_errors()
    test_run_once()
    test_blocked_platform_does_not_hog_queue()
    test_attempts_and_stuck()
    test_post_now()
    test_instagram_off()
    print("\n" + "=" * 46)
    print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
    for f in FAILS:
        print("  •", f)
    print("=" * 46)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
