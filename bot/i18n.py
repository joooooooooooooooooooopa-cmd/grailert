"""Мультиязычность бота.

Аудитория Vinted почти вся европейская (FR 13 млн, DE 11 млн, UK 8 млн),
поэтому язык по умолчанию — английский, а русский лишь один из семи.

Язык определяется по language_code из Telegram при первом старте,
дальше пользователь может сменить его вручную (кнопка 🌐 в меню).
Все тексты интерфейса ходят только через t(); строк в коде быть не должно.
"""
from __future__ import annotations

# Порядок важен: он же порядок кнопок в переключателе языка.
LANGS: dict[str, str] = {
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "es": "🇪🇸 Español",
    "it": "🇮🇹 Italiano",
    "pl": "🇵🇱 Polski",
    "ru": "🇷🇺 Русский",
}
DEFAULT_LANG = "en"


def detect_lang(tg_code: str | None) -> str:
    """Язык из Telegram (может быть 'pt-br', 'en-GB') → наш код или английский."""
    if not tg_code:
        return DEFAULT_LANG
    code = tg_code.split("-")[0].lower()
    return code if code in LANGS else DEFAULT_LANG


def t(lang: str | None, key: str, **kw) -> str:
    """Строка на языке пользователя. Фолбэк — английский, затем сам ключ."""
    table = STRINGS.get(lang or DEFAULT_LANG) or STRINGS[DEFAULT_LANG]
    raw = table.get(key)
    if raw is None:
        raw = STRINGS[DEFAULT_LANG].get(key, key)
    return raw.format(**kw) if kw else raw


# Ключи, по которым узнаём нажатие постоянной нижней кнопки на ЛЮБОМ языке:
# юзер мог сменить язык, а старая клавиатура осталась висеть у него в чате.
REPLY_BUTTON_KEYS = (
    "btn_menu", "btn_add", "btn_list", "btn_plan", "btn_stats",
    "btn_invite", "btn_help", "btn_lang", "btn_diag", "btn_admin",
)


def match_reply_button(text: str) -> str | None:
    """Возвращает ключ кнопки, если текст совпал с ней в любом из языков."""
    for key in REPLY_BUTTON_KEYS:
        for table in STRINGS.values():
            if table.get(key) == text:
                return key
    return None


STRINGS: dict[str, dict[str, str]] = {

# ============================================================ ENGLISH (canon)
"en": {
    # --- нижняя клавиатура ---
    "btn_menu": "🛍 Menu",
    "btn_add": "➕ New search",
    "btn_list": "📋 My searches",
    "kb_pinned": "🛍 The <b>Menu</b> button is always down below 👇",

    # --- меню ---
    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "I watch Vinted for you and send every new listing the moment it appears — photos, price, size, link.",
    "menu_searches": "📂 Searches: <b>{total}</b>   🟢 running: <b>{active}</b>   ⏸ paused: <b>{paused}</b>",
    "menu_found": "🆕 Found so far: <b>{total}</b>   📅 today: <b>{today}</b>",
    "menu_plan": "💎 Plan: <b>{plan}</b>{until}",
    "menu_plan_until": " · until {date}",

    "btn_new_search": "➕ New search",
    "btn_my_searches": "📋 My searches",
    "btn_stats": "📊 Stats",
    "btn_diag": "🩺 Diagnostics",
    "btn_help": "❓ How it works",
    "btn_plan": "💎 Plan",
    "btn_lang": "🌐 Language",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Back",
    "btn_back_menu": "⬅️ Menu",
    "btn_cancel": "✖️ Cancel",

    # --- старт / язык ---
    "welcome": (
        "👋 <b>Welcome to Grailert.</b>\n\n"
        "Tell me what you're hunting for, and I'll ping you the second it's listed — "
        "before anyone scrolling the app sees it.\n\n"
        "🎁 <b>Your {days}-day Pro trial is active</b> — unlimited searches, checks every 30 seconds."
    ),
    "welcome_back": "👋 Welcome back.",
    "lang_choose": "🌐 Choose your language:",
    "lang_saved": "✅ Language set to English.",

    # --- добавление поиска ---
    "add_prompt": (
        "➕ <b>New search</b>\n\n"
        "Send a <b>keyword</b> — like <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — and I'll search the whole site.\n\n"
        "Or paste a <b>filtered Vinted link</b> (<code>vinted.fr/catalog?...</code>) if you want brand, "
        "size and price filters exactly as you set them."
    ),
    "domain_prompt": "🔎 Searching for: <b>{kw}</b>\n\nWhich Vinted country?",
    "preview_checking": "⏳ Checking that search…",
    "preview_ok": "✅ Found <b>{n}</b> listings matching this search.",
    "preview_fail": "⚠️ Couldn't check it right now (Vinted rate limit), but you can still save the search.",
    "name_prompt": "What should I call this search?",
    "btn_auto_name": "✨ Auto name",
    "name_set": "Name: <b>{name}</b>\n\nHow often should I check?",
    "interval_prompt": "⏱ New check interval:",
    "interval_custom": "Send the interval in seconds (minimum {min}).",
    "need_number": "I need a number of seconds. Try again or /cancel",
    "added_ok": "✅ Search added. I'm watching for new listings now.",
    "baseline_note": "💡 I quietly noted the listings that are already there, so you only get what appears <i>from now on</i>.",

    # --- список / карточка ---
    "list_empty": "📋 No searches yet.\nTap «New search» to add your first one.",
    "list_title": "📋 <b>My searches</b> ({n})\nPick one to open it:",
    "btn_pause_all": "⏸ Pause all",
    "btn_resume_all": "▶️ Resume all",
    "btn_export": "📤 Export searches",
    "btn_new_short": "➕ New",

    "card_active": "🟢 Running",
    "card_paused": "⏸ Paused",
    "card_error": "⚠️ Last check failed",
    "card_interval": "⏱ Interval: <b>{interval}</b>",
    "card_found": "🆕 Found: <b>{total}</b>   📅 today: <b>{today}</b>",
    "card_last": "🕐 Last check: {ago}",
    "card_kwi": "🔔 Include: <code>{v}</code>",
    "card_kwe": "🔕 Exclude: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">search link ↗</a>",
    "btn_price": "💶 Price",
    "price_prompt": "Send a price range for this search: <code>10-50</code>, <code>-50</code> (max only) or <code>10-</code> (min only). Send <code>-</code> to clear.",
    "price_updated": "✅ Price filter updated.",
    "price_invalid": "Doesn't look like a range. Examples: <code>10-50</code>, <code>-50</code>, <code>10-</code>, or <code>-</code> to clear.",
    "card_pricef": "💶 Price: <code>{v}</code>",
    "cap_size": "📏 Size: {v}",
    "cap_protect": "  <i>({v} with Buyer Protection)</i>",
    "cap_open": "Open on Vinted ↗",
    "cap_untitled": "Untitled",
    "deal_badge": "🔥 Priced well below similar listings",
    "btn_presets": "⭐ Popular searches",
    "presets_prompt": "Pick a brand and I'll set up the search:",
    "card_price_now": "💹 From <b>{price}</b>{usd} · {n} listings right now",

    "btn_resume": "▶️ Resume",
    "btn_pause": "⏸ Pause",
    "btn_check": "🔍 Check now",
    "btn_rename": "✏️ Name",
    "btn_interval": "⏱ Interval",
    "btn_kwi": "🔔 Include",
    "btn_kwe": "🔕 Exclude",
    "btn_url": "🔗 Link",
    "btn_delete": "🗑 Delete",
    "btn_back_list": "⬅️ Back to list",

    "check_running": "🔍 Checking Vinted…",
    "check_found": "🔍 Found and sent: +{n}",
    "check_none": "🔍 Nothing new right now",
    "check_error": "⚠️ Vinted isn't responding at the moment",

    "delete_confirm": "🗑 Delete search «{name}»?\nThis can't be undone.",
    "btn_delete_yes": "🗑 Yes, delete",
    "btn_delete_no": "↩️ Keep it",

    "edit_name": "✏️ Send the new name for this search:",
    "edit_url": "🔗 Current link:\n<code>{url}</code>\n\nSend the new Vinted search link:",
    "edit_kwi": "🔔 <b>Include filter</b> — only notify when the title has these words.\nCurrent: <code>{v}</code>\n\nSend words separated by commas (or «-» to clear):",
    "edit_kwe": "🔕 <b>Exclude filter</b> — skip listings with these words.\nCurrent: <code>{v}</code>\n\nSend words separated by commas (or «-» to clear):",
    "url_invalid": "That doesn't look like a Vinted link. Send a link or /cancel",
    "name_updated": "✅ Name updated",
    "url_updated": "✅ Link updated",
    "kwi_updated": "✅ Include filter updated",
    "kwe_updated": "✅ Exclude filter updated",
    "interval_updated": "✅ Interval updated",
    "cancelled": "Cancelled. /start for the menu.",

    # --- уведомления ---
    "notify_overflow": "… and <b>{n}</b> more new for «{name}» (newest shown).",

    # --- статистика ---
    "stats_title": "📊 <b>Your stats</b>",
    "stats_searches": "📂 Searches: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Found in total: <b>{n}</b>",
    "stats_today": "📅 Today: <b>{n}</b>",
    "stats_by_search": "<b>By search:</b>",

    # --- помощь ---
    "help": (
        "❓ <b>How to use this</b>\n\n"
        "<b>Fast way:</b> tap <b>➕ New search</b> and send a <b>keyword</b> "
        "(<code>stone island</code>, <code>nike tn</code>). I'll search the whole site.\n\n"
        "<b>Precise way:</b> open Vinted, set your filters (brand, size, price, condition), "
        "copy the link from the address bar and send it to me. I'll watch exactly that.\n\n"
        "Then pick a name and how often I check.\n\n"
        "From then on you get <b>every new listing</b>: photo album, price, size, brand, link.\n\n"
        "🔔 <b>Include</b> — only notify if the title contains these words.\n"
        "🔕 <b>Exclude</b> — skip listings containing these words.\n"
        "🔍 <b>Check now</b> — poll this search immediately.\n\n"
        "🔒 <b>Your Vinted account is never touched.</b> I only read public listings and message you here — "
        "no logging in, no auto-buying, no reposting. Nothing that puts your account at risk."
    ),
    "support_line": "🛟 Something not working or have a question? Write us: {sup} — a human replies.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert is invite-only for now.</b>\n\n"
        "Send me your invite key (it looks like <code>GRL-XXXX-XXXX</code>) and I'll unlock <b>{days} days of Pro</b> — no card needed.\n\n"
        "No key yet? Join the waitlist — we open access in small batches."
    ),
    "gate_btn_waitlist": "⏳ Join the waitlist",
    "waitlist_joined": "✅ You're on the waitlist, position <b>#{n}</b>. I'll message you here when your access is ready.",
    "waitlist_already": "⏳ You're on the waitlist, position <b>#{n}</b>. Got a key? Just send it here.",
    "key_ok": "🔑 <b>Key accepted!</b> Pro is on for {days} days, until {date}. Add your first search 👇",
    "key_used": "⚠️ This key has already been used. One key opens one account.",
    "key_bad": "❌ That key doesn't work. Check the spelling or ask the person who gave it to you.",
    "key_ratelimited": "⏱ Too many attempts. Try again in an hour.",
    "invite_granted": "🎉 <b>Your access is ready!</b> Pro for {days} days, until {date}. Send /start to begin.",

    # --- диагностика ---
    "diag_running": "🩺 Checking whether Vinted responds…",
    "diag_title": "🩺 <b>Diagnostics</b>",
    "diag_host": "Domain: <b>{host}</b>",
    "diag_ok": "🟢 reachable",
    "diag_fail": "🔴 not reachable (Cloudflare/Datadome or network)",
    "diag_status": "API status: {status}",
    "diag_proxy_on": "Proxy: on",
    "diag_proxy_off": "Proxy: off (direct connection)",

    # --- тарифы ---
    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Pro trial",
    "plan_title": "💎 <b>Your plan</b>",
    "plan_current": "Current: <b>{plan}</b>",
    "plan_until": "Active until <b>{date}</b> ({days} days left)",
    "plan_free_desc": "Free: <b>1 search</b>, checked every <b>15 minutes</b>.",
    "plan_pitch": (
        "A single good find pays for a whole year of this.\n\n"
        "<b>Basic</b> — 3 searches, checks every <b>2 minutes</b>\n"
        "<b>Pro</b> — <b>unlimited</b> searches, checks every <b>30 seconds</b>, priority queue\n\n"
        "The faster the check, the earlier you see an underpriced listing — and on Vinted the good ones "
        "are gone in minutes."
    ),
    "plan_safety": "🔒 We never touch your Vinted account — read-only alerts, nothing automated on your side.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro for a year — {price} (2 months free)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nHow would you like to pay?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Crypto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Open payment",
    "btn_pay_check": "🔄 I've paid — check",
    "period_month": "1 month",
    "period_year": "12 months",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "{plan} plan for {period}. Instant activation.",
    "crypto_created": (
        "₿ <b>Invoice created</b> — {amount} USDT\n\n"
        "Tap the button to pay in Crypto Pay (USDT, TON, BTC and others).\n"
        "Activation is automatic within seconds of payment."
    ),
    "crypto_unavailable": "₿ Crypto payments are temporarily unavailable. Telegram Stars work fine.",
    "pay_ok": "🎉 <b>Payment received. {plan} is active until {date}.</b>\n\nGo add the searches you were holding back.",
    "pay_pending": "⏳ Payment not seen yet. If you've just paid, give it a few seconds and tap check again.",
    "pay_failed": "⚠️ Payment didn't go through. Nothing was charged.",

    # --- лимиты / пейволл ---
    "limit_searches": (
        "🔒 <b>{plan} — search limit: {limit}</b>\n\n"
        "You're watching {current} right now. Upgrade and add as many as you want — "
        "most people run one search per brand they flip."
    ),
    "limit_interval": (
        "🔒 <b>{interval} checks are part of {needed}.</b>\n\n"
        "On {plan} I check every {current}. On Vinted a well-priced item is usually gone "
        "within minutes, so the interval is the whole game."
    ),
    "btn_upgrade": "💎 Upgrade",

    # --- удержание ---
    "trial_ends_soon": (
        "⏳ <b>Your Pro trial ends in {days} days.</b>\n\n"
        "So far I've found <b>{found}</b> listings for you.\n"
        "Keep it running — Basic is {basic}, Pro is {pro}."
    ),
    "trial_over": (
        "Your Pro trial has ended — you're on Free now: 1 search, checked every 15 minutes.\n\n"
        "I found <b>{found}</b> listings for you during the trial. "
        "Everything is paused, not deleted — pick a plan and it all comes back on."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} ends in {days} days.</b>\n\n"
        "Renew and nothing changes — your searches keep running without a gap."
    ),
    "plan_expired": (
        "Your {plan} plan has ended — you're on Free now.\n\n"
        "Your searches are paused, not deleted. Renew and they pick up where they left off."
    ),
    "paused_by_limit": "⏸ Paused because your plan changed: «{name}»",
    "digest_missed": (
        "📬 <b>While you were on Free</b>\n\n"
        "Your paused searches would have caught <b>{n}</b> new listings in the last {days} days. "
        "That's what you're not seeing."
    ),

    # --- ошибки/доступ ---
    "btn_invite": "🎁 Invite a friend",
    "invite_h": "🎁 <b>Invite a friend</b>",
    "invite_p": "Send this link to someone who flips on Vinted. When they pay for any plan, <b>you get {days} days of Pro</b> — and they start with a free week of Pro anyway.",
    "invite_link": "Your link:",
    "invite_stat": "Invited: <b>{n}</b> · of them paid: <b>{p}</b>",
    "ref_reward": "🎁 <b>Someone you invited just subscribed.</b>\n\n{days} days of Pro added — your plan now runs until <b>{date}</b>. Thanks for spreading it.",
    "no_access": "No access. Send /start",
    "admin_only": "Admins only.",
    "unit_h": "h",
    "unit_min": "min",
    "unit_sec": "sec",
    "ago_never": "not yet",
    "ago_now": "just now",
    "ago_min": "{n} min ago",
    "ago_h": "{n} h ago",
    "ago_d": "{n} d ago",
},

