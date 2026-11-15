"""Комплексный прогон тестов: парсинг, фильтры, цена, фото, курсы, БД, живой Vinted.

Запуск:  ./.venv/bin/python test_all.py
Использует временную БД в /tmp, прод не трогает.
"""
import asyncio
import os
import sys
import tempfile
import time

os.environ.setdefault("BOT_TOKEN", "123:dummy")
# Блоки G и I ходят в сеть (курсы валют, живой Vinted) - по умолчанию выключены,
# чтобы прогон был детерминированным и офлайн. Включить: LIVE_TESTS=1.
LIVE = os.environ.get("LIVE_TESTS", "") == "1"
_TMPDB = os.path.join(tempfile.gettempdir(), "vinted_test.db")
for _ext in ("", "-wal", "-shm"):
    try:
        os.remove(_TMPDB + _ext)
    except OSError:
        pass
os.environ["DB_PATH"] = _TMPDB

import config  # noqa: E402
import db  # noqa: E402
import rates  # noqa: E402
import vinted  # noqa: E402
import bot  # noqa: E402,F401  (проверяем, что весь бот импортируется/компилируется)

PASS = 0
FAIL = 0
FAILS: list[str] = []


def check(name: str, cond: bool, extra="") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  ❌ {name}   {extra}")


# ---------------------------------------------------------------- A) URL parse
print("\n[A] Разбор поисковых ссылок (все типы фильтров)")
host, p = vinted.parse_search_url(
    "https://www.vinted.pl/catalog?search_text=nike+air&brand_ids[]=53&brand_ids[]=88"
    "&catalog[]=1242&size_ids[]=207&status[]=6&color_ids[]=1&material_ids[]=44"
    "&price_from=10&price_to=200&currency=PLN&order=relevance&time=999&page=3"
)
check("host = vinted.pl", host == "vinted.pl", host)
check("search_text декодирован", p.get("search_text") == "nike air", p.get("search_text"))
check("brand_ids[] → brand_ids '53,88'", p.get("brand_ids") == "53,88", p.get("brand_ids"))
check("catalog[] → catalog_ids", p.get("catalog_ids") == "1242", p.get("catalog_ids"))
check("size_ids[] → size_ids", p.get("size_ids") == "207", p.get("size_ids"))
check("status[] → status_ids", p.get("status_ids") == "6", p.get("status_ids"))
check("color_ids[] → color_ids", p.get("color_ids") == "1", p.get("color_ids"))
check("material_ids[] → material_ids", p.get("material_ids") == "44", p.get("material_ids"))
check("price_from / price_to", p.get("price_from") == "10" and p.get("price_to") == "200")
check("currency", p.get("currency") == "PLN")
check("order форсится newest_first", p.get("order") == "newest_first", p.get("order"))
check("page отброшен", "page" not in p)
check("time отброшен", "time" not in p)
check("per_page по умолчанию = 20", p.get("per_page") == "20", p.get("per_page"))
h2, _ = vinted.parse_search_url("https://www.vinted.fr/catalog?search_text=zara")
check("домен .fr распознан", h2 == "vinted.fr", h2)

# поиск по ключевому слову (без ссылки)
kw_url = vinted.build_search_url("womens bag")
check("build_search_url кодирует слово", "search_text=womens+bag" in kw_url, kw_url)
check("build_search_url содержит домен по умолчанию", config.DEFAULT_HOST in kw_url)
kh, kp = vinted.parse_search_url(kw_url)
check("слово → search_text", kp.get("search_text") == "womens bag", kp.get("search_text"))
check("слово → order newest_first", kp.get("order") == "newest_first")
check("кириллическое слово кодируется", "search_text=" in vinted.build_search_url("сумка женская"))
check("build_search_url с доменом DE", "www.vinted.de/catalog" in vinted.build_search_url("schuhe", "vinted.de"))
check("build_search_url домен по умолчанию = PL", "www.vinted.pl" in vinted.build_search_url("nike"))

# ----------------------------------------------------------- B) URL validation
print("\n[B] Валидация ссылок")
check("vinted.pl валидна", vinted.looks_like_vinted_url("https://www.vinted.pl/catalog?x=1"))
check("vinted.de валидна", vinted.looks_like_vinted_url("https://vinted.de/catalog"))
check("мусор не валиден", not vinted.looks_like_vinted_url("привет как дела"))
check("google не валиден", not vinted.looks_like_vinted_url("https://google.com"))

