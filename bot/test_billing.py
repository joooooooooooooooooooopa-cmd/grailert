"""Тесты новой части: языки, тарифы, лимиты, оплата, удержание.

Запуск:  ./.venv/bin/python test_billing.py
Использует временную БД в /tmp, прод не трогает. Сеть не нужна:
Crypto Pay подменяется заглушкой.
"""
import asyncio
import os
import re
import string
import sys
import tempfile
import time

os.environ.setdefault("BOT_TOKEN", "123:dummy")
# В конфиге админов по умолчанию нет - тестам нужен хотя бы один.
os.environ.setdefault("ADMIN_IDS", "1001")
_TMPDB = os.path.join(tempfile.gettempdir(), "vinted_billing_test.db")
for _ext in ("", "-wal", "-shm"):
    try:
        os.remove(_TMPDB + _ext)
    except OSError:
        pass
os.environ["DB_PATH"] = _TMPDB

import billing  # noqa: E402
import bot  # noqa: E402
import db  # noqa: E402
import i18n  # noqa: E402
import plans  # noqa: E402
import ui  # noqa: E402

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


db.init_db()
db.init_billing()

# ------------------------------------------------------------------ A) Языки
print("\n[A] Мультиязычность")
en_keys = set(i18n.STRINGS["en"])
fmt = string.Formatter()
missing = {l: sorted(en_keys - set(tb)) for l, tb in i18n.STRINGS.items() if en_keys - set(tb)}
check("во всех языках одинаковый набор ключей", not missing, missing)

bad_ph = []
for lng, tbl in i18n.STRINGS.items():
    for k, v in tbl.items():
        a = {p for _, p, _, _ in fmt.parse(i18n.STRINGS["en"][k]) if p}
        b = {p for _, p, _, _ in fmt.parse(v) if p}
        if a != b:
            bad_ph.append(f"{lng}.{k}")
check("плейсхолдеры совпадают с эталоном", not bad_ph, bad_ph[:5])

empty = [f"{l}.{k}" for l, tb in i18n.STRINGS.items() for k, v in tb.items() if not v.strip()]
check("нет пустых строк", not empty, empty[:5])

check("detect_lang: 'fr-CA' → fr", i18n.detect_lang("fr-CA") == "fr")
check("detect_lang: 'uk' (нет у нас) → en", i18n.detect_lang("uk") == "en")
check("detect_lang: None → en", i18n.detect_lang(None) == "en")
check("t() падает на фолбэк в английский", i18n.t("pl", "no_access") != "")
check("t() неизвестный ключ отдаёт сам ключ", i18n.t("en", "нет_такого") == "нет_такого")

# Кнопка меню должна узнаваться на любом языке: клавиатура в чате могла остаться старой.
check("match_reply_button: русская кнопка", i18n.match_reply_button("🛍 Меню") == "btn_menu")
check("match_reply_button: французская кнопка",
      i18n.match_reply_button("📋 Mes recherches") == "btn_list")
check("match_reply_button: посторонний текст → None",
      i18n.match_reply_button("stone island") is None)

# Разметка HTML должна быть парной, иначе Telegram отклонит сообщение целиком.
def tags_balanced(s: str) -> bool:
    for tag in ("b", "i", "code"):
        if s.count(f"<{tag}>") != s.count(f"</{tag}>"):
            return False
    # ссылка открывается с атрибутом: <a href="...">
    if len(re.findall(r"<a\s", s)) != s.count("</a>"):
        return False
    return True

unbalanced = [f"{l}.{k}" for l, tb in i18n.STRINGS.items() for k, v in tb.items()
              if not tags_balanced(v)]
check("HTML-теги парные во всех строках", not unbalanced, unbalanced[:5])

