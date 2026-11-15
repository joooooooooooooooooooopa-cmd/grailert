"""Grailert Bot — мониторинг новых объявлений Vinted по поисковым ссылкам.

Мультиюзер, мультиязычный (7 языков), с тарифами и оплатой в Telegram Stars
или криптой через Crypto Pay.

Продуктовая логика в двух словах: аккаунт Vinted пользователя мы не трогаем
вообще — только читаем публичный каталог и пишем в Telegram. Это принципиально,
потому что Vinted банит именно за автоматизацию действий на аккаунте, и наша
безопасность здесь и есть главное отличие от конкурентов с автовыкупом.
"""
from __future__ import annotations

import asyncio
import csv
import html
import io
import logging
import os
import random
import time
from datetime import datetime, timezone

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    LabeledPrice,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

import billing
import config
import db
import i18n
import plans
import rates
import ui
import vinted
import webapp
from i18n import t

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("bot")

# Приложение PTB. Нужно пульту: он живёт в своём потоке и через него шлёт счета
# и начисляет оплаты. Заполняется в on_startup.
_APP: Application | None = None


# --- Доступ и язык -----------------------------------------------------------

def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDS


def lang_of(uid: int, tg_user=None) -> str:
    """Язык пользователя: сохранённый, иначе — из Telegram, иначе английский."""
    saved = db.get_lang(uid)
    if saved:
        return saved
    detected = i18n.detect_lang(getattr(tg_user, "language_code", None))
    if db.get_user(uid):
        db.set_lang(uid, detected)
    return detected


def plan_of(uid: int) -> tuple[str, int]:
    if is_admin(uid):
        return plans.PRO, 0  # админам — полный доступ без оплаты
    return db.effective_plan(uid)


def plan_name(lang: str, plan: str, trial: bool = False) -> str:
    if trial:
        return t(lang, "plan_trial")
    return t(lang, f"plan_{plan}")


def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d.%m.%Y")


# --- Хелперы вывода ----------------------------------------------------------

async def edit(query, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    try:
        await query.edit_message_text(
            text, reply_markup=kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            log.debug("edit failed: %s", e)


def render_menu(uid: int, lang: str):
    st = db.user_stats(uid)
    plan, until = plan_of(uid)
    until_part = t(lang, "menu_plan_until", date=fmt_date(until)) if until and plan != plans.FREE else ""
    text = (
        f"{t(lang, 'menu_title')}\n"
        f"{t(lang, 'menu_sub')}\n\n"
        f"{t(lang, 'menu_searches', total=st['total'], active=st['active'], paused=st['paused'])}\n"
        f"{t(lang, 'menu_found', total=st['notif_total'], today=st['notif_today'])}\n"
        f"{t(lang, 'menu_plan', plan=plan_name(lang, plan), until=until_part)}"
    )
    # Инлайн-меню убрано: все действия живут в нижней панели (ui.reply_kb).
    return text, None


def render_card(sub, lang: str, banner: str | None = None, price_line: str | None = None):
    inc = sub["kw_include"] or "—"
    exc = sub["kw_exclude"] or "—"
    if not sub["active"]:
        state = t(lang, "card_paused")
    elif sub["last_status"] == "error":
        state = t(lang, "card_error")
    else:
        state = t(lang, "card_active")
    head = (banner + "\n\n") if banner else ""
    price = (price_line + "\n") if price_line else ""
    pf = vinted.pretty_price_range(*vinted.price_filter_of(sub["url"])) or "—"
    text = (
        f"{head}🔎 <b>{html.escape(sub['name'])}</b>\n"
        f"{state}\n\n"
        f"{price}"
        f"{t(lang, 'card_interval', interval=ui.pretty_interval(sub['interval_sec'], lang))}\n"
        f"{t(lang, 'card_found', total=db.notif_total(sub['id']), today=db.notif_today(sub['id']))}\n"
        f"{t(lang, 'card_last', ago=ui.ago(sub['last_check'], lang))}\n"
        f"{t(lang, 'card_kwi', v=html.escape(inc))}\n"
        f"{t(lang, 'card_kwe', v=html.escape(exc))}\n"
        f"{t(lang, 'card_pricef', v=html.escape(pf))}\n"
        f"{t(lang, 'card_link', url=html.escape(sub['url'], quote=True))}"
    )
    return text, ui.sub_card(lang, sub)


async def price_snapshot(sub, lang: str) -> str | None:
    """Живой срез цен по поиску: от какой цены и сколько объявлений сейчас."""
    host, params = vinted.parse_search_url(sub["url"])
    client = await vinted.get_client(host)
    items = await client.get_items(params)
    if not items:
        return None
    priced = [(a, c) for a, c in (vinted.price_amount(i) for i in items) if a is not None]
    if not priced:
        return None
    mn = min(a for a, _ in priced)
    cur = priced[0][1]
    usd = await rates.to_usd(mn, cur)
    usd_part = f" ≈ ${usd:,.2f}" if usd else ""
    return t(lang, "card_price_now", price=f"{mn:g} {cur}", usd=usd_part, n=len(items))


def render_list(uid: int, lang: str, page: int):
    subs = db.list_subscriptions(uid)
    if not subs:
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(t(lang, "btn_new_search"), callback_data="add")],
                [InlineKeyboardButton(t(lang, "btn_back_menu"), callback_data="menu")],
            ]
        )
        return t(lang, "list_empty"), kb
    return t(lang, "list_title", n=len(subs)), ui.subs_list(lang, subs, page)


def render_stats(uid: int, lang: str):
    st = db.user_stats(uid)
    lines = [
        t(lang, "stats_title") + "\n",
        t(lang, "stats_searches", total=st["total"], active=st["active"], paused=st["paused"]),
        t(lang, "stats_total", n=st["notif_total"]),
        t(lang, "stats_today", n=st["notif_today"]),
    ]
    subs = db.list_subscriptions(uid)
    if subs:
        lines.append("\n" + t(lang, "stats_by_search"))
        for s in subs[:15]:
            lines.append(
                f"{ui.status_emoji(s)} {html.escape(s['name'])} — "
                f"{db.notif_total(s['id'])} ({db.notif_today(s['id'])})"
            )
    return "\n".join(lines), ui.back_menu(lang, "menu")


def render_invite(uid: int, lang: str):
    st = db.referral_stats(uid)
    link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{uid}"
    text = (
        f"{t(lang, 'invite_h')}\n\n"
        f"{t(lang, 'invite_p', days=plans.REFERRAL_BONUS_DAYS)}\n\n"
        f"{t(lang, 'invite_link')}\n<code>{link}</code>\n\n"
        f"{t(lang, 'invite_stat', n=st['invited'], p=st['paid'])}"
    )
    return text, ui.back_menu(lang, "menu")