# -------------------------------------------------------------- C) kw filter
print("\n[C] Фильтр по ключевым словам")
pk = vinted.passes_keywords
check("include совпадает", pk("Nike Air Max", "nike", ""))
check("include не совпадает", not pk("Adidas Originals", "nike", ""))
check("include регистронезависим", pk("NIKE buty", "nike", ""))
check("include любой из списка", pk("Puma shoes", "nike, puma", ""))
check("exclude отсекает", not pk("fake nike", "", "fake"))
check("exclude не мешает", pk("oryginalne nike", "", "fake"))
check("include + exclude (ок)", pk("nike original", "nike", "fake"))
check("include + exclude (отсев)", not pk("nike fake", "nike", "fake"))
check("пустые фильтры пропускают всё", pk("что угодно", "", ""))

# ------------------------------------------------------------------- D) price
print("\n[D] Цена")
it = {
    "price": {"amount": "179.39", "currency_code": "PLN"},
    "total_item_price": {"amount": "191.26", "currency_code": "PLN"},
}
amt, cur = vinted.price_amount(it)
check("amount из dict", abs(amt - 179.39) < 0.01, amt)
check("currency из dict", cur == "PLN", cur)
check("item_price формат", vinted.item_price(it) == "179.39 PLN", vinted.item_price(it))
check("total_price формат", vinted.total_price(it) == "191.26 PLN", vinted.total_price(it))
check("нет цены → None", vinted.price_amount({})[0] is None)
check("нет total → None", vinted.total_price({}) is None)

# ------------------------------------------------------------------ E) photos
print("\n[E] Фото")
check(
    "галерея из каталога photos[]",
    vinted.photo_urls(None, {"photos": [{"full_size_url": "u1"}, {"url": "u2"}]}) == ["u1", "u2"],
)
check(
    "одиночное photo как fallback",
    vinted.photo_urls(None, {"photo": {"url": "single"}}) == ["single"],
)
check("нет фото → пусто", vinted.photo_urls(None, {}) == [])
check(
    "обрезка до MAX_PHOTOS",
    len(vinted.photo_urls(None, {"photos": [{"url": f"u{i}"} for i in range(15)]})) == config.MAX_PHOTOS,
)

# ----------------------------------------------------------------- F) caption
print("\n[F] Карточка уведомления (+ экранирование HTML)")
evil = {
    "title": "<b>hack</b> & <script>",
    "price": {"amount": "50", "currency_code": "PLN"},
    "size_title": "M",
    "brand_title": "Nike",
    "status": "Bardzo dobry",
    "url": "https://www.vinted.pl/items/1",
}
cap = vinted.format_caption("Поиск", evil, usd=13.6)
check("HTML в title экранирован", "&lt;b&gt;hack&lt;/b&gt;" in cap)
check("USD показан", "$13.60" in cap, cap)
check("цена показана", "50 PLN" in cap)
check("ссылка-кнопка есть", "Открыть на Vinted" in cap)
check("без usd нет ≈$", "≈" not in vinted.format_caption("Поиск", evil, usd=None))

# ------------------------------------------------------------ F2) краевые случаи
print("\n[F2] Краевые случаи")
h_empty, p_empty = vinted.parse_search_url("https://www.vinted.pl/catalog")
check("ссылка без параметров → order+per_page", p_empty.get("order") == "newest_first" and p_empty.get("per_page") == "20")
check("host при пустом query", h_empty == "vinted.pl")
amt_plain, cur_plain = vinted.price_amount({"price": "50", "currency": "EUR"})
check("plain-цена (не dict)", amt_plain == 50.0 and cur_plain == "EUR", (amt_plain, cur_plain))
cap_min = vinted.format_caption("X", {})
check("пустой item → не падает", "Без названия" in cap_min and "📏" in cap_min)
special = 'nike "air" & <co>'
_, sp = vinted.parse_search_url(vinted.build_search_url(special))
check("спецсимволы кодируются и парсятся обратно", sp.get("search_text") == special, sp.get("search_text"))
check("фильтр с лишними запятыми/пробелами", vinted.passes_keywords("Air Jordan", "  nike , , air  ", ""))
check("exclude пустые токены не ломают", vinted.passes_keywords("nike", "", " , , "))