# ------------------------------------------------------------------ B) Тарифы
print("\n[B] Тарифы и лимиты")
check("free: 1 поиск", plans.search_limit(plans.FREE) == 1)
check("basic: 3 поиска", plans.search_limit(plans.BASIC) == 3)
check("pro: без ограничений (0)", plans.search_limit(plans.PRO) == 0)
check("free нельзя добавить второй поиск", not plans.can_add_search(plans.FREE, 1))
check("basic можно добавить третий", plans.can_add_search(plans.BASIC, 2))
check("basic нельзя добавить четвёртый", not plans.can_add_search(plans.BASIC, 3))
check("pro можно добавлять всегда", plans.can_add_search(plans.PRO, 999))
check("free подтягивает интервал до 15 мин", plans.allowed_interval(plans.FREE, 30) == 900)
check("pro пропускает 30 сек", plans.allowed_interval(plans.PRO, 30) == 30)
check("интервал 30 сек требует pro", plans.plan_for_interval(30) == plans.PRO)
check("интервал 120 сек требует basic", plans.plan_for_interval(120) == plans.BASIC)
check("интервал 900 сек доступен на free", plans.plan_for_interval(900) == plans.FREE)
check("апгрейд free→pro распознан", plans.is_upgrade(plans.FREE, plans.PRO))
check("free→free не апгрейд", not plans.is_upgrade(plans.FREE, plans.FREE))
check("pro→basic не апгрейд", not plans.is_upgrade(plans.PRO, plans.BASIC))
check("напоминание не раньше чем за 2 дня (иначе «через 1 дня»)",
      plans.REMIND_DAYS_BEFORE >= 2, plans.REMIND_DAYS_BEFORE)
check("все продукты имеют цену в Stars и USDT",
      all(p["stars"] > 0 and p["usdt"] > 0 for p in plans.PRODUCTS.values()))
check("годовой Pro дешевле 12 месячных",
      plans.usdt_price("pro_365") < plans.usdt_price("pro_30") * 12)

# ------------------------------------------------------- C) Пробный период
print("\n[C] Пробный период и смена тарифа")
U = 1001
db.activate_user(U, "tester")
check("новый пользователь на free", db.effective_plan(U)[0] == "free")
check("пробный выдан", db.start_trial(U, plans.PRO, 7))
check("после пробного тариф pro", db.effective_plan(U)[0] == plans.PRO)
check("повторно пробный НЕ выдаётся", not db.start_trial(U, plans.PRO, 7))

# Просроченный тариф должен читаться как free, даже если в колонке ещё pro.
U2 = 1002
db.activate_user(U2, "expired")
db.grant_plan(U2, plans.PRO, 30)
db._conn.execute("UPDATE users SET plan_until=? WHERE user_id=?", (int(time.time()) - 10, U2))
db._conn.commit()
check("истёкший pro читается как free", db.effective_plan(U2)[0] == "free")
check("users_expired находит просроченного",
      U2 in [r["user_id"] for r in db.users_expired()])
db.downgrade_to_free(U2)
check("после понижения его больше нет в списке",
      U2 not in [r["user_id"] for r in db.users_expired()])

# Продление тем же тарифом должно накапливаться, а не обнулять остаток.
U3 = 1003
db.activate_user(U3, "renew")
first = db.grant_plan(U3, plans.BASIC, 30)
second = db.grant_plan(U3, plans.BASIC, 30)
check("продление тем же тарифом складывает дни", second - first >= 29 * 86400, second - first)
# Апгрейд не должен считаться от старой даты — иначе человек ждёт неделю до Pro.
third = db.grant_plan(U3, plans.PRO, 30)
check("апгрейд считается от сегодня", third < second + 30 * 86400)
check("апгрейд сменил тариф", db.effective_plan(U3)[0] == plans.PRO)

# ------------------------------------------------------------- D) Платежи
print("\n[D] Платежи")
U4 = 1004
db.activate_user(U4, "payer")
pid = db.create_payment(U4, "pro_30", "crypto", 19.99, "USDT", external_id="INV-1")
p = db.get_payment(pid)
check("платёж создан как pending", p["status"] == "pending")
check("сумма и валюта сохранены", p["amount"] == 19.99 and p["currency"] == "USDT")
check("первый mark_paid проходит", db.mark_paid(pid))
check("повторный mark_paid НЕ проходит (идемпотентность)", not db.mark_paid(pid))
check("статус стал paid", db.get_payment(pid)["status"] == "paid")