# ============================================================ РУССКИЙ
"ru": {
    "btn_menu": "🛍 Меню",
    "btn_add": "➕ Новый поиск",
    "btn_list": "📋 Мои поиски",
    "kb_pinned": "🛍 Кнопка <b>«Меню»</b> теперь всегда снизу 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Слежу за Vinted и присылаю каждое новое объявление сразу — фото, цена, размер, ссылка.",
    "menu_searches": "📂 Поисков: <b>{total}</b>   🟢 активных: <b>{active}</b>   ⏸ пауза: <b>{paused}</b>",
    "menu_found": "🆕 Найдено всего: <b>{total}</b>   📅 сегодня: <b>{today}</b>",
    "menu_plan": "💎 Тариф: <b>{plan}</b>{until}",
    "menu_plan_until": " · до {date}",

    "btn_new_search": "➕ Новый поиск",
    "btn_my_searches": "📋 Мои поиски",
    "btn_stats": "📊 Статистика",
    "btn_diag": "🩺 Диагностика",
    "btn_help": "❓ Как это работает",
    "btn_plan": "💎 Тариф",
    "btn_lang": "🌐 Язык",
    "btn_admin": "🔐 Админка",
    "btn_back": "⬅️ Назад",
    "btn_back_menu": "⬅️ Меню",
    "btn_cancel": "✖️ Отмена",

    "welcome": (
        "👋 <b>Это Grailert.</b>\n\n"
        "Скажи, что ищешь, и я напишу в ту же секунду, как вещь выложат — "
        "раньше, чем её увидят те, кто листает ленту.\n\n"
        "🎁 <b>Пробный Pro на {days} дней уже включён</b> — поисков сколько угодно, проверка раз в 30 секунд."
    ),
    "welcome_back": "👋 С возвращением.",
    "lang_choose": "🌐 Выбери язык:",
    "lang_saved": "✅ Язык переключён на русский.",

    "add_prompt": (
        "➕ <b>Новый поиск</b>\n\n"
        "Пришли <b>ключевое слово</b> — например <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — и я поищу по всему сайту.\n\n"
        "Или вставь <b>ссылку с фильтрами</b> (<code>vinted.pl/catalog?...</code>), если хочешь бренд, "
        "размер и цену ровно так, как настроил сам."
    ),
    "domain_prompt": "🔎 Ищу: <b>{kw}</b>\n\nВ каком Vinted искать?",
    "preview_checking": "⏳ Проверяю запрос…",
    "preview_ok": "✅ Нашёл <b>{n}</b> объявлений по этому запросу.",
    "preview_fail": "⚠️ Сейчас проверить не вышло (лимит Vinted), но поиск можно сохранить.",
    "name_prompt": "Как назвать этот поиск?",
    "btn_auto_name": "✨ Авто-название",
    "name_set": "Название: <b>{name}</b>\n\nКак часто проверять?",
    "interval_prompt": "⏱ Новый интервал проверки:",
    "interval_custom": "Пришли интервал в секундах (минимум {min}).",
    "need_number": "Нужно число секунд. Попробуй ещё раз или /cancel",
    "added_ok": "✅ Поиск добавлен. Слежу за новыми объявлениями.",
    "baseline_note": "💡 То, что уже выложено, я молча запомнил — придёт только то, что появится <i>дальше</i>.",

    "list_empty": "📋 Поисков пока нет.\nЖми «Новый поиск», чтобы добавить первый.",
    "list_title": "📋 <b>Мои поиски</b> ({n})\nВыбери, чтобы открыть:",
    "btn_pause_all": "⏸ Пауза всех",
    "btn_resume_all": "▶️ Запустить все",
    "btn_export": "📤 Экспорт поисков",
    "btn_new_short": "➕ Новый",

    "card_active": "🟢 Активен",
    "card_paused": "⏸ На паузе",
    "card_error": "⚠️ Последняя проверка не удалась",
    "card_interval": "⏱ Интервал: <b>{interval}</b>",
    "card_found": "🆕 Найдено: <b>{total}</b>   📅 сегодня: <b>{today}</b>",
    "card_last": "🕐 Последняя проверка: {ago}",
    "card_kwi": "🔔 Фильтр +: <code>{v}</code>",
    "card_kwe": "🔕 Фильтр −: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">ссылка поиска ↗</a>",
    "btn_price": "💶 Цена",
    "price_prompt": "Пришли диапазон цены: <code>10-50</code>, <code>-50</code> (только макс.) или <code>10-</code> (только мин.). <code>-</code> — убрать фильтр.",
    "price_updated": "✅ Фильтр цены обновлён.",
    "price_invalid": "Не похоже на диапазон. Примеры: <code>10-50</code>, <code>-50</code>, <code>10-</code>, или <code>-</code> — убрать.",
    "card_pricef": "💶 Цена: <code>{v}</code>",
    "cap_size": "📏 Размер: {v}",
    "cap_protect": "  <i>(с защитой {v})</i>",
    "cap_open": "Открыть на Vinted ↗",
    "cap_untitled": "Без названия",
    "deal_badge": "🔥 Заметно дешевле похожих",
    "btn_presets": "⭐ Готовые поиски",
    "presets_prompt": "Выбери бренд — настрою поиск:",
    "card_price_now": "💹 Сейчас от <b>{price}</b>{usd} · {n} объявл.",

    "btn_resume": "▶️ Запустить",
    "btn_pause": "⏸ Пауза",
    "btn_check": "🔍 Проверить",
    "btn_rename": "✏️ Имя",
    "btn_interval": "⏱ Интервал",
    "btn_kwi": "🔔 Фильтр +",
    "btn_kwe": "🔕 Фильтр −",
    "btn_url": "🔗 Ссылка",
    "btn_delete": "🗑 Удалить",
    "btn_back_list": "⬅️ К списку",

    "check_running": "🔍 Проверяю Vinted…",
    "check_found": "🔍 Нашёл и отправил: +{n}",
    "check_none": "🔍 Новых объявлений нет",
    "check_error": "⚠️ Vinted сейчас не отвечает",

    "delete_confirm": "🗑 Удалить поиск «{name}»?\nЭто необратимо.",
    "btn_delete_yes": "🗑 Да, удалить",
    "btn_delete_no": "↩️ Оставить",

    "edit_name": "✏️ Пришли новое название поиска:",
    "edit_url": "🔗 Текущая ссылка:\n<code>{url}</code>\n\nПришли новую ссылку поиска Vinted:",
    "edit_kwi": "🔔 <b>Фильтр +</b> — слать только если в названии есть эти слова.\nСейчас: <code>{v}</code>\n\nПришли слова через запятую (или «-» чтобы очистить):",
    "edit_kwe": "🔕 <b>Фильтр −</b> — пропускать объявления с этими словами.\nСейчас: <code>{v}</code>\n\nПришли слова через запятую (или «-» чтобы очистить):",
    "url_invalid": "Это не похоже на ссылку Vinted. Пришли ссылку или /cancel",
    "name_updated": "✅ Имя обновлено",
    "url_updated": "✅ Ссылка обновлена",
    "kwi_updated": "✅ Фильтр + обновлён",
    "kwe_updated": "✅ Фильтр − обновлён",
    "interval_updated": "✅ Интервал обновлён",
    "cancelled": "Отменил. /start — в меню.",

    "notify_overflow": "… и ещё <b>{n}</b> новых по «{name}» (показаны самые свежие).",

    "stats_title": "📊 <b>Статистика</b>",
    "stats_searches": "📂 Поисков: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Найдено всего: <b>{n}</b>",
    "stats_today": "📅 За сегодня: <b>{n}</b>",
    "stats_by_search": "<b>По поискам:</b>",

    "help": (
        "❓ <b>Как пользоваться</b>\n\n"
        "<b>Быстро:</b> жми <b>➕ Новый поиск</b> и пришли <b>ключевое слово</b> "
        "(<code>stone island</code>, <code>nike tn</code>) — ищу по всему сайту.\n\n"
        "<b>Точно:</b> открой Vinted, настрой фильтры (бренд, размер, цена, состояние), "
        "скопируй ссылку из адресной строки и пришли мне. Буду следить ровно за этим.\n\n"
        "Дальше задашь название и частоту проверки.\n\n"
        "После этого получаешь <b>каждое новое объявление</b>: альбом фото, цену, размер, бренд, ссылку.\n\n"
        "🔔 <b>Фильтр +</b> — слать только если в названии есть эти слова.\n"
        "🔕 <b>Фильтр −</b> — пропускать объявления с этими словами.\n"
        "🔍 <b>Проверить</b> — опросить поиск прямо сейчас.\n\n"
        "🔒 <b>Твой аккаунт Vinted я не трогаю вообще.</b> Только читаю публичные объявления и пишу тебе сюда — "
        "без входа в аккаунт, автовыкупа и перезаливов. Ничего, из-за чего аккаунт можно потерять."
    ),
    "support_line": "🛟 Что-то не работает или есть вопрос? Напиши нам: {sup} — ответит живой человек.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert пока работает по приглашениям.</b>\n\n"
        "Пришли ключ-инвайт (он выглядит как <code>GRL-XXXX-XXXX</code>), и я включу <b>Pro на {days} дней</b> — без карты.\n\n"
        "Ключа нет? Встань в лист ожидания — доступ открываем небольшими партиями."
    ),
    "gate_btn_waitlist": "⏳ Встать в лист ожидания",
    "waitlist_joined": "✅ Ты в листе ожидания, позиция <b>#{n}</b>. Напишу сюда, когда доступ будет готов.",
    "waitlist_already": "⏳ Ты в листе ожидания, позиция <b>#{n}</b>. Появился ключ? Просто пришли его сюда.",
    "key_ok": "🔑 <b>Ключ принят!</b> Pro включён на {days} дней, до {date}. Добавь первый поиск 👇",
    "key_used": "⚠️ Этот ключ уже использован. Один ключ открывает один аккаунт.",
    "key_bad": "❌ Такой ключ не подходит. Проверь написание или спроси у того, кто его дал.",
    "key_ratelimited": "⏱ Слишком много попыток. Попробуй через час.",
    "invite_granted": "🎉 <b>Доступ открыт!</b> Pro на {days} дней, до {date}. Нажми /start, чтобы начать.",

    "diag_running": "🩺 Проверяю доступность Vinted…",
    "diag_title": "🩺 <b>Диагностика</b>",
    "diag_host": "Домен: <b>{host}</b>",
    "diag_ok": "🟢 доступен",
    "diag_fail": "🔴 недоступен (Cloudflare/Datadome или сеть)",
    "diag_status": "Статус API: {status}",
    "diag_proxy_on": "Прокси: включён",
    "diag_proxy_off": "Прокси: нет (прямое подключение)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Пробный Pro",
    "plan_title": "💎 <b>Твой тариф</b>",
    "plan_current": "Сейчас: <b>{plan}</b>",
    "plan_until": "Активен до <b>{date}</b> (осталось дней: {days})",
    "plan_free_desc": "Free: <b>1 поиск</b>, проверка раз в <b>15 минут</b>.",
    "plan_pitch": (
        "Одна удачная находка окупает год подписки.\n\n"
        "<b>Basic</b> — 3 поиска, проверка раз в <b>2 минуты</b>\n"
        "<b>Pro</b> — <b>без ограничений</b> по поискам, проверка раз в <b>30 секунд</b>, приоритет в очереди\n\n"
        "Чем чаще проверка, тем раньше видишь недооценённый лот — а на Vinted хорошее разбирают за минуты."
    ),
    "plan_safety": "🔒 Твой аккаунт Vinted мы не трогаем — только алерты, никакой автоматизации с твоей стороны.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro на год — {price} (2 месяца в подарок)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nЧем оплатишь?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Крипта (USDT, TON, BTC)",
    "btn_pay_open": "💳 Открыть оплату",
    "btn_pay_check": "🔄 Оплатил — проверить",
    "period_month": "1 месяц",
    "period_year": "12 месяцев",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Тариф {plan} на {period}. Включается сразу.",
    "crypto_created": (
        "₿ <b>Счёт создан</b> — {amount} USDT\n\n"
        "Жми кнопку и оплати в Crypto Pay (USDT, TON, BTC и другие).\n"
        "Тариф включится автоматически через несколько секунд после оплаты."
    ),
    "crypto_unavailable": "₿ Оплата криптой временно недоступна. Telegram Stars работают.",
    "pay_ok": "🎉 <b>Оплата получена. {plan} активен до {date}.</b>\n\nДобавляй поиски, которые откладывал.",
    "pay_pending": "⏳ Платёж пока не вижу. Если только что оплатил — подожди пару секунд и нажми ещё раз.",
    "pay_failed": "⚠️ Платёж не прошёл. Деньги не списаны.",

    "limit_searches": (
        "🔒 <b>{plan} — лимит поисков: {limit}</b>\n\n"
        "Сейчас у тебя {current}. Подними тариф и добавляй сколько нужно — "
        "обычно держат по одному поиску на каждый бренд, который перепродают."
    ),
    "limit_interval": (
        "🔒 <b>Проверка раз в {interval} — это {needed}.</b>\n\n"
        "На {plan} проверяю раз в {current}. На Vinted вещь по хорошей цене уходит за минуты, "
        "так что интервал тут решает всё."
    ),
    "btn_upgrade": "💎 Поднять тариф",

    "trial_ends_soon": (
        "⏳ <b>Пробный Pro заканчивается через {days} дня.</b>\n\n"
        "За это время я нашёл тебе <b>{found}</b> объявлений.\n"
        "Продолжим — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "Пробный Pro закончился — ты на Free: 1 поиск, проверка раз в 15 минут.\n\n"
        "За пробный период я нашёл тебе <b>{found}</b> объявлений. "
        "Ничего не удалено, всё просто на паузе — выбери тариф, и оно снова заработает."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} заканчивается через {days} дня.</b>\n\n"
        "Продли — и ничего не изменится, поиски продолжат работать без паузы."
    ),
    "plan_expired": (
        "Тариф {plan} закончился — ты на Free.\n\n"
        "Поиски на паузе, не удалены. Продлишь — продолжат с того же места."
    ),
    "paused_by_limit": "⏸ Поставлен на паузу из-за смены тарифа: «{name}»",
    "digest_missed": (
        "📬 <b>Пока ты на Free</b>\n\n"
        "Твои поиски на паузе поймали бы <b>{n}</b> новых объявлений за последние {days} дней. "
        "Вот столько ты сейчас не видишь."
    ),

    "btn_invite": "🎁 Пригласить друга",
    "invite_h": "🎁 <b>Пригласить друга</b>",
    "invite_p": "Отправь эту ссылку тому, кто перепродаёт на Vinted. Когда он оплатит любой тариф, <b>тебе прилетит {days} дней Pro</b> — а он и так начнёт с бесплатной недели Pro.",
    "invite_link": "Твоя ссылка:",
    "invite_stat": "Пришло по ссылке: <b>{n}</b> · из них оплатили: <b>{p}</b>",
    "ref_reward": "🎁 <b>Приглашённый тобой оплатил подписку.</b>\n\nТебе начислено {days} дней Pro — теперь тариф до <b>{date}</b>. Спасибо, что рассказываешь о нас.",
    "no_access": "Нет доступа. Пришли /start",
    "admin_only": "Только для админов.",
    "unit_h": "ч",
    "unit_min": "мин",
    "unit_sec": "сек",
    "ago_never": "ещё не было",
    "ago_now": "только что",
    "ago_min": "{n} мин назад",
    "ago_h": "{n} ч назад",
    "ago_d": "{n} дн назад",
},

