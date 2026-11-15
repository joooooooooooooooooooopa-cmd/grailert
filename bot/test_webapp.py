# -*- coding: utf-8 -*-
"""Тесты пульта (Mini App): подпись initData, доступ к чужому, лимиты, ленты.

Запуск: ./.venv/bin/python test_webapp.py
Сеть не нужна — Vinted и петля бота подменяются заглушками.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
from urllib.parse import urlencode

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import config  # noqa: E402
import db  # noqa: E402
import plans  # noqa: E402
import vinted  # noqa: E402
import webapp  # noqa: E402
from app_i18n import APP_STRINGS, strings  # noqa: E402

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


def make_init_data(uid: int, auth_date: int | None = None, token: str | None = None) -> str:
    """Собирает подписанную строку initData ровно так, как это делает Telegram."""
    user = json.dumps({"id": uid, "first_name": "T"}, separators=(",", ":"))
    pairs = {"auth_date": str(auth_date or int(time.time())), "user": user, "query_id": "AA"}
    check_str = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", (token or config.BOT_TOKEN).encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check_str.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


# --- заглушки бота -----------------------------------------------------------

SCHEDULED: list[int] = []
UNSCHEDULED: list[int] = []
POLLED: list[int] = []
INVOICES: list[dict] = []


class FakeJobQueue:
    pass


def fake_schedule(_jq, sub, first=3):
    SCHEDULED.append(sub["id"])


def fake_unschedule(_jq, sid):
    UNSCHEDULED.append(sid)


FAKE_ITEMS = [
    {"id": 1, "title": "Stone Island jacket", "price": {"amount": "65.00", "currency_code": "EUR"},
     "size_title": "M", "brand_title": "Stone Island", "url": "https://vinted.pl/items/1",
     "photos": [{"full_size_url": "https://img/1.jpg"}]},
    {"id": 2, "title": "Nike TN sneakers", "price": {"amount": "50.00", "currency_code": "EUR"},
     "size_title": "43", "brand_title": "Nike", "url": "https://vinted.pl/items/2",
     "photos": [{"full_size_url": "https://img/2.jpg"}]},
]


def install_fakes():
    """Подменяем только сеть; корутины выполняем по-настоящему.

    Так тест проверяет реальный путь: api_* → call_bot → _schedule → хук бота,
    а не наше представление о нём.
    """
    import asyncio

    async def fake_fetch(url):
        return list(FAKE_ITEMS)

    webapp._fetch_items = fake_fetch
    webapp._loop = object()   # не None, чтобы call_bot не ругался
    webapp.call_bot = lambda coro, timeout=40: asyncio.run(coro)

    async def run_poll(_bot, sub, force=False):
        POLLED.append(sub["id"])
        return 2

    async def make_invoice(uid, lang, code, method):
        INVOICES.append({"uid": uid, "code": code, "method": method})
        return {"ok": True, "kind": method, "url": "https://pay", "id": 7}

    async def check_payment(payment):
        return "pending"

    webapp._hooks = {
        "lang_of": lambda uid: "en",
        "plan_of": lambda uid: PLAN.get(uid, (plans.FREE, 0)),
        "plan_name": lambda lang, plan: plan.capitalize(),
        "fmt_date": lambda ts: "01.01.2027",
        "schedule": fake_schedule,
        "unschedule": fake_unschedule,
        "job_queue": lambda: FakeJobQueue(),
        "bot": lambda: None,
        "run_poll": run_poll,
        "crypto_enabled": lambda: True,
        "make_invoice": make_invoice,
        "check_payment": check_payment,
    }


PLAN: dict[int, tuple[str, int]] = {}


# --- тесты -------------------------------------------------------------------

def test_init_data():
    print("\n[A] Подпись initData")
    uid = 111
    check("правильная подпись пускает", webapp.validate_init_data(make_init_data(uid)) == uid)
    check("пустая строка не пускает", webapp.validate_init_data("") is None)
    check("подпись чужим токеном не проходит",
          webapp.validate_init_data(make_init_data(uid, token="999:OTHER")) is None)

    tampered = make_init_data(uid).replace("first_name", "firstXname")
    check("подмена данных ломает подпись", webapp.validate_init_data(tampered) is None)

    old = make_init_data(uid, auth_date=int(time.time()) - 48 * 3600)
    check("протухшая строка не пускает", webapp.validate_init_data(old) is None)
    check("свежая строка при коротком сроке пускает",
          webapp.validate_init_data(make_init_data(uid), max_age=3600) == uid)

    no_date = urlencode({"user": '{"id":1}', "hash": "deadbeef"})
    check("без auth_date не пускает", webapp.validate_init_data(no_date) is None)


def test_strings():
    print("\n[B] Языки пульта")
    en = set(APP_STRINGS["en"])
    for lang in APP_STRINGS:
        missing = en - set(APP_STRINGS[lang])
        check(f"{lang}: все ключи на месте", not missing, sorted(missing)[:4])
    check("языков столько же, сколько у бота", len(APP_STRINGS) == 7, len(APP_STRINGS))
    check("незнакомый язык падает в английский", strings("xx")["save"] == APP_STRINGS["en"]["save"])
    # Плейсхолдеры должны совпадать, иначе перевод покажет {limit} сырым
    import re
    for lang, block in APP_STRINGS.items():
        for key, en_text in APP_STRINGS["en"].items():
            if key not in block:
                continue
            want = set(re.findall(r"\{(\w+)\}", en_text))
            got = set(re.findall(r"\{(\w+)\}", block[key]))
            if want != got:
                check(f"{lang}.{key}: плейсхолдеры совпадают", False, f"{want} vs {got}")
                break
        else:
            check(f"{lang}: плейсхолдеры везде совпадают", True)


def test_add_and_limits():
    print("\n[C] Добавление поиска и лимиты тарифа")
    uid = 201
    db.activate_user(uid, "tester")
    PLAN[uid] = (plans.FREE, 0)

    r = webapp.api_add(uid, {"query": "stone island", "host": "vinted.pl", "interval": 30})
    check("поиск создан", r.get("ok") is True, r)
    sid = r["search"]["id"]
    check("интервал подтянут до тарифного",
          r["search"]["interval"] == plans.min_interval(plans.FREE), r["search"]["interval"])
    check("домен разобрался", r["search"]["host"] == "vinted.pl", r["search"]["host"])

    r2 = webapp.api_add(uid, {"query": "carhartt", "host": "vinted.pl"})
    check("второй поиск на Free упирается в лимит", r2.get("error") == "limit", r2)

    PLAN[uid] = (plans.PRO, int(time.time()) + 86400)

    r3 = webapp.api_add(uid, {"query": "x", "host": "evil.example.com"})
    check("чужой домен отклоняется", r3.get("error") == "bad_host", r3)

    r4 = webapp.api_add(uid, {"query": "   "})
    check("пустой запрос отклоняется", r4.get("error") == "empty", r4)

    r5 = webapp.api_add(uid, {"query": "carhartt", "host": "vinted.de", "interval": 30})
    check("на Pro второй поиск создаётся", r5.get("ok") is True, r5)
    check("на Pro доступен интервал 30 с", r5["search"]["interval"] == 30, r5["search"]["interval"])
    return uid, sid


def test_ownership(uid: int, sid: int):
    print("\n[D] Чужое не отдаём")
    other = 202
    db.activate_user(other, "other")
    PLAN[other] = (plans.PRO, 0)
    check("чужой поиск не читается", webapp.api_feed(other, {"id": sid}).get("error") == "not_found")
    check("чужой поиск не правится", webapp.api_save(other, {"id": sid, "name": "hacked"}).get("error") == "not_found")
    check("чужой поиск не удаляется", webapp.api_delete(other, {"id": sid}).get("error") == "not_found")
    check("чужой поиск не проверяется", webapp.api_check(other, {"id": sid}).get("error") == "not_found")
    check("имя поиска не изменилось", db.get_subscription(sid)["name"] != "hacked")
    check("несуществующий id не падает", webapp.api_save(uid, {"id": 99999}).get("error") == "not_found")


def test_save(uid: int, sid: int):
    print("\n[E] Правка поиска")
    PLAN[uid] = (plans.FREE, 0)
    r = webapp.api_save(uid, {"id": sid, "interval": 30})
    check("интервал ниже тарифа не сохраняется", r.get("error") == "interval_locked", r)
    check("в базе остался прежний интервал",
          db.get_subscription(sid)["interval_sec"] >= plans.min_interval(plans.FREE))

    r2 = webapp.api_save(uid, {"id": sid, "name": "Grails", "kw_include": "wool", "kw_exclude": "kids"})
    check("имя и фильтры сохраняются",
          r2["search"]["name"] == "Grails" and r2["search"]["kw_include"] == "wool", r2)

    r3 = webapp.api_save(uid, {"id": sid, "active": False})
    check("поиск ставится на паузу", r3["search"]["active"] is False)
    check("снят с расписания", sid in UNSCHEDULED)

    PLAN[uid] = (plans.PRO, int(time.time()) + 86400)
    r4 = webapp.api_save(uid, {"id": sid, "active": True})
    check("поиск снова включается", r4["search"]["active"] is True, r4)
    check("возвращён в расписание", sid in SCHEDULED)


def test_activation_limit():
    print("\n[F] Включение сверх лимита")
    uid = 203
    db.activate_user(uid, "u3")
    PLAN[uid] = (plans.PRO, 0)
    a = webapp.api_add(uid, {"query": "a", "host": "vinted.pl"})["search"]["id"]
    b = webapp.api_add(uid, {"query": "b", "host": "vinted.pl"})["search"]["id"]
    webapp.api_save(uid, {"id": b, "active": False})
    PLAN[uid] = (plans.FREE, 0)   # тариф кончился
    r = webapp.api_save(uid, {"id": b, "active": True})
    check("второй поиск на Free включить нельзя", r.get("error") == "limit", r)
    check("первый остался активным", db.get_subscription(a)["active"] == 1)


def test_feed_and_check(uid: int, sid: int):
    print("\n[G] Лента и проверка сейчас")
    db.set_keywords(sid, "", "")   # предыдущий тест оставил фильтры
    r = webapp.api_feed(uid, {"id": sid})
    check("лента отдаёт объявления", r.get("ok") and len(r["items"]) == 2, r)
    item = r["items"][0]
    check("в карточке есть цена, ссылка и фото",
          item["price"] and item["url"] and item["photo"], item)

    db.set_keywords(sid, "nike", "")
    r2 = webapp.api_feed(uid, {"id": sid})
    check("фильтр слов применяется к ленте", len(r2["items"]) == 1, r2["items"])
    db.set_keywords(sid, "", "")

    r3 = webapp.api_check(uid, {"id": sid})
    check("проверка сейчас возвращает число отправленных", r3.get("sent") == 2, r3)

    p = webapp.api_preview(uid, {"query": "stone island", "host": "vinted.pl"})
    check("превью считает объявления", p.get("count") == 2, p)


def test_session(uid: int):
    print("\n[H] Сессия")
    PLAN[uid] = (plans.BASIC, int(time.time()) + 86400)
    s = webapp.session_payload(uid)
    check("отдаётся тариф и дата", s["plan"] == plans.BASIC and s["plan_until"], s["plan"])
    check("строки языка приехали", s["t"]["save"] == APP_STRINGS["en"]["save"])
    check("интервалы помечены замком по тарифу",
          any(i["locked"] for i in s["intervals"]) and any(not i["locked"] for i in s["intervals"]))
    check("замок стоит именно на быстрых интервалах",
          all(i["locked"] == (i["sec"] < plans.min_interval(plans.BASIC)) for i in s["intervals"]))
    check("список доменов не пуст", len(s["hosts"]) >= 10)
    check("тарифы для покупки отданы", len(s["products"]) == len(plans.PRODUCTS))
    check("свои поиски видны", all(x["id"] for x in s["searches"]))


def test_buy(uid: int):
    print("\n[I] Касса")
    r = webapp.api_buy(uid, {"code": "pro_30", "method": "stars"})
    check("счёт звёздами создаётся", r.get("kind") == "stars", r)
    check("счёт создан на нужный тариф", INVOICES and INVOICES[-1]["code"] == "pro_30")
    check("несуществующий тариф отклоняется",
          webapp.api_buy(uid, {"code": "gold_1000"}).get("error") == "bad_product")
    r2 = webapp.api_buy(uid, {"code": "pro_30", "method": "wire"})
    check("неизвестный способ падает в звёзды", r2.get("kind") == "stars", r2)

    webapp._hooks["crypto_enabled"] = lambda: False
    r3 = webapp.api_buy(uid, {"code": "pro_30", "method": "crypto"})
    check("выключенная крипта не создаёт счёт", r3.get("error") == "crypto_off", r3)
    webapp._hooks["crypto_enabled"] = lambda: True

    pid = db.create_payment(uid, "pro_30", "stars", 999, "XTR")
    check("чужой платёж не проверяется",
          webapp.api_paystatus(999999, {"id": pid}).get("error") == "not_found")
    check("свой платёж отдаёт фазу", webapp.api_paystatus(uid, {"id": pid}).get("phase") == "pending")


def test_security_fixes():
    """Дыры, найденные ревью 06.09. Каждая — с конкретным сценарием обхода."""
    print("\n[K] Закрытые дыры")
    uid = 301
    db.activate_user(uid, "sec")
    PLAN[uid] = (plans.PRO, 0)

    # SSRF: превью не должно ходить на произвольный хост
    r = webapp.api_preview(uid, {"query": "x", "host": "attacker.tld"})
    check("превью не ходит на чужой хост", r.get("error") == "bad_host", r)
    check("превью по своему домену работает",
          webapp.api_preview(uid, {"query": "x", "host": "vinted.pl"}).get("ok"))
    check("ссылка вида vinted.evil.com не считается своей",
          not vinted.looks_like_vinted_url("https://vinted.evil.com/catalog"))
    check("подставной хост в ссылке не уводит запрос",
          vinted.parse_search_url("https://attacker.tld/catalog?q=1")[0] != "attacker.tld")

    # Кулдаун на «проверить сейчас»
    webapp._last_manual.pop(uid, None)
    sid = webapp.api_add(uid, {"query": "cooldown", "host": "vinted.pl"})["search"]["id"]
    check("первая ручная проверка проходит", webapp.api_check(uid, {"id": sid}).get("ok"))
    again = webapp.api_check(uid, {"id": sid})
    check("вторая подряд упирается в паузу", again.get("error") == "cooldown", again)
    check("паузу называют в секундах", again.get("seconds", 0) > 0)
    webapp._last_manual.pop(uid, None)

    # Мастер-тумблер не должен поднимать поисков больше лимита
    uid2 = 302
    db.activate_user(uid2, "toggle")
    PLAN[uid2] = (plans.PRO, 0)
    ids = [webapp.api_add(uid2, {"query": f"q{i}", "host": "vinted.pl"})["search"]["id"]
           for i in range(4)]
    webapp.api_save(uid2, {"id": ids[0], "active": False})
    webapp.api_save(uid2, {"id": ids[1], "active": False})
    PLAN[uid2] = (plans.BASIC, 0)          # лимит 3, активны два
    webapp.api_toggleall(uid2, {"on": True})
    active = sum(1 for s in db.list_subscriptions(uid2) if s["active"])
    check("мастер-тумблер не превышает лимит тарифа",
          active <= plans.search_limit(plans.BASIC), active)

    # Правка не должна записываться до проверки интервала
    uid3 = 303
    db.activate_user(uid3, "save")
    PLAN[uid3] = (plans.PRO, 0)
    sid3 = webapp.api_add(uid3, {"query": "keep", "host": "vinted.pl",
                                 "interval": 30, "name": "старое"})["search"]["id"]
    PLAN[uid3] = (plans.FREE, 0)
    r3 = webapp.api_save(uid3, {"id": sid3, "name": "новое", "interval": 30})
    check("сохранение с наследным интервалом не блокируется", r3.get("ok"), r3)
    check("имя действительно сохранилось", db.get_subscription(sid3)["name"] == "новое")
    r4 = webapp.api_save(uid3, {"id": sid3, "name": "ещё", "interval": 60})
    check("попытка ускориться отклоняется", r4.get("error") == "interval_locked", r4)
    check("и имя при отказе НЕ записано", db.get_subscription(sid3)["name"] == "новое")

    # Пульт показывает интервал, по которому опрос идёт на самом деле
    shown = webapp.session_payload(uid3)["searches"][0]["interval"]
    check("карточка показывает реальную частоту опроса",
          shown >= plans.min_interval(plans.FREE), shown)

    # initData с процентами в имени должна проходить
    import json as _json
    from urllib.parse import urlencode as _enc
    user = _json.dumps({"id": 304, "first_name": 'A%22B'}, separators=(",", ":"))
    pairs = {"auth_date": str(int(time.time())), "user": user}
    cs = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, cs.encode(), hashlib.sha256).hexdigest()
    check("проценты в имени не ломают вход", webapp.validate_init_data(_enc(pairs)) == 304)


def test_page():
    print("\n[J] Страница пульта")
    html = webapp._page().decode()
    check("страница читается", len(html) > 4000)
    check("подключён telegram-web-app.js", "telegram-web-app.js" in html)
    check("нет других внешних скриптов", html.count("<script src=") == 1)
    check("вкладки на месте", all(x in html for x in ("pane-searches", "pane-feed", "pane-plan")))
    check("тема переключается", 'data-theme' in html)
    for key in ("tab_searches", "check_now", "add_new", "pay_stars"):
        check(f"строка {key} используется на странице", f"T.{key}" in html)


def main():
    db.init_db()
    db.init_billing()
    install_fakes()

    test_init_data()
    test_strings()
    uid, sid = test_add_and_limits()
    test_ownership(uid, sid)
    test_save(uid, sid)
    test_activation_limit()
    test_feed_and_check(uid, sid)
    test_session(uid)
    test_buy(uid)
    test_security_fixes()
    test_page()

    print("\n" + "=" * 46)
    print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
    for f in FAILS:
        print("  •", f)
    print("=" * 46)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