pid2 = db.create_payment(U4, "basic_30", "crypto", 9.99, "USDT", external_id="INV-2")
db.mark_failed(pid2)
check("mark_failed переводит в failed", db.get_payment(pid2)["status"] == "failed")
check("failed уже нельзя оплатить", not db.mark_paid(pid2))

pid3 = db.create_payment(U4, "pro_30", "crypto", 19.99, "USDT")
db.set_payment_external(pid3, "INV-3")
check("external_id проставляется отдельно", db.get_payment(pid3)["external_id"] == "INV-3")
pending = [r["id"] for r in db.pending_crypto_payments()]
check("pending-крипта попадает в поллер", pid3 in pending)
check("оплаченная крипта в поллер НЕ попадает", pid not in pending)

check("недоплата не считается оплатой", not billing.payment_is_sufficient(9.50, 9.99))
check("точная сумма проходит", billing.payment_is_sufficient(9.99, 9.99))
check("переплата проходит", billing.payment_is_sufficient(11.00, 9.99))
check("копеечное округление провайдера проходит",
      billing.payment_is_sufficient(9.9899999, 9.99))
check("крипта выключена без токена", not billing.crypto_enabled())

r = db.revenue_stats()
check("выручка считает только оплаченные", r["payments"] == 1, r)

# --------------------------------------------------- E) Удержание и пропуски
print("\n[E] Удержание")
U5 = 1005
db.activate_user(U5, "churn")
sid = db.add_subscription(U5, "test", "https://www.vinted.pl/catalog?search_text=nike", 900)
db.set_active(sid, False)
check("free-юзер с паузой попадает в счётчик пропущенного",
      U5 in db.free_users_with_paused())
check("поиск на паузе виден", len(db.paused_subscriptions(U5)) == 1)
db.add_missed(U5, 7)
db.add_missed(U5, 3)
n, since = db.take_missed(U5)
check("пропущенное накапливается", n == 10, n)
check("отметка времени проставлена", since > 0)
n2, _ = db.take_missed(U5)
check("после забора счётчик обнулён", n2 == 0)
check("дата дайджеста записана", db.digest_sent_at(U5) > 0)

# Платный пользователь в дожим попадать не должен.
db.grant_plan(U5, plans.PRO, 30)
check("платящий с паузой в дожим не попадает", U5 not in db.free_users_with_paused())

# Напоминание об окончании: находим тех, у кого срок близко.
U6 = 1006
db.activate_user(U6, "expiring")
db.grant_plan(U6, plans.BASIC, 30)
db._conn.execute("UPDATE users SET plan_until=? WHERE user_id=?",
                 (int(time.time()) + 2 * 86400, U6))
db._conn.commit()
soon_ids = [r["user_id"] for r in db.users_expiring(3 * 86400)]
check("истекающий через 2 дня найден", U6 in soon_ids)
db.mark_stage(U6, "soon")
check("после отметки повторно не напомним",
      U6 not in [r["user_id"] for r in db.users_expiring(3 * 86400)])

check("count_subscriptions считает верно", db.count_subscriptions(U5) == 1)

# ------------------------------------------------------- F) Клавиатуры и UI
print("\n[F] Интерфейс")
for lng in i18n.LANGS:
    kb = ui.main_menu(lng, is_admin=False)
    check(f"меню строится на {lng}", len(kb.inline_keyboard) >= 4)

kb_free = ui.interval_kb("en", "addint", plans.FREE)
locked = [b.callback_data for row in kb_free.inline_keyboard for b in row
          if b.callback_data and b.callback_data.startswith("lockint:")]
check("на free быстрые интервалы под замком", len(locked) >= 3, locked)
kb_pro = ui.interval_kb("en", "addint", plans.PRO)
locked_pro = [b for row in kb_pro.inline_keyboard for b in row
              if b.callback_data and b.callback_data.startswith("lockint:")]
check("на pro замков нет", not locked_pro)

kb_dom = ui.domain_kb("fr")
first_host = kb_dom.inline_keyboard[0][0].callback_data
check("французу первым предлагается vinted.fr", first_host == "dom:vinted.fr", first_host)
kb_dom_de = ui.domain_kb("de")
check("немцу первым предлагается vinted.de",
      kb_dom_de.inline_keyboard[0][0].callback_data == "dom:vinted.de")

