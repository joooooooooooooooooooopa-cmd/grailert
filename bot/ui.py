"""Инлайн-клавиатуры и хелперы форматирования интерфейса.

Каждая клавиатура принимает язык пользователя: подписи кнопок берутся из i18n,
своих строк в этом модуле нет.
"""
from __future__ import annotations

import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import config
import i18n
import plans
from i18n import t


def reply_kb(lang: str, admin: bool = False) -> ReplyKeyboardMarkup:
    """Постоянная нижняя клавиатура — теперь это и есть всё меню бота.

    Инлайн-меню под приветствием убрано: одна панель
    внизу, без дублирующих кнопок в ленте чата.
    """
    rows = [
        [t(lang, "btn_add"), t(lang, "btn_list")],
        [t(lang, "btn_plan"), t(lang, "btn_stats")],
        [t(lang, "btn_invite"), t(lang, "btn_help")],
        [t(lang, "btn_lang"), t(lang, "btn_diag")],
    ]
    if admin:
        rows.append([t(lang, "btn_admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def pretty_interval(sec: int, lang: str) -> str:
    if sec % 3600 == 0 and sec >= 3600:
        return f"{sec // 3600} {t(lang, 'unit_h')}"
    if sec % 60 == 0 and sec >= 60:
        return f"{sec // 60} {t(lang, 'unit_min')}"
    return f"{sec} {t(lang, 'unit_sec')}"


def ago(ts: int, lang: str) -> str:
    if not ts:
        return t(lang, "ago_never")
    d = int(time.time()) - int(ts)  # ts может прийти float — иначе получим «vor 1.0 Std»
    if d < 60:
        return t(lang, "ago_now")
    if d < 3600:
        return t(lang, "ago_min", n=d // 60)
    if d < 86400:
        return t(lang, "ago_h", n=d // 3600)
    return t(lang, "ago_d", n=d // 86400)


def status_emoji(sub) -> str:
    if not sub["active"]:
        return "⏸"
    if sub["last_status"] == "error":
        return "⚠️"
    return "🟢"


# --- Клавиатуры --------------------------------------------------------------

def main_menu(lang: str, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(t(lang, "btn_new_search"), callback_data="add")],
        [InlineKeyboardButton(t(lang, "btn_my_searches"), callback_data="list:0")],
        [
            InlineKeyboardButton(t(lang, "btn_plan"), callback_data="plan"),
            InlineKeyboardButton(t(lang, "btn_stats"), callback_data="stats"),
        ],
        [InlineKeyboardButton(t(lang, "btn_invite"), callback_data="invite")],
        [
            InlineKeyboardButton(t(lang, "btn_help"), callback_data="help"),
            InlineKeyboardButton(t(lang, "btn_lang"), callback_data="lang"),
        ],
        [InlineKeyboardButton(t(lang, "btn_diag"), callback_data="diag")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(t(lang, "btn_admin"), callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def gate_kb(lang: str, on_waitlist: bool = False) -> InlineKeyboardMarkup:
    """Экран «только по приглашению»: встать в очередь + сменить язык."""
    rows = []
    if not on_waitlist:
        rows.append([InlineKeyboardButton(t(lang, "gate_btn_waitlist"), callback_data="wl_join")])
    rows.append([InlineKeyboardButton(t(lang, "btn_lang"), callback_data="lang")])
    return InlineKeyboardMarkup(rows)


def back_menu(lang: str, target: str = "menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data=target)]])


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")]])


# Готовые поиски для новичка: топ перепродаваемых брендов ЕС. Индекс в callback
# (preset:<i>) — названия в callback_data не влезают в 64 байта и не нужны.
PRESETS = [
    "Stone Island", "Carhartt", "Ralph Lauren", "Nike vintage",
    "Arc'teryx", "The North Face", "Patagonia", "Levi's 501",
    "Adidas vintage", "Burberry", "Lacoste", "New Balance",
]


def add_kb(lang: str) -> InlineKeyboardMarkup:
    """Клавиатура шага «пришли ссылку/слово»: готовые поиски + отмена."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "btn_presets"), callback_data="presets")],
            [InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")],
        ]
    )


def presets_kb(lang: str) -> InlineKeyboardMarkup:
    btns = [
        InlineKeyboardButton(name, callback_data=f"preset:{i}")
        for i, name in enumerate(PRESETS)
    ]
    rows = [btns[i : i + 2] for i in range(0, len(btns), 2)]
    rows.append([InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def lang_kb(current: str) -> InlineKeyboardMarkup:
    """Выбор языка. Текущий помечен галочкой — видно, что уже выбрано."""
    btns = [
        InlineKeyboardButton(("✓ " if code == current else "") + label, callback_data=f"setlang:{code}")
        for code, label in i18n.LANGS.items()
    ]
    rows = [btns[i : i + 2] for i in range(0, len(btns), 2)]
    rows.append([InlineKeyboardButton(t(current, "btn_back_menu"), callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def add_name_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "btn_auto_name"), callback_data="addauto")],
            [InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")],
        ]
    )


def interval_kb(lang: str, prefix: str, plan: str) -> InlineKeyboardMarkup:
    """Интервалы. Недоступные на тарифе показываем с замком — это и есть витрина.

    Прятать их нельзя: пользователь должен видеть, что существует проверка раз
    в 30 секунд, иначе ему нечего хотеть.
    """
    opts = [30, 60, 120, 300, 900, 1800]
    allowed_min = plans.min_interval(plan)
    btns = []
    for sec in opts:
        label = pretty_interval(sec, lang)
        if sec < allowed_min:
            btns.append(InlineKeyboardButton(f"🔒 {label}", callback_data=f"lockint:{sec}"))
        else:
            btns.append(InlineKeyboardButton(label, callback_data=f"{prefix}:{sec}"))
    rows = [btns[i : i + 3] for i in range(0, len(btns), 3)]
    rows.append([InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(rows)


DOMAINS = [
    ("🇵🇱 PL", "vinted.pl"), ("🇩🇪 DE", "vinted.de"), ("🇫🇷 FR", "vinted.fr"),
    ("🇮🇹 IT", "vinted.it"), ("🇪🇸 ES", "vinted.es"), ("🇳🇱 NL", "vinted.nl"),
    ("🇬🇧 UK", "vinted.co.uk"), ("🇨🇿 CZ", "vinted.cz"), ("🇱🇹 LT", "vinted.lt"),
    ("🇵🇹 PT", "vinted.pt"), ("🇧🇪 BE", "vinted.be"), ("🇸🇰 SK", "vinted.sk"),
]

# Язык интерфейса → домен Vinted, который логично предложить первым.
LANG_DEFAULT_HOST = {
    "fr": "vinted.fr", "de": "vinted.de", "es": "vinted.es",
    "it": "vinted.it", "pl": "vinted.pl", "en": "vinted.co.uk", "ru": "vinted.pl",
}


def domain_kb(lang: str) -> InlineKeyboardMarkup:
    """Выбор страны Vinted. Домен под язык пользователя идёт первым."""
    preferred = LANG_DEFAULT_HOST.get(lang)
    items = sorted(DOMAINS, key=lambda d: (d[1] != preferred,))
    btns = [InlineKeyboardButton(txt, callback_data=f"dom:{host}") for txt, host in items]
    rows = [btns[i : i + 3] for i in range(0, len(btns), 3)]
    rows.append([InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def subs_list(lang: str, subs: list, page: int) -> InlineKeyboardMarkup:
    size = config.PAGE_SIZE
    chunk = subs[page * size : (page + 1) * size]
    rows = [
        [InlineKeyboardButton(f"{status_emoji(s)} {s['name']}", callback_data=f"sub:{s['id']}")]
        for s in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"list:{page - 1}"))
    if (page + 1) * size < len(subs):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"list:{page + 1}"))
    if nav:
        rows.append(nav)
    if subs:
        rows.append(
            [
                InlineKeyboardButton(t(lang, "btn_pause_all"), callback_data="pauseall"),
                InlineKeyboardButton(t(lang, "btn_resume_all"), callback_data="resumeall"),
            ]
        )
        rows.append([InlineKeyboardButton(t(lang, "btn_export"), callback_data="export")])
    rows.append(
        [
            InlineKeyboardButton(t(lang, "btn_new_short"), callback_data="add"),
            InlineKeyboardButton(t(lang, "btn_back_menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def sub_card(lang: str, sub) -> InlineKeyboardMarkup:
    sid = sub["id"]
    if sub["active"]:
        toggle = (t(lang, "btn_pause"), "off")
    else:
        toggle = (t(lang, "btn_resume"), "on")
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(toggle[0], callback_data=f"toggle:{sid}:{toggle[1]}"),
                InlineKeyboardButton(t(lang, "btn_check"), callback_data=f"check:{sid}"),
            ],
            [
                InlineKeyboardButton(t(lang, "btn_rename"), callback_data=f"name:{sid}"),
                InlineKeyboardButton(t(lang, "btn_interval"), callback_data=f"int:{sid}"),
            ],
            [
                InlineKeyboardButton(t(lang, "btn_kwi"), callback_data=f"kwi:{sid}"),
                InlineKeyboardButton(t(lang, "btn_kwe"), callback_data=f"kwe:{sid}"),
            ],
            [
                InlineKeyboardButton(t(lang, "btn_price"), callback_data=f"price:{sid}"),
                InlineKeyboardButton(t(lang, "btn_url"), callback_data=f"url:{sid}"),
            ],
            [InlineKeyboardButton(t(lang, "btn_delete"), callback_data=f"del:{sid}")],
            [InlineKeyboardButton(t(lang, "btn_back_list"), callback_data="list:0")],
        ]
    )


def confirm_delete(lang: str, sid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t(lang, "btn_delete_yes"), callback_data=f"delok:{sid}"),
                InlineKeyboardButton(t(lang, "btn_delete_no"), callback_data=f"sub:{sid}"),
            ]
        ]
    )


# --- Тарифы и оплата ---------------------------------------------------------

def price_label(code: str, crypto_on: bool) -> str:
    """Цена для кнопки: показываем крипту, если она включена — она дешевле."""
    p = plans.PRODUCTS[code]
    if crypto_on:
        return f"${p['usdt']:.2f} / {p['stars']} ⭐"
    return f"{p['stars']} ⭐"


def plan_kb(lang: str, plan: str, crypto_on: bool) -> InlineKeyboardMarkup:
    rows = []
    if plan != plans.PRO:
        rows.append([InlineKeyboardButton(
            t(lang, "btn_buy_basic", price=price_label("basic_30", crypto_on)),
            callback_data="buy:basic_30")])
    rows.append([InlineKeyboardButton(
        t(lang, "btn_buy_pro", price=price_label("pro_30", crypto_on)),
        callback_data="buy:pro_30")])
    rows.append([InlineKeyboardButton(
        t(lang, "btn_buy_pro_year", price=price_label("pro_365", crypto_on)),
        callback_data="buy:pro_365")])
    rows.append([InlineKeyboardButton(t(lang, "btn_back_menu"), callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def pay_method_kb(lang: str, code: str, crypto_on: bool) -> InlineKeyboardMarkup:
    rows = []
    if crypto_on:
        # Крипта первой: комиссия ~3% против ~32% у Stars на мобильных.
        rows.append([InlineKeyboardButton(t(lang, "btn_pay_crypto"), callback_data=f"pay:crypto:{code}")])
    rows.append([InlineKeyboardButton(t(lang, "btn_pay_stars"), callback_data=f"pay:stars:{code}")])
    rows.append([InlineKeyboardButton(t(lang, "btn_back"), callback_data="plan")])
    return InlineKeyboardMarkup(rows)


def crypto_invoice_kb(lang: str, url: str, payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "btn_pay_open"), url=url)],
            [InlineKeyboardButton(t(lang, "btn_pay_check"), callback_data=f"paychk:{payment_id}")],
            [InlineKeyboardButton(t(lang, "btn_back"), callback_data="plan")],
        ]
    )


def upgrade_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "btn_upgrade"), callback_data="plan")],
            [InlineKeyboardButton(t(lang, "btn_back_menu"), callback_data="menu")],
        ]
    )


def admin_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔑 Ключ", callback_data="adm_newkey"),
                InlineKeyboardButton("🔑 Пачка ключей", callback_data="adm_batch"),
            ],
            [
                InlineKeyboardButton("🗝 Ключи", callback_data="adm_keys"),
                InlineKeyboardButton("⛔ Отозвать ключ", callback_data="adm_revoke"),
            ],
            [
                InlineKeyboardButton("⏳ Лист ожидания", callback_data="adm_waitlist"),
                InlineKeyboardButton("👥 Пользователи", callback_data="adm_users"),
            ],
            [
                InlineKeyboardButton("💰 Деньги", callback_data="adm_money"),
                InlineKeyboardButton("📡 Каналы", callback_data="adm_sources"),
            ],
            [
                InlineKeyboardButton("🎁 Выдать тариф", callback_data="adm_grant"),
                InlineKeyboardButton("📢 Рассылка", callback_data="adm_bcast"),
            ],
            [InlineKeyboardButton("📊 Статистика", callback_data="adm_stats")],
            [InlineKeyboardButton(t(lang, "btn_back_menu"), callback_data="menu")],
        ]
    )