# ============================================================ FRANÇAIS
"fr": {
    "btn_menu": "🛍 Menu",
    "btn_add": "➕ Nouvelle recherche",
    "btn_list": "📋 Mes recherches",
    "kb_pinned": "🛍 Le bouton <b>Menu</b> reste toujours en bas 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Je surveille Vinted pour toi et j'envoie chaque nouvelle annonce dès sa mise en ligne — photos, prix, taille, lien.",
    "menu_searches": "📂 Recherches : <b>{total}</b>   🟢 actives : <b>{active}</b>   ⏸ en pause : <b>{paused}</b>",
    "menu_found": "🆕 Trouvé au total : <b>{total}</b>   📅 aujourd'hui : <b>{today}</b>",
    "menu_plan": "💎 Formule : <b>{plan}</b>{until}",
    "menu_plan_until": " · jusqu'au {date}",

    "btn_new_search": "➕ Nouvelle recherche",
    "btn_my_searches": "📋 Mes recherches",
    "btn_stats": "📊 Statistiques",
    "btn_diag": "🩺 Diagnostic",
    "btn_help": "❓ Comment ça marche",
    "btn_plan": "💎 Formule",
    "btn_lang": "🌐 Langue",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Retour",
    "btn_back_menu": "⬅️ Menu",
    "btn_cancel": "✖️ Annuler",

    "welcome": (
        "👋 <b>Bienvenue sur Grailert.</b>\n\n"
        "Dis-moi ce que tu cherches et je te préviens à la seconde où c'est mis en ligne — "
        "avant ceux qui font défiler l'appli.\n\n"
        "🎁 <b>Ton essai Pro de {days} jours est actif</b> — recherches illimitées, vérification toutes les 30 secondes."
    ),
    "welcome_back": "👋 Content de te revoir.",
    "lang_choose": "🌐 Choisis ta langue :",
    "lang_saved": "✅ Langue réglée sur le français.",

    "add_prompt": (
        "➕ <b>Nouvelle recherche</b>\n\n"
        "Envoie un <b>mot-clé</b> — par exemple <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — et je cherche sur tout le site.\n\n"
        "Ou colle un <b>lien Vinted filtré</b> (<code>vinted.fr/catalog?...</code>) si tu veux la marque, "
        "la taille et le prix exactement comme tu les as réglés."
    ),
    "domain_prompt": "🔎 Recherche : <b>{kw}</b>\n\nSur quel Vinted ?",
    "preview_checking": "⏳ Je vérifie cette recherche…",
    "preview_ok": "✅ <b>{n}</b> annonces trouvées pour cette recherche.",
    "preview_fail": "⚠️ Impossible de vérifier maintenant (limite Vinted), mais tu peux quand même enregistrer.",
    "name_prompt": "Comment nommer cette recherche ?",
    "btn_auto_name": "✨ Nom auto",
    "name_set": "Nom : <b>{name}</b>\n\nÀ quelle fréquence dois-je vérifier ?",
    "interval_prompt": "⏱ Nouvel intervalle :",
    "interval_custom": "Envoie l'intervalle en secondes (minimum {min}).",
    "need_number": "Il me faut un nombre de secondes. Réessaie ou /cancel",
    "added_ok": "✅ Recherche ajoutée. Je surveille les nouvelles annonces.",
    "baseline_note": "💡 J'ai noté sans rien envoyer ce qui est déjà en ligne : tu ne reçois que ce qui arrive <i>ensuite</i>.",

    "list_empty": "📋 Aucune recherche pour l'instant.\nAppuie sur « Nouvelle recherche » pour commencer.",
    "list_title": "📋 <b>Mes recherches</b> ({n})\nChoisis-en une :",
    "btn_pause_all": "⏸ Tout mettre en pause",
    "btn_resume_all": "▶️ Tout relancer",
    "btn_export": "📤 Exporter",
    "btn_new_short": "➕ Nouvelle",

    "card_active": "🟢 Active",
    "card_paused": "⏸ En pause",
    "card_error": "⚠️ Dernière vérification échouée",
    "card_interval": "⏱ Intervalle : <b>{interval}</b>",
    "card_found": "🆕 Trouvé : <b>{total}</b>   📅 aujourd'hui : <b>{today}</b>",
    "card_last": "🕐 Dernière vérification : {ago}",
    "card_kwi": "🔔 Inclure : <code>{v}</code>",
    "card_kwe": "🔕 Exclure : <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">lien de la recherche ↗</a>",
    "btn_price": "💶 Prix",
    "price_prompt": "Envoie une fourchette de prix : <code>10-50</code>, <code>-50</code> (max seul) ou <code>10-</code> (min seul). Envoie <code>-</code> pour retirer.",
    "price_updated": "✅ Filtre de prix mis à jour.",
    "price_invalid": "Format invalide. Exemples : <code>10-50</code>, <code>-50</code>, <code>10-</code>, ou <code>-</code> pour retirer.",
    "card_pricef": "💶 Prix : <code>{v}</code>",
    "cap_size": "📏 Taille : {v}",
    "cap_protect": "  <i>({v} avec protection acheteur)</i>",
    "cap_open": "Ouvrir sur Vinted ↗",
    "cap_untitled": "Sans titre",
    "deal_badge": "🔥 Bien moins cher que les annonces similaires",
    "btn_presets": "⭐ Recherches prêtes",
    "presets_prompt": "Choisis une marque, je configure la recherche :",
    "card_price_now": "💹 À partir de <b>{price}</b>{usd} · {n} annonces",

    "btn_resume": "▶️ Relancer",
    "btn_pause": "⏸ Pause",
    "btn_check": "🔍 Vérifier",
    "btn_rename": "✏️ Nom",
    "btn_interval": "⏱ Intervalle",
    "btn_kwi": "🔔 Inclure",
    "btn_kwe": "🔕 Exclure",
    "btn_url": "🔗 Lien",
    "btn_delete": "🗑 Supprimer",
    "btn_back_list": "⬅️ Retour à la liste",

    "check_running": "🔍 Je vérifie Vinted…",
    "check_found": "🔍 Trouvé et envoyé : +{n}",
    "check_none": "🔍 Rien de nouveau",
    "check_error": "⚠️ Vinted ne répond pas pour le moment",

    "delete_confirm": "🗑 Supprimer la recherche « {name} » ?\nC'est irréversible.",
    "btn_delete_yes": "🗑 Oui, supprimer",
    "btn_delete_no": "↩️ Garder",

    "edit_name": "✏️ Envoie le nouveau nom :",
    "edit_url": "🔗 Lien actuel :\n<code>{url}</code>\n\nEnvoie le nouveau lien Vinted :",
    "edit_kwi": "🔔 <b>Filtre inclure</b> — n'alerter que si le titre contient ces mots.\nActuel : <code>{v}</code>\n\nEnvoie les mots séparés par des virgules (ou « - » pour effacer) :",
    "edit_kwe": "🔕 <b>Filtre exclure</b> — ignorer les annonces avec ces mots.\nActuel : <code>{v}</code>\n\nEnvoie les mots séparés par des virgules (ou « - » pour effacer) :",
    "url_invalid": "Ça ne ressemble pas à un lien Vinted. Envoie un lien ou /cancel",
    "name_updated": "✅ Nom mis à jour",
    "url_updated": "✅ Lien mis à jour",
    "kwi_updated": "✅ Filtre inclure mis à jour",
    "kwe_updated": "✅ Filtre exclure mis à jour",
    "interval_updated": "✅ Intervalle mis à jour",
    "cancelled": "Annulé. /start pour le menu.",

    "notify_overflow": "… et <b>{n}</b> autres nouveautés pour « {name} » (les plus récentes affichées).",

    "stats_title": "📊 <b>Tes statistiques</b>",
    "stats_searches": "📂 Recherches : <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Trouvé au total : <b>{n}</b>",
    "stats_today": "📅 Aujourd'hui : <b>{n}</b>",
    "stats_by_search": "<b>Par recherche :</b>",

    "help": (
        "❓ <b>Mode d'emploi</b>\n\n"
        "<b>Rapide :</b> appuie sur <b>➕ Nouvelle recherche</b> et envoie un <b>mot-clé</b> "
        "(<code>stone island</code>, <code>nike tn</code>). Je cherche sur tout le site.\n\n"
        "<b>Précis :</b> ouvre Vinted, règle tes filtres (marque, taille, prix, état), "
        "copie le lien de la barre d'adresse et envoie-le moi. Je surveille exactement ça.\n\n"
        "Ensuite tu choisis un nom et la fréquence.\n\n"
        "Après ça tu reçois <b>chaque nouvelle annonce</b> : album photo, prix, taille, marque, lien.\n\n"
        "🔔 <b>Inclure</b> — n'alerter que si le titre contient ces mots.\n"
        "🔕 <b>Exclure</b> — ignorer les annonces contenant ces mots.\n"
        "🔍 <b>Vérifier</b> — interroger la recherche tout de suite.\n\n"
        "🔒 <b>Je ne touche jamais à ton compte Vinted.</b> Je lis seulement les annonces publiques et je t'écris ici — "
        "aucune connexion, aucun achat automatique, aucune republication. Rien qui mette ton compte en danger."
    ),
    "support_line": "🛟 Un souci ou une question ? Écris-nous : {sup} — un humain te répond.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert est sur invitation pour le moment.</b>\n\n"
        "Envoie-moi ta clé d'invitation (elle ressemble à <code>GRL-XXXX-XXXX</code>) et j'active <b>{days} jours de Pro</b> — sans carte bancaire.\n\n"
        "Pas de clé ? Inscris-toi sur la liste d'attente — on ouvre l'accès par petites vagues."
    ),
    "gate_btn_waitlist": "⏳ Rejoindre la liste d'attente",
    "waitlist_joined": "✅ Tu es sur la liste d'attente, position <b>#{n}</b>. Je t'écris ici dès que ton accès est prêt.",
    "waitlist_already": "⏳ Tu es sur la liste d'attente, position <b>#{n}</b>. Tu as une clé ? Envoie-la ici.",
    "key_ok": "🔑 <b>Clé acceptée !</b> Pro activé pour {days} jours, jusqu'au {date}. Ajoute ta première recherche 👇",
    "key_used": "⚠️ Cette clé a déjà été utilisée. Une clé ouvre un seul compte.",
    "key_bad": "❌ Cette clé ne fonctionne pas. Vérifie l'orthographe ou demande à la personne qui te l'a donnée.",
    "key_ratelimited": "⏱ Trop de tentatives. Réessaie dans une heure.",
    "invite_granted": "🎉 <b>Ton accès est prêt !</b> Pro pour {days} jours, jusqu'au {date}. Envoie /start pour commencer.",

    "diag_running": "🩺 Je vérifie si Vinted répond…",
    "diag_title": "🩺 <b>Diagnostic</b>",
    "diag_host": "Domaine : <b>{host}</b>",
    "diag_ok": "🟢 accessible",
    "diag_fail": "🔴 inaccessible (Cloudflare/Datadome ou réseau)",
    "diag_status": "État de l'API : {status}",
    "diag_proxy_on": "Proxy : activé",
    "diag_proxy_off": "Proxy : désactivé (connexion directe)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Essai Pro",
    "plan_title": "💎 <b>Ta formule</b>",
    "plan_current": "Actuelle : <b>{plan}</b>",
    "plan_until": "Active jusqu'au <b>{date}</b> ({days} jours restants)",
    "plan_free_desc": "Free : <b>1 recherche</b>, vérifiée toutes les <b>15 minutes</b>.",
    "plan_pitch": (
        "Une seule bonne trouvaille paie une année entière.\n\n"
        "<b>Basic</b> — 3 recherches, vérification toutes les <b>2 minutes</b>\n"
        "<b>Pro</b> — recherches <b>illimitées</b>, vérification toutes les <b>30 secondes</b>, file prioritaire\n\n"
        "Plus la vérification est rapide, plus tôt tu vois une annonce sous-évaluée — et sur Vinted "
        "les bonnes partent en quelques minutes."
    ),
    "plan_safety": "🔒 On ne touche jamais à ton compte Vinted — uniquement des alertes, rien d'automatisé de ton côté.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro un an — {price} (2 mois offerts)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nComment veux-tu payer ?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Crypto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Ouvrir le paiement",
    "btn_pay_check": "🔄 J'ai payé — vérifier",
    "period_month": "1 mois",
    "period_year": "12 mois",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Formule {plan} pour {period}. Activation immédiate.",
    "crypto_created": (
        "₿ <b>Facture créée</b> — {amount} USDT\n\n"
        "Appuie sur le bouton pour payer dans Crypto Pay (USDT, TON, BTC et autres).\n"
        "L'activation est automatique quelques secondes après le paiement."
    ),
    "crypto_unavailable": "₿ Le paiement en crypto est temporairement indisponible. Les Telegram Stars fonctionnent.",
    "pay_ok": "🎉 <b>Paiement reçu. {plan} est actif jusqu'au {date}.</b>\n\nAjoute les recherches que tu gardais de côté.",
    "pay_pending": "⏳ Je ne vois pas encore le paiement. Si tu viens de payer, attends quelques secondes et revérifie.",
    "pay_failed": "⚠️ Le paiement n'a pas abouti. Rien n'a été débité.",

    "limit_searches": (
        "🔒 <b>{plan} — limite de recherches : {limit}</b>\n\n"
        "Tu en surveilles {current} en ce moment. Passe au niveau supérieur et ajoutes-en autant que tu veux — "
        "la plupart en gardent une par marque revendue."
    ),
    "limit_interval": (
        "🔒 <b>Une vérification toutes les {interval}, c'est {needed}.</b>\n\n"
        "En {plan} je vérifie toutes les {current}. Sur Vinted une pièce bien tarifée part en quelques minutes : "
        "l'intervalle, c'est tout le jeu."
    ),
    "btn_upgrade": "💎 Passer au niveau supérieur",

    "trial_ends_soon": (
        "⏳ <b>Ton essai Pro se termine dans {days} jours.</b>\n\n"
        "J'ai déjà trouvé <b>{found}</b> annonces pour toi.\n"
        "On continue — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "Ton essai Pro est terminé — tu es en Free : 1 recherche, vérifiée toutes les 15 minutes.\n\n"
        "Pendant l'essai j'ai trouvé <b>{found}</b> annonces pour toi. "
        "Rien n'est supprimé, tout est en pause — choisis une formule et tout repart."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} se termine dans {days} jours.</b>\n\n"
        "Renouvelle et rien ne change — tes recherches continuent sans interruption."
    ),
    "plan_expired": (
        "Ta formule {plan} est terminée — tu es en Free.\n\n"
        "Tes recherches sont en pause, pas supprimées. Renouvelle et elles reprennent où elles en étaient."
    ),
    "paused_by_limit": "⏸ Mise en pause suite au changement de formule : « {name} »",
    "digest_missed": (
        "📬 <b>Pendant que tu es en Free</b>\n\n"
        "Tes recherches en pause auraient attrapé <b>{n}</b> nouvelles annonces ces {days} derniers jours. "
        "C'est ce que tu ne vois pas."
    ),

    "btn_invite": "🎁 Inviter un ami",
    "invite_h": "🎁 <b>Inviter un ami</b>",
    "invite_p": "Envoie ce lien à quelqu'un qui revend sur Vinted. Quand il prend une formule, <b>tu reçois {days} jours de Pro</b> — et lui commence de toute façon avec une semaine de Pro offerte.",
    "invite_link": "Ton lien :",
    "invite_stat": "Venus par ton lien : <b>{n}</b> · dont payants : <b>{p}</b>",
    "ref_reward": "🎁 <b>Quelqu'un que tu as invité vient de s'abonner.</b>\n\n{days} jours de Pro ajoutés — ta formule court jusqu'au <b>{date}</b>. Merci d'en parler autour de toi.",
    "no_access": "Pas d'accès. Envoie /start",
    "admin_only": "Réservé aux admins.",
    "unit_h": "h",
    "unit_min": "min",
    "unit_sec": "s",
    "ago_never": "pas encore",
    "ago_now": "à l'instant",
    "ago_min": "il y a {n} min",
    "ago_h": "il y a {n} h",
    "ago_d": "il y a {n} j",
},