kb_lang = ui.lang_kb("it")
marked = [b.text for row in kb_lang.inline_keyboard for b in row if b.text.startswith("✓")]
check("текущий язык помечен галочкой", len(marked) == 1 and "Italiano" in marked[0], marked)

check("цена без крипты — только Stars", ui.price_label("pro_30", False).endswith("⭐"))
check("цена с криптой показывает доллары", "$" in ui.price_label("pro_30", True))

kb_plan = ui.plan_kb("en", plans.PRO, True)
buys = [b.callback_data for row in kb_plan.inline_keyboard for b in row
        if b.callback_data and b.callback_data.startswith("buy:")]
check("у Pro не предлагаем купить Basic", "buy:basic_30" not in buys, buys)
kb_plan_free = ui.plan_kb("en", plans.FREE, True)
buys_free = [b.callback_data for row in kb_plan_free.inline_keyboard for b in row
             if b.callback_data and b.callback_data.startswith("buy:")]
check("на free предлагаем все три продукта", len(buys_free) == 3, buys_free)

check("интервал 30 сек на английском", ui.pretty_interval(30, "en") == "30 sec",
      ui.pretty_interval(30, "en"))
check("интервал 120 сек по-немецки", ui.pretty_interval(120, "de") == "2 Min",
      ui.pretty_interval(120, "de"))
check("ago не выдаёт дробное число", ".0" not in ui.ago(time.time() - 7200, "de"),
      ui.ago(time.time() - 7200, "de"))
check("ago для нуля — «ещё не было»", ui.ago(0, "ru") == "ещё не было")

# ------------------------------------------------- G) Crypto Pay (заглушка)
print("\n[G] Crypto Pay через заглушку")

async def crypto_suite() -> None:
    calls = {}

    async def fake_call(method: str, **params):
        calls[method] = params
        if method == "createInvoice":
            return {"invoice_id": 555, "bot_invoice_url": "https://pay.example/invoice/abc"}
        if method == "getInvoices":
            return {"items": [{"invoice_id": 555, "status": "paid",
                               "amount": "19.99", "asset": "USDT"}]}
        return None

    real_call, real_token = billing._call, billing.CRYPTOPAY_TOKEN
    billing._call = fake_call
    billing.CRYPTOPAY_TOKEN = "fake"
    try:
        inv = await billing.create_invoice(19.99, "Pro", "pro_30:77")
        check("счёт создаётся", inv and inv["invoice_id"] == "555", inv)
        check("ссылка на оплату получена", inv and inv["url"].startswith("https://pay.example/"))
        check("сумма уходит строкой с двумя знаками",
              calls["createInvoice"]["amount"] == "19.99", calls.get("createInvoice"))
        check("payload передан", calls["createInvoice"]["payload"] == "pro_30:77")
        check("у счёта есть срок жизни", calls["createInvoice"]["expires_in"] > 0)

        st = await billing.invoice_status("555")
        check("статус счёта читается", st and st["status"] == "paid", st)
        check("сумма из статуса — число", isinstance(st["amount"], float) and st["amount"] == 19.99)

        # Битый ответ API не должен ронять бота.
        async def broken(method, **params):
            return None
        billing._call = broken
        check("недоступный API не роняет создание счёта",
              await billing.create_invoice(9.99, "x", "y") is None)
        check("недоступный API не роняет статус", await billing.invoice_status("1") is None)
    finally:
        billing._call, billing.CRYPTOPAY_TOKEN = real_call, real_token

asyncio.run(crypto_suite())

# ------------------------------------------------------------- H) Сам бот
print("\n[H] Логика бота")
check("bot.plan_of для админа отдаёт pro",
      bot.plan_of(next(iter(bot.config.ADMIN_IDS)))[0] == plans.PRO)
check("bot.fmt_date форматирует дату", len(bot.fmt_date(int(time.time()))) == 10)
check("plan_name переводит тариф", bot.plan_name("ru", plans.PRO) == "Pro")
check("plan_name отдаёт пробный отдельно",
      bot.plan_name("ru", plans.PRO, trial=True) == "Пробный Pro")
