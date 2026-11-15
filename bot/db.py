"""Слой SQLite: пользователи, ключи доступа, подписки, виденные объявления, статистика."""
from __future__ import annotations

import secrets
import sqlite3
import threading
import time

import config

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def init_db() -> None:
    global _conn
    _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            activated_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS access_keys (
            key        TEXT PRIMARY KEY,
            created_by INTEGER,
            created_at INTEGER,
            used_by    INTEGER,
            used_at    INTEGER
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         TEXT,
            url          TEXT NOT NULL,
            interval_sec INTEGER NOT NULL,
            active       INTEGER NOT NULL DEFAULT 1,
            kw_include   TEXT DEFAULT '',
            kw_exclude   TEXT DEFAULT '',
            last_check   INTEGER DEFAULT 0,
            last_status  TEXT DEFAULT '',
            created_at   INTEGER
        );

        CREATE TABLE IF NOT EXISTS seen_items (
            subscription_id INTEGER NOT NULL,
            item_id         TEXT NOT NULL,
            seen_at         INTEGER,
            PRIMARY KEY (subscription_id, item_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            subscription_id INTEGER NOT NULL,
            item_id         TEXT NOT NULL,
            notified_at     INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_notif_sub ON notifications(subscription_id);
        """
    )
    _conn.commit()
    _migrate()


def _migrate() -> None:
    """Доводит старую схему до актуальной (ALTER TABLE для недостающих колонок)."""
    cols = {r["name"] for r in _conn.execute("PRAGMA table_info(subscriptions)")}
    for col, ddl in (
        ("kw_include", "ALTER TABLE subscriptions ADD COLUMN kw_include TEXT DEFAULT ''"),
        ("kw_exclude", "ALTER TABLE subscriptions ADD COLUMN kw_exclude TEXT DEFAULT ''"),
        ("last_check", "ALTER TABLE subscriptions ADD COLUMN last_check INTEGER DEFAULT 0"),
        ("last_status", "ALTER TABLE subscriptions ADD COLUMN last_status TEXT DEFAULT ''"),
    ):
        if col not in cols:
            _conn.execute(ddl)
    _conn.commit()


def _now() -> int:
    return int(time.time())


def _midnight() -> int:
    t = time.localtime()
    return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1)))


# --- Пользователи / доступ ---------------------------------------------------

def activate_user(user_id: int, username: str | None) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO users (user_id, username, activated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
            (user_id, username, _now()),
        )
        _conn.commit()


def is_activated(user_id: int) -> bool:
    return _conn.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone() is not None


def list_users() -> list[sqlite3.Row]:
    return _conn.execute("SELECT * FROM users ORDER BY activated_at DESC").fetchall()


def user_ids() -> list[int]:
    return [r["user_id"] for r in _conn.execute("SELECT user_id FROM users")]


# --- Ключи доступа (инвайты) --------------------------------------------------
#
# Закрытый тест (09.09.2026): доступ только по ключу GRL-XXXX-XXXX.
# Ключ одноразовый: первый, кто его прислал, становится владельцем (1 ключ =
# 1 аккаунт), остальным — отказ. Отзыв ключа снимает белый список с владельца.
# Алфавит без похожих символов (0/O, 1/I/L), чтобы ключ читался с экрана.

KEY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
KEY_PREFIX = "GRL"


def _gen_key() -> str:
    body = "".join(secrets.choice(KEY_ALPHABET) for _ in range(8))
    return f"{KEY_PREFIX}-{body[:4]}-{body[4:]}"


def normalize_key(text: str) -> str | None:
    """Приводит ввод к каноническому виду GRL-XXXX-XXXX (или VIN-XXXXXX для
    старых ключей). Терпит пробелы, регистр и пропущенные дефисы.
    Возвращает None, если текст на ключ не похож."""
    raw = "".join(ch for ch in (text or "").upper() if ch.isalnum())
    if raw.startswith(KEY_PREFIX) and len(raw) == len(KEY_PREFIX) + 8:
        body = raw[len(KEY_PREFIX):]
        if all(ch in KEY_ALPHABET for ch in body):
            return f"{KEY_PREFIX}-{body[:4]}-{body[4:]}"
        return None
    if raw.startswith("VIN") and len(raw) == 9:
        return "VIN-" + raw[3:]
    return None


def create_key(created_by: int, days: int | None = None, note: str = "") -> str:
    days = config.INVITE_TRIAL_DAYS if days is None else int(days)
    with _lock:
        while True:
            key = _gen_key()
            if _conn.execute("SELECT 1 FROM access_keys WHERE key=?", (key,)).fetchone() is None:
                break
        _conn.execute(
            "INSERT INTO access_keys (key, created_by, created_at, days, note) VALUES (?, ?, ?, ?, ?)",
            (key, created_by, _now(), days, note or None),
        )
        _conn.commit()
    return key


def seed_keys(spec: str, created_by: int = 0) -> int:
    """Заводит ключи из строки «KEY:days:note,KEY,…» (см. config.INVITE_SEED_KEYS).
    Идемпотентно: существующие ключи не трогает. Возвращает число новых."""
    added = 0
    with _lock:
        for chunk in (spec or "").split(","):
            parts = chunk.strip().split(":")
            key = normalize_key(parts[0]) if parts and parts[0] else None
            if not key:
                continue
            days = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else config.INVITE_TRIAL_DAYS
            note = parts[2].strip() if len(parts) > 2 else ""
            cur = _conn.execute(
                "INSERT OR IGNORE INTO access_keys (key, created_by, created_at, days, note) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, created_by, _now(), days, note or None),
            )
            added += cur.rowcount
        _conn.commit()
    return added


def create_keys(created_by: int, n: int, days: int | None = None, note: str = "") -> list[str]:
    return [create_key(created_by, days, note) for _ in range(max(1, min(int(n), 100)))]


def get_key(key: str) -> sqlite3.Row | None:
    return _conn.execute("SELECT * FROM access_keys WHERE key=?", (key,)).fetchone()


def use_key(key: str, user_id: int) -> str:
    """Активирует ключ пользователем. Возвращает статус:
    ok — ключ принят, пользователь в белом списке;
    used — ключ уже занят другим (или этим же) аккаунтом;
    revoked — ключ отозван; unknown — такого ключа нет."""
    with _lock:
        row = _conn.execute("SELECT * FROM access_keys WHERE key=?", (key,)).fetchone()
        if row is None:
            return "unknown"
        if row["revoked_at"]:
            return "revoked"
        cur = _conn.execute(
            "UPDATE access_keys SET used_by=?, used_at=? WHERE key=? AND used_by IS NULL",
            (user_id, _now(), key),
        )
        if cur.rowcount == 0:
            _conn.commit()
            return "used"
        _conn.execute(
            "UPDATE users SET whitelisted=1, invite_key=? WHERE user_id=?", (key, user_id)
        )
        _conn.execute("DELETE FROM waitlist WHERE user_id=?", (user_id,))
        _conn.commit()
        return "ok"


def revoke_key(key: str) -> dict | None:
    """Отзывает ключ. Если он уже был использован — владелец теряет белый список
    (тариф не трогаем: оплаченное остаётся оплаченным, но в бот его не пустит).
    Возвращает {'used_by': id|None} или None, если ключа нет."""
    with _lock:
        row = _conn.execute("SELECT * FROM access_keys WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        _conn.execute(
            "UPDATE access_keys SET revoked_at=? WHERE key=? AND revoked_at IS NULL", (_now(), key)
        )
        if row["used_by"]:
            _conn.execute(
                "UPDATE users SET whitelisted=0 WHERE user_id=? AND invite_key=?",
                (row["used_by"], key),
            )
        _conn.commit()
        return {"used_by": row["used_by"]}


def list_keys() -> list[sqlite3.Row]:
    return _conn.execute("SELECT * FROM access_keys ORDER BY created_at DESC").fetchall()


def is_whitelisted(user_id: int) -> bool:
    row = _conn.execute("SELECT whitelisted FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["whitelisted"])


def whitelist_user(user_id: int, key: str | None = None) -> None:
    with _lock:
        _conn.execute(
            "UPDATE users SET whitelisted=1, invite_key=COALESCE(?, invite_key) WHERE user_id=?",
            (key, user_id),
        )
        _conn.execute("DELETE FROM waitlist WHERE user_id=?", (user_id,))
        _conn.commit()


def invite_user(user_id: int, admin_id: int, days: int | None = None, note: str = "") -> str:
    """Админ выдаёт доступ напрямую (из листа ожидания): ключ создаётся уже
    привязанным к человеку, тот попадает в белый список и уходит из очереди."""
    key = create_key(admin_id, days, note)
    with _lock:
        _conn.execute(
            "UPDATE access_keys SET used_by=?, used_at=? WHERE key=?", (user_id, _now(), key)
        )
        _conn.commit()
    whitelist_user(user_id, key)
    return key


# Попытки ввода ключа: антиперебор (N в час на человека) и сигнал «ключ гуляет».

def record_key_attempt(user_id: int, key: str, ok: bool) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO key_attempts (user_id, key, ok, ts) VALUES (?, ?, ?, ?)",
            (user_id, key, 1 if ok else 0, _now()),
        )
        _conn.commit()


def failed_key_attempts(user_id: int, window_sec: int = 3600) -> int:
    return _conn.execute(
        "SELECT COUNT(*) c FROM key_attempts WHERE user_id=? AND ok=0 AND ts>?",
        (user_id, _now() - window_sec),
    ).fetchone()["c"]


def key_attempt_users(key: str, window_sec: int = 86400) -> int:
    """Сколько разных людей пробовали этот ключ за окно (включая владельца)."""
    return _conn.execute(
        "SELECT COUNT(DISTINCT user_id) c FROM key_attempts WHERE key=? AND ts>?",
        (key, _now() - window_sec),
    ).fetchone()["c"]


# --- Лист ожидания -----------------------------------------------------------

def join_waitlist(user_id: int, username: str | None, lang: str, source: str | None = None) -> int:
    """Ставит в очередь (повторный вызов не двигает позицию). Возвращает позицию."""
    with _lock:
        _conn.execute(
            "INSERT OR IGNORE INTO waitlist (user_id, username, lang, joined_at, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, username, lang, _now(), source),
        )
        _conn.commit()
    return waitlist_position(user_id) or 0


def waitlist_position(user_id: int) -> int | None:
    row = _conn.execute("SELECT joined_at FROM waitlist WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        return None
    ahead = _conn.execute(
        "SELECT COUNT(*) c FROM waitlist WHERE joined_at<? OR (joined_at=? AND user_id<?)",
        (row["joined_at"], row["joined_at"], user_id),
    ).fetchone()["c"]
    return ahead + 1


def waitlist_count() -> int:
    return _conn.execute("SELECT COUNT(*) c FROM waitlist").fetchone()["c"]


def list_waitlist(limit: int = 30) -> list[sqlite3.Row]:
    return _conn.execute(
        "SELECT * FROM waitlist ORDER BY joined_at, user_id LIMIT ?", (limit,)
    ).fetchall()


def remove_from_waitlist(user_id: int) -> bool:
    with _lock:
        cur = _conn.execute("DELETE FROM waitlist WHERE user_id=?", (user_id,))
        _conn.commit()
        return cur.rowcount > 0


def init_invites() -> None:
    """Колонки и таблицы закрытого теста. Идемпотентно.

    🔑 Разовая миграция: все, кто уже был в базе на момент включения режима,
    попадают в белый список — иначе действующие пользователи (в том числе
    платящие) проснулись бы перед закрытой дверью."""
    with _lock:
        for col, ddl in (
            ("whitelisted", "INTEGER DEFAULT 0"),
            ("invite_key", "TEXT"),
        ):
            try:
                _conn.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError:
                pass
        for col, ddl in (
            ("days", "INTEGER"),
            ("note", "TEXT"),
            ("revoked_at", "INTEGER"),
        ):
            try:
                _conn.execute(f"ALTER TABLE access_keys ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError:
                pass
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                lang      TEXT,
                joined_at INTEGER,
                source    TEXT
            );
            CREATE TABLE IF NOT EXISTS key_attempts (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                key     TEXT,
                ok      INTEGER,
                ts      INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_key_attempts_user ON key_attempts(user_id, ts);
            CREATE INDEX IF NOT EXISTS idx_key_attempts_key ON key_attempts(key, ts);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        done = _conn.execute(
            "SELECT value FROM meta WHERE key='invite_grandfathered'"
        ).fetchone()
        if done is None:
            cur = _conn.execute("UPDATE users SET whitelisted=1")
            _conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('invite_grandfathered', ?)",
                (f"{_now()}:{cur.rowcount}",),
            )
        _conn.commit()


# --- Подписки ----------------------------------------------------------------

def add_subscription(user_id: int, name: str, url: str, interval_sec: int) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO subscriptions (user_id, name, url, interval_sec, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (user_id, name, url, interval_sec, _now()),
        )
        _conn.commit()
        return cur.lastrowid


def get_subscription(sub_id: int) -> sqlite3.Row | None:
    return _conn.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,)).fetchone()


def list_subscriptions(user_id: int) -> list[sqlite3.Row]:
    return _conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=? ORDER BY id", (user_id,)
    ).fetchall()


def all_active_subscriptions() -> list[sqlite3.Row]:
    return _conn.execute("SELECT * FROM subscriptions WHERE active=1 ORDER BY id").fetchall()


def set_active(sub_id: int, active: bool) -> None:
    with _lock:
        _conn.execute("UPDATE subscriptions SET active=? WHERE id=?", (1 if active else 0, sub_id))
        _conn.commit()


def set_active_all(user_id: int, active: bool) -> list[int]:
    with _lock:
        ids = [
            r["id"]
            for r in _conn.execute(
                "SELECT id FROM subscriptions WHERE user_id=? AND active=?",
                (user_id, 0 if active else 1),
            )
        ]
        _conn.execute(
            "UPDATE subscriptions SET active=? WHERE user_id=?", (1 if active else 0, user_id)
        )
        _conn.commit()
        return ids


def set_interval(sub_id: int, interval_sec: int) -> None:
    with _lock:
        _conn.execute("UPDATE subscriptions SET interval_sec=? WHERE id=?", (interval_sec, sub_id))
        _conn.commit()


def set_name(sub_id: int, name: str) -> None:
    with _lock:
        _conn.execute("UPDATE subscriptions SET name=? WHERE id=?", (name, sub_id))
        _conn.commit()


def set_url(sub_id: int, url: str) -> None:
    with _lock:
        _conn.execute("UPDATE subscriptions SET url=? WHERE id=?", (url, sub_id))
        _conn.commit()


def set_keywords(sub_id: int, include: str | None = None, exclude: str | None = None) -> None:
    with _lock:
        if include is not None:
            _conn.execute("UPDATE subscriptions SET kw_include=? WHERE id=?", (include, sub_id))
        if exclude is not None:
            _conn.execute("UPDATE subscriptions SET kw_exclude=? WHERE id=?", (exclude, sub_id))
        _conn.commit()


def record_check(sub_id: int, status: str) -> None:
    with _lock:
        _conn.execute(
            "UPDATE subscriptions SET last_check=?, last_status=? WHERE id=?",
            (_now(), status, sub_id),
        )
        _conn.commit()


def delete_subscription(sub_id: int) -> None:
    with _lock:
        _conn.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
        _conn.execute("DELETE FROM seen_items WHERE subscription_id=?", (sub_id,))
        _conn.execute("DELETE FROM notifications WHERE subscription_id=?", (sub_id,))
        _conn.commit()


# --- Виденные объявления -----------------------------------------------------

def seen_count(sub_id: int) -> int:
    return _conn.execute(
        "SELECT COUNT(*) AS c FROM seen_items WHERE subscription_id=?", (sub_id,)
    ).fetchone()["c"]


def is_seen(sub_id: int, item_id) -> bool:
    return _conn.execute(
        "SELECT 1 FROM seen_items WHERE subscription_id=? AND item_id=?", (sub_id, str(item_id))
    ).fetchone() is not None


def mark_many_seen(sub_id: int, item_ids: list) -> None:
    with _lock:
        _conn.executemany(
            "INSERT OR IGNORE INTO seen_items (subscription_id, item_id, seen_at) VALUES (?, ?, ?)",
            [(sub_id, str(i), _now()) for i in item_ids],
        )
        _conn.commit()


# --- Статистика уведомлений --------------------------------------------------

def add_notification(sub_id: int, item_id) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO notifications (subscription_id, item_id, notified_at) VALUES (?, ?, ?)",
            (sub_id, str(item_id), _now()),
        )
        _conn.commit()


def notif_total(sub_id: int) -> int:
    return _conn.execute(
        "SELECT COUNT(*) AS c FROM notifications WHERE subscription_id=?", (sub_id,)
    ).fetchone()["c"]


def notif_today(sub_id: int) -> int:
    return _conn.execute(
        "SELECT COUNT(*) AS c FROM notifications WHERE subscription_id=? AND notified_at>=?",
        (sub_id, _midnight()),
    ).fetchone()["c"]


def user_stats(user_id: int) -> dict:
    subs = list_subscriptions(user_id)
    ids = [s["id"] for s in subs]
    active = sum(1 for s in subs if s["active"])
    total_notif = today_notif = 0
    if ids:
        ph = ",".join("?" * len(ids))
        total_notif = _conn.execute(
            f"SELECT COUNT(*) c FROM notifications WHERE subscription_id IN ({ph})", ids
        ).fetchone()["c"]
        today_notif = _conn.execute(
            f"SELECT COUNT(*) c FROM notifications WHERE subscription_id IN ({ph}) AND notified_at>=?",
            (*ids, _midnight()),
        ).fetchone()["c"]
    return {
        "total": len(subs),
        "active": active,
        "paused": len(subs) - active,
        "notif_total": total_notif,
        "notif_today": today_notif,
    }


def global_stats() -> dict:
    g = lambda q: _conn.execute(q).fetchone()["c"]  # noqa: E731
    return {
        "users": g("SELECT COUNT(*) c FROM users"),
        "keys_free": g("SELECT COUNT(*) c FROM access_keys WHERE used_by IS NULL AND revoked_at IS NULL"),
        "whitelisted": g("SELECT COUNT(*) c FROM users WHERE COALESCE(whitelisted,0)=1"),
        "waitlist": g("SELECT COUNT(*) c FROM waitlist"),
        "subs": g("SELECT COUNT(*) c FROM subscriptions"),
        "subs_active": g("SELECT COUNT(*) c FROM subscriptions WHERE active=1"),
        "notif_total": g("SELECT COUNT(*) c FROM notifications"),
    }


# =============================================================================
# Тарифы, язык, платежи
# =============================================================================
# Схема дополняется здесь, а не в init_db, чтобы боевая база пережила выкатку:
# у живых пользователей таблица users уже есть, ей нужны только новые колонки.

def init_billing() -> None:
    """Досоздаёт таблицы и колонки для тарифов и оплаты. Идемпотентно."""
    with _lock:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product     TEXT NOT NULL,
                provider    TEXT NOT NULL,        -- stars | crypto
                amount      REAL NOT NULL,
                currency    TEXT NOT NULL,        -- XTR | USDT
                status      TEXT NOT NULL,        -- pending | paid | failed
                external_id TEXT,                 -- invoice_id у Crypto Pay
                created_at  INTEGER,
                paid_at     INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_pay_ext ON payments(external_id)
                WHERE external_id IS NOT NULL;
            """
        )
        cols = {r["name"] for r in _conn.execute("PRAGMA table_info(users)")}
        for col, ddl in (
            ("lang", "ALTER TABLE users ADD COLUMN lang TEXT DEFAULT ''"),
            ("plan", "ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'"),
            ("plan_until", "ALTER TABLE users ADD COLUMN plan_until INTEGER DEFAULT 0"),
            ("trial_used", "ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0"),
            ("notified_stage", "ALTER TABLE users ADD COLUMN notified_stage TEXT DEFAULT ''"),
            ("missed_count", "ALTER TABLE users ADD COLUMN missed_count INTEGER DEFAULT 0"),
            ("missed_since", "ALTER TABLE users ADD COLUMN missed_since INTEGER DEFAULT 0"),
            ("digest_at", "ALTER TABLE users ADD COLUMN digest_at INTEGER DEFAULT 0"),
            ("plan_source", "ALTER TABLE users ADD COLUMN plan_source TEXT DEFAULT ''"),
            ("source", "ALTER TABLE users ADD COLUMN source TEXT DEFAULT ''"),
            ("ref_by", "ALTER TABLE users ADD COLUMN ref_by INTEGER DEFAULT 0"),
            ("ref_paid", "ALTER TABLE users ADD COLUMN ref_paid INTEGER DEFAULT 0"),
        ):
            if col not in cols:
                _conn.execute(ddl)
        _conn.commit()
    # Закрытый тест: белый список, ключи, лист ожидания. Здесь же, чтобы ни один
    # вызов init_billing (бот, тесты) не остался без этих таблиц.
    init_invites()


def get_user(user_id: int) -> sqlite3.Row | None:
    return _conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_lang(user_id: int) -> str:
    row = _conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return (row["lang"] if row and row["lang"] else "") or ""


def set_lang(user_id: int, lang: str) -> None:
    with _lock:
        _conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
        _conn.commit()


def effective_plan(user_id: int) -> tuple[str, int]:
    """(тариф, до какого времени). Просроченный платный тариф отдаётся как free."""
    row = get_user(user_id)
    if not row:
        return "free", 0
    plan = row["plan"] or "free"
    until = row["plan_until"] or 0
    if plan != "free" and until and until < _now():
        return "free", until
    return plan, until


def grant_plan(user_id: int, plan: str, days: int, source: str = "paid") -> int:
    """Включает тариф. Если тот же тариф ещё активен — продлевает от его конца.

    Возвращает новую дату окончания. Апгрейд на более высокий тариф не крадёт
    остаток: считается от текущего момента, но не раньше уже оплаченного конца.
    """
    with _lock:
        row = _conn.execute(
            "SELECT plan, plan_until FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        base = _now()
        if row and (row["plan_until"] or 0) > base and (row["plan"] or "free") == plan:
            base = row["plan_until"]
        until = base + days * 86400
        _conn.execute(
            "UPDATE users SET plan=?, plan_until=?, plan_source=?, notified_stage='' WHERE user_id=?",
            (plan, until, source, user_id),
        )
        _conn.commit()
        return until


def start_trial(user_id: int, plan: str, days: int) -> bool:
    """Выдаёт пробный период один раз за всё время. True — если выдали сейчас."""
    with _lock:
        cur = _conn.execute(
            "UPDATE users SET plan=?, plan_until=?, trial_used=1, plan_source='trial' "
            "WHERE user_id=? AND COALESCE(trial_used,0)=0",
            (plan, _now() + days * 86400, user_id),
        )
        _conn.commit()
        return cur.rowcount > 0


def count_subscriptions(user_id: int) -> int:
    return _conn.execute(
        "SELECT COUNT(*) c FROM subscriptions WHERE user_id=?", (user_id,)
    ).fetchone()["c"]


def users_expiring(within_seconds: int) -> list[sqlite3.Row]:
    """Платные тарифы, которые заканчиваются скоро и по которым ещё не напоминали."""
    return _conn.execute(
        "SELECT * FROM users WHERE plan!='free' AND plan_until>? AND plan_until<=? "
        "AND COALESCE(notified_stage,'')!='soon'",
        (_now(), _now() + within_seconds),
    ).fetchall()


def users_expired() -> list[sqlite3.Row]:
    """Тарифы, которые уже кончились, но пользователь ещё числится платным."""
    return _conn.execute(
        "SELECT * FROM users WHERE plan!='free' AND plan_until>0 AND plan_until<=?", (_now(),)
    ).fetchall()


def mark_stage(user_id: int, stage: str) -> None:
    with _lock:
        _conn.execute("UPDATE users SET notified_stage=? WHERE user_id=?", (stage, user_id))
        _conn.commit()


def downgrade_to_free(user_id: int) -> None:
    with _lock:
        _conn.execute(
            "UPDATE users SET plan='free', notified_stage='expired' WHERE user_id=?", (user_id,)
        )
        _conn.commit()


def free_users_with_paused() -> list[int]:
    """Кому есть смысл считать пропущенное: free-тариф и есть поиски на паузе."""
    return [
        r["user_id"]
        for r in _conn.execute(
            "SELECT DISTINCT s.user_id FROM subscriptions s "
            "JOIN users u ON u.user_id=s.user_id "
            "WHERE s.active=0 AND (u.plan='free' OR u.plan_until<=?)",
            (_now(),),
        )
    ]


def paused_subscriptions(user_id: int) -> list[sqlite3.Row]:
    return _conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=? AND active=0", (user_id,)
    ).fetchall()


def add_missed(user_id: int, n: int) -> None:
    """Копит счётчик «сколько ты не увидел». Цифра всегда реальная, не выдуманная."""
    if n <= 0:
        return
    with _lock:
        _conn.execute(
            "UPDATE users SET missed_count=COALESCE(missed_count,0)+?, "
            "missed_since=CASE WHEN COALESCE(missed_since,0)=0 THEN ? ELSE missed_since END "
            "WHERE user_id=?",
            (n, _now(), user_id),
        )
        _conn.commit()


def take_missed(user_id: int) -> tuple[int, int]:
    """Забирает накопленное (счётчик, с какого времени) и обнуляет."""
    row = get_user(user_id)
    if not row:
        return 0, 0
    n, since = row["missed_count"] or 0, row["missed_since"] or 0
    with _lock:
        _conn.execute(
            "UPDATE users SET missed_count=0, missed_since=0, digest_at=? WHERE user_id=?",
            (_now(), user_id),
        )
        _conn.commit()
    return n, since


def digest_sent_at(user_id: int) -> int:
    row = get_user(user_id)
    return (row["digest_at"] or 0) if row else 0


# --- Платежи -----------------------------------------------------------------

def create_payment(user_id: int, product: str, provider: str, amount: float,
                   currency: str, external_id: str | None = None) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO payments (user_id, product, provider, amount, currency, status, "
            "external_id, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (user_id, product, provider, amount, currency, external_id, _now()),
        )
        _conn.commit()
        return cur.lastrowid


def get_payment(payment_id: int) -> sqlite3.Row | None:
    return _conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()


def mark_paid(payment_id: int) -> bool:
    """Идемпотентно: тариф начисляется только тому, кто перевёл pending → paid."""
    with _lock:
        cur = _conn.execute(
            "UPDATE payments SET status='paid', paid_at=? WHERE id=? AND status='pending'",
            (_now(), payment_id),
        )
        _conn.commit()
        return cur.rowcount > 0


def mark_failed(payment_id: int) -> None:
    with _lock:
        _conn.execute(
            "UPDATE payments SET status='failed' WHERE id=? AND status='pending'", (payment_id,)
        )
        _conn.commit()


def pending_crypto_payments(max_age_hours: int = 24) -> list[sqlite3.Row]:
    return _conn.execute(
        "SELECT * FROM payments WHERE provider='crypto' AND status='pending' "
        "AND external_id IS NOT NULL AND created_at>=?",
        (_now() - max_age_hours * 3600,),
    ).fetchall()


def revenue_stats() -> dict:
    row = _conn.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(CASE WHEN currency='XTR' THEN amount END),0) stars, "
        "COALESCE(SUM(CASE WHEN currency='USDT' THEN amount END),0) usdt "
        "FROM payments WHERE status='paid'"
    ).fetchone()
    plans = {
        r["plan"]: r["c"]
        for r in _conn.execute(
            "SELECT COALESCE(plan,'free') plan, COUNT(*) c FROM users "
            "WHERE plan!='free' AND plan_until>? GROUP BY plan",
            (_now(),),
        )
    }
    return {
        "payments": row["c"],
        "stars": row["stars"],
        "usdt": row["usdt"],
        "paying": sum(plans.values()),
        "by_plan": plans,
    }