# ============================================================ DEUTSCH
"de": {
    "btn_menu": "🛍 Menü",
    "btn_add": "➕ Neue Suche",
    "btn_list": "📋 Meine Suchen",
    "kb_pinned": "🛍 Der <b>Menü</b>-Button ist ab jetzt immer unten 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Ich beobachte Vinted für dich und schicke jedes neue Angebot sofort — Fotos, Preis, Größe, Link.",
    "menu_searches": "📂 Suchen: <b>{total}</b>   🟢 aktiv: <b>{active}</b>   ⏸ pausiert: <b>{paused}</b>",
    "menu_found": "🆕 Insgesamt gefunden: <b>{total}</b>   📅 heute: <b>{today}</b>",
    "menu_plan": "💎 Tarif: <b>{plan}</b>{until}",
    "menu_plan_until": " · bis {date}",

    "btn_new_search": "➕ Neue Suche",
    "btn_my_searches": "📋 Meine Suchen",
    "btn_stats": "📊 Statistik",
    "btn_diag": "🩺 Diagnose",
    "btn_help": "❓ So funktioniert's",
    "btn_plan": "💎 Tarif",
    "btn_lang": "🌐 Sprache",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Zurück",
    "btn_back_menu": "⬅️ Menü",
    "btn_cancel": "✖️ Abbrechen",

    "welcome": (
        "👋 <b>Willkommen bei Grailert.</b>\n\n"
        "Sag mir, wonach du suchst, und ich melde mich in der Sekunde, in der es eingestellt wird — "
        "bevor es jemand beim Scrollen sieht.\n\n"
        "🎁 <b>Deine {days}-tägige Pro-Testphase läuft</b> — unbegrenzte Suchen, Prüfung alle 30 Sekunden."
    ),
    "welcome_back": "👋 Schön, dass du wieder da bist.",
    "lang_choose": "🌐 Wähle deine Sprache:",
    "lang_saved": "✅ Sprache auf Deutsch gestellt.",

    "add_prompt": (
        "➕ <b>Neue Suche</b>\n\n"
        "Schick ein <b>Stichwort</b> — etwa <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — und ich durchsuche die ganze Seite.\n\n"
        "Oder füge einen <b>gefilterten Vinted-Link</b> ein (<code>vinted.de/catalog?...</code>), wenn Marke, "
        "Größe und Preis genau so bleiben sollen, wie du sie eingestellt hast."
    ),
    "domain_prompt": "🔎 Suche nach: <b>{kw}</b>\n\nIn welchem Vinted-Land?",
    "preview_checking": "⏳ Ich prüfe die Suche…",
    "preview_ok": "✅ <b>{n}</b> Angebote zu dieser Suche gefunden.",
    "preview_fail": "⚠️ Gerade nicht prüfbar (Vinted-Limit), speichern kannst du sie trotzdem.",
    "name_prompt": "Wie soll die Suche heißen?",
    "btn_auto_name": "✨ Automatisch benennen",
    "name_set": "Name: <b>{name}</b>\n\nWie oft soll ich prüfen?",
    "interval_prompt": "⏱ Neues Prüfintervall:",
    "interval_custom": "Schick das Intervall in Sekunden (mindestens {min}).",
    "need_number": "Ich brauche eine Sekundenzahl. Nochmal oder /cancel",
    "added_ok": "✅ Suche angelegt. Ich achte ab jetzt auf neue Angebote.",
    "baseline_note": "💡 Was schon online ist, habe ich still vermerkt — du bekommst nur, was <i>ab jetzt</i> dazukommt.",

    "list_empty": "📋 Noch keine Suchen.\nTippe auf «Neue Suche», um die erste anzulegen.",
    "list_title": "📋 <b>Meine Suchen</b> ({n})\nWähle eine aus:",
    "btn_pause_all": "⏸ Alle pausieren",
    "btn_resume_all": "▶️ Alle starten",
    "btn_export": "📤 Suchen exportieren",
    "btn_new_short": "➕ Neu",

    "card_active": "🟢 Aktiv",
    "card_paused": "⏸ Pausiert",
    "card_error": "⚠️ Letzte Prüfung fehlgeschlagen",
    "card_interval": "⏱ Intervall: <b>{interval}</b>",
    "card_found": "🆕 Gefunden: <b>{total}</b>   📅 heute: <b>{today}</b>",
    "card_last": "🕐 Letzte Prüfung: {ago}",
    "card_kwi": "🔔 Einschließen: <code>{v}</code>",
    "card_kwe": "🔕 Ausschließen: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">Such-Link ↗</a>",
    "btn_price": "💶 Preis",
    "price_prompt": "Sende eine Preisspanne: <code>10-50</code>, <code>-50</code> (nur max.) oder <code>10-</code> (nur min.). Sende <code>-</code> zum Entfernen.",
    "price_updated": "✅ Preisfilter aktualisiert.",
    "price_invalid": "Keine gültige Spanne. Beispiele: <code>10-50</code>, <code>-50</code>, <code>10-</code>, oder <code>-</code> zum Entfernen.",
    "card_pricef": "💶 Preis: <code>{v}</code>",
    "cap_size": "📏 Größe: {v}",
    "cap_protect": "  <i>({v} mit Käuferschutz)</i>",
    "cap_open": "Auf Vinted öffnen ↗",
    "cap_untitled": "Ohne Titel",
    "deal_badge": "🔥 Deutlich günstiger als ähnliche Anzeigen",
    "btn_presets": "⭐ Fertige Suchen",
    "presets_prompt": "Wähle eine Marke, ich richte die Suche ein:",
    "card_price_now": "💹 Ab <b>{price}</b>{usd} · aktuell {n} Angebote",

    "btn_resume": "▶️ Starten",
    "btn_pause": "⏸ Pause",
    "btn_check": "🔍 Jetzt prüfen",
    "btn_rename": "✏️ Name",
    "btn_interval": "⏱ Intervall",
    "btn_kwi": "🔔 Einschließen",
    "btn_kwe": "🔕 Ausschließen",
    "btn_url": "🔗 Link",
    "btn_delete": "🗑 Löschen",
    "btn_back_list": "⬅️ Zur Liste",

    "check_running": "🔍 Ich prüfe Vinted…",
    "check_found": "🔍 Gefunden und geschickt: +{n}",
    "check_none": "🔍 Nichts Neues",
    "check_error": "⚠️ Vinted antwortet gerade nicht",

    "delete_confirm": "🗑 Suche «{name}» löschen?\nDas lässt sich nicht rückgängig machen.",
    "btn_delete_yes": "🗑 Ja, löschen",
    "btn_delete_no": "↩️ Behalten",

    "edit_name": "✏️ Schick den neuen Namen:",
    "edit_url": "🔗 Aktueller Link:\n<code>{url}</code>\n\nSchick den neuen Vinted-Link:",
    "edit_kwi": "🔔 <b>Einschließen</b> — nur melden, wenn der Titel diese Wörter enthält.\nAktuell: <code>{v}</code>\n\nWörter mit Komma trennen (oder «-» zum Leeren):",
    "edit_kwe": "🔕 <b>Ausschließen</b> — Angebote mit diesen Wörtern überspringen.\nAktuell: <code>{v}</code>\n\nWörter mit Komma trennen (oder «-» zum Leeren):",
    "url_invalid": "Das sieht nicht nach einem Vinted-Link aus. Schick einen Link oder /cancel",
    "name_updated": "✅ Name aktualisiert",
    "url_updated": "✅ Link aktualisiert",
    "kwi_updated": "✅ Einschließen-Filter aktualisiert",
    "kwe_updated": "✅ Ausschließen-Filter aktualisiert",
    "interval_updated": "✅ Intervall aktualisiert",
    "cancelled": "Abgebrochen. /start fürs Menü.",

    "notify_overflow": "… und <b>{n}</b> weitere neue zu «{name}» (die neuesten sind oben).",

    "stats_title": "📊 <b>Deine Statistik</b>",
    "stats_searches": "📂 Suchen: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Insgesamt gefunden: <b>{n}</b>",
    "stats_today": "📅 Heute: <b>{n}</b>",
    "stats_by_search": "<b>Nach Suche:</b>",

    "help": (
        "❓ <b>So geht's</b>\n\n"
        "<b>Schnell:</b> tippe auf <b>➕ Neue Suche</b> und schick ein <b>Stichwort</b> "
        "(<code>stone island</code>, <code>nike tn</code>). Ich durchsuche die ganze Seite.\n\n"
        "<b>Genau:</b> öffne Vinted, stell deine Filter ein (Marke, Größe, Preis, Zustand), "
        "kopiere den Link aus der Adresszeile und schick ihn mir. Genau das beobachte ich dann.\n\n"
        "Danach vergibst du Namen und Prüfintervall.\n\n"
        "Ab dann bekommst du <b>jedes neue Angebot</b>: Fotoalbum, Preis, Größe, Marke, Link.\n\n"
        "🔔 <b>Einschließen</b> — nur melden, wenn der Titel diese Wörter enthält.\n"
        "🔕 <b>Ausschließen</b> — Angebote mit diesen Wörtern überspringen.\n"
        "🔍 <b>Jetzt prüfen</b> — die Suche sofort abfragen.\n\n"
        "🔒 <b>Dein Vinted-Konto rühre ich nie an.</b> Ich lese nur öffentliche Angebote und schreibe dir hier — "
        "kein Login, kein Auto-Kauf, kein Neu-Einstellen. Nichts, was dein Konto gefährdet."
    ),
    "support_line": "🛟 Etwas geht nicht oder du hast eine Frage? Schreib uns: {sup} — ein Mensch antwortet.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert läuft derzeit nur mit Einladung.</b>\n\n"
        "Schick mir deinen Einladungsschlüssel (er sieht so aus: <code>GRL-XXXX-XXXX</code>) und ich schalte <b>{days} Tage Pro</b> frei — ohne Karte.\n\n"
        "Noch keinen Schlüssel? Trag dich auf die Warteliste ein — wir öffnen den Zugang in kleinen Wellen."
    ),
    "gate_btn_waitlist": "⏳ Auf die Warteliste",
    "waitlist_joined": "✅ Du stehst auf der Warteliste, Position <b>#{n}</b>. Ich melde mich hier, sobald dein Zugang bereit ist.",
    "waitlist_already": "⏳ Du stehst auf der Warteliste, Position <b>#{n}</b>. Schlüssel bekommen? Schick ihn einfach hier.",
    "key_ok": "🔑 <b>Schlüssel angenommen!</b> Pro ist für {days} Tage aktiv, bis {date}. Leg deine erste Suche an 👇",
    "key_used": "⚠️ Dieser Schlüssel wurde schon benutzt. Ein Schlüssel öffnet genau ein Konto.",
    "key_bad": "❌ Dieser Schlüssel funktioniert nicht. Prüf die Schreibweise oder frag die Person, die ihn dir gegeben hat.",
    "key_ratelimited": "⏱ Zu viele Versuche. Probier es in einer Stunde noch mal.",
    "invite_granted": "🎉 <b>Dein Zugang ist da!</b> Pro für {days} Tage, bis {date}. Schick /start, um loszulegen.",

    "diag_running": "🩺 Ich prüfe, ob Vinted antwortet…",
    "diag_title": "🩺 <b>Diagnose</b>",
    "diag_host": "Domain: <b>{host}</b>",
    "diag_ok": "🟢 erreichbar",
    "diag_fail": "🔴 nicht erreichbar (Cloudflare/Datadome oder Netzwerk)",
    "diag_status": "API-Status: {status}",
    "diag_proxy_on": "Proxy: an",
    "diag_proxy_off": "Proxy: aus (direkte Verbindung)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Pro-Test",
    "plan_title": "💎 <b>Dein Tarif</b>",
    "plan_current": "Aktuell: <b>{plan}</b>",
    "plan_until": "Aktiv bis <b>{date}</b> (noch {days} Tage)",
    "plan_free_desc": "Free: <b>1 Suche</b>, Prüfung alle <b>15 Minuten</b>.",
    "plan_pitch": (
        "Ein einziger guter Fund zahlt ein ganzes Jahr.\n\n"
        "<b>Basic</b> — 3 Suchen, Prüfung alle <b>2 Minuten</b>\n"
        "<b>Pro</b> — <b>unbegrenzte</b> Suchen, Prüfung alle <b>30 Sekunden</b>, Vorrang in der Warteschlange\n\n"
        "Je schneller die Prüfung, desto früher siehst du ein unterbewertetes Angebot — und auf Vinted "
        "sind die guten in Minuten weg."
    ),
    "plan_safety": "🔒 Wir fassen dein Vinted-Konto nie an — nur Benachrichtigungen, nichts Automatisches auf deiner Seite.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro für ein Jahr — {price} (2 Monate gratis)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nWie möchtest du zahlen?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Krypto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Zahlung öffnen",
    "btn_pay_check": "🔄 Bezahlt — prüfen",
    "period_month": "1 Monat",
    "period_year": "12 Monate",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Tarif {plan} für {period}. Sofort aktiv.",
    "crypto_created": (
        "₿ <b>Rechnung erstellt</b> — {amount} USDT\n\n"
        "Tippe auf den Button und zahle in Crypto Pay (USDT, TON, BTC und mehr).\n"
        "Die Freischaltung erfolgt automatisch wenige Sekunden nach der Zahlung."
    ),
    "crypto_unavailable": "₿ Krypto-Zahlung ist gerade nicht verfügbar. Telegram Stars funktionieren.",
    "pay_ok": "🎉 <b>Zahlung erhalten. {plan} ist aktiv bis {date}.</b>\n\nLeg die Suchen an, die du dir aufgehoben hast.",
    "pay_pending": "⏳ Die Zahlung sehe ich noch nicht. Falls du gerade bezahlt hast, warte kurz und prüfe erneut.",
    "pay_failed": "⚠️ Die Zahlung ist nicht durchgegangen. Es wurde nichts abgebucht.",

    "limit_searches": (
        "🔒 <b>{plan} — Suchen-Limit: {limit}</b>\n\n"
        "Du beobachtest gerade {current}. Mit einem höheren Tarif legst du so viele an, wie du willst — "
        "die meisten führen eine pro Marke, die sie weiterverkaufen."
    ),
    "limit_interval": (
        "🔒 <b>Prüfung alle {interval} gehört zu {needed}.</b>\n\n"
        "In {plan} prüfe ich alle {current}. Auf Vinted ist ein gut bepreistes Teil in Minuten weg — "
        "am Intervall hängt alles."
    ),
    "btn_upgrade": "💎 Upgrade",

    "trial_ends_soon": (
        "⏳ <b>Deine Pro-Testphase endet in {days} Tagen.</b>\n\n"
        "Bisher habe ich <b>{found}</b> Angebote für dich gefunden.\n"
        "Lass es weiterlaufen — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "Deine Pro-Testphase ist vorbei — du bist jetzt auf Free: 1 Suche, Prüfung alle 15 Minuten.\n\n"
        "Während des Tests habe ich <b>{found}</b> Angebote für dich gefunden. "
        "Nichts ist gelöscht, alles nur pausiert — wähle einen Tarif und es läuft wieder."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} endet in {days} Tagen.</b>\n\n"
        "Verlängere, und nichts ändert sich — deine Suchen laufen ohne Lücke weiter."
    ),
    "plan_expired": (
        "Dein Tarif {plan} ist abgelaufen — du bist jetzt auf Free.\n\n"
        "Deine Suchen sind pausiert, nicht gelöscht. Nach der Verlängerung machen sie genau dort weiter."
    ),
    "paused_by_limit": "⏸ Wegen Tarifwechsel pausiert: «{name}»",
    "digest_missed": (
        "📬 <b>Während du auf Free bist</b>\n\n"
        "Deine pausierten Suchen hätten in den letzten {days} Tagen <b>{n}</b> neue Angebote erwischt. "
        "So viel siehst du gerade nicht."
    ),

    "btn_invite": "🎁 Freund einladen",
    "invite_h": "🎁 <b>Freund einladen</b>",
    "invite_p": "Schick diesen Link an jemanden, der auf Vinted weiterverkauft. Sobald er einen Tarif bezahlt, <b>bekommst du {days} Tage Pro</b> — und er startet ohnehin mit einer Gratiswoche Pro.",
    "invite_link": "Dein Link:",
    "invite_stat": "Über deinen Link gekommen: <b>{n}</b> · davon zahlend: <b>{p}</b>",
    "ref_reward": "🎁 <b>Jemand, den du eingeladen hast, hat gerade gebucht.</b>\n\n{days} Tage Pro gutgeschrieben — dein Tarif läuft jetzt bis <b>{date}</b>. Danke fürs Weitersagen.",
    "no_access": "Kein Zugriff. Schick /start",
    "admin_only": "Nur für Admins.",
    "unit_h": "Std",
    "unit_min": "Min",
    "unit_sec": "Sek",
    "ago_never": "noch nie",
    "ago_now": "gerade eben",
    "ago_min": "vor {n} Min",
    "ago_h": "vor {n} Std",
    "ago_d": "vor {n} T",
},