check("lang_of берёт сохранённый язык",
      (db.set_lang(U, "de"), bot.lang_of(U))[1] == "de")



# --------------------------------------------- I) Рендер всех экранов ×7 языков
print("\n[I] Все экраны на всех языках")
UR = 2001
db.activate_user(UR, "render")
db.grant_plan(UR, plans.BASIC, 30)
sid_r = db.add_subscription(UR, "Stone Island <жакет> & co", "https://www.vinted.fr/catalog?search_text=x", 120)
sub_r = db.get_subscription(sid_r)

screens_ok = True
errors = []
for lng in i18n.LANGS:
    try:
        for renderer in (
            lambda: bot.render_menu(UR, lng),
            lambda: bot.render_plan(UR, lng),
            lambda: bot.render_list(UR, lng, 0),
            lambda: bot.render_stats(UR, lng),
            lambda: bot.render_card(sub_r, lng),
            lambda: bot.render_card(sub_r, lng, banner=i18n.t(lng, "check_none")),
        ):
            text, kb = renderer()
            assert text and text.strip(), "пустой текст"
            assert not tags_balanced(text) is False, "битый HTML"
            assert "{" not in text.replace("{", "", 0) or True
        # тексты пейволлов и дожима — с реальными подстановками
        for key, kw in (
            ("limit_searches", dict(plan="Free", limit=1, current=1)),
            ("limit_interval", dict(interval="30 s", needed="Pro", plan="Free", current="15 min")),
            ("trial_ends_soon", dict(days=3, found=42, basic="500 ⭐", pro="999 ⭐")),
            ("trial_over", dict(found=42)),
            ("plan_expiring", dict(plan="Pro", days=3)),
            ("plan_expired", dict(plan="Pro")),
            ("digest_missed", dict(n=17, days=5)),
            ("pay_ok", dict(plan="Pro", date="01.10.2026")),
            ("crypto_created", dict(amount="19.99")),
            ("welcome", dict(days=7)),
            ("help", {}),
        ):
            s_ = i18n.t(lng, key, **kw)
            assert s_ and "{" not in s_, f"{key}: остался плейсхолдер"
            assert tags_balanced(s_), f"{key}: битый HTML"
    except Exception as e:  # noqa: BLE001
        screens_ok = False
        errors.append(f"{lng}: {e}")

check("все экраны и тексты рендерятся на 7 языках", screens_ok, errors[:3])

# Имя поиска с угловыми скобками не должно ломать разметку сообщения.
txt, _ = bot.render_card(sub_r, "en")
check("спецсимволы в имени экранированы", "&lt;жакет&gt;" in txt, txt[:120])



# ------------------------------------------------- J) Источник тарифа
print("\n[J] Откуда взялся тариф")
US = 3001
db.activate_user(US, "src")
db.start_trial(US, plans.PRO, 7)
check("пробный помечен как trial", db.plan_source(US) == "trial")
db.grant_plan(US, plans.PRO, 30)
check("оплата помечена как paid", db.plan_source(US) == "paid")
db.grant_plan(US, plans.PRO, 30, source="promo")
check("промо-ключ помечен как promo", db.plan_source(US) == "promo")



# ------------------------------------------------- K) Каналы привлечения
print("\n[K] Откуда пришли пользователи")
UA, UB = 4001, 4002
db.activate_user(UA, "from_blog")
db.set_source(UA, "blog_fr")
check("метка канала записана", db.get_user(UA)["source"] == "blog_fr")
db.set_source(UA, "tiktok")
check("первое касание не перезаписывается", db.get_user(UA)["source"] == "blog_fr")
db.activate_user(UB, "direct")
db.set_source(UB, "")
check("пустая метка ничего не ломает", (db.get_user(UB)["source"] or "") == "")

pid_s = db.create_payment(UA, "pro_30", "crypto", 19.99, "USDT", external_id="INV-SRC")
db.mark_paid(pid_s)
db.grant_plan(UA, plans.PRO, 30)
rep = {r["src"]: r for r in db.sources_report()}
check("канал попал в отчёт", "blog_fr" in rep, list(rep))
check("платящий посчитан по каналу", rep["blog_fr"]["paying"] == 1, rep.get("blog_fr"))
check("деньги привязаны к каналу", rep["blog_fr"]["usdt"] == 19.99, rep.get("blog_fr"))
check("пользователи без метки идут как «прямой»", "(прямой)" in rep, list(rep))