# ---------------------------------------------------------- F3) фильтр цены и 🔥
print("\n[F3] Фильтр цены в URL и бейдж выгоды")
u = "https://www.vinted.pl/catalog?search_text=nike&order=newest_first"
u2 = vinted.set_price_filter(u, 10, 50)
check("set_price_filter пишет обе грани", vinted.price_filter_of(u2) == (10.0, 50.0), u2)
u3 = vinted.set_price_filter(u2, None, 30)
check("замена диапазона", vinted.price_filter_of(u3) == (None, 30.0), u3)
check("снятие фильтра", vinted.price_filter_of(vinted.set_price_filter(u3, None, None)) == (None, None))
check("search_text уцелел после правок", "search_text=nike" in vinted.set_price_filter(u2, 5, None))
_, papi = vinted.parse_search_url(u2)
check("price_from/to доходят до API-параметров", papi.get("price_from") == "10" and papi.get("price_to") == "50", papi)
check("parse: 10-50", vinted.parse_price_range("10-50") == (10.0, 50.0))
check("parse: -50", vinted.parse_price_range("-50") == (None, 50.0))
check("parse: 10-", vinted.parse_price_range("10-") == (10.0, None))
check("parse: '-' очищает", vinted.parse_price_range("-") == (None, None))
check("parse: 50-10 переворачивается", vinted.parse_price_range("50-10") == (10.0, 50.0))
check("parse: запятая как точка", vinted.parse_price_range("9,5-20") == (9.5, 20.0))
check("parse: мусор -> None", vinted.parse_price_range("abc") is None)
check("parse: отрицательное -> None", vinted.parse_price_range("x-5") is None)
check("pretty: диапазон", vinted.pretty_price_range(10, 50) == "10–50")
check("pretty: только мин", vinted.pretty_price_range(10, None) == "≥ 10")

def _items(prices):
    return [{"price": {"amount": str(p), "currency_code": "PLN"}} for p in prices]

check("медиана: мало данных -> None", vinted.deal_median(_items([10, 20])) is None)
med = vinted.deal_median(_items([10, 20, 30, 40, 50, 60, 70, 80]))
check("медиана чётной пачки", med == 45.0, med)
check("🔥 при цене ≤ 60% медианы", vinted.is_deal(_items([20])[0], 45.0))
check("нет 🔥 у обычной цены", not vinted.is_deal(_items([40])[0], 45.0))
check("нет 🔥 без медианы", not vinted.is_deal(_items([1])[0], None))

cap_en = vinted.format_caption("S", evil, usd=None, lang="en", deal=True)
check("caption en: локализована", "Open on Vinted" in cap_en and "Size:" in cap_en)
check("caption en: 🔥 бейдж на месте", "🔥" in cap_en)
check("caption ru: без deal нет 🔥", "🔥" not in vinted.format_caption("S", evil, lang="ru"))
for _lg in ("en", "fr", "de", "es", "it", "pl", "ru"):
    _c = vinted.format_caption("S", evil, usd=1.0, lang=_lg, deal=True)
    check(f"caption {_lg}: рендерится", bool(_c) and "50 PLN" in _c)

# ------------------------------------------------------------------- G) rates
print("\n[G] Курсы валют → USD (сеть)")


async def g_rates():
    check("USD→USD = сумма", await rates.to_usd(30, "USD") == 30.0)
    pln = await rates.to_usd(100, "PLN")
    check("PLN→USD адекватный", pln is not None and 10 < pln < 100, pln)
    eur = await rates.to_usd(100, "EUR")
    check("EUR→USD адекватный", eur is not None and 60 < eur < 200, eur)
    check("None сумма → None", await rates.to_usd(None, "PLN") is None)
    check("неизвестная валюта → None", await rates.to_usd(10, "QQQ") is None)
    t0 = time.monotonic()
    await rates.to_usd(100, "PLN")
    check("кеш мгновенный (<0.05с)", time.monotonic() - t0 < 0.05)


if LIVE:
    asyncio.run(g_rates())
else:
    print("  (пропущено: сеть, LIVE_TESTS=1 чтобы включить)")