# ============================================================ ESPAÑOL
"es": {
    "btn_menu": "🛍 Menú",
    "btn_add": "➕ Nueva búsqueda",
    "btn_list": "📋 Mis búsquedas",
    "kb_pinned": "🛍 El botón <b>Menú</b> queda siempre abajo 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Vigilo Vinted por ti y te envío cada anuncio nuevo en cuanto se publica — fotos, precio, talla, enlace.",
    "menu_searches": "📂 Búsquedas: <b>{total}</b>   🟢 activas: <b>{active}</b>   ⏸ en pausa: <b>{paused}</b>",
    "menu_found": "🆕 Encontrado en total: <b>{total}</b>   📅 hoy: <b>{today}</b>",
    "menu_plan": "💎 Plan: <b>{plan}</b>{until}",
    "menu_plan_until": " · hasta {date}",

    "btn_new_search": "➕ Nueva búsqueda",
    "btn_my_searches": "📋 Mis búsquedas",
    "btn_stats": "📊 Estadísticas",
    "btn_diag": "🩺 Diagnóstico",
    "btn_help": "❓ Cómo funciona",
    "btn_plan": "💎 Plan",
    "btn_lang": "🌐 Idioma",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Atrás",
    "btn_back_menu": "⬅️ Menú",
    "btn_cancel": "✖️ Cancelar",

    "welcome": (
        "👋 <b>Bienvenido a Grailert.</b>\n\n"
        "Dime qué buscas y te aviso en el segundo en que se publique — "
        "antes de que lo vea quien está deslizando la app.\n\n"
        "🎁 <b>Tu prueba Pro de {days} días está activa</b> — búsquedas ilimitadas, revisión cada 30 segundos."
    ),
    "welcome_back": "👋 Bienvenido de nuevo.",
    "lang_choose": "🌐 Elige tu idioma:",
    "lang_saved": "✅ Idioma cambiado a español.",

    "add_prompt": (
        "➕ <b>Nueva búsqueda</b>\n\n"
        "Envía una <b>palabra clave</b> — por ejemplo <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — y busco en todo el sitio.\n\n"
        "O pega un <b>enlace de Vinted con filtros</b> (<code>vinted.es/catalog?...</code>) si quieres marca, "
        "talla y precio tal como los configuraste."
    ),
    "domain_prompt": "🔎 Buscando: <b>{kw}</b>\n\n¿En qué Vinted?",
    "preview_checking": "⏳ Comprobando la búsqueda…",
    "preview_ok": "✅ Encontrados <b>{n}</b> anuncios con esta búsqueda.",
    "preview_fail": "⚠️ Ahora no se pudo comprobar (límite de Vinted), pero puedes guardarla igualmente.",
    "name_prompt": "¿Cómo llamamos a esta búsqueda?",
    "btn_auto_name": "✨ Nombre automático",
    "name_set": "Nombre: <b>{name}</b>\n\n¿Cada cuánto reviso?",
    "interval_prompt": "⏱ Nuevo intervalo:",
    "interval_custom": "Envía el intervalo en segundos (mínimo {min}).",
    "need_number": "Necesito un número de segundos. Inténtalo otra vez o /cancel",
    "added_ok": "✅ Búsqueda añadida. Ya vigilo los anuncios nuevos.",
    "baseline_note": "💡 Lo que ya está publicado lo anoté en silencio: solo recibirás lo que aparezca <i>a partir de ahora</i>.",

    "list_empty": "📋 Todavía no hay búsquedas.\nPulsa «Nueva búsqueda» para crear la primera.",
    "list_title": "📋 <b>Mis búsquedas</b> ({n})\nElige una:",
    "btn_pause_all": "⏸ Pausar todas",
    "btn_resume_all": "▶️ Reanudar todas",
    "btn_export": "📤 Exportar búsquedas",
    "btn_new_short": "➕ Nueva",

    "card_active": "🟢 Activa",
    "card_paused": "⏸ En pausa",
    "card_error": "⚠️ La última comprobación falló",
    "card_interval": "⏱ Intervalo: <b>{interval}</b>",
    "card_found": "🆕 Encontrado: <b>{total}</b>   📅 hoy: <b>{today}</b>",
    "card_last": "🕐 Última comprobación: {ago}",
    "card_kwi": "🔔 Incluir: <code>{v}</code>",
    "card_kwe": "🔕 Excluir: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">enlace de la búsqueda ↗</a>",
    "btn_price": "💶 Precio",
    "price_prompt": "Envía un rango de precio: <code>10-50</code>, <code>-50</code> (solo máx.) o <code>10-</code> (solo mín.). Envía <code>-</code> para quitar.",
    "price_updated": "✅ Filtro de precio actualizado.",
    "price_invalid": "No parece un rango. Ejemplos: <code>10-50</code>, <code>-50</code>, <code>10-</code>, o <code>-</code> para quitar.",
    "card_pricef": "💶 Precio: <code>{v}</code>",
    "cap_size": "📏 Talla: {v}",
    "cap_protect": "  <i>({v} con protección al comprador)</i>",
    "cap_open": "Abrir en Vinted ↗",
    "cap_untitled": "Sin título",
    "deal_badge": "🔥 Mucho más barato que anuncios similares",
    "btn_presets": "⭐ Búsquedas listas",
    "presets_prompt": "Elige una marca y configuro la búsqueda:",
    "card_price_now": "💹 Desde <b>{price}</b>{usd} · {n} anuncios ahora",

    "btn_resume": "▶️ Reanudar",
    "btn_pause": "⏸ Pausar",
    "btn_check": "🔍 Comprobar",
    "btn_rename": "✏️ Nombre",
    "btn_interval": "⏱ Intervalo",
    "btn_kwi": "🔔 Incluir",
    "btn_kwe": "🔕 Excluir",
    "btn_url": "🔗 Enlace",
    "btn_delete": "🗑 Eliminar",
    "btn_back_list": "⬅️ A la lista",

    "check_running": "🔍 Comprobando Vinted…",
    "check_found": "🔍 Encontrado y enviado: +{n}",
    "check_none": "🔍 Nada nuevo por ahora",
    "check_error": "⚠️ Vinted no responde en este momento",

    "delete_confirm": "🗑 ¿Eliminar la búsqueda «{name}»?\nNo se puede deshacer.",
    "btn_delete_yes": "🗑 Sí, eliminar",
    "btn_delete_no": "↩️ Conservar",

    "edit_name": "✏️ Envía el nuevo nombre:",
    "edit_url": "🔗 Enlace actual:\n<code>{url}</code>\n\nEnvía el nuevo enlace de Vinted:",
    "edit_kwi": "🔔 <b>Filtro incluir</b> — avisar solo si el título tiene estas palabras.\nActual: <code>{v}</code>\n\nEnvía palabras separadas por comas (o «-» para borrar):",
    "edit_kwe": "🔕 <b>Filtro excluir</b> — saltar anuncios con estas palabras.\nActual: <code>{v}</code>\n\nEnvía palabras separadas por comas (o «-» para borrar):",
    "url_invalid": "Eso no parece un enlace de Vinted. Envía un enlace o /cancel",
    "name_updated": "✅ Nombre actualizado",
    "url_updated": "✅ Enlace actualizado",
    "kwi_updated": "✅ Filtro incluir actualizado",
    "kwe_updated": "✅ Filtro excluir actualizado",
    "interval_updated": "✅ Intervalo actualizado",
    "cancelled": "Cancelado. /start para el menú.",

    "notify_overflow": "… y <b>{n}</b> nuevos más en «{name}» (se muestran los más recientes).",

    "stats_title": "📊 <b>Tus estadísticas</b>",
    "stats_searches": "📂 Búsquedas: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Encontrado en total: <b>{n}</b>",
    "stats_today": "📅 Hoy: <b>{n}</b>",
    "stats_by_search": "<b>Por búsqueda:</b>",

    "help": (
        "❓ <b>Cómo usarlo</b>\n\n"
        "<b>Rápido:</b> pulsa <b>➕ Nueva búsqueda</b> y envía una <b>palabra clave</b> "
        "(<code>stone island</code>, <code>nike tn</code>). Busco en todo el sitio.\n\n"
        "<b>Preciso:</b> abre Vinted, ajusta tus filtros (marca, talla, precio, estado), "
        "copia el enlace de la barra de direcciones y envíamelo. Vigilaré exactamente eso.\n\n"
        "Luego eliges nombre y frecuencia.\n\n"
        "A partir de ahí recibes <b>cada anuncio nuevo</b>: álbum de fotos, precio, talla, marca, enlace.\n\n"
        "🔔 <b>Incluir</b> — avisar solo si el título contiene estas palabras.\n"
        "🔕 <b>Excluir</b> — saltar anuncios con estas palabras.\n"
        "🔍 <b>Comprobar</b> — consultar la búsqueda ahora mismo.\n\n"
        "🔒 <b>Nunca toco tu cuenta de Vinted.</b> Solo leo anuncios públicos y te escribo aquí — "
        "sin iniciar sesión, sin compra automática, sin republicar. Nada que ponga tu cuenta en riesgo."
    ),
    "support_line": "🛟 ¿Algo no funciona o tienes una pregunta? Escríbenos: {sup} — te responde una persona.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert funciona solo por invitación por ahora.</b>\n\n"
        "Envíame tu clave de invitación (tiene esta pinta: <code>GRL-XXXX-XXXX</code>) y activo <b>{days} días de Pro</b> — sin tarjeta.\n\n"
        "¿Sin clave? Apúntate a la lista de espera — abrimos el acceso en pequeñas tandas."
    ),
    "gate_btn_waitlist": "⏳ Apuntarme a la lista de espera",
    "waitlist_joined": "✅ Estás en la lista de espera, posición <b>#{n}</b>. Te escribo aquí cuando tu acceso esté listo.",
    "waitlist_already": "⏳ Estás en la lista de espera, posición <b>#{n}</b>. ¿Tienes clave? Envíala aquí.",
    "key_ok": "🔑 <b>¡Clave aceptada!</b> Pro activo durante {days} días, hasta el {date}. Añade tu primera búsqueda 👇",
    "key_used": "⚠️ Esta clave ya se ha usado. Una clave abre una sola cuenta.",
    "key_bad": "❌ Esa clave no funciona. Revisa cómo está escrita o pregunta a quien te la dio.",
    "key_ratelimited": "⏱ Demasiados intentos. Prueba de nuevo en una hora.",
    "invite_granted": "🎉 <b>¡Tu acceso está listo!</b> Pro durante {days} días, hasta el {date}. Envía /start para empezar.",

    "diag_running": "🩺 Comprobando si Vinted responde…",
    "diag_title": "🩺 <b>Diagnóstico</b>",
    "diag_host": "Dominio: <b>{host}</b>",
    "diag_ok": "🟢 accesible",
    "diag_fail": "🔴 no accesible (Cloudflare/Datadome o red)",
    "diag_status": "Estado de la API: {status}",
    "diag_proxy_on": "Proxy: activado",
    "diag_proxy_off": "Proxy: desactivado (conexión directa)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Prueba Pro",
    "plan_title": "💎 <b>Tu plan</b>",
    "plan_current": "Actual: <b>{plan}</b>",
    "plan_until": "Activo hasta el <b>{date}</b> (quedan {days} días)",
    "plan_free_desc": "Free: <b>1 búsqueda</b>, revisada cada <b>15 minutos</b>.",
    "plan_pitch": (
        "Un solo buen hallazgo paga un año entero.\n\n"
        "<b>Basic</b> — 3 búsquedas, revisión cada <b>2 minutos</b>\n"
        "<b>Pro</b> — búsquedas <b>ilimitadas</b>, revisión cada <b>30 segundos</b>, cola prioritaria\n\n"
        "Cuanto más rápida la revisión, antes ves un anuncio infravalorado — y en Vinted "
        "lo bueno vuela en minutos."
    ),
    "plan_safety": "🔒 Nunca tocamos tu cuenta de Vinted — solo avisos, nada automatizado por tu parte.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro un año — {price} (2 meses gratis)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\n¿Cómo prefieres pagar?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Cripto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Abrir el pago",
    "btn_pay_check": "🔄 Ya pagué — comprobar",
    "period_month": "1 mes",
    "period_year": "12 meses",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Plan {plan} por {period}. Activación inmediata.",
    "crypto_created": (
        "₿ <b>Factura creada</b> — {amount} USDT\n\n"
        "Pulsa el botón y paga en Crypto Pay (USDT, TON, BTC y más).\n"
        "La activación es automática segundos después del pago."
    ),
    "crypto_unavailable": "₿ El pago con cripto no está disponible ahora. Telegram Stars funciona.",
    "pay_ok": "🎉 <b>Pago recibido. {plan} activo hasta el {date}.</b>\n\nAñade las búsquedas que tenías guardadas.",
    "pay_pending": "⏳ Aún no veo el pago. Si acabas de pagar, espera unos segundos y comprueba otra vez.",
    "pay_failed": "⚠️ El pago no se completó. No se cobró nada.",

    "limit_searches": (
        "🔒 <b>{plan} — límite de búsquedas: {limit}</b>\n\n"
        "Ahora mismo vigilas {current}. Sube de plan y añade las que quieras — "
        "lo normal es una por cada marca que revendes."
    ),
    "limit_interval": (
        "🔒 <b>Revisar cada {interval} es parte de {needed}.</b>\n\n"
        "En {plan} reviso cada {current}. En Vinted una prenda bien puesta de precio vuela en minutos: "
        "el intervalo lo es todo."
    ),
    "btn_upgrade": "💎 Subir de plan",

    "trial_ends_soon": (
        "⏳ <b>Tu prueba Pro termina en {days} días.</b>\n\n"
        "Hasta ahora te he encontrado <b>{found}</b> anuncios.\n"
        "Sigamos — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "Tu prueba Pro ha terminado — ahora estás en Free: 1 búsqueda, revisión cada 15 minutos.\n\n"
        "Durante la prueba te encontré <b>{found}</b> anuncios. "
        "No se ha borrado nada, solo está en pausa — elige un plan y todo vuelve a funcionar."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} termina en {days} días.</b>\n\n"
        "Renueva y no cambia nada — tus búsquedas siguen sin interrupción."
    ),
    "plan_expired": (
        "Tu plan {plan} ha terminado — ahora estás en Free.\n\n"
        "Tus búsquedas están en pausa, no borradas. Al renovar siguen donde se quedaron."
    ),
    "paused_by_limit": "⏸ En pausa por el cambio de plan: «{name}»",
    "digest_missed": (
        "📬 <b>Mientras estás en Free</b>\n\n"
        "Tus búsquedas en pausa habrían cazado <b>{n}</b> anuncios nuevos en los últimos {days} días. "
        "Eso es lo que no estás viendo."
    ),

    "btn_invite": "🎁 Invitar a un amigo",
    "invite_h": "🎁 <b>Invitar a un amigo</b>",
    "invite_p": "Envía este enlace a alguien que revenda en Vinted. Cuando pague cualquier plan, <b>tú recibes {days} días de Pro</b> — y él empieza igualmente con una semana de Pro gratis.",
    "invite_link": "Tu enlace:",
    "invite_stat": "Llegaron por tu enlace: <b>{n}</b> · de ellos pagaron: <b>{p}</b>",
    "ref_reward": "🎁 <b>Alguien a quien invitaste acaba de suscribirse.</b>\n\nTe hemos añadido {days} días de Pro — tu plan llega hasta el <b>{date}</b>. Gracias por difundirlo.",
    "no_access": "Sin acceso. Envía /start",
    "admin_only": "Solo para admins.",
    "unit_h": "h",
    "unit_min": "min",
    "unit_sec": "s",
    "ago_never": "todavía no",
    "ago_now": "ahora mismo",
    "ago_min": "hace {n} min",
    "ago_h": "hace {n} h",
    "ago_d": "hace {n} d",
},

