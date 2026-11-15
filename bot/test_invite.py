"""Закрытый тест: инвайт-ключи, белый список, лист ожидания, антиперебор.

Запуск: ./.venv/bin/python test_invite.py  (временная БД, прод не трогает)
"""
import os
import sys
import tempfile

os.environ.setdefault("BOT_TOKEN", "123:dummy")
# В конфиге админов по умолчанию нет - тестам нужен хотя бы один.
os.environ.setdefault("ADMIN_IDS", "1001")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "invite_test.db")
os.environ["INVITE_ONLY"] = "1"
os.environ.pop("MASTER_KEY", None)  # проверяем дефолт конфига, а не окружение

import config  # noqa: E402
import db  # noqa: E402
import i18n  # noqa: E402
import plans  # noqa: E402

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


print("\n[A] Миграция и «старички»")
db.init_db()
db.activate_user(1001, "old_user")          # был в базе ДО включения режима
db.init_billing()                            # → init_invites: разовая миграция
check("старый пользователь в белом списке", db.is_whitelisted(1001))
db.activate_user(2001, "newbie")
check("новый пользователь НЕ в белом списке", not db.is_whitelisted(2001))
db.init_billing()
check("повторный init не даёт белый список новичку", not db.is_whitelisted(2001))
g = db.global_stats()
check("global_stats считает whitelisted/waitlist", g["whitelisted"] == 1 and g["waitlist"] == 0)

print("\n[B] Формат и нормализация ключа")
k = db.create_key(1, days=14, note="partner")
check("формат GRL-XXXX-XXXX", len(k) == 13 and k.startswith("GRL-") and k[8] == "-", k)
check("нет похожих символов 0/O/1/I/L", not any(c in "0O1IL" for c in k.replace("GRL-", "")))
check("normalize: как есть", db.normalize_key(k) == k)
check("normalize: строчные", db.normalize_key(k.lower()) == k)
check("normalize: без дефисов и с пробелами", db.normalize_key(" " + k.replace("-", "") + " ") == k)
check("normalize: мусор → None", db.normalize_key("hello world") is None)
check("normalize: короткий → None", db.normalize_key("GRL-ABCD") is None)
check("normalize: запрещённый символ → None", db.normalize_key("GRL-ABC0-DEFG") is None)
check("normalize: legacy VIN", db.normalize_key("vin-a1b2c3") == "VIN-A1B2C3")
check("normalize: ссылка Vinted не ключ", db.normalize_key("https://www.vinted.fr/catalog?x=1") is None)
row = db.get_key(k)
check("дни и метка сохранены", row["days"] == 14 and row["note"] == "partner")
ks = db.create_keys(1, 3, 7, "batch")
check("пачка из 3", len(ks) == 3 and len(set(ks)) == 3)
check("пачка ограничена сотней", len(db.create_keys(1, 500)) == 100)

print("\n[C] Активация: 1 ключ = 1 аккаунт")
check("неизвестный ключ", db.use_key("GRL-ZZZZ-ZZZZ", 2001) == "unknown")
check("ключ принят", db.use_key(k, 2001) == "ok")
check("владелец в белом списке", db.is_whitelisted(2001))
check("ключ привязан к аккаунту", db.get_user(2001)["invite_key"] == k)
db.activate_user(2002, "second")
check("тот же ключ второму — отказ", db.use_key(k, 2002) == "used")
check("второй не в белом списке", not db.is_whitelisted(2002))
check("повтор владельцем — тоже used (без второго триала)", db.use_key(k, 2001) == "used")
check("триал по ключу выдаётся", db.start_trial(2001, plans.PRO, 14))
plan, until = db.effective_plan(2001)
check("Pro на ~14 дней", plan == plans.PRO and 13 * 86400 < until - db._now() <= 14 * 86400)
check("второй триал не выдаётся", not db.start_trial(2001, plans.PRO, 14))

print("\n[D] Отзыв ключа")
check("отзыв несуществующего → None", db.revoke_key("GRL-ZZZZ-ZZZZ") is None)
res = db.revoke_key(k)
check("отзыв использованного возвращает владельца", res == {"used_by": 2001})
check("владелец потерял белый список", not db.is_whitelisted(2001))
check("отозванный ключ больше не принимается", db.use_key(k, 2002) == "revoked")
k2 = db.create_key(1)
db.revoke_key(k2)
check("отзыв свободного ключа: нельзя использовать", db.use_key(k2, 2002) == "revoked")
check("свободные в статистике без отозванных", db.global_stats()["keys_free"] == len([r for r in db.list_keys() if r["used_by"] is None and not r["revoked_at"]]) == 103)
free_after = [r for r in db.list_keys() if r["revoked_at"]]
check("отозванные видны в списке", len(free_after) == 2)

print("\n[E] Антиперебор")
db.activate_user(3001, "bruter")
for i in range(config.KEY_ATTEMPTS_PER_HOUR):
    db.record_key_attempt(3001, f"GRL-AAAA-AAA{i}", False)
check("N неудач за час посчитаны", db.failed_key_attempts(3001) == config.KEY_ATTEMPTS_PER_HOUR)
check("успешная попытка не считается неудачей", (db.record_key_attempt(3001, "GRL-X", True),
                                                   db.failed_key_attempts(3001))[1] == config.KEY_ATTEMPTS_PER_HOUR)