def render_plan(uid: int, lang: str):
    plan, until = plan_of(uid)
    lines = [t(lang, "plan_title") + "\n", t(lang, "plan_current", plan=plan_name(lang, plan))]
    if plan != plans.FREE and until:
        days_left = max(0, (until - int(time.time())) // 86400)
        lines.append(t(lang, "plan_until", date=fmt_date(until), days=days_left))
    else:
        lines.append(t(lang, "plan_free_desc"))
    lines += ["", t(lang, "plan_pitch"), "", t(lang, "plan_safety")]
    return "\n".join(lines), ui.plan_kb(lang, plan, billing.crypto_enabled())


# --- Планировщик -------------------------------------------------------------

def schedule_sub(jq, sub, first: float = 3) -> None:
    name = f"sub:{sub['id']}"
    for j in jq.get_jobs_by_name(name):
        j.schedule_removal()
    # Интервал ниже тарифного не даём даже если он остался в базе с прошлого тарифа.
    plan, _ = plan_of(sub["user_id"])
    interval = plans.allowed_interval(plan, sub["interval_sec"])
    jq.run_repeating(
        poll_job, interval=interval, first=first, name=name, data={"sub_id": sub["id"]}
    )


def unschedule_sub(jq, sid: int) -> None:
    for j in jq.get_jobs_by_name(f"sub:{sid}"):
        j.schedule_removal()


async def poll_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    sid = context.job.data["sub_id"]
    sub = db.get_subscription(sid)
    if not sub or not sub["active"]:
        unschedule_sub(context.job_queue, sid)
        return
    await run_poll(context.bot, sub)


async def run_poll(bot, sub, force: bool = False) -> int:
    """Опрашивает поиск, шлёт новые объявления. Возвращает число отправленных."""
    sid = sub["id"]
    lang = lang_of(sub["user_id"])
    host, params = vinted.parse_search_url(sub["url"])
    client = await vinted.get_client(host)
    items = await client.get_items(params)
    if items is None:
        db.record_check(sid, "error")
        return 0
    db.record_check(sid, "ok")

    ids = [i["id"] for i in items if i.get("id")]
    if db.seen_count(sid) == 0:
        db.mark_many_seen(sid, ids)  # первичный baseline — без уведомлений
        return 0

    new = [i for i in items if i.get("id") and not db.is_seen(sid, i["id"])]
    if not new:
        return 0
    new.reverse()  # от старых к новым — порядок уведомлений
    db.mark_many_seen(sid, [i["id"] for i in new])  # дедуп независимо от фильтра

    inc, exc = sub["kw_include"] or "", sub["kw_exclude"] or ""
    to_notify = [i for i in new if vinted.passes_keywords(i.get("title", ""), inc, exc)]

    overflow = 0
    if len(to_notify) > config.MAX_NOTIFY_PER_POLL:
        overflow = len(to_notify) - config.MAX_NOTIFY_PER_POLL
        to_notify = to_notify[-config.MAX_NOTIFY_PER_POLL :]

    # «Рынок» для бейджа 🔥 — медиана цен свежей выдачи этого же поиска.
    median = vinted.deal_median(items)

    sent = 0
    try:
        for item in to_notify:
            if await send_notification(bot, sub, item, lang, deal=vinted.is_deal(item, median)):
                db.add_notification(sid, item["id"])
                sent += 1
            await asyncio.sleep(0.4)
        if overflow:
            await bot.send_message(
                sub["user_id"],
                t(lang, "notify_overflow", n=overflow, name=html.escape(sub["name"])),
                parse_mode=ParseMode.HTML,
            )
    except Forbidden:
        # Пользователь заблокировал бота — снимаем его поиск с автоопроса.
        db.set_active(sid, False)
        log.info("Пользователь %s заблокировал бота — поиск %s на паузе", sub["user_id"], sid)
    return sent


async def send_notification(bot, sub, item, lang: str | None = None, deal: bool = False) -> bool:
    # Фото и все поля берём из ответа каталога — там уже есть полная галерея photos[].
    if lang is None:
        lang = lang_of(sub["user_id"])
    amount, currency = vinted.price_amount(item)
    usd = await rates.to_usd(amount, currency)
    caption = vinted.format_caption(sub["name"], item, usd=usd, lang=lang, deal=deal)
    photos = vinted.photo_urls(None, item)
    chat_id = sub["user_id"]
    try:
        if len(photos) >= 2:
            # sendMediaGroup принимает 2–10 фото; подпись — только на первом.
            media = [
                InputMediaPhoto(media=u, caption=caption if i == 0 else None,
                                parse_mode=ParseMode.HTML if i == 0 else None)
                for i, u in enumerate(photos)
            ]
            await bot.send_media_group(chat_id=chat_id, media=media)
        elif len(photos) == 1:
            await bot.send_photo(chat_id, photos[0], caption=caption, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML)
        return True
    except Forbidden:
        raise  # обрабатывается в run_poll (ставим поиск на паузу)
    except Exception as e:  # noqa: BLE001
        log.warning("Уведомление не отправлено (%s), пробую текстом: %s", sub["id"], e)
        try:
            await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML)
            return True
        except Forbidden:
            raise
        except Exception:  # noqa: BLE001
            return False


# --- Команды -----------------------------------------------------------------