# ============================================================ ITALIANO
"it": {
    "btn_menu": "🛍 Menu",
    "btn_add": "➕ Nuova ricerca",
    "btn_list": "📋 Le mie ricerche",
    "kb_pinned": "🛍 Il pulsante <b>Menu</b> resta sempre in basso 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Tengo d'occhio Vinted per te e ti mando ogni nuovo annuncio appena esce — foto, prezzo, taglia, link.",
    "menu_searches": "📂 Ricerche: <b>{total}</b>   🟢 attive: <b>{active}</b>   ⏸ in pausa: <b>{paused}</b>",
    "menu_found": "🆕 Trovati in tutto: <b>{total}</b>   📅 oggi: <b>{today}</b>",
    "menu_plan": "💎 Piano: <b>{plan}</b>{until}",
    "menu_plan_until": " · fino al {date}",

    "btn_new_search": "➕ Nuova ricerca",
    "btn_my_searches": "📋 Le mie ricerche",
    "btn_stats": "📊 Statistiche",
    "btn_diag": "🩺 Diagnostica",
    "btn_help": "❓ Come funziona",
    "btn_plan": "💎 Piano",
    "btn_lang": "🌐 Lingua",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Indietro",
    "btn_back_menu": "⬅️ Menu",
    "btn_cancel": "✖️ Annulla",

    "welcome": (
        "👋 <b>Benvenuto su Grailert.</b>\n\n"
        "Dimmi cosa cerchi e ti avviso nel secondo in cui viene pubblicato — "
        "prima di chi sta scorrendo l'app.\n\n"
        "🎁 <b>La tua prova Pro di {days} giorni è attiva</b> — ricerche illimitate, controllo ogni 30 secondi."
    ),
    "welcome_back": "👋 Bentornato.",
    "lang_choose": "🌐 Scegli la lingua:",
    "lang_saved": "✅ Lingua impostata su italiano.",

    "add_prompt": (
        "➕ <b>Nuova ricerca</b>\n\n"
        "Manda una <b>parola chiave</b> — ad esempio <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — e cerco su tutto il sito.\n\n"
        "Oppure incolla un <b>link Vinted con i filtri</b> (<code>vinted.it/catalog?...</code>) se vuoi marca, "
        "taglia e prezzo esattamente come li hai impostati."
    ),
    "domain_prompt": "🔎 Cerco: <b>{kw}</b>\n\nSu quale Vinted?",
    "preview_checking": "⏳ Sto verificando la ricerca…",
    "preview_ok": "✅ Trovati <b>{n}</b> annunci con questa ricerca.",
    "preview_fail": "⚠️ Ora non riesco a verificarla (limite Vinted), ma puoi salvarla lo stesso.",
    "name_prompt": "Come chiamiamo questa ricerca?",
    "btn_auto_name": "✨ Nome automatico",
    "name_set": "Nome: <b>{name}</b>\n\nOgni quanto controllo?",
    "interval_prompt": "⏱ Nuovo intervallo:",
    "interval_custom": "Manda l'intervallo in secondi (minimo {min}).",
    "need_number": "Mi serve un numero di secondi. Riprova o /cancel",
    "added_ok": "✅ Ricerca aggiunta. Ora seguo i nuovi annunci.",
    "baseline_note": "💡 Quello che è già online l'ho annotato in silenzio: ricevi solo ciò che arriva <i>da adesso</i>.",

    "list_empty": "📋 Ancora nessuna ricerca.\nTocca «Nuova ricerca» per la prima.",
    "list_title": "📋 <b>Le mie ricerche</b> ({n})\nScegline una:",
    "btn_pause_all": "⏸ Metti tutte in pausa",
    "btn_resume_all": "▶️ Riavvia tutte",
    "btn_export": "📤 Esporta ricerche",
    "btn_new_short": "➕ Nuova",

    "card_active": "🟢 Attiva",
    "card_paused": "⏸ In pausa",
    "card_error": "⚠️ Ultimo controllo fallito",
    "card_interval": "⏱ Intervallo: <b>{interval}</b>",
    "card_found": "🆕 Trovati: <b>{total}</b>   📅 oggi: <b>{today}</b>",
    "card_last": "🕐 Ultimo controllo: {ago}",
    "card_kwi": "🔔 Includi: <code>{v}</code>",
    "card_kwe": "🔕 Escludi: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">link della ricerca ↗</a>",
    "btn_price": "💶 Prezzo",
    "price_prompt": "Invia un intervallo di prezzo: <code>10-50</code>, <code>-50</code> (solo max) o <code>10-</code> (solo min). Invia <code>-</code> per rimuovere.",
    "price_updated": "✅ Filtro prezzo aggiornato.",
    "price_invalid": "Non sembra un intervallo. Esempi: <code>10-50</code>, <code>-50</code>, <code>10-</code>, o <code>-</code> per rimuovere.",
    "card_pricef": "💶 Prezzo: <code>{v}</code>",
    "cap_size": "📏 Taglia: {v}",
    "cap_protect": "  <i>({v} con protezione acquirente)</i>",
    "cap_open": "Apri su Vinted ↗",
    "cap_untitled": "Senza titolo",
    "deal_badge": "🔥 Molto più economico di annunci simili",
    "btn_presets": "⭐ Ricerche pronte",
    "presets_prompt": "Scegli un marchio e configuro la ricerca:",
    "card_price_now": "💹 Da <b>{price}</b>{usd} · {n} annunci ora",

    "btn_resume": "▶️ Riavvia",
    "btn_pause": "⏸ Pausa",
    "btn_check": "🔍 Controlla",
    "btn_rename": "✏️ Nome",
    "btn_interval": "⏱ Intervallo",
    "btn_kwi": "🔔 Includi",
    "btn_kwe": "🔕 Escludi",
    "btn_url": "🔗 Link",
    "btn_delete": "🗑 Elimina",
    "btn_back_list": "⬅️ All'elenco",

    "check_running": "🔍 Sto controllando Vinted…",
    "check_found": "🔍 Trovati e inviati: +{n}",
    "check_none": "🔍 Nulla di nuovo",
    "check_error": "⚠️ Vinted non risponde in questo momento",

    "delete_confirm": "🗑 Eliminare la ricerca «{name}»?\nNon si può annullare.",
    "btn_delete_yes": "🗑 Sì, elimina",
    "btn_delete_no": "↩️ Tienila",

    "edit_name": "✏️ Manda il nuovo nome:",
    "edit_url": "🔗 Link attuale:\n<code>{url}</code>\n\nManda il nuovo link Vinted:",
    "edit_kwi": "🔔 <b>Filtro includi</b> — avvisa solo se il titolo contiene queste parole.\nOra: <code>{v}</code>\n\nManda le parole separate da virgole (o «-» per cancellare):",
    "edit_kwe": "🔕 <b>Filtro escludi</b> — salta gli annunci con queste parole.\nOra: <code>{v}</code>\n\nManda le parole separate da virgole (o «-» per cancellare):",
    "url_invalid": "Non sembra un link Vinted. Manda un link oppure /cancel",
    "name_updated": "✅ Nome aggiornato",
    "url_updated": "✅ Link aggiornato",
    "kwi_updated": "✅ Filtro includi aggiornato",
    "kwe_updated": "✅ Filtro escludi aggiornato",
    "interval_updated": "✅ Intervallo aggiornato",
    "cancelled": "Annullato. /start per il menu.",

    "notify_overflow": "… e altri <b>{n}</b> nuovi per «{name}» (mostrati i più recenti).",

    "stats_title": "📊 <b>Le tue statistiche</b>",
    "stats_searches": "📂 Ricerche: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Trovati in tutto: <b>{n}</b>",
    "stats_today": "📅 Oggi: <b>{n}</b>",
    "stats_by_search": "<b>Per ricerca:</b>",

    "help": (
        "❓ <b>Come si usa</b>\n\n"
        "<b>Veloce:</b> tocca <b>➕ Nuova ricerca</b> e manda una <b>parola chiave</b> "
        "(<code>stone island</code>, <code>nike tn</code>). Cerco su tutto il sito.\n\n"
        "<b>Preciso:</b> apri Vinted, imposta i filtri (marca, taglia, prezzo, condizione), "
        "copia il link dalla barra degli indirizzi e mandamelo. Seguirò esattamente quello.\n\n"
        "Poi scegli nome e frequenza.\n\n"
        "Da lì ricevi <b>ogni nuovo annuncio</b>: album foto, prezzo, taglia, marca, link.\n\n"
        "🔔 <b>Includi</b> — avvisa solo se il titolo contiene queste parole.\n"
        "🔕 <b>Escludi</b> — salta gli annunci con queste parole.\n"
        "🔍 <b>Controlla</b> — interroga la ricerca subito.\n\n"
        "🔒 <b>Non tocco mai il tuo account Vinted.</b> Leggo solo annunci pubblici e ti scrivo qui — "
        "nessun accesso, nessun acquisto automatico, nessuna ripubblicazione. Niente che metta a rischio l'account."
    ),
    "support_line": "🛟 Qualcosa non va o hai una domanda? Scrivici: {sup} — risponde una persona vera.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert per ora è solo su invito.</b>\n\n"
        "Mandami la tua chiave d'invito (è fatta così: <code>GRL-XXXX-XXXX</code>) e attivo <b>{days} giorni di Pro</b> — senza carta.\n\n"
        "Non hai una chiave? Iscriviti alla lista d'attesa — apriamo l'accesso a piccoli gruppi."
    ),
    "gate_btn_waitlist": "⏳ Entra in lista d'attesa",
    "waitlist_joined": "✅ Sei in lista d'attesa, posizione <b>#{n}</b>. Ti scrivo qui quando il tuo accesso è pronto.",
    "waitlist_already": "⏳ Sei in lista d'attesa, posizione <b>#{n}</b>. Hai una chiave? Mandala qui.",
    "key_ok": "🔑 <b>Chiave accettata!</b> Pro attivo per {days} giorni, fino al {date}. Aggiungi la tua prima ricerca 👇",
    "key_used": "⚠️ Questa chiave è già stata usata. Una chiave apre un solo account.",
    "key_bad": "❌ Questa chiave non funziona. Controlla come è scritta o chiedi a chi te l'ha data.",
    "key_ratelimited": "⏱ Troppi tentativi. Riprova tra un'ora.",
    "invite_granted": "🎉 <b>Il tuo accesso è pronto!</b> Pro per {days} giorni, fino al {date}. Invia /start per iniziare.",

    "diag_running": "🩺 Controllo se Vinted risponde…",
    "diag_title": "🩺 <b>Diagnostica</b>",
    "diag_host": "Dominio: <b>{host}</b>",
    "diag_ok": "🟢 raggiungibile",
    "diag_fail": "🔴 non raggiungibile (Cloudflare/Datadome o rete)",
    "diag_status": "Stato API: {status}",
    "diag_proxy_on": "Proxy: attivo",
    "diag_proxy_off": "Proxy: spento (connessione diretta)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Prova Pro",
    "plan_title": "💎 <b>Il tuo piano</b>",
    "plan_current": "Attuale: <b>{plan}</b>",
    "plan_until": "Attivo fino al <b>{date}</b> ({days} giorni rimasti)",
    "plan_free_desc": "Free: <b>1 ricerca</b>, controllata ogni <b>15 minuti</b>.",
    "plan_pitch": (
        "Un solo buon affare ripaga un anno intero.\n\n"
        "<b>Basic</b> — 3 ricerche, controllo ogni <b>2 minuti</b>\n"
        "<b>Pro</b> — ricerche <b>illimitate</b>, controllo ogni <b>30 secondi</b>, coda prioritaria\n\n"
        "Più veloce è il controllo, prima vedi un annuncio sottoprezzo — e su Vinted "
        "le cose buone spariscono in pochi minuti."
    ),
    "plan_safety": "🔒 Non tocchiamo mai il tuo account Vinted — solo avvisi, niente di automatico dalla tua parte.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro per un anno — {price} (2 mesi gratis)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nCome preferisci pagare?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Cripto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Apri il pagamento",
    "btn_pay_check": "🔄 Ho pagato — controlla",
    "period_month": "1 mese",
    "period_year": "12 mesi",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Piano {plan} per {period}. Attivazione immediata.",
    "crypto_created": (
        "₿ <b>Fattura creata</b> — {amount} USDT\n\n"
        "Tocca il pulsante e paga in Crypto Pay (USDT, TON, BTC e altri).\n"
        "L'attivazione è automatica pochi secondi dopo il pagamento."
    ),
    "crypto_unavailable": "₿ Il pagamento in cripto non è disponibile ora. Telegram Stars funziona.",
    "pay_ok": "🎉 <b>Pagamento ricevuto. {plan} attivo fino al {date}.</b>\n\nAggiungi le ricerche che tenevi da parte.",
    "pay_pending": "⏳ Il pagamento non risulta ancora. Se hai appena pagato, aspetta qualche secondo e ricontrolla.",
    "pay_failed": "⚠️ Il pagamento non è andato a buon fine. Non è stato addebitato nulla.",

    "limit_searches": (
        "🔒 <b>{plan} — limite di ricerche: {limit}</b>\n\n"
        "Al momento ne segui {current}. Passa a un piano superiore e aggiungine quante vuoi — "
        "di solito se ne tiene una per ogni marca che si rivende."
    ),
    "limit_interval": (
        "🔒 <b>Il controllo ogni {interval} fa parte di {needed}.</b>\n\n"
        "Con {plan} controllo ogni {current}. Su Vinted un capo a buon prezzo sparisce in minuti: "
        "l'intervallo è tutto."
    ),
    "btn_upgrade": "💎 Passa a un piano superiore",

    "trial_ends_soon": (
        "⏳ <b>La tua prova Pro finisce tra {days} giorni.</b>\n\n"
        "Finora ti ho trovato <b>{found}</b> annunci.\n"
        "Continuiamo — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "La prova Pro è finita — ora sei su Free: 1 ricerca, controllo ogni 15 minuti.\n\n"
        "Durante la prova ti ho trovato <b>{found}</b> annunci. "
        "Non è stato cancellato niente, è tutto in pausa — scegli un piano e riparte."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} finisce tra {days} giorni.</b>\n\n"
        "Rinnova e non cambia nulla — le tue ricerche continuano senza interruzioni."
    ),
    "plan_expired": (
        "Il piano {plan} è scaduto — ora sei su Free.\n\n"
        "Le tue ricerche sono in pausa, non cancellate. Al rinnovo riprendono da dove erano."
    ),
    "paused_by_limit": "⏸ In pausa per il cambio di piano: «{name}»",
    "digest_missed": (
        "📬 <b>Mentre sei su Free</b>\n\n"
        "Le tue ricerche in pausa avrebbero preso <b>{n}</b> nuovi annunci negli ultimi {days} giorni. "
        "È quello che non stai vedendo."
    ),

    "btn_invite": "🎁 Invita un amico",
    "invite_h": "🎁 <b>Invita un amico</b>",
    "invite_p": "Manda questo link a chi rivende su Vinted. Quando paga un piano, <b>tu ricevi {days} giorni di Pro</b> — e lui parte comunque con una settimana di Pro gratis.",
    "invite_link": "Il tuo link:",
    "invite_stat": "Arrivati dal tuo link: <b>{n}</b> · di cui paganti: <b>{p}</b>",
    "ref_reward": "🎁 <b>Una persona che hai invitato si è appena abbonata.</b>\n\nTi abbiamo aggiunto {days} giorni di Pro — il piano ora arriva al <b>{date}</b>. Grazie per averne parlato.",
    "no_access": "Nessun accesso. Manda /start",
    "admin_only": "Solo per admin.",
    "unit_h": "h",
    "unit_min": "min",
    "unit_sec": "s",
    "ago_never": "non ancora",
    "ago_now": "proprio ora",
    "ago_min": "{n} min fa",
    "ago_h": "{n} h fa",
    "ago_d": "{n} g fa",
},

