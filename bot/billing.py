"""Оплата: Telegram Stars и крипта через Crypto Pay API.

Почему два способа. Stars удобны (оплата в два тапа, без ухода из Telegram),
но Apple и Google забирают ~30% с мобильных покупок, а мобильных у нас будет
большинство. Крипта берёт около 3% и в пересчёте дешевле для пользователя,
поэтому она стоит первой у тех, кто платит регулярно.

Начисление тарифа идёт ТОЛЬКО через db.mark_paid(), который переводит платёж
из pending в paid одним UPDATE. Это даёт идемпотентность: и вебхук, и поллер,
и кнопка «я оплатил» могут прийти одновременно — начислит ровно один из них.
"""
from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("billing")

CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN", "").strip()
CRYPTOPAY_TESTNET = os.getenv("CRYPTOPAY_TESTNET", "").strip().lower() in ("1", "true", "yes")
CRYPTOPAY_ASSET = os.getenv("CRYPTOPAY_ASSET", "USDT").strip() or "USDT"

_API = "https://testnet-pay.crypt.bot/api" if CRYPTOPAY_TESTNET else "https://pay.crypt.bot/api"

# Сколько живёт счёт: дольше суток держать смысла нет, курс и настроение уходят.
INVOICE_TTL_SEC = int(os.getenv("INVOICE_TTL_SEC", "3600"))

_client: httpx.AsyncClient | None = None


def crypto_enabled() -> bool:
    return bool(CRYPTOPAY_TOKEN)


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN},
        )
    return _client


async def close() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None


async def _call(method: str, **params) -> dict | None:
    """Вызов Crypto Pay. None — если API недоступен или ответил ошибкой."""
    if not crypto_enabled():
        return None
    try:
        client = await _get_client()
        r = await client.post(f"{_API}/{method}", json=params)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("CryptoPay %s: сеть/разбор ответа — %s", method, e)
        return None
    if not data.get("ok"):
        log.warning("CryptoPay %s: ошибка API — %s", method, data.get("error"))
        return None
    return data.get("result")


async def check_token() -> dict | None:
    """Проверка токена на старте: чтобы не узнать о битом токене от первого клиента."""
    return await _call("getMe")


async def create_invoice(amount: float, description: str, payload: str) -> dict | None:
    """Создаёт счёт. Возвращает {'invoice_id', 'url'} либо None."""
    res = await _call(
        "createInvoice",
        asset=CRYPTOPAY_ASSET,
        amount=f"{amount:.2f}",
        description=description[:1024],
        payload=payload[:4096],
        expires_in=INVOICE_TTL_SEC,
        allow_comments=False,
        allow_anonymous=True,
    )
    if not res:
        return None
    # Поле со ссылкой в разных версиях API называется по-разному — берём что есть.
    url = (
        res.get("bot_invoice_url")
        or res.get("mini_app_invoice_url")
        or res.get("web_app_invoice_url")
        or res.get("pay_url")
    )
    if not url or not res.get("invoice_id"):
        log.warning("CryptoPay: в ответе нет ссылки или invoice_id: %s", res)
        return None
    return {"invoice_id": str(res["invoice_id"]), "url": url}


async def invoice_status(invoice_id: str) -> dict | None:
    """Статус счёта: {'status': active|paid|expired, 'amount': float, 'asset': str}."""
    res = await _call("getInvoices", invoice_ids=str(invoice_id))
    if not res:
        return None
    items = res.get("items") or []
    if not items:
        return None
    inv = items[0]
    try:
        amount = float(inv.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return {"status": inv.get("status"), "amount": amount, "asset": inv.get("asset")}


def payment_is_sufficient(paid_amount: float, expected: float) -> bool:
    """Недоплату успехом не считаем.

    Допуск в один цент — на округление у провайдера, не на скидку: без него
    счёт на 9.99, пришедший как 9.9899999, отвалился бы как недоплата.
    """
    return paid_amount + 0.01 >= expected