async def open_menu(message, uid: int, lang: str) -> None:
    text, kb = render_menu(uid, lang)
    await message.reply_text(
        text, reply_markup=kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


# --- Закрытый тест: белый список, ключи, лист ожидания -----------------------

def has_access(uid: int) -> bool:
    """Пускать ли человека к функционалу. Админы и режим без инвайтов — всегда."""
    if is_admin(uid) or not config.INVITE_ONLY:
        return True
    return db.is_whitelisted(uid)


def gate_text(uid: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    pos = db.waitlist_position(uid)
    text = t(lang, "gate_text", days=config.INVITE_TRIAL_DAYS)
    if pos:
        text += "\n\n" + t(lang, "waitlist_already", n=pos)
    return text, ui.gate_kb(lang, on_waitlist=bool(pos))


async def send_gate(message, uid: int, lang: str) -> None:
    text, kb = gate_text(uid, lang)
    await message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def notify_admins(context, text: str) -> None:
    for admin in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin, text, parse_mode=ParseMode.HTML)
        except Exception:  # noqa: BLE001
            pass


async def try_key(message, context, uid: int, lang: str, key: str) -> None:
    """Обрабатывает присланный ключ: антиперебор → активация → Pro на N дней."""
    user = message.from_user
    if db.failed_key_attempts(uid) >= config.KEY_ATTEMPTS_PER_HOUR:
        await message.reply_text(t(lang, "key_ratelimited"), parse_mode=ParseMode.HTML)
        return
    if db.is_whitelisted(uid):
        # Второй ключ на тот же аккаунт трюком с лишним триалом не считаем.
        await message.reply_text(t(lang, "key_used"), parse_mode=ParseMode.HTML)
        return
    status = db.use_key(key, uid)
    db.record_key_attempt(uid, key, status == "ok")
    if status == "ok":
        row = db.get_key(key)
        days = int(row["days"] or config.INVITE_TRIAL_DAYS)
        # Пробный период по ключу: если триал уже был (ключ после отзыва и
        # повторного приглашения), продлеваем Pro обычной выдачей.
        if not db.start_trial(uid, plans.PRO, days):
            db.grant_plan(uid, plans.PRO, days, source="invite")
        _, until = plan_of(uid)
        await restore_after_upgrade(context, uid)
        await message.reply_text(
            t(lang, "key_ok", days=days, date=fmt_date(until)),
            reply_markup=ui.reply_kb(lang, is_admin(uid)), parse_mode=ParseMode.HTML,
        )
        await open_menu(message, uid, lang)
        who = f"@{user.username}" if user.username else str(uid)
        note = f" · {html.escape(row['note'])}" if row["note"] else ""
        await notify_admins(context, f"🔑 Ключ <code>{key}</code> активирован: {html.escape(who)} "
                                     f"(<code>{uid}</code>), Pro на {days} дн.{note}")
        return
    if status == "used":
        await message.reply_text(t(lang, "key_used"), parse_mode=ParseMode.HTML)
        # Один и тот же занятый ключ пробуют разные люди — утёк в чат.
        if db.key_attempt_users(key) >= config.KEY_SHARE_ALERT_USERS:
            await notify_admins(context, f"⚠️ Ключ <code>{key}</code> гуляет: его пробовали "
                                         f"{db.key_attempt_users(key)} разных аккаунта за сутки.")
        return
    await message.reply_text(t(lang, "key_bad"), parse_mode=ParseMode.HTML)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid = user.id
    context.user_data.pop("flow", None)

    known = db.get_user(uid) is not None
    db.activate_user(uid, user.username)
    lang = lang_of(uid, user)
    if not db.get_lang(uid):
        db.set_lang(uid, lang)
    # Метка канала из диплинка t.me/<бот>?start=<метка> — по ней потом
    # видно, какой посев привёл платящих, а какой только показы.
    key_from_link = None
    if context.args:
        payload = context.args[0]
        key_from_link = db.normalize_key(payload)
        if key_from_link:
            # Ссылка с ключом: t.me/<бот>?start=GRL-XXXX-XXXX. Источник — метка
            # ключа (кому выдали), сам ключ в отчёт по каналам не пишем.
            row = db.get_key(key_from_link)
            db.set_source(uid, (row["note"] if row and row["note"] else "invite"))
        else:
            db.set_source(uid, payload)
        # Приглашение: t.me/<бот>?start=ref_<id>. Привязка одноразовая
        # и только к существующему пользователю — см. db.set_referrer.
        if payload.startswith("ref_"):
            try:
                db.set_referrer(uid, int(payload[4:]))
            except ValueError:
                pass

    if not has_access(uid):
        if key_from_link:
            await try_key(update.effective_message, context, uid, lang, key_from_link)
            return
        await send_gate(update.effective_message, uid, lang)
        return

    # Пробный Pro выдаётся один раз за всё время — за это отвечает сам запрос.
    got_trial = db.start_trial(uid, plans.PRO, plans.TRIAL_DAYS)

    await update.effective_message.reply_text(
        t(lang, "kb_pinned"), reply_markup=ui.reply_kb(lang, is_admin(uid)), parse_mode=ParseMode.HTML
    )
    if got_trial:
        await update.effective_message.reply_text(
            t(lang, "welcome", days=plans.TRIAL_DAYS), parse_mode=ParseMode.HTML
        )
    elif known:
        # Вернувшийся здоровается, новичок без пробного — редкий случай, ему хватит меню.
        await update.effective_message.reply_text(t(lang, "welcome_back"), parse_mode=ParseMode.HTML)
    await open_menu(update.effective_message, uid, lang)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("flow", None)
    lang = lang_of(update.effective_user.id, update.effective_user)
    await update.effective_message.reply_text(t(lang, "cancelled"))


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    lang = lang_of(uid, update.effective_user)
    await update.effective_message.reply_text(
        t(lang, "lang_choose"), reply_markup=ui.lang_kb(lang)
    )


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    lang = lang_of(uid, update.effective_user)
    if not has_access(uid):
        await send_gate(update.effective_message, uid, lang)
        return
    text, kb = render_plan(uid, lang)
    await update.effective_message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# --- Пейволлы ----------------------------------------------------------------

async def paywall_searches(query_or_msg, uid: int, lang: str, is_query: bool) -> None:
    plan, _ = plan_of(uid)
    text = t(
        lang, "limit_searches",
        plan=plan_name(lang, plan),
        limit=plans.search_limit(plan) or "∞",
        current=db.count_subscriptions(uid),
    )
    kb = ui.upgrade_kb(lang)
    if is_query:
        await edit(query_or_msg, text, kb)
    else:
        await query_or_msg.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def paywall_interval(query, uid: int, lang: str, requested: int) -> None:
    plan, _ = plan_of(uid)
    needed = plans.plan_for_interval(requested)
    text = t(
        lang, "limit_interval",
        interval=ui.pretty_interval(requested, lang),
        needed=plan_name(lang, needed),
        plan=plan_name(lang, plan),
        current=ui.pretty_interval(plans.min_interval(plan), lang),
    )
    await edit(query, text, ui.upgrade_kb(lang))


# --- Оплата ------------------------------------------------------------------

async def send_stars_invoice(context, uid: int, lang: str, code: str) -> None:
    p = plans.PRODUCTS[code]
    period = t(lang, p["period_key"])
    title = t(lang, "invoice_title", plan=plan_name(lang, p["plan"]))
    desc = t(lang, "invoice_desc", plan=plan_name(lang, p["plan"]), period=period)
    pid = db.create_payment(uid, code, "stars", p["stars"], "XTR")
    await context.bot.send_invoice(
        chat_id=uid,
        title=title[:32],
        description=desc[:255],
        payload=f"{code}:{pid}",
        currency="XTR",
        prices=[LabeledPrice(label=title[:32], amount=p["stars"])],
    )


async def send_crypto_invoice(query, context, uid: int, lang: str, code: str) -> None:
    p = plans.PRODUCTS[code]
    desc = t(lang, "invoice_desc", plan=plan_name(lang, p["plan"]), period=t(lang, p["period_key"]))
    pid = db.create_payment(uid, code, "crypto", p["usdt"], "USDT")
    inv = await billing.create_invoice(p["usdt"], desc, payload=f"{code}:{pid}")
    if not inv:
        db.mark_failed(pid)
        await edit(query, t(lang, "crypto_unavailable"), ui.back_menu(lang, "plan"))
        return
    db.set_payment_external(pid, inv["invoice_id"])
    await edit(
        query,
        t(lang, "crypto_created", amount=f"{p['usdt']:.2f}"),
        ui.crypto_invoice_kb(lang, inv["url"], pid),
    )


async def apply_payment(context, payment_row) -> bool:
    """Начисляет тариф по оплаченному платежу. Идемпотентно.

    Всё, что связано с деньгами, проходит здесь и только здесь: и Stars,
    и крипта, и кнопка «я оплатил», и фоновый поллер.
    """
    if not db.mark_paid(payment_row["id"]):
        return False  # уже начислено кем-то другим
    uid = payment_row["user_id"]
    code = payment_row["product"]
    p = plans.PRODUCTS.get(code)
    if not p:
        log.error("Платёж %s: неизвестный продукт %s", payment_row["id"], code)
        return False
    until = db.grant_plan(uid, p["plan"], p["days"])
    lang = lang_of(uid)
    # Тариф вырос — снимаем паузы, которые ставил лимит, и переводим на быстрый интервал.
    await restore_after_upgrade(context, uid)
    try:
        await context.bot.send_message(
            uid,
            t(lang, "pay_ok", plan=plan_name(lang, p["plan"]), date=fmt_date(until)),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Не смог сообщить об оплате %s: %s", uid, e)
    log.info("Оплата: user=%s product=%s until=%s", uid, code, fmt_date(until))
    await reward_referrer(context, uid)
    return True


async def reward_referrer(context, uid: int) -> None:
    """Дарит пригласившему Pro за ПЕРВУЮ оплату приглашённого."""
    inviter = db.claim_referral_bonus(uid)
    if not inviter:
        return
    until = db.grant_plan(inviter, plans.PRO, plans.REFERRAL_BONUS_DAYS, source="referral")
    await restore_after_upgrade(context, inviter)
    ilang = lang_of(inviter)
    try:
        await context.bot.send_message(
            inviter,
            t(ilang, "ref_reward", days=plans.REFERRAL_BONUS_DAYS, date=fmt_date(until)),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Не смог сообщить о бонусе за друга %s: %s", inviter, e)
    log.info("Бонус за приглашение: inviter=%s друг=%s до %s", inviter, uid, fmt_date(until))


async def restore_after_upgrade(context, uid: int) -> None:
    """После апгрейда включает всё, что было на паузе, в рамках нового лимита."""
    plan, _ = plan_of(uid)
    limit = plans.search_limit(plan)
    subs = db.list_subscriptions(uid)
    active = sum(1 for s in subs if s["active"])
    for s in subs:
        if s["active"]:
            continue
        if limit and active >= limit:
            break
        db.set_active(s["id"], True)
        active += 1
    for s in db.list_subscriptions(uid):
        if s["active"]:
            schedule_sub(context.job_queue, s, first=random.uniform(2, 10))


async def on_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stars: подтверждаем счёт, только если он наш и ещё не оплачен."""
    q = update.pre_checkout_query
    try:
        code, pid = q.invoice_payload.split(":")
        payment = db.get_payment(int(pid))
    except (ValueError, AttributeError):
        payment, code = None, None
    if not payment or payment["status"] != "pending" or code not in plans.PRODUCTS:
        await q.answer(ok=False, error_message="This invoice is no longer valid.")
        return
    await q.answer(ok=True)


async def app_make_invoice(uid: int, lang: str, code: str, method: str) -> dict:
    """Счёт для пульта. Тот же путь денег, что в чате: одна запись в payments."""
    p = plans.PRODUCTS[code]
    period = t(lang, p["period_key"])
    title = t(lang, "invoice_title", plan=plan_name(lang, p["plan"]))
    desc = t(lang, "invoice_desc", plan=plan_name(lang, p["plan"]), period=period)
    if method == "stars":
        pid = db.create_payment(uid, code, "stars", p["stars"], "XTR")
        url = await _APP.bot.create_invoice_link(
            title=title[:32],
            description=desc[:255],
            payload=f"{code}:{pid}",
            currency="XTR",
            prices=[LabeledPrice(label=title[:32], amount=p["stars"])],
        )
        return {"ok": True, "kind": "stars", "url": url, "id": pid}

    pid = db.create_payment(uid, code, "crypto", p["usdt"], "USDT")
    inv = await billing.create_invoice(p["usdt"], desc, payload=f"{code}:{pid}")
    if not inv:
        db.mark_failed(pid)
        return {"error": "payment_failed"}
    db.set_payment_external(pid, inv["invoice_id"])
    return {"ok": True, "kind": "crypto", "url": inv["url"], "id": pid}


async def app_check_payment(payment) -> str:
    """Фаза платежа для пульта: paid | failed | pending. Начисляет, если оплачено.

    Звёзды не опрашиваются — их приносит апдейт successful_payment, поэтому по
    ним просто отдаём текущий статус из базы.
    """
    if payment["status"] == "paid":
        return "paid"
    if payment["provider"] == "crypto" and payment["external_id"]:
        st = await billing.invoice_status(payment["external_id"])
        if st and st["status"] == "paid":
            if billing.payment_is_sufficient(st["amount"], payment["amount"]):
                await apply_payment(_APP, payment)
                return "paid"
            db.mark_failed(payment["id"])
            return "failed"
        if st and st["status"] == "expired":
            db.mark_failed(payment["id"])
            return "failed"
    return "pending"


async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sp = update.message.successful_payment
    try:
        _, pid = sp.invoice_payload.split(":")
        payment = db.get_payment(int(pid))
    except (ValueError, AttributeError):
        payment = None
    if not payment:
        log.error("Stars: платёж по payload %s не найден", sp.invoice_payload)
        return
    await apply_payment(context, payment)


async def crypto_poll_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Догоняет оплаты криптой: у нас воркер без вебхука, поэтому опрашиваем сами."""
    for pay in db.pending_crypto_payments():
        st = await billing.invoice_status(pay["external_id"])
        if not st:
            continue
        if st["status"] == "paid":
            if billing.payment_is_sufficient(st["amount"], pay["amount"]):
                await apply_payment(context, pay)
            else:
                # Недоплата успехом не считается: тариф не выдаём, помечаем и не трогаем.
                log.warning(
                    "Недоплата по счёту %s: пришло %.2f вместо %.2f",
                    pay["external_id"], st["amount"], pay["amount"],
                )
                db.mark_failed(pay["id"])
        elif st["status"] == "expired":
            db.mark_failed(pay["id"])


# --- Фоновые задачи удержания ------------------------------------------------

async def expiry_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Напоминает об окончании тарифа и мягко опускает на Free."""
    soon = plans.REMIND_DAYS_BEFORE * 86400
    for u in db.users_expiring(soon):
        uid = u["user_id"]
        lang = lang_of(uid)
        days = max(plans.REMIND_DAYS_BEFORE, (u["plan_until"] - int(time.time())) // 86400)
        st = db.user_stats(uid)
        # Пробным считаем только настоящий пробный период, а не выданный или купленный.
        trial = (u["plan_source"] or "") == "trial"
        crypto_on = billing.crypto_enabled()
        try:
            if trial and u["notified_stage"] != "soon":
                text = t(lang, "trial_ends_soon", days=days, found=st["notif_total"],
                         basic=ui.price_label("basic_30", crypto_on),
                         pro=ui.price_label("pro_30", crypto_on))
            else:
                text = t(lang, "plan_expiring", plan=plan_name(lang, u["plan"]), days=days)
            await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML,
                                           reply_markup=ui.upgrade_kb(lang))
            db.mark_stage(uid, "soon")
        except Forbidden:
            db.mark_stage(uid, "soon")
        except Exception as e:  # noqa: BLE001
            log.warning("Напоминание об окончании тарифа %s: %s", uid, e)

    for u in db.users_expired():
        uid = u["user_id"]
        lang = lang_of(uid)
        was_trial = (u["plan_source"] or "") == "trial"
        st = db.user_stats(uid)
        db.downgrade_to_free(uid)
        await enforce_free_limits(context, uid)
        try:
            text = (t(lang, "trial_over", found=st["notif_total"]) if was_trial
                    else t(lang, "plan_expired", plan=plan_name(lang, u["plan"])))
            await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML,
                                           reply_markup=ui.upgrade_kb(lang))
        except Forbidden:
            pass
        except Exception as e:  # noqa: BLE001
            log.warning("Сообщение об окончании тарифа %s: %s", uid, e)


async def enforce_free_limits(context, uid: int) -> None:
    """Опускает пользователя в рамки Free: лишние поиски на паузу, интервал вверх.

    Ничего не удаляем — это принципиально: человек вернётся и увидит свои поиски
    на месте. Удалённые поиски он бы уже не восстановил, а с ними и не вернулся.
    """
    limit = plans.search_limit(plans.FREE)
    min_int = plans.min_interval(plans.FREE)
    kept = 0
    # Сначала работающие: иначе у человека с активным третьим поиском оставят
    # первый (стоящий на паузе), а тот, которым он реально пользуется, остановят.
    subs = sorted(db.list_subscriptions(uid), key=lambda r: (0 if r["active"] else 1, r["id"]))
    for s in subs:
        if kept < limit:
            kept += 1
            if s["interval_sec"] < min_int:
                db.set_interval(s["id"], min_int)
            if s["active"]:
                schedule_sub(context.job_queue, db.get_subscription(s["id"]),
                             first=random.uniform(5, 30))
        else:
            if s["active"]:
                db.set_active(s["id"], False)
            unschedule_sub(context.job_queue, s["id"])


async def missed_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раз в сутки считает, сколько объявлений прошло мимо поисков на паузе.

    Цифра в дожиме должна быть настоящей, поэтому мы её реально измеряем,
    а не выдумываем: один запрос в сутки на поиск — это дёшево.
    """
    for uid in db.free_users_with_paused():
        total = 0
        for sub in db.paused_subscriptions(uid):
            try:
                host, params = vinted.parse_search_url(sub["url"])
                client = await vinted.get_client(host)
                items = await client.get_items(params)
            except Exception:  # noqa: BLE001
                continue
            if not items:
                continue
            new = [i for i in items if i.get("id") and not db.is_seen(sub["id"], i["id"])]
            if new:
                db.mark_many_seen(sub["id"], [i["id"] for i in new])
                total += len(new)
            await asyncio.sleep(1.0)
        db.add_missed(uid, total)

    # Дожим отправляем не чаще раза в 3 дня и только когда цифра говорит сама за себя.
    now = int(time.time())
    for uid in db.free_users_with_paused():
        u = db.get_user(uid)
        if not u or (u["missed_count"] or 0) < 5:
            continue
        if now - (u["digest_at"] or 0) < 3 * 86400:
            continue
        n, since = db.take_missed(uid)
        days = max(1, (now - since) // 86400) if since else 1
        lang = lang_of(uid)
        try:
            await context.bot.send_message(
                uid, t(lang, "digest_missed", n=n, days=days),
                parse_mode=ParseMode.HTML, reply_markup=ui.upgrade_kb(lang),
            )
        except Exception:  # noqa: BLE001
            pass


# --- Роутер callback-кнопок --------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = query.from_user.id
    lang = lang_of(uid, query.from_user)
    await query.answer()
    data = query.data
    parts = data.split(":")
    cmd = parts[0]
    jq = context.job_queue

    # --- Закрытый тест: лист ожидания и смена языка доступны всем, остальное — нет ---
    if cmd == "wl_join":
        if has_access(uid):
            await edit(query, *render_menu(uid, lang))
            return
        already = db.waitlist_position(uid)
        urow = db.get_user(uid)
        pos = already or db.join_waitlist(uid, query.from_user.username, lang,
                                          urow["source"] if urow else None)
        key_msg = "waitlist_already" if already else "waitlist_joined"
        await edit(query, t(lang, "gate_text", days=config.INVITE_TRIAL_DAYS) + "\n\n"
                   + t(lang, key_msg, n=pos), ui.gate_kb(lang, on_waitlist=True))
        if not already:
            who = f"@{query.from_user.username}" if query.from_user.username else str(uid)
            await notify_admins(context, f"⏳ В листе ожидания #{pos}: {html.escape(who)} "
                                         f"(<code>{uid}</code>, {lang}). Выдать доступ: "
                                         f"Админ → ⏳ Лист ожидания.")
        return
    if not has_access(uid) and cmd not in ("lang", "setlang"):
        await edit(query, *gate_text(uid, lang))
        return

    # --- Навигация ---
    if cmd == "menu":
        context.user_data.pop("flow", None)
        await edit(query, *render_menu(uid, lang))
    elif cmd == "list":
        page = int(parts[1]) if len(parts) > 1 else 0
        await edit(query, *render_list(uid, lang, page))
    elif cmd == "stats":
        await edit(query, *render_stats(uid, lang))
    elif cmd == "plan":
        await edit(query, *render_plan(uid, lang))
    elif cmd == "invite":
        await edit(query, *render_invite(uid, lang))
    elif cmd == "lang":
        await edit(query, t(lang, "lang_choose"), ui.lang_kb(lang))
    elif cmd == "setlang":
        new_lang = parts[1]
        if new_lang in i18n.LANGS:
            db.set_lang(uid, new_lang)
            lang = new_lang
            await query.message.reply_text(t(lang, "lang_saved"), reply_markup=ui.reply_kb(lang, is_admin(uid)))
            await edit(query, *render_menu(uid, lang))
    elif cmd == "export":
        subs = db.list_subscriptions(uid)
        if not subs:
            await query.answer(t(lang, "list_empty"), show_alert=True)
        else:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["name", "url", "interval_sec", "kw_include", "kw_exclude", "active", "found_total"])
            for s in subs:
                w.writerow([s["name"], s["url"], s["interval_sec"], s["kw_include"] or "",
                            s["kw_exclude"] or "", s["active"], db.notif_total(s["id"])])
            bio = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # BOM — корректно в Excel
            bio.name = "vinted_searches.csv"
            await context.bot.send_document(uid, document=bio, filename="vinted_searches.csv")
    elif cmd == "help":
        help_text = t(lang, "help") + "\n\n" + t(lang, "support_line", sup=config.SUPPORT_HANDLE)
        await edit(query, help_text, ui.back_menu(lang, "menu"))
    elif cmd == "diag":
        await edit(query, t(lang, "diag_running"), None)
        res = await (await vinted.get_client(config.DEFAULT_HOST)).check()
        status = t(lang, "diag_ok") if res["ok"] else t(lang, "diag_fail")
        text = (
            f"{t(lang, 'diag_title')}\n\n"
            f"{t(lang, 'diag_host', host=res['host'])}\n"
            f"{t(lang, 'diag_status', status=status)}\n"
            f"{t(lang, 'diag_proxy_on') if res['proxy'] else t(lang, 'diag_proxy_off')}"
        )
        await edit(query, text, ui.back_menu(lang, "menu"))

    # --- Оплата ---
    elif cmd == "buy":
        code = parts[1]
        if code not in plans.PRODUCTS:
            return
        p = plans.PRODUCTS[code]
        await edit(
            query,
            t(lang, "pay_choose", plan=plan_name(lang, p["plan"]), period=t(lang, p["period_key"])),
            ui.pay_method_kb(lang, code, billing.crypto_enabled()),
        )
    elif cmd == "pay":
        method, code = parts[1], parts[2]
        if code not in plans.PRODUCTS:
            return
        if method == "stars":
            await send_stars_invoice(context, uid, lang, code)
        elif method == "crypto":
            await send_crypto_invoice(query, context, uid, lang, code)
    elif cmd == "paychk":
        pid = int(parts[1])
        pay = db.get_payment(pid)
        if not pay or pay["user_id"] != uid:
            return
        if pay["status"] == "paid":
            # Платёж уже начислен: показываем настоящий тариф и дату, а не пустые места.
            plan_now, until_now = plan_of(uid)
            await query.answer(
                t(lang, "pay_ok", plan=plan_name(lang, plan_now),
                  date=fmt_date(until_now) if until_now else "—"),
                show_alert=True,
            )
            await edit(query, *render_plan(uid, lang))
            return
        st = await billing.invoice_status(pay["external_id"]) if pay["external_id"] else None
        if st and st["status"] == "paid" and billing.payment_is_sufficient(st["amount"], pay["amount"]):
            await apply_payment(context, pay)
            await edit(query, *render_plan(uid, lang))
        else:
            await query.answer(t(lang, "pay_pending"), show_alert=True)

    # --- Добавление поиска ---
    elif cmd == "add":
        plan, _ = plan_of(uid)
        if not plans.can_add_search(plan, db.count_subscriptions(uid)):
            await paywall_searches(query, uid, lang, is_query=True)
            return
        context.user_data["flow"] = {"step": "url"}
        await edit(query, t(lang, "add_prompt"), ui.add_kb(lang))
    elif cmd == "presets":
        plan, _ = plan_of(uid)
        if not plans.can_add_search(plan, db.count_subscriptions(uid)):
            await paywall_searches(query, uid, lang, is_query=True)
            return
        await edit(query, t(lang, "presets_prompt"), ui.presets_kb(lang))
    elif cmd == "preset":
        plan, _ = plan_of(uid)
        if not plans.can_add_search(plan, db.count_subscriptions(uid)):
            await paywall_searches(query, uid, lang, is_query=True)
            return
        try:
            keyword = ui.PRESETS[int(parts[1])]
        except (ValueError, IndexError):
            return
        context.user_data["flow"] = {"step": "domain", "keyword": keyword}
        await edit(
            query,
            t(lang, "domain_prompt", kw=html.escape(keyword)),
            ui.domain_kb(lang),
        )
    elif cmd == "addauto":
        flow = context.user_data.get("flow") or {}
        if flow.get("step") == "name":
            params = flow.get("params", {})
            flow["name"] = (params.get("search_text") or "Vinted").replace(",", " ")[:60]
            flow["step"] = "interval"
            plan, _ = plan_of(uid)
            await edit(
                query,
                t(lang, "name_set", name=html.escape(flow["name"])),
                ui.interval_kb(lang, "addint", plan),
            )
    elif cmd == "lockint":
        await paywall_interval(query, uid, lang, int(parts[1]))
    elif cmd == "addint":
        flow = context.user_data.get("flow") or {}
        if flow.get("step") != "interval":
            return
        if parts[1] == "custom":
            flow["step"] = "interval_custom"
            await edit(query, t(lang, "interval_custom", min=config.MIN_INTERVAL), ui.cancel_kb(lang))
        else:
            await finalize_add(query, context, uid, lang, int(parts[1]))
    elif cmd == "dom":
        flow = context.user_data.get("flow") or {}
        if flow.get("step") == "domain" and flow.get("keyword"):
            host = parts[1]
            url = vinted.build_search_url(flow["keyword"], host)
            await edit(query, f"🔎 <b>{html.escape(flow['keyword'])}</b> · {host} ✓", None)
            await _preview_and_name(query.message, context, uid, lang, url)

    # --- Карточка поиска ---
    elif cmd == "sub":
        sub = db.get_subscription(int(parts[1]))
        if sub and sub["user_id"] == uid:
            await edit(query, *render_card(sub, lang))  # быстрый рендер
            try:  # затем подгружаем живой срез цен (с таймаутом)
                pl = await asyncio.wait_for(price_snapshot(sub, lang), 12)
            except Exception:  # noqa: BLE001
                pl = None
            if pl:
                await edit(query, *render_card(sub, lang, price_line=pl))
    elif cmd == "toggle":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if sub and sub["user_id"] == uid:
            active = parts[2] == "on"
            plan, _ = plan_of(uid)
            running = sum(1 for s in db.list_subscriptions(uid) if s["active"])
            if active and not plans.can_add_search(plan, running):
                await paywall_searches(query, uid, lang, is_query=True)
                return
            db.set_active(sid, active)
            if active:
                schedule_sub(jq, db.get_subscription(sid))
            else:
                unschedule_sub(jq, sid)
            await edit(query, *render_card(db.get_subscription(sid), lang))
    elif cmd == "check":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if sub and sub["user_id"] == uid:
            await edit(query, t(lang, "check_running"), None)
            n = await run_poll(context.bot, sub, force=True)
            sub = db.get_subscription(sid)
            if sub["last_status"] == "error":
                banner = t(lang, "check_error")
            elif n > 0:
                banner = t(lang, "check_found", n=n)
            else:
                banner = t(lang, "check_none")
            await edit(query, *render_card(sub, lang, banner))
    elif cmd == "del":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if sub and sub["user_id"] == uid:
            await edit(query, t(lang, "delete_confirm", name=html.escape(sub["name"])),
                       ui.confirm_delete(lang, sid))
    elif cmd == "delok":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if sub and sub["user_id"] == uid:
            unschedule_sub(jq, sid)
            db.delete_subscription(sid)
            await edit(query, *render_list(uid, lang, 0))

    # --- Редактирование (запрос текста) ---
    elif cmd in ("name", "url", "kwi", "kwe", "price"):
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if not (sub and sub["user_id"] == uid):
            return
        prompts = {
            "name": (t(lang, "edit_name"), "edit_name"),
            "url": (t(lang, "edit_url", url=html.escape(sub["url"])), "edit_url"),
            "kwi": (t(lang, "edit_kwi", v=html.escape(sub["kw_include"] or "—")), "edit_kwi"),
            "kwe": (t(lang, "edit_kwe", v=html.escape(sub["kw_exclude"] or "—")), "edit_kwe"),
            "price": (t(lang, "price_prompt"), "edit_price"),
        }
        prompt, step = prompts[cmd]
        context.user_data["flow"] = {"step": step, "sid": sid}
        await edit(query, prompt, ui.cancel_kb(lang))
    elif cmd == "int":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if sub and sub["user_id"] == uid:
            plan, _ = plan_of(uid)
            await edit(query, t(lang, "interval_prompt"), ui.interval_kb(lang, f"setint:{sid}", plan))
    elif cmd == "setint":
        sid = int(parts[1])
        sub = db.get_subscription(sid)
        if not (sub and sub["user_id"] == uid):
            return
        if parts[2] == "custom":
            context.user_data["flow"] = {"step": "edit_interval", "sid": sid}
            await edit(query, t(lang, "interval_custom", min=config.MIN_INTERVAL), ui.cancel_kb(lang))
        else:
            plan, _ = plan_of(uid)
            requested = int(parts[2])
            if requested < plans.min_interval(plan):
                await paywall_interval(query, uid, lang, requested)
                return
            db.set_interval(sid, requested)
            schedule_sub(jq, db.get_subscription(sid))
            await edit(query, *render_card(db.get_subscription(sid), lang, t(lang, "interval_updated")))

    # --- Пауза/запуск всех ---
    elif cmd in ("pauseall", "resumeall"):
        active = cmd == "resumeall"
        if active:
            plan, _ = plan_of(uid)
            limit = plans.search_limit(plan)
            started = sum(1 for s in db.list_subscriptions(uid) if s["active"])
            for s in db.list_subscriptions(uid):
                if s["active"]:
                    continue
                if limit and started >= limit:
                    break
                db.set_active(s["id"], True)
                schedule_sub(jq, db.get_subscription(s["id"]), first=random.uniform(3, 20))
                started += 1
        else:
            for sid in db.set_active_all(uid, False):
                unschedule_sub(jq, sid)
        await edit(query, *render_list(uid, lang, 0))

    # --- Админка ---
    elif cmd.startswith("adm_") or cmd == "admin":
        if not is_admin(uid):
            return
        await handle_admin(query, context, lang, cmd)


async def finalize_add(query, context, uid: int, lang: str, interval: int) -> None:
    flow = context.user_data.get("flow") or {}
    plan, _ = plan_of(uid)
    interval = plans.allowed_interval(plan, max(config.MIN_INTERVAL, interval))
    sid = db.add_subscription(uid, flow.get("name", "Vinted"), flow["url"], interval)
    context.user_data.pop("flow", None)
    schedule_sub(context.job_queue, db.get_subscription(sid), first=3)
    sub = db.get_subscription(sid)
    banner = t(lang, "added_ok") + "\n" + t(lang, "baseline_note")
    await edit(query, *render_card(sub, lang, banner))


# --- Админ-действия ----------------------------------------------------------

def key_issued_text(keys: list[str], days: int, note: str) -> str:
    """Текст с выданными ключами и готовыми ссылками для пересылки."""
    lines = [f"🔑 <b>Ключ{'и' if len(keys) > 1 else ''}</b> — Pro на {days} дн."
             + (f", метка <b>{html.escape(note)}</b>" if note else "") + "\n"]
    for k in keys:
        lines.append(f"<code>{k}</code>\nhttps://t.me/{config.BOT_USERNAME}?start={k}")
    lines.append("\nЧеловек присылает ключ боту или открывает ссылку. Один ключ = один аккаунт.")
    return "\n".join(lines)


async def handle_admin(query, context, lang: str, cmd: str) -> None:
    if cmd == "admin":
        g = db.global_stats()
        mode = "🔒 только по ключу" if config.INVITE_ONLY else "🔓 открытая регистрация"
        text = (
            "🔐 <b>Админ-панель</b>\n\n"
            f"Режим: <b>{mode}</b>\n"
            f"👥 Юзеров: <b>{g['users']}</b> (в белом списке {g['whitelisted']})\n"
            f"⏳ В листе ожидания: <b>{g['waitlist']}</b>\n"
            f"🔑 Свободных ключей: <b>{g['keys_free']}</b>\n"
            f"📂 Поисков: <b>{g['subs']}</b> (🟢 {g['subs_active']})\n"
            f"🆕 Уведомлений всего: <b>{g['notif_total']}</b>"
        )
        await edit(query, text, ui.admin_menu(lang))
    elif cmd == "adm_money":
        r = db.revenue_stats()
        by_plan = ", ".join(f"{k}: {v}" for k, v in r["by_plan"].items()) or "—"
        text = (
            "💰 <b>Деньги</b>\n\n"
            f"Платежей: <b>{r['payments']}</b>\n"
            f"Stars: <b>{r['stars']:.0f} ⭐</b>\n"
            f"Крипта: <b>{r['usdt']:.2f} USDT</b>\n"
            f"Активных платящих: <b>{r['paying']}</b>\n"
            f"По тарифам: {by_plan}"
        )
        await edit(query, text, ui.admin_menu(lang))
    elif cmd == "adm_sources":
        rep = db.sources_report()
        lines = ["📡 <b>Каналы привлечения</b>\n"]
        for r in rep[:25]:
            money = []
            if r["stars"]:
                money.append(f"{r['stars']:.0f}⭐")
            if r["usdt"]:
                money.append(f"{r['usdt']:.2f}$")
            lines.append(
                f"• <b>{html.escape(str(r['src']))}</b> — пришло {r['users']}, "
                f"платят {r['paying']}" + (", " + " + ".join(money) if money else "")
            )
        if len(rep) == 1 and rep[0]["src"] == "(прямой)":
            lines.append("\nМеток пока нет. Ссылка с меткой: "
                         f"<code>t.me/{config.BOT_USERNAME}?start=ИМЯ_КАНАЛА</code>")
        await edit(query, "\n".join(lines), ui.admin_menu(lang))
    elif cmd == "adm_grant":
        context.user_data["flow"] = {"step": "grant"}
        await edit(query, "🎁 Пришли: <code>user_id тариф дней</code>\n"
                          "например <code>12345 pro 30</code>", ui.cancel_kb(lang))
    elif cmd == "adm_newkey":
        key = db.create_key(query.from_user.id)
        await edit(query, key_issued_text([key], config.INVITE_TRIAL_DAYS, ""), ui.admin_menu(lang))
    elif cmd == "adm_batch":
        context.user_data["flow"] = {"step": "keys_batch"}
        await edit(query, "🔑 Пришли: <code>сколько [дней] [метка]</code>\n"
                          "например <code>5 14 partner</code> — 5 ключей на 14 дней с меткой partner.\n"
                          "Метка попадает в отчёт «Каналы» как источник.", ui.cancel_kb(lang))
    elif cmd == "adm_revoke":
        context.user_data["flow"] = {"step": "revoke"}
        await edit(query, "⛔ Пришли ключ, который отозвать (<code>GRL-XXXX-XXXX</code>).\n"
                          "Если ключ уже использован — владелец теряет доступ к боту.",
                   ui.cancel_kb(lang))
    elif cmd == "adm_keys":
        keys = db.list_keys()
        free = [k for k in keys if k["used_by"] is None and not k["revoked_at"]]
        used = [k for k in keys if k["used_by"] is not None and not k["revoked_at"]]
        revoked = [k for k in keys if k["revoked_at"]]

        def _lbl(k):
            d = k["days"] or config.INVITE_TRIAL_DAYS
            n = f" {html.escape(k['note'])}" if k["note"] else ""
            return f"• <code>{k['key']}</code> {d}д{n}"

        lines = ["🗝 <b>Ключи</b>\n", f"Свободные ({len(free)}):"]
        lines += [_lbl(k) for k in free[:20]] or ["—"]
        lines.append(f"\nИспользованные ({len(used)}):")
        lines += [f"{_lbl(k)} → <code>{k['used_by']}</code>" for k in used[:20]] or ["—"]
        if revoked:
            lines.append(f"\nОтозванные: {len(revoked)}")
        await edit(query, "\n".join(lines), ui.admin_menu(lang))
    elif cmd == "adm_waitlist":
        rows = db.list_waitlist(30)
        total = db.waitlist_count()
        lines = [f"⏳ <b>Лист ожидания</b> — {total}\n"]
        for i, r in enumerate(rows, 1):
            who = f"@{html.escape(r['username'])}" if r["username"] else "без юзернейма"
            src = f" · {html.escape(r['source'])}" if r["source"] else ""
            lines.append(f"{i}. {who} <code>{r['user_id']}</code> · {r['lang']}{src} · "
                         f"{fmt_date(r['joined_at'])}")
        if not rows:
            lines.append("—")
        lines.append("\nВыдать доступ: пришли <code>user_id [дней] [метка]</code>, "
                     "например <code>12345 14 partner</code>.")
        context.user_data["flow"] = {"step": "invite"}
        await edit(query, "\n".join(lines), ui.cancel_kb(lang))
    elif cmd == "adm_users":
        users = db.list_users()
        lines = [f"👥 <b>Пользователи</b> ({len(users)})\n"]
        for u in users[:40]:
            uname = f"@{u['username']}" if u["username"] else "—"
            plan, _ = db.effective_plan(u["user_id"])
            lines.append(f"• <code>{u['user_id']}</code> {html.escape(uname)} — {plan}")
        await edit(query, "\n".join(lines), ui.admin_menu(lang))
    elif cmd == "adm_stats":
        g = db.global_stats()
        r = db.revenue_stats()
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"👥 Пользователей: <b>{g['users']}</b>\n"
            f"📂 Поисков всего: <b>{g['subs']}</b> (🟢 {g['subs_active']})\n"
            f"🆕 Уведомлений: <b>{g['notif_total']}</b>\n"
            f"💰 Платящих сейчас: <b>{r['paying']}</b>"
        )
        await edit(query, text, ui.admin_menu(lang))
    elif cmd == "adm_bcast":
        context.user_data["flow"] = {"step": "broadcast"}
        await edit(query, "📢 Пришли текст рассылки для всех пользователей:", ui.cancel_kb(lang))


# --- Запуск создания поиска (по ссылке или ключевому слову) ------------------

async def begin_search(message, context: ContextTypes.DEFAULT_TYPE, uid: int, lang: str, raw: str) -> None:
    raw = raw.strip()
    if vinted.looks_like_vinted_url(raw):
        # Готовая ссылка — домен уже в ней.
        await _preview_and_name(message, context, uid, lang, raw)
    else:
        # Ключевое слово — сперва спросим страну/домен.
        context.user_data["flow"] = {"step": "domain", "keyword": raw}
        await message.reply_text(
            t(lang, "domain_prompt", kw=html.escape(raw)),
            reply_markup=ui.domain_kb(lang),
            parse_mode=ParseMode.HTML,
        )


async def _preview_and_name(message, context, uid: int, lang: str, url: str) -> None:
    host, params = vinted.parse_search_url(url)
    m = await message.reply_text(t(lang, "preview_checking"))
    client = await vinted.get_client(host)
    items = await client.get_items(params)
    context.user_data["flow"] = {"url": url, "params": params, "step": "name"}
    note = t(lang, "preview_fail") if items is None else t(lang, "preview_ok", n=len(items))
    await m.edit_text(
        f"{note}\n\n{t(lang, 'name_prompt')}",
        reply_markup=ui.add_name_kb(lang),
        parse_mode=ParseMode.HTML,
    )


# --- Роутер текстовых сообщений ----------------------------------------------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid = user.id
    text = (update.message.text or "").strip()
    if not db.get_user(uid):
        db.activate_user(uid, user.username)
    lang = lang_of(uid, user)

    # Закрытый тест: без белого списка единственное, что принимаем, — ключ.
    if not has_access(uid):
        key = db.normalize_key(text)
        if key:
            await try_key(update.message, context, uid, lang, key)
        else:
            await send_gate(update.message, uid, lang)
        return

    # Постоянные нижние кнопки — приоритетнее любого активного ввода.
    # Совпадение ищем по всем языкам: юзер мог сменить язык, а клавиатура
    # в его чате осталась старой.
    btn = i18n.match_reply_button(text)
    if btn == "btn_menu":
        context.user_data.pop("flow", None)
        await open_menu(update.message, uid, lang)
        return
    if btn == "btn_list":
        context.user_data.pop("flow", None)
        tx, kb = render_list(uid, lang, 0)
        await update.message.reply_text(tx, reply_markup=kb, parse_mode=ParseMode.HTML,
                                        disable_web_page_preview=True)
        return
    if btn == "btn_add":
        plan, _ = plan_of(uid)
        if not plans.can_add_search(plan, db.count_subscriptions(uid)):
            await paywall_searches(update.message, uid, lang, is_query=False)
            return
        context.user_data["flow"] = {"step": "url"}
        await update.message.reply_text(t(lang, "add_prompt"), parse_mode=ParseMode.HTML,
                                        reply_markup=ui.add_kb(lang))
        return
    if btn in ("btn_plan", "btn_stats", "btn_invite", "btn_help", "btn_lang", "btn_diag", "btn_admin"):
        context.user_data.pop("flow", None)
        if btn == "btn_plan":
            tx, kb = render_plan(uid, lang)
        elif btn == "btn_stats":
            tx, kb = render_stats(uid, lang)
            kb = None  # назад некуда — панель всегда внизу
        elif btn == "btn_invite":
            tx, kb = render_invite(uid, lang)
            kb = None
        elif btn == "btn_help":
            tx = t(lang, "help") + "\n\n" + t(lang, "support_line", sup=config.SUPPORT_HANDLE)
            kb = None
        elif btn == "btn_lang":
            tx, kb = t(lang, "lang_choose"), ui.lang_kb(lang)
        elif btn == "btn_admin":
            if not is_admin(uid):
                return
            tx, kb = "🔐 Admin", ui.admin_menu(lang)
        else:  # btn_diag
            m = await update.message.reply_text(t(lang, "diag_running"))
            res = await (await vinted.get_client(config.DEFAULT_HOST)).check()
            status = t(lang, "diag_ok") if res["ok"] else t(lang, "diag_fail")
            await m.edit_text(
                f"{t(lang, 'diag_title')}\n\n"
                f"{t(lang, 'diag_host', host=res['host'])}\n"
                f"{t(lang, 'diag_status', status=status)}\n"
                f"{t(lang, 'diag_proxy_on') if res['proxy'] else t(lang, 'diag_proxy_off')}"
            )
            return
        await update.message.reply_text(tx, reply_markup=kb, parse_mode=ParseMode.HTML,
                                        disable_web_page_preview=True)
        return

    # Инвайт-ключ от того, кто уже в белом списке: объясняем, что он одноразовый.
    if db.normalize_key(text):
        await try_key(update.message, context, uid, lang, db.normalize_key(text))
        return

    # Мастер-ключ: даёт Pro на 30 дней (раздаём блогерам и первым пользователям).
    if config.MASTER_KEY and text == config.MASTER_KEY:
        db.whitelist_user(uid)
        until = db.grant_plan(uid, plans.PRO, 30, source="promo")
        await restore_after_upgrade(context, uid)
        await update.message.reply_text(
            t(lang, "pay_ok", plan=t(lang, "plan_pro"), date=fmt_date(until)),
            reply_markup=ui.reply_kb(lang, is_admin(uid)), parse_mode=ParseMode.HTML,
        )
        await open_menu(update.message, uid, lang)
        return

    flow = context.user_data.get("flow")
    if not flow:
        plan, _ = plan_of(uid)
        if not plans.can_add_search(plan, db.count_subscriptions(uid)):
            await paywall_searches(update.message, uid, lang, is_query=False)
            return
        # Любой свободный текст = поиск по ключевому слову по всему сайту.
        await begin_search(update.message, context, uid, lang, text)
        return

    step = flow.get("step")

    # --- Шаги добавления ---
    if step == "url":
        await begin_search(update.message, context, uid, lang, text)
    elif step == "domain":
        # Пользователь прислал другое слово вместо выбора домена — обновляем.
        flow["keyword"] = text
        await update.message.reply_text(
            t(lang, "domain_prompt", kw=html.escape(text)),
            reply_markup=ui.domain_kb(lang), parse_mode=ParseMode.HTML,
        )
    elif step == "name":
        flow["name"] = text[:60]
        flow["step"] = "interval"
        plan, _ = plan_of(uid)
        await update.message.reply_text(
            t(lang, "name_set", name=html.escape(flow["name"])),
            reply_markup=ui.interval_kb(lang, "addint", plan), parse_mode=ParseMode.HTML,
        )
    elif step == "interval_custom":
        sec = _parse_int(text)
        if sec is None:
            await update.message.reply_text(t(lang, "need_number"))
            return
        await _finalize_add_from_message(update, context, uid, lang, max(config.MIN_INTERVAL, sec))

    # --- Шаги редактирования ---
    elif step == "edit_name":
        db.set_name(flow["sid"], text[:60])
        await _reply_card(update, flow["sid"], lang, t(lang, "name_updated"))
        context.user_data.pop("flow", None)
    elif step == "edit_url":
        if not vinted.looks_like_vinted_url(text):
            await update.message.reply_text(t(lang, "url_invalid"))
            return
        db.set_url(flow["sid"], text)
        schedule_sub(context.job_queue, db.get_subscription(flow["sid"]))
        await _reply_card(update, flow["sid"], lang, t(lang, "url_updated"))
        context.user_data.pop("flow", None)
    elif step == "edit_kwi":
        db.set_keywords(flow["sid"], include="" if text == "-" else text)
        await _reply_card(update, flow["sid"], lang, t(lang, "kwi_updated"))
        context.user_data.pop("flow", None)
    elif step == "edit_kwe":
        db.set_keywords(flow["sid"], exclude="" if text == "-" else text)
        await _reply_card(update, flow["sid"], lang, t(lang, "kwe_updated"))
        context.user_data.pop("flow", None)
    elif step == "edit_price":
        rng = vinted.parse_price_range(text)
        if rng is None:
            await update.message.reply_text(t(lang, "price_invalid"), parse_mode=ParseMode.HTML)
            return
        sub = db.get_subscription(flow["sid"])
        db.set_url(flow["sid"], vinted.set_price_filter(sub["url"], *rng))
        schedule_sub(context.job_queue, db.get_subscription(flow["sid"]))
        await _reply_card(update, flow["sid"], lang, t(lang, "price_updated"))
        context.user_data.pop("flow", None)
    elif step == "edit_interval":
        sec = _parse_int(text)
        if sec is None:
            await update.message.reply_text(t(lang, "need_number"))
            return
        plan, _ = plan_of(uid)
        sec = max(config.MIN_INTERVAL, sec)
        if sec < plans.min_interval(plan):
            sec = plans.min_interval(plan)
        db.set_interval(flow["sid"], sec)
        schedule_sub(context.job_queue, db.get_subscription(flow["sid"]))
        await _reply_card(update, flow["sid"], lang, t(lang, "interval_updated"))
        context.user_data.pop("flow", None)

    # --- Админ ---
    elif step == "grant" and is_admin(uid):
        context.user_data.pop("flow", None)
        try:
            target, plan_code, days = text.split()
            until = db.grant_plan(int(target), plan_code, int(days))
            await restore_after_upgrade(context, int(target))
            await update.message.reply_text(f"✅ {target} → {plan_code} до {fmt_date(until)}")
            tlang = lang_of(int(target))
            await context.bot.send_message(
                int(target),
                t(tlang, "pay_ok", plan=plan_name(tlang, plan_code), date=fmt_date(until)),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Не вышло: {e}")
    elif step == "keys_batch" and is_admin(uid):
        context.user_data.pop("flow", None)
        try:
            parts = text.split()
            n = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else config.INVITE_TRIAL_DAYS
            note = " ".join(parts[2:] if len(parts) > 1 and parts[1].isdigit() else parts[1:])
            keys = db.create_keys(uid, n, days, note)
            await update.message.reply_text(key_issued_text(keys, days, note),
                                            parse_mode=ParseMode.HTML,
                                            reply_markup=ui.admin_menu(lang))
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Не вышло: {e}")
    elif step == "revoke" and is_admin(uid):
        context.user_data.pop("flow", None)
        key = db.normalize_key(text)
        res = db.revoke_key(key) if key else None
        if res is None:
            await update.message.reply_text("⚠️ Такого ключа нет.", reply_markup=ui.admin_menu(lang))
        else:
            who = f", владелец <code>{res['used_by']}</code> потерял доступ" if res["used_by"] else ""
            await update.message.reply_text(f"⛔ Ключ <code>{key}</code> отозван{who}.",
                                            parse_mode=ParseMode.HTML,
                                            reply_markup=ui.admin_menu(lang))
    elif step == "invite" and is_admin(uid):
        context.user_data.pop("flow", None)
        try:
            parts = text.split()
            target = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else config.INVITE_TRIAL_DAYS
            note = " ".join(parts[2:] if len(parts) > 1 and parts[1].isdigit() else parts[1:])
            if not db.get_user(target):
                raise ValueError("такого пользователя в базе нет — он должен хотя бы нажать /start")
            key = db.invite_user(target, uid, days, note)
            if note:
                db.set_source(target, note)
            if not db.start_trial(target, plans.PRO, days):
                db.grant_plan(target, plans.PRO, days, source="invite")
            _, until = plan_of(target)
            await restore_after_upgrade(context, target)
            tlang = lang_of(target)
            await context.bot.send_message(
                target, t(tlang, "invite_granted", days=days, date=fmt_date(until)),
                reply_markup=ui.reply_kb(tlang, is_admin(target)), parse_mode=ParseMode.HTML,
            )
            await update.message.reply_text(
                f"✅ <code>{target}</code> → доступ открыт, Pro до {fmt_date(until)}, "
                f"ключ <code>{key}</code>", parse_mode=ParseMode.HTML,
                reply_markup=ui.admin_menu(lang))
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Не вышло: {e}")
    elif step == "broadcast" and is_admin(uid):
        context.user_data.pop("flow", None)
        sent = 0
        for target in db.user_ids():
            try:
                await context.bot.send_message(target, text, parse_mode=ParseMode.HTML)
                sent += 1
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.05)
        await update.message.reply_text(f"📢 Разослано: {sent}")


def _parse_int(text: str) -> int | None:
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


async def _finalize_add_from_message(update, context, uid: int, lang: str, interval: int) -> None:
    flow = context.user_data.get("flow") or {}
    plan, _ = plan_of(uid)
    interval = plans.allowed_interval(plan, interval)
    sid = db.add_subscription(uid, flow.get("name", "Vinted"), flow["url"], interval)
    context.user_data.pop("flow", None)
    schedule_sub(context.job_queue, db.get_subscription(sid), first=3)
    banner = t(lang, "added_ok") + "\n" + t(lang, "baseline_note")
    text, kb = render_card(db.get_subscription(sid), lang, banner)
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True)


async def _reply_card(update, sid: int, lang: str, banner: str) -> None:
    text, kb = render_card(db.get_subscription(sid), lang, banner)
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True)


