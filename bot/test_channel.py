# -*- coding: utf-8 -*-
"""Тесты канала Grailert: запоминание канала и ежедневный пост с находкой.

Запуск: ./.venv/bin/python test_channel.py
Сеть не нужна — Vinted и Telegram подменяются заглушками.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMIN_IDS"] = "777"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot as B  # noqa: E402
import db  # noqa: E402

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


ITEMS = [
    {"id": 1, "title": "Stone Island jacket", "price": {"amount": "180.00", "currency_code": "EUR"},
     "size_title": "L", "brand_title": "Stone Island", "url": "https://vinted.pl/items/1",
     "photos": [{"full_size_url": "https://img/1.jpg"}]},
    {"id": 2, "title": "Stone Island tee", "price": {"amount": "45.00", "currency_code": "EUR"},
     "size_title": "M", "brand_title": "Stone Island", "url": "https://vinted.pl/items/2",
     "photos": [{"full_size_url": "https://img/2.jpg"}]},
    {"id": 3, "title": "No photo item", "price": {"amount": "5.00", "currency_code": "EUR"},
     "url": "https://vinted.pl/items/3", "photos": []},
    {"id": 4, "title": "No price", "photos": [{"full_size_url": "https://img/4.jpg"}],
     "url": "https://vinted.pl/items/4"},
]


class FakeBot:
    def __init__(self, fail=False):
        self.photos = []
        self.messages = []
        self.fail = fail

    async def send_photo(self, chat_id, photo, caption=None, parse_mode=None, reply_markup=None):
        if self.fail:
            raise RuntimeError("chat not found")
        self.photos.append({"chat": chat_id, "photo": photo, "caption": caption,
                            "kb": reply_markup})

    async def send_message(self, chat_id, text=None, **kw):
        self.messages.append({"chat": chat_id, "text": text})


class Ctx:
    def __init__(self, bot):
        self.bot = bot


class Chat:
    def __init__(self, cid, ctype="channel", title="Grails"):
        self.id, self.type, self.title = cid, ctype, title


class Upd:
    def __init__(self, chat, status, by=777):
        self.my_chat_member = type("E", (), {
            "chat": chat,
            "new_chat_member": type("M", (), {"status": status})(),
            "from_user": type("U", (), {"id": by})()})()


class FakeClient:
    def __init__(self, items):
        self.items = items

    async def get_items(self, params):
        return self.items


def install(items=ITEMS):
    async def get_client(host):
        return FakeClient(items)

    async def to_usd(amount, cur):
        return float(amount) * 1.1 if amount else None

    B.vinted.get_client = get_client
    B.rates.to_usd = to_usd


def test_pick():
    print("\n[A] Выбор находки")
    picked = B._pick_for_channel(ITEMS)
    check("выбрана самая дешёвая с фото", picked and picked[0]["id"] == 2, picked and picked[0]["id"])
    check("без фото не берём", B._pick_for_channel([ITEMS[2]]) is None)
    check("без цены не берём", B._pick_for_channel([ITEMS[3]]) is None)
    check("пустая выдача не ломает", B._pick_for_channel([]) is None)


def test_caption():
    print("\n[B] Подпись")
    cap = B._channel_caption("stone island", "vinted.pl", ITEMS[1], 49.5)
    check("есть название", "Stone Island tee" in cap)
    check("есть цена", "45 EUR" in cap, cap)
    check("есть доллары", "$49.50" in cap, cap)
    check("есть страна", "PL" in cap)
    check("есть ссылка на вещь", "vinted.pl/items/2" in cap)

    evil = dict(ITEMS[1], title="<script>alert(1)</script>", brand_title="A&B")
    cap2 = B._channel_caption("q", "vinted.pl", evil, None)
    check("html в названии экранирован", "<script>" not in cap2 and "&lt;script&gt;" in cap2)
    check("амперсанд экранирован", "A&amp;B" in cap2)


async def test_post():
    print("\n[C] Ежедневный пост")
    install()
    fb = FakeBot()
    ctx = Ctx(fb)

    db.clear_channel()
    await B.channel_job(ctx)
    check("без канала ничего не шлём", not fb.photos)

    db.set_channel(-1005, "Grails")
    hour = datetime.now(timezone.utc).hour
    B.CHANNEL_POST_HOUR_UTC = (hour + 1) % 24
    await B.channel_job(ctx)
    check("не в свой час не постим", not fb.photos)

    B.CHANNEL_POST_HOUR_UTC = hour
    await B.channel_job(ctx)
    check("в свой час пост ушёл", len(fb.photos) == 1, fb.photos)
    check("ушёл в наш канал", fb.photos[0]["chat"] == -1005)
    check("с фотографией вещи", fb.photos[0]["photo"] == "https://img/2.jpg")
    check("с кнопкой в бота", fb.photos[0]["kb"] is not None)

    await B.channel_job(ctx)
    check("второй раз за день не постим", len(fb.photos) == 1)


async def test_failures():
    print("\n[D] Сбои")
    key = f"channel_post:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    db.drop_flag(key)
    install(items=[])
    fb = FakeBot()
    await B.channel_job(Ctx(fb))
    check("пустая выдача — не постим", not fb.photos)
    check("и день не сгорает", db.flag_once(key) is True)

    db.drop_flag(key)
    install()
    bad = FakeBot(fail=True)
    await B.channel_job(Ctx(bad))
    check("отказ Telegram не роняет джобу", not bad.photos)
    check("после отказа попробуем завтра снова", db.flag_once(key) is True)


async def test_remember():
    print("\n[E] Бот запоминает канал")
    fb = FakeBot()
    ctx = Ctx(fb)
    await B.on_my_chat_member(Upd(Chat(-2001, title="Мой"), "administrator"), ctx)
    check("канал запомнен", (db.get_channel() or {}).get("id") == -2001)
    check("админу написали", any("-2001" in (m["text"] or "") for m in fb.messages))

    await B.on_my_chat_member(Upd(Chat(-2002, ctype="private"), "administrator"), ctx)
    check("личный чат не канал", (db.get_channel() or {}).get("id") == -2001)

    await B.on_my_chat_member(Upd(Chat(-2002), "kicked"), ctx)
    check("выгнали из чужого — наш на месте", (db.get_channel() or {}).get("id") == -2001)

    await B.on_my_chat_member(Upd(Chat(-9001, title="Чужой"), "administrator", by=31337), ctx)
    check("посторонний не уводит канал себе", (db.get_channel() or {}).get("id") == -2001)

    await B.on_my_chat_member(Upd(Chat(-2001), "restricted"), ctx)
    check("разжалованный бот — канал отключён", db.get_channel() is None)

    await B.on_my_chat_member(Upd(Chat(-2001, title="Мой"), "administrator"), ctx)
    await B.on_my_chat_member(Upd(Chat(-2001), "kicked"), ctx)
    check("выгнали из нашего — забыли", db.get_channel() is None)


async def main():
    db.init_db()
    db.init_billing()
    test_pick()
    test_caption()
    await test_post()
    await test_failures()
    await test_remember()
    print("\n" + "=" * 46)
    print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
    for f in FAILS:
        print("  •", f)
    print("=" * 46)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