def set_payment_external(payment_id: int, external_id: str) -> None:
    with _lock:
        _conn.execute(
            "UPDATE payments SET external_id=? WHERE id=?", (external_id, payment_id)
        )
        _conn.commit()


# --- Разовые миграции --------------------------------------------------------

def _meta_get(key: str) -> str | None:
    _conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    row = _conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _meta_set(key: str, value: str) -> None:
    # Таблицу создаём и здесь: запись может случиться раньше первого чтения.
    _conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    _conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))


def set_channel(chat_id: int, title: str) -> None:
    """Запоминает канал, куда бота сделали админом.

    Иначе id канала пришлось бы доставать руками через getUpdates, а бот на
    поллинге — второй getUpdates просто не дадут.
    """
    with _lock:
        _meta_set("tg_channel_id", str(chat_id))
        _meta_set("tg_channel_title", title or "")
        _conn.commit()


def get_channel() -> dict | None:
    cid = _meta_get("tg_channel_id")
    if not cid:
        return None
    return {"id": int(cid), "title": _meta_get("tg_channel_title") or ""}


def flag_once(key: str) -> bool:
    """True — если флаг поставлен именно сейчас. Защита от повторов раз в сутки.

    Ставим ДО действия: перезапуск сервиса в то же время не должен выложить
    в канал второй пост за день.
    """
    with _lock:
        if _meta_get(key):
            _conn.commit()
            return False
        _meta_set(key, "1")
        _conn.commit()
        return True