# --- Запуск ------------------------------------------------------------------

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.warning("Необработанная ошибка: %s", context.error)


# Во сколько выходит пост в канал (UTC). 16 UTC — 18:00 по Центральной Европе,
# вечернее время, когда ленту листают.
CHANNEL_POST_HOUR_UTC = int(os.getenv("CHANNEL_POST_HOUR_UTC", "16"))

# Что показываем в канале. Ходовые вещи перекупов: по ним всегда есть свежая
# выдача, и они же показывают, ради чего человеку нужен алерт.
CHANNEL_QUERIES = [
    ("stone island", "vinted.pl"),
    ("carhartt wip", "vinted.de"),
    ("arcteryx", "vinted.fr"),
    ("nike tn", "vinted.pl"),
    ("the north face nuptse", "vinted.de"),
    ("ralph lauren", "vinted.it"),
    ("stussy", "vinted.co.uk"),
]


async def channel_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ежедневный пост в канал: живая находка с Vinted и кнопка в бота.

    Канал, который наполняют руками, умирает на третьей неделе. Тут контент
    берётся из того же источника, что и сам продукт, поэтому не кончится.
    Пока бота не сделали админом канала — задача молча ничего не делает.
    """
    channel = db.get_channel()
    if not channel:
        return
    now = datetime.now(timezone.utc)
    # Вечер по Европе — время, когда перекупы листают ленту. Берём окно в два
    # часа, а не ровно час: джоба привязана к моменту старта процесса, и при
    # неудачном рестарте проверка «ровно этот час» пропустила бы день целиком.
    if not (CHANNEL_POST_HOUR_UTC <= now.hour < CHANNEL_POST_HOUR_UTC + 2):
        return
    key = f"channel_post:{now.strftime('%Y-%m-%d')}"
    if not db.flag_once(key):
        return

    query, host = CHANNEL_QUERIES[datetime.now(timezone.utc).timetuple().tm_yday
                                  % len(CHANNEL_QUERIES)]
    try:
        url = vinted.build_search_url(query, host)
        _host, params = vinted.parse_search_url(url)
        client = await vinted.get_client(_host)
        items = await client.get_items(params) or []
        picked = _pick_for_channel(items)
        if not picked:
            db.drop_flag(key)
            return
        item, photos = picked
        amount, currency = vinted.price_amount(item)
        usd = await rates.to_usd(amount, currency)
        caption = _channel_caption(query, _host, item, usd)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            "⚡ Get alerts like this",
            url=f"https://t.me/{config.BOT_USERNAME}?start=channel")]])
        await context.bot.send_photo(channel["id"], photos[0], caption=caption,
                                     parse_mode=ParseMode.HTML, reply_markup=kb)
        log.info("Пост в канал %s: %s", channel["id"], query)
    except Exception:
        log.exception("Пост в канал не вышел")
        db.drop_flag(key)   # завтра попробуем снова, день не сгорает


def _pick_for_channel(items: list) -> tuple[dict, list] | None:
    """Самая дешёвая вещь с фотографией: именно такие находки и продают продукт."""
    best = None
    for item in items:
        photos = vinted.photo_urls(None, item)
        amount, _ = vinted.price_amount(item)
        if not photos or amount is None or amount <= 0:
            continue
        if best is None or amount < best[0]:
            best = (amount, item, photos)
    return (best[1], best[2]) if best else None


def _channel_caption(query: str, host: str, item: dict, usd: float | None) -> str:
    title = html.escape(item.get("title") or "")
    brand = html.escape(item.get("brand_title") or "")
    size = html.escape(item.get("size_title") or "—")
    price = html.escape(vinted.item_price(item))
    usd_part = f" ≈ <b>${usd:,.2f}</b>" if usd else ""
    link = html.escape(item.get("url") or "", quote=True)
    country = host.split(".")[-1].upper()
    lines = [
        f"🔥 <b>{title}</b>",
        f"💶 <b>{price}</b>{usd_part} · {country}",
    ]
    if brand:
        lines.append(f"🏷 {brand} · size {size}")
    if link:
        lines.append(f'\n<a href="{link}">Open on Vinted ↗</a>')
    lines.append(f"\n<i>Found by watching «{html.escape(query)}» — "
                 f"listed minutes ago, still available.</i>")
    return "\n".join(lines)


async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Бота добавили админом в канал — запоминаем канал сами.

    Так автопостинг заводится одним действием в Telegram: id канала доставать
    руками не нужно, а getUpdates у бота на поллинге занят.
    """
    upd = update.my_chat_member
    chat = upd.chat
    if chat.type not in ("channel", "supergroup"):
        return
    status = upd.new_chat_member.status
    # Канал принимаем только от своих: иначе любой человек создаёт канал, делает
    # бота админом — и наш ежедневный пост уезжает к нему, а наш канал молчит.
    by = getattr(upd, "from_user", None)
    if status == "administrator" and not is_admin(getattr(by, "id", 0)):
        log.warning("Бота сделали админом канала %s (%s) не из ADMIN_IDS — игнорирую",
                    chat.title, chat.id)
        return
    if status == "administrator":
        db.set_channel(chat.id, chat.title or "")
        log.info("Канал подключён: %s (%s)", chat.title, chat.id)
        for admin in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin, f"📡 Канал <b>{html.escape(chat.title or str(chat.id))}</b> "
                           f"подключён (<code>{chat.id}</code>). Автопостинг может публиковать туда.",
                    parse_mode=ParseMode.HTML)
            except Exception:  # noqa: BLE001
                pass
    else:
        # Любой статус кроме админского значит, что постить туда мы уже не можем:
        # разжалованный до участника или ограниченный бот прав на публикацию не имеет.
        current = db.get_channel()
        if current and current["id"] == chat.id:
            db.clear_channel()
            log.info("Канал отключён (статус %s): %s", status, chat.id)