check("старые попытки вне окна", db.failed_key_attempts(3001, window_sec=0) == 0)
shared = db.create_key(1)
db.use_key(shared, 3001)
for u in (3002, 3003, 3004):
    db.activate_user(u, None)
    db.record_key_attempt(u, shared, db.use_key(shared, u) == "ok")
check("ключ, который пробовали 3 чужих — сигнал", db.key_attempt_users(shared) >= config.KEY_SHARE_ALERT_USERS)
check("все чужие получили used, никто не прошёл", not any(db.is_whitelisted(u) for u in (3002, 3003, 3004)))

print("\n[F] Лист ожидания")
db.activate_user(4001, "w1")
db.activate_user(4002, "w2")
db.activate_user(4003, "w3")
check("нет в очереди → None", db.waitlist_position(4001) is None)
check("первый = #1", db.join_waitlist(4001, "w1", "en", "reddit") == 1)
check("второй = #2", db.join_waitlist(4002, "w2", "fr") == 2)
check("третий = #3", db.join_waitlist(4003, "w3", "de") == 3)
check("повторный вход не двигает позицию", db.join_waitlist(4002, "w2", "fr") == 2)
check("count = 3", db.waitlist_count() == 3)
check("источник сохранён", db.list_waitlist()[0]["source"] == "reddit")
inv = db.invite_user(4002, admin_id=1, days=14, note="from-waitlist")
check("invite_user: ключ уже привязан", db.get_key(inv)["used_by"] == 4002)
check("invite_user: в белом списке", db.is_whitelisted(4002))
check("invite_user: ушёл из очереди", db.waitlist_position(4002) is None)
check("третий стал #2", db.waitlist_position(4003) == 2)
kk = db.create_key(1)
db.use_key(kk, 4003)
check("активация ключом тоже убирает из очереди", db.waitlist_position(4003) is None and db.waitlist_count() == 1)
check("remove_from_waitlist", db.remove_from_waitlist(4001) and db.waitlist_count() == 0)

print("\n[G] Тексты на 7 языках")
for lng in i18n.LANGS:
    for key in ("gate_text", "gate_btn_waitlist", "waitlist_joined", "waitlist_already",
                "key_ok", "key_used", "key_bad", "key_ratelimited", "invite_granted"):
        check(f"{lng}.{key} есть", key in i18n.STRINGS[lng])
    check(f"{lng}: gate_text рендерится", "GRL-XXXX-XXXX" in i18n.t(lng, "gate_text", days=14))
    check(f"{lng}: key_ok/invite_granted с датой", "23.09" in i18n.t(lng, "key_ok", days=14, date="23.09")
          and "23.09" in i18n.t(lng, "invite_granted", days=14, date="23.09"))

print("\n[G2] Секретов по умолчанию нет")
# Дефолт мастер-ключа в исходниках = Pro любому, кто прочитал репозиторий.
check("мастер-ключ без env выключен", config.MASTER_KEY == "")

print("\n[H] Логика доступа бота")
import bot  # noqa: E402
check("админ всегда с доступом", bot.has_access(next(iter(config.ADMIN_IDS))))
check("новичок без ключа — нет", not bot.has_access(2002))
check("после ключа — да", bot.has_access(4003))
text, kb = bot.gate_text(2002, "en")
check("gate: кнопка листа ожидания есть", any("wl_join" == b.callback_data
                                             for row in kb.inline_keyboard for b in row))
db.join_waitlist(2002, None, "en")
text, kb = bot.gate_text(2002, "en")
check("gate для стоящего в очереди: позиция и без кнопки", "#1" in text and not any(
    "wl_join" == b.callback_data for row in kb.inline_keyboard for b in row))
txt = bot.key_issued_text(["GRL-ABCD-EFGH"], 14, "partner")
check("текст выдачи ключа содержит ссылку", f"t.me/{config.BOT_USERNAME}?start=GRL-ABCD-EFGH" in txt)
config.INVITE_ONLY = False
check("INVITE_ONLY=0 — доступ всем", bot.has_access(2002))
config.INVITE_ONLY = True

print("\n[I] Посев ключей из окружения")
spec = "GRL-SEED-AAAA:14:partner, grl-seed-bbbb , GRL-SEED-AAAA:14:partner, мусор, GRL-SEED-CCCC:7"
check("посев: 3 новых, дубли и мусор пропущены", db.seed_keys(spec) == 3)
check("посев идемпотентен", db.seed_keys(spec) == 0)
r = db.get_key("GRL-SEED-AAAA")
check("посев: дни и метка", r["days"] == 14 and r["note"] == "partner")
check("посев: дефолтные дни", db.get_key("GRL-SEED-BBBB")["days"] == config.INVITE_TRIAL_DAYS)
check("посев: свои дни", db.get_key("GRL-SEED-CCCC")["days"] == 7)
check("посеянный ключ активируется", db.use_key("GRL-SEED-BBBB", 4001) == "ok")

print(f"\n{PASS} ✅  {FAIL} ❌")
if FAILS:
    print("Провалы:", *FAILS, sep="\n  - ")
sys.exit(1 if FAIL else 0)