# ---------------------------------------------------------------------- H) DB
print("\n[H] База данных (полный CRUD + статистика)")
db.init_db()
db.activate_user(1001, "alice")
check("активация / проверка доступа", db.is_activated(1001) and not db.is_activated(9999))
db.init_billing()  # ключи и белый список живут в init_invites (вызывается из init_billing)
key = db.create_key(1)
check("ключ создан (GRL-XXXX-XXXX)", key.startswith("GRL-") and len(key) == 13)
check("ключ одноразовый", db.use_key(key, 2002) == "ok" and db.use_key(key, 2003) == "used")
check("несуществующий ключ отклонён", db.use_key("GRL-ZZZZ-ZZZZ", 2004) == "unknown")
sid = db.add_subscription(1001, "Nike", "https://www.vinted.pl/catalog?search_text=nike", 120)
check("подписка создана", sid > 0 and len(db.list_subscriptions(1001)) == 1)
db.set_keywords(sid, include="nike", exclude="fake")
s = db.get_subscription(sid)
check("ключевые слова сохранены", s["kw_include"] == "nike" and s["kw_exclude"] == "fake")
db.set_interval(sid, 300)
check("интервал обновлён", db.get_subscription(sid)["interval_sec"] == 300)
db.set_name(sid, "Найки")
check("имя обновлено", db.get_subscription(sid)["name"] == "Найки")
db.set_url(sid, "https://www.vinted.pl/catalog?search_text=nike2")
check("url обновлён", "nike2" in db.get_subscription(sid)["url"])
check("baseline изначально пуст", db.seen_count(sid) == 0)
db.mark_many_seen(sid, ["a", "b", "c"])
check("seen учтены / дедуп", db.seen_count(sid) == 3 and db.is_seen(sid, "a") and not db.is_seen(sid, "z"))
db.add_notification(sid, "a")
db.add_notification(sid, "b")
check("notif_total = 2", db.notif_total(sid) == 2)
check("notif_today = 2", db.notif_today(sid) == 2)
db.set_active(sid, False)
check("пауза снимает с активных", db.get_subscription(sid)["active"] == 0 and not db.all_active_subscriptions())
ids = db.set_active_all(1001, True)
check("запустить все", sid in ids and db.get_subscription(sid)["active"] == 1)
st = db.user_stats(1001)
check("user_stats корректен", st["total"] == 1 and st["notif_total"] == 2 and st["active"] == 1)
g = db.global_stats()
check("global_stats корректен", g["users"] >= 1 and g["subs"] >= 1 and g["notif_total"] >= 2)
db.delete_subscription(sid)
check(
    "удаление каскадом (sub+seen+notif)",
    db.get_subscription(sid) is None and db.seen_count(sid) == 0 and db.notif_total(sid) == 0,
)

# -------------------------------------------------------------- I) LIVE Vinted
print("\n[I] Живой парсинг Vinted — разные поиски (сеть)")


async def g_live():
    client = await vinted.get_client("vinted.pl")
    chk = await client.check()
    check("check() — Vinted доступен", chk["ok"], chk)
    searches = {
        "слово 'nike'": "https://www.vinted.pl/catalog?search_text=nike",
        "по слову 'womens bag' (build_search_url)": vinted.build_search_url("womens bag"),
        "бренд+цена 'stone island' ≤300": "https://www.vinted.pl/catalog?search_text=stone+island&price_to=300&currency=PLN",
        "широкий 'adidas'": "https://www.vinted.pl/catalog?search_text=adidas",
        "фраза 'vintage levis'": "https://www.vinted.pl/catalog?search_text=vintage+levis",
    }
    for label, url in searches.items():
        _, params = vinted.parse_search_url(url)
        items = await client.get_items(params)
        ok = items is not None and len(items) > 0
        check(f"{label}: объявления получены", ok, f"items={items if items is None else len(items)}")
        if ok:
            first = items[0]
            check(f"{label}: id+title есть", first.get("id") and first.get("title"))
            check(f"{label}: цена парсится", vinted.price_amount(first)[0] is not None)
            check(f"{label}: фото есть", len(vinted.photo_urls(None, first)) > 0)
            cnt = sum(1 for i in items if len(vinted.photo_urls(None, i)) >= 1)
            print(f"       ↳ {len(items)} объявл., с фото: {cnt}")
        await asyncio.sleep(1)

    # Срез цен для карточки (фейковый sub-словарь — Row не нужен)
    pl = await bot.price_snapshot({"url": "https://www.vinted.pl/catalog?search_text=nike"}, "en")
    # Проверяем содержимое, а не язык: строка теперь переводится.
    check("price_snapshot — срез цен", pl is not None and "PLN" in pl, pl)

    # Мультидомен: vinted.de по ключевому слову
    de_client = await vinted.get_client("vinted.de")
    _, de_params = vinted.parse_search_url(vinted.build_search_url("schuhe", "vinted.de"))
    de_items = await de_client.get_items(de_params)
    check("vinted.de парсится по слову", de_items is not None and len(de_items) > 0,
          f"items={de_items if de_items is None else len(de_items)}")


if LIVE:
    asyncio.run(g_live())
else:
    print("  (пропущено: сеть, LIVE_TESTS=1 чтобы включить)")

# --------------------------------------------------------------------- ИТОГ
print(f"\n{'=' * 46}")
print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
if FAILS:
    print("Провалены:\n  - " + "\n  - ".join(FAILS))
print("=" * 46)
sys.exit(1 if FAIL else 0)