async def on_startup(app: Application) -> None:
    global _APP
    _APP = app
    await app.bot.set_my_commands(
        [
            BotCommand("menu", "Main menu"),
            BotCommand("plan", "Plan and payment"),
            BotCommand("language", "Change language"),
            BotCommand("start", "Restart the bot"),
            BotCommand("cancel", "Cancel current input"),
        ]
    )
    if billing.crypto_enabled():
        me = await billing.check_token()
        log.info("CryptoPay: %s", "токен рабочий" if me else "ТОКЕН НЕ ОТВЕЧАЕТ — крипта выключится")
    else:
        log.warning("CryptoPay: токен не задан, оплата только через Stars")

    # Те, кто пользовался ботом до появления тарифов, не должны проснуться
    # на Free с одним поиском — выдаём им Pro на переходный период.
    granted = db.grant_legacy_users(plans.PRO, config.LEGACY_GRANT_DAYS)
    if granted:
        log.info("Старым пользователям выдан Pro на %s дней: %d чел.",
                 config.LEGACY_GRANT_DAYS, granted)

    subs = db.all_active_subscriptions()
    for sub in subs:
        schedule_sub(app.job_queue, sub, first=random.uniform(5, 30))
    log.info("Запланировано активных поисков: %d", len(subs))

    jq = app.job_queue
    jq.run_repeating(crypto_poll_job, interval=20, first=15, name="crypto_poll")
    jq.run_repeating(expiry_job, interval=3600, first=60, name="expiry")
    jq.run_repeating(missed_job, interval=86400, first=300, name="missed")
    # Пост в канал раз в сутки; внутри стоит защита «один раз в день», поэтому
    # частая проверка безопасна и переживает рестарты сервиса.
    jq.run_repeating(channel_job, interval=600, first=120, name="channel")

    # Пульт и статистика. Запускаем здесь, а не в main(): серверу нужна живая
    # петля бота — из своего потока он через неё дёргает опрос и счета.
    webapp.start({
        "lang_of": lang_of,
        "plan_of": plan_of,
        "plan_name": plan_name,
        "fmt_date": fmt_date,
        "schedule": schedule_sub,
        "unschedule": unschedule_sub,
        "job_queue": lambda: app.job_queue,
        "bot": lambda: app.bot,
        "run_poll": run_poll,
        "crypto_enabled": billing.crypto_enabled,
        "make_invoice": app_make_invoice,
        "check_payment": app_check_payment,
    })
    if config.APP_URL:
        try:
            await app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Grailert", web_app=WebAppInfo(url=f"{config.APP_URL}/app")))
            log.info("Пульт: %s/app", config.APP_URL)
        except Exception as e:  # noqa: BLE001
            log.warning("Не удалось поставить кнопку пульта: %s", e)
    else:
        log.warning("APP_URL не задан — пульт не показывается")


async def on_shutdown(app: Application) -> None:
    await billing.close()


def main() -> None:
    db.init_db()
    db.init_billing()
    if config.INVITE_SEED_KEYS:
        n = db.seed_keys(config.INVITE_SEED_KEYS)
        log.info("Посев ключей из INVITE_SEED_KEYS: новых %d", n)
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .concurrent_updates(True)  # медленный запрос одного юзера не блокирует других
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("language", cmd_lang))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(PreCheckoutQueryHandler(on_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    log.info("Grailert Bot запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