# ============================================================ POLSKI
"pl": {
    "btn_menu": "🛍 Menu",
    "btn_add": "➕ Nowe wyszukiwanie",
    "btn_list": "📋 Moje wyszukiwania",
    "kb_pinned": "🛍 Przycisk <b>Menu</b> jest teraz zawsze na dole 👇",

    "menu_title": "🛍 <b>Grailert</b>",
    "menu_sub": "Obserwuję Vinted i wysyłam każde nowe ogłoszenie od razu — zdjęcia, cena, rozmiar, link.",
    "menu_searches": "📂 Wyszukiwania: <b>{total}</b>   🟢 aktywne: <b>{active}</b>   ⏸ wstrzymane: <b>{paused}</b>",
    "menu_found": "🆕 Znalezione łącznie: <b>{total}</b>   📅 dziś: <b>{today}</b>",
    "menu_plan": "💎 Plan: <b>{plan}</b>{until}",
    "menu_plan_until": " · do {date}",

    "btn_new_search": "➕ Nowe wyszukiwanie",
    "btn_my_searches": "📋 Moje wyszukiwania",
    "btn_stats": "📊 Statystyki",
    "btn_diag": "🩺 Diagnostyka",
    "btn_help": "❓ Jak to działa",
    "btn_plan": "💎 Plan",
    "btn_lang": "🌐 Język",
    "btn_admin": "🔐 Admin",
    "btn_back": "⬅️ Wstecz",
    "btn_back_menu": "⬅️ Menu",
    "btn_cancel": "✖️ Anuluj",

    "welcome": (
        "👋 <b>Witaj w Grailert.</b>\n\n"
        "Powiedz, czego szukasz, a napiszę w sekundzie, w której to wystawią — "
        "zanim zobaczy to ktoś przewijający aplikację.\n\n"
        "🎁 <b>Twój {days}-dniowy okres próbny Pro jest aktywny</b> — bez limitu wyszukiwań, sprawdzanie co 30 sekund."
    ),
    "welcome_back": "👋 Dobrze cię znowu widzieć.",
    "lang_choose": "🌐 Wybierz język:",
    "lang_saved": "✅ Język ustawiony na polski.",

    "add_prompt": (
        "➕ <b>Nowe wyszukiwanie</b>\n\n"
        "Wyślij <b>słowo kluczowe</b> — na przykład <code>stone island</code>, <code>nike tn</code>, "
        "<code>vintage levis</code> — a przeszukam całą stronę.\n\n"
        "Albo wklej <b>link z filtrami</b> (<code>vinted.pl/catalog?...</code>), jeśli chcesz markę, "
        "rozmiar i cenę dokładnie tak, jak ustawiłeś."
    ),
    "domain_prompt": "🔎 Szukam: <b>{kw}</b>\n\nW którym Vinted?",
    "preview_checking": "⏳ Sprawdzam wyszukiwanie…",
    "preview_ok": "✅ Znaleziono <b>{n}</b> ogłoszeń dla tego wyszukiwania.",
    "preview_fail": "⚠️ Teraz nie udało się sprawdzić (limit Vinted), ale i tak możesz zapisać.",
    "name_prompt": "Jak nazwać to wyszukiwanie?",
    "btn_auto_name": "✨ Nazwa automatyczna",
    "name_set": "Nazwa: <b>{name}</b>\n\nJak często mam sprawdzać?",
    "interval_prompt": "⏱ Nowy odstęp sprawdzania:",
    "interval_custom": "Wyślij odstęp w sekundach (minimum {min}).",
    "need_number": "Potrzebuję liczby sekund. Spróbuj ponownie albo /cancel",
    "added_ok": "✅ Wyszukiwanie dodane. Pilnuję nowych ogłoszeń.",
    "baseline_note": "💡 To, co już jest wystawione, po cichu zapisałem — dostaniesz tylko to, co pojawi się <i>od teraz</i>.",

    "list_empty": "📋 Nie masz jeszcze wyszukiwań.\nNaciśnij «Nowe wyszukiwanie», żeby dodać pierwsze.",
    "list_title": "📋 <b>Moje wyszukiwania</b> ({n})\nWybierz jedno:",
    "btn_pause_all": "⏸ Wstrzymaj wszystkie",
    "btn_resume_all": "▶️ Wznów wszystkie",
    "btn_export": "📤 Eksport wyszukiwań",
    "btn_new_short": "➕ Nowe",

    "card_active": "🟢 Aktywne",
    "card_paused": "⏸ Wstrzymane",
    "card_error": "⚠️ Ostatnie sprawdzenie nieudane",
    "card_interval": "⏱ Odstęp: <b>{interval}</b>",
    "card_found": "🆕 Znalezione: <b>{total}</b>   📅 dziś: <b>{today}</b>",
    "card_last": "🕐 Ostatnie sprawdzenie: {ago}",
    "card_kwi": "🔔 Zawiera: <code>{v}</code>",
    "card_kwe": "🔕 Pomija: <code>{v}</code>",
    "card_link": "🔗 <a href=\"{url}\">link wyszukiwania ↗</a>",
    "btn_price": "💶 Cena",
    "price_prompt": "Wyślij zakres ceny: <code>10-50</code>, <code>-50</code> (tylko maks.) lub <code>10-</code> (tylko min.). Wyślij <code>-</code>, aby usunąć.",
    "price_updated": "✅ Filtr ceny zaktualizowany.",
    "price_invalid": "To nie wygląda na zakres. Przykłady: <code>10-50</code>, <code>-50</code>, <code>10-</code>, lub <code>-</code>, aby usunąć.",
    "card_pricef": "💶 Cena: <code>{v}</code>",
    "cap_size": "📏 Rozmiar: {v}",
    "cap_protect": "  <i>({v} z ochroną kupującego)</i>",
    "cap_open": "Otwórz na Vinted ↗",
    "cap_untitled": "Bez tytułu",
    "deal_badge": "🔥 Znacznie taniej niż podobne ogłoszenia",
    "btn_presets": "⭐ Gotowe wyszukiwania",
    "presets_prompt": "Wybierz markę, a ustawię wyszukiwanie:",
    "card_price_now": "💹 Od <b>{price}</b>{usd} · teraz {n} ogłoszeń",

    "btn_resume": "▶️ Wznów",
    "btn_pause": "⏸ Wstrzymaj",
    "btn_check": "🔍 Sprawdź teraz",
    "btn_rename": "✏️ Nazwa",
    "btn_interval": "⏱ Odstęp",
    "btn_kwi": "🔔 Zawiera",
    "btn_kwe": "🔕 Pomija",
    "btn_url": "🔗 Link",
    "btn_delete": "🗑 Usuń",
    "btn_back_list": "⬅️ Do listy",

    "check_running": "🔍 Sprawdzam Vinted…",
    "check_found": "🔍 Znalezione i wysłane: +{n}",
    "check_none": "🔍 Nic nowego",
    "check_error": "⚠️ Vinted teraz nie odpowiada",

    "delete_confirm": "🗑 Usunąć wyszukiwanie «{name}»?\nTego nie da się cofnąć.",
    "btn_delete_yes": "🗑 Tak, usuń",
    "btn_delete_no": "↩️ Zostaw",

    "edit_name": "✏️ Wyślij nową nazwę:",
    "edit_url": "🔗 Obecny link:\n<code>{url}</code>\n\nWyślij nowy link wyszukiwania Vinted:",
    "edit_kwi": "🔔 <b>Filtr „zawiera”</b> — powiadamiaj tylko, gdy tytuł ma te słowa.\nObecnie: <code>{v}</code>\n\nWyślij słowa po przecinku (albo «-», żeby wyczyścić):",
    "edit_kwe": "🔕 <b>Filtr „pomija”</b> — pomijaj ogłoszenia z tymi słowami.\nObecnie: <code>{v}</code>\n\nWyślij słowa po przecinku (albo «-», żeby wyczyścić):",
    "url_invalid": "To nie wygląda na link Vinted. Wyślij link albo /cancel",
    "name_updated": "✅ Nazwa zaktualizowana",
    "url_updated": "✅ Link zaktualizowany",
    "kwi_updated": "✅ Filtr „zawiera” zaktualizowany",
    "kwe_updated": "✅ Filtr „pomija” zaktualizowany",
    "interval_updated": "✅ Odstęp zaktualizowany",
    "cancelled": "Anulowane. /start — menu.",

    "notify_overflow": "… i jeszcze <b>{n}</b> nowych dla «{name}» (pokazane najświeższe).",

    "stats_title": "📊 <b>Twoje statystyki</b>",
    "stats_searches": "📂 Wyszukiwania: <b>{total}</b>  (🟢 {active} / ⏸ {paused})",
    "stats_total": "🆕 Znalezione łącznie: <b>{n}</b>",
    "stats_today": "📅 Dziś: <b>{n}</b>",
    "stats_by_search": "<b>Według wyszukiwania:</b>",

    "help": (
        "❓ <b>Jak korzystać</b>\n\n"
        "<b>Szybko:</b> naciśnij <b>➕ Nowe wyszukiwanie</b> i wyślij <b>słowo kluczowe</b> "
        "(<code>stone island</code>, <code>nike tn</code>). Przeszukam całą stronę.\n\n"
        "<b>Dokładnie:</b> otwórz Vinted, ustaw filtry (marka, rozmiar, cena, stan), "
        "skopiuj link z paska adresu i wyślij mi. Będę pilnował dokładnie tego.\n\n"
        "Potem podajesz nazwę i częstotliwość.\n\n"
        "Od tej pory dostajesz <b>każde nowe ogłoszenie</b>: album zdjęć, cenę, rozmiar, markę, link.\n\n"
        "🔔 <b>Zawiera</b> — powiadamiaj tylko, gdy tytuł ma te słowa.\n"
        "🔕 <b>Pomija</b> — pomijaj ogłoszenia z tymi słowami.\n"
        "🔍 <b>Sprawdź teraz</b> — odpytaj wyszukiwanie natychmiast.\n\n"
        "🔒 <b>Nigdy nie dotykam twojego konta Vinted.</b> Czytam tylko publiczne ogłoszenia i piszę tutaj — "
        "bez logowania, bez auto-kupowania, bez przestawiania ogłoszeń. Nic, co naraziłoby konto."
    ),
    "support_line": "🛟 Coś nie działa albo masz pytanie? Napisz do nas: {sup} — odpowiada człowiek.",

    # --- закрытый тест: ключи и лист ожидания ---
    "gate_text": (
        "🔒 <b>Grailert działa na razie tylko na zaproszenia.</b>\n\n"
        "Wyślij mi swój klucz zaproszenia (wygląda tak: <code>GRL-XXXX-XXXX</code>), a odblokuję <b>{days} dni Pro</b> — bez karty.\n\n"
        "Nie masz klucza? Zapisz się na listę oczekujących — otwieramy dostęp małymi partiami."
    ),
    "gate_btn_waitlist": "⏳ Zapisz mnie na listę",
    "waitlist_joined": "✅ Jesteś na liście oczekujących, pozycja <b>#{n}</b>. Napiszę tutaj, gdy dostęp będzie gotowy.",
    "waitlist_already": "⏳ Jesteś na liście oczekujących, pozycja <b>#{n}</b>. Masz klucz? Po prostu wyślij go tutaj.",
    "key_ok": "🔑 <b>Klucz przyjęty!</b> Pro włączone na {days} dni, do {date}. Dodaj pierwsze wyszukiwanie 👇",
    "key_used": "⚠️ Ten klucz został już użyty. Jeden klucz otwiera jedno konto.",
    "key_bad": "❌ Ten klucz nie działa. Sprawdź pisownię albo zapytaj osobę, która ci go dała.",
    "key_ratelimited": "⏱ Za dużo prób. Spróbuj ponownie za godzinę.",
    "invite_granted": "🎉 <b>Twój dostęp jest gotowy!</b> Pro na {days} dni, do {date}. Wyślij /start, żeby zacząć.",

    "diag_running": "🩺 Sprawdzam, czy Vinted odpowiada…",
    "diag_title": "🩺 <b>Diagnostyka</b>",
    "diag_host": "Domena: <b>{host}</b>",
    "diag_ok": "🟢 dostępny",
    "diag_fail": "🔴 niedostępny (Cloudflare/Datadome albo sieć)",
    "diag_status": "Status API: {status}",
    "diag_proxy_on": "Proxy: włączone",
    "diag_proxy_off": "Proxy: wyłączone (połączenie bezpośrednie)",

    "plan_free": "Free",
    "plan_basic": "Basic",
    "plan_pro": "Pro",
    "plan_trial": "Okres próbny Pro",
    "plan_title": "💎 <b>Twój plan</b>",
    "plan_current": "Obecnie: <b>{plan}</b>",
    "plan_until": "Aktywny do <b>{date}</b> (pozostało dni: {days})",
    "plan_free_desc": "Free: <b>1 wyszukiwanie</b>, sprawdzane co <b>15 minut</b>.",
    "plan_pitch": (
        "Jedna dobra okazja spłaca cały rok.\n\n"
        "<b>Basic</b> — 3 wyszukiwania, sprawdzanie co <b>2 minuty</b>\n"
        "<b>Pro</b> — <b>bez limitu</b> wyszukiwań, sprawdzanie co <b>30 sekund</b>, priorytet w kolejce\n\n"
        "Im szybsze sprawdzanie, tym wcześniej widzisz zaniżoną cenę — a na Vinted "
        "dobre rzeczy znikają w kilka minut."
    ),
    "plan_safety": "🔒 Nigdy nie ruszamy twojego konta Vinted — tylko powiadomienia, żadnej automatyzacji po twojej stronie.",
    "btn_buy_basic": "Basic — {price}",
    "btn_buy_pro": "Pro — {price}",
    "btn_buy_pro_year": "Pro na rok — {price} (2 miesiące gratis)",
    "pay_choose": "💳 <b>{plan}</b> — {period}\n\nJak chcesz zapłacić?",
    "btn_pay_stars": "⭐ Telegram Stars",
    "btn_pay_crypto": "₿ Krypto (USDT, TON, BTC)",
    "btn_pay_open": "💳 Otwórz płatność",
    "btn_pay_check": "🔄 Zapłaciłem — sprawdź",
    "period_month": "1 miesiąc",
    "period_year": "12 miesięcy",
    "invoice_title": "Grailert — {plan}",
    "invoice_desc": "Plan {plan} na {period}. Włącza się od razu.",
    "crypto_created": (
        "₿ <b>Faktura utworzona</b> — {amount} USDT\n\n"
        "Naciśnij przycisk i zapłać w Crypto Pay (USDT, TON, BTC i inne).\n"
        "Aktywacja jest automatyczna kilka sekund po płatności."
    ),
    "crypto_unavailable": "₿ Płatność kryptowalutą jest chwilowo niedostępna. Telegram Stars działają.",
    "pay_ok": "🎉 <b>Płatność otrzymana. {plan} aktywny do {date}.</b>\n\nDodaj wyszukiwania, które odkładałeś.",
    "pay_pending": "⏳ Nie widzę jeszcze płatności. Jeśli właśnie zapłaciłeś, poczekaj chwilę i sprawdź ponownie.",
    "pay_failed": "⚠️ Płatność nie przeszła. Nic nie zostało pobrane.",

    "limit_searches": (
        "🔒 <b>{plan} — limit wyszukiwań: {limit}</b>\n\n"
        "Teraz masz {current}. Podnieś plan i dodawaj ile chcesz — "
        "zwykle trzyma się po jednym na każdą markę, którą się odsprzedaje."
    ),
    "limit_interval": (
        "🔒 <b>Sprawdzanie co {interval} należy do {needed}.</b>\n\n"
        "W {plan} sprawdzam co {current}. Na Vinted dobrze wyceniona rzecz znika w kilka minut — "
        "odstęp decyduje o wszystkim."
    ),
    "btn_upgrade": "💎 Podnieś plan",

    "trial_ends_soon": (
        "⏳ <b>Okres próbny Pro kończy się za {days} dni.</b>\n\n"
        "Do tej pory znalazłem dla ciebie <b>{found}</b> ogłoszeń.\n"
        "Lecimy dalej — Basic {basic}, Pro {pro}."
    ),
    "trial_over": (
        "Okres próbny Pro się skończył — jesteś na Free: 1 wyszukiwanie, sprawdzanie co 15 minut.\n\n"
        "W czasie okresu próbnego znalazłem dla ciebie <b>{found}</b> ogłoszeń. "
        "Nic nie zostało usunięte, wszystko jest tylko wstrzymane — wybierz plan i znów ruszy."
    ),
    "plan_expiring": (
        "⏳ <b>{plan} kończy się za {days} dni.</b>\n\n"
        "Przedłuż i nic się nie zmieni — twoje wyszukiwania będą działać bez przerwy."
    ),
    "plan_expired": (
        "Plan {plan} się skończył — jesteś na Free.\n\n"
        "Wyszukiwania są wstrzymane, nie usunięte. Po przedłużeniu ruszą od tego samego miejsca."
    ),
    "paused_by_limit": "⏸ Wstrzymane z powodu zmiany planu: «{name}»",
    "digest_missed": (
        "📬 <b>Kiedy jesteś na Free</b>\n\n"
        "Twoje wstrzymane wyszukiwania złapałyby <b>{n}</b> nowych ogłoszeń przez ostatnie {days} dni. "
        "Tyle właśnie ci umyka."
    ),

    "btn_invite": "🎁 Zaproś znajomego",
    "invite_h": "🎁 <b>Zaproś znajomego</b>",
    "invite_p": "Wyślij ten link komuś, kto odsprzedaje na Vinted. Gdy opłaci dowolny plan, <b>dostajesz {days} dni Pro</b> — a on i tak zaczyna od darmowego tygodnia Pro.",
    "invite_link": "Twój link:",
    "invite_stat": "Przyszło z twojego linku: <b>{n}</b> · z tego zapłaciło: <b>{p}</b>",
    "ref_reward": "🎁 <b>Ktoś z twojego zaproszenia właśnie wykupił plan.</b>\n\nDopisaliśmy ci {days} dni Pro — plan działa do <b>{date}</b>. Dzięki, że o nas mówisz.",
    "no_access": "Brak dostępu. Wyślij /start",
    "admin_only": "Tylko dla adminów.",
    "unit_h": "godz",
    "unit_min": "min",
    "unit_sec": "sek",
    "ago_never": "jeszcze nie",
    "ago_now": "przed chwilą",
    "ago_min": "{n} min temu",
    "ago_h": "{n} godz temu",
    "ago_d": "{n} dni temu",
},

}