def drop_flag(key: str) -> None:
    """Снимает флаг — чтобы после сбоя попытка повторилась."""
    with _lock:
        _conn.execute("DELETE FROM meta WHERE key=?", (key,))
        _conn.commit()


def clear_channel() -> None:
    with _lock:
        _meta_set("tg_channel_id", "")
        _conn.commit()


def grant_legacy_users(plan: str, days: int) -> int:
    """Разово выдаёт тариф тем, кто пользовался ботом ДО появления тарифов.

    Без этого старые пользователи молча оказались бы на Free с одним поиском:
    они пришли, когда всё было бесплатно, и терять их на ровном месте нельзя.
    Выполняется один раз — отметка лежит в таблице meta.
    """
    with _lock:
        if _meta_get("legacy_granted"):
            _conn.commit()
            return 0
        until = _now() + days * 86400
        cur = _conn.execute(
            "UPDATE users SET plan=?, plan_until=?, trial_used=1, plan_source='legacy' "
            "WHERE COALESCE(plan,'free')='free' AND COALESCE(plan_until,0)=0",
            (plan, until),
        )
        _meta_set("legacy_granted", str(_now()))
        _conn.commit()
        return cur.rowcount


def plan_source(user_id: int) -> str:
    row = get_user(user_id)
    return (row["plan_source"] or "") if row else ""