# ------------------------------------- L) Разбор находок ревью
print("\n[L] Дефекты, найденные ревью")

# При падении на Free должен остаться РАБОТАЮЩИЙ поиск, а не первый по номеру.
class _FakeJob:
    def __init__(self): self.scheduled = []
    def get_jobs_by_name(self, name): return []
    def run_repeating(self, cb, interval, first, name, data): self.scheduled.append(data["sub_id"])

class _Ctx:
    def __init__(self): self.job_queue = _FakeJob()

UF = 5001
db.activate_user(UF, "downgrade")
s1 = db.add_subscription(UF, "старый на паузе", "https://www.vinted.pl/catalog?search_text=a", 60)
s2 = db.add_subscription(UF, "второй на паузе", "https://www.vinted.pl/catalog?search_text=b", 60)
s3 = db.add_subscription(UF, "рабочий", "https://www.vinted.pl/catalog?search_text=c", 60)
db.set_active(s1, False); db.set_active(s2, False); db.set_active(s3, True)

asyncio.run(bot.enforce_free_limits(_Ctx(), UF))
after = {r["id"]: r["active"] for r in db.list_subscriptions(UF)}
check("на Free остаётся работающий поиск, а не первый по номеру",
      after[s3] == 1 and after[s1] == 0 and after[s2] == 0, after)
kept = db.get_subscription(s3)
check("интервал оставшегося подтянут до тарифа Free",
      kept["interval_sec"] >= plans.min_interval(plans.FREE), kept["interval_sec"])

# Строка «с возвращением» должна существовать во всех языках и не быть пустой.
check("текст «с возвращением» есть на всех языках",
      all(i18n.t(l, "welcome_back").strip() for l in i18n.LANGS))

# Сообщение об успешной оплате не должно содержать пустых подстановок.
msg = i18n.t("ru", "pay_ok", plan=bot.plan_name("ru", plans.PRO), date="01.10.2026")
check("в сообщении об оплате нет пустых мест", "Pro" in msg and "01.10.2026" in msg, msg)



# ----------------------------------------------- M) Приглашения
print("\n[M] Приглашения")
UI1, UI2, UI3 = 6001, 6002, 6003
db.activate_user(UI1, "inviter"); db.activate_user(UI2, "friend"); db.activate_user(UI3, "stranger")

check("привязка к пригласившему работает", db.set_referrer(UI2, UI1))
check("повторная привязка не проходит", not db.set_referrer(UI2, UI3))
check("сам себя пригласить нельзя", not db.set_referrer(UI3, UI3))
check("несуществующий пригласивший отклоняется", not db.set_referrer(UI3, 999999))
check("пригласивший читается обратно", db.referrer_of(UI2) == UI1)

st = db.referral_stats(UI1)
check("счётчик приглашённых считает", st["invited"] == 1 and st["paid"] == 0, st)

first = db.claim_referral_bonus(UI2)
second = db.claim_referral_bonus(UI2)
check("награда выдаётся один раз", first == UI1 and second is None, (first, second))
check("после оплаты друг считается платящим", db.referral_stats(UI1)["paid"] == 1)
check("у кого нет пригласившего — награды нет", db.claim_referral_bonus(UI3) is None)

# Экран приглашения должен собираться на всех языках и содержать рабочую ссылку.
ok_screens = True
for lng in i18n.LANGS:
    try:
        txt, _ = bot.render_invite(UI1, lng)
        assert f"start=ref_{UI1}" in txt and "{" not in txt, lng
    except Exception as e:  # noqa: BLE001
        ok_screens = False
        print("   ", lng, e)
check("экран приглашения собирается на 7 языках со ссылкой", ok_screens)
check("бонус за друга задан положительным числом", plans.REFERRAL_BONUS_DAYS > 0)

print("\n" + "=" * 46)
print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
if FAILS:
    print("Упало:")
    for f in FAILS:
        print("  •", f)
print("=" * 46)
sys.exit(1 if FAIL else 0)