# --- Откуда пришёл пользователь ----------------------------------------------

def set_source(user_id: int, source: str) -> None:
    """Записывает канал привлечения. Первое касание побеждает.

    Перезаписывать нельзя: иначе человек, который перешёл по ссылке блогера,
    а потом кликнул свою же реферальную, «переедет» в другой канал, и отчёт
    покажет не тех, кто привёл платящего.
    """
    if not source:
        return
    with _lock:
        _conn.execute(
            "UPDATE users SET source=? WHERE user_id=? AND COALESCE(source,'')=''",
            (source[:64], user_id),
        )
        _conn.commit()


def sources_report() -> list[dict]:
    """Разрез по каналам: пришло → платящих сейчас → сколько денег принесли."""
    rows = _conn.execute(
        """
        SELECT COALESCE(NULLIF(u.source,''),'(прямой)') AS src,
               COUNT(DISTINCT u.user_id) AS users,
               COUNT(DISTINCT CASE WHEN u.plan!='free' AND u.plan_until>? THEN u.user_id END) AS paying,
               COALESCE(SUM(CASE WHEN p.currency='XTR' THEN p.amount END),0) AS stars,
               COALESCE(SUM(CASE WHEN p.currency='USDT' THEN p.amount END),0) AS usdt
        FROM users u
        LEFT JOIN payments p ON p.user_id=u.user_id AND p.status='paid'
        GROUP BY src
        ORDER BY users DESC
        """,
        (_now(),),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Приглашения ------------------------------------------------------------

def set_referrer(user_id: int, referrer_id: int) -> bool:
    """Привязывает пригласившего. Только один раз и только не самого себя.

    Награду выдаём не за переход, а за первую оплату приглашённого — иначе
    рефералка превращается в ферму пустых аккаунтов.
    """
    if not referrer_id or referrer_id == user_id:
        return False
    if not get_user(referrer_id):
        return False
    with _lock:
        cur = _conn.execute(
            "UPDATE users SET ref_by=? WHERE user_id=? AND COALESCE(ref_by,0)=0",
            (referrer_id, user_id),
        )
        _conn.commit()
        return cur.rowcount > 0


def referrer_of(user_id: int) -> int | None:
    row = get_user(user_id)
    return (row["ref_by"] or None) if row else None


def claim_referral_bonus(user_id: int) -> int | None:
    """Забирает право на награду за приглашённого. Возвращает id пригласившего.

    Идемпотентно: пока флаг не снят, повторная оплата того же человека награду
    не приносит. Иначе один друг с подпиской кормил бы пригласившего вечно.
    """
    with _lock:
        row = _conn.execute(
            "SELECT ref_by, COALESCE(ref_paid,0) AS paid FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row or not row["ref_by"] or row["paid"]:
            return None
        _conn.execute("UPDATE users SET ref_paid=1 WHERE user_id=?", (user_id,))
        _conn.commit()
        return row["ref_by"]


def referral_stats(user_id: int) -> dict:
    invited = _conn.execute(
        "SELECT COUNT(*) c FROM users WHERE ref_by=?", (user_id,)
    ).fetchone()["c"]
    paid = _conn.execute(
        "SELECT COUNT(*) c FROM users WHERE ref_by=? AND COALESCE(ref_paid,0)=1", (user_id,)
    ).fetchone()["c"]
    return {"invited": invited, "paid": paid}


def growth_report(days: int = 14) -> list[dict]:
    """Новые пользователи по дням — для графика роста в дашборде."""
    since = _now() - days * 86400
    rows = _conn.execute(
        "SELECT date(activated_at,'unixepoch') d, COUNT(*) c FROM users "
        "WHERE activated_at>=? GROUP BY d ORDER BY d",
        (since,),
    ).fetchall()
    return [{"day": r["d"], "users": r["c"]} for r in rows]
