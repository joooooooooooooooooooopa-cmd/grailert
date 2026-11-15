"""Тарифы, лимиты и цены.

Логика денег отделена от бота намеренно: цены и лимиты меняются часто,
а трогать хендлеры при каждом изменении цены не хочется.

Почему такие лимиты: ценность инструмента — не в числе поисков, а в скорости
проверки. Недооценённый лот на Vinted уходит за минуты, поэтому интервал и есть
главное, что продаётся. Число поисков — вторая ось, по ней растут перекупы.
"""
from __future__ import annotations

import os

FREE = "free"
BASIC = "basic"
PRO = "pro"

# Сколько дней даём Pro новому пользователю без оплаты.
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "3"))  # было 7, сокращено до 3

# За сколько дней до конца тарифа напоминаем. Значение всегда >= 2,
# иначе в текстах получится «через 1 дня» — грамматика ломается на всех языках.
REMIND_DAYS_BEFORE = int(os.getenv("REMIND_DAYS_BEFORE", "3"))

# Сколько дней Pro получает пригласивший, когда друг ВПЕРВЫЕ оплатил.
# Награда за оплату, а не за переход: иначе рефералка превращается
# в ферму пустых аккаунтов.
REFERRAL_BONUS_DAYS = int(os.getenv("REFERRAL_BONUS_DAYS", "14"))

# searches: 0 = без ограничений. min_interval — минимально допустимая частота (сек).
LIMITS: dict[str, dict[str, int]] = {
    FREE: {"searches": 1, "min_interval": 900},
    BASIC: {"searches": 3, "min_interval": 120},
    PRO: {"searches": 0, "min_interval": 30},
}

# Иерархия: нужна, чтобы понять, апгрейд это или нет.
RANK = {FREE: 0, BASIC: 1, PRO: 2}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


# Что можно купить. stars — цена в Telegram Stars, usdt — цена в USDT через Crypto Pay.
# Stars дороже в пересчёте не по нашей воле: Apple и Google забирают ~30% с мобильных
# покупок, поэтому крипта для нас выгоднее и стоит для пользователя дешевле.
PRODUCTS: dict[str, dict] = {
    "basic_30": {
        "plan": BASIC,
        "days": 30,
        "stars": _int_env("PRICE_BASIC_STARS", 500),
        "usdt": _float_env("PRICE_BASIC_USDT", 9.99),
        "period_key": "period_month",
    },
    "pro_30": {
        "plan": PRO,
        "days": 30,
        "stars": _int_env("PRICE_PRO_STARS", 999),
        "usdt": _float_env("PRICE_PRO_USDT", 19.99),
        "period_key": "period_month",
    },
    "pro_365": {
        "plan": PRO,
        "days": 365,
        "stars": _int_env("PRICE_PRO_YEAR_STARS", 9990),
        "usdt": _float_env("PRICE_PRO_YEAR_USDT", 199.0),
        "period_key": "period_year",
    },
}


def product(code: str) -> dict | None:
    return PRODUCTS.get(code)


def limits(plan: str) -> dict[str, int]:
    return LIMITS.get(plan, LIMITS[FREE])


def search_limit(plan: str) -> int:
    """0 — без ограничений."""
    return limits(plan)["searches"]


def min_interval(plan: str) -> int:
    return limits(plan)["min_interval"]


def can_add_search(plan: str, current: int) -> bool:
    limit = search_limit(plan)
    return limit == 0 or current < limit


def allowed_interval(plan: str, requested: int) -> int:
    """Подтягивает интервал до минимально допустимого на тарифе."""
    return max(requested, min_interval(plan))


def plan_for_interval(interval: int) -> str:
    """Самый дешёвый тариф, на котором такой интервал разрешён."""
    for p in (FREE, BASIC, PRO):
        if interval >= min_interval(p):
            return p
    return PRO


def is_upgrade(current: str, new: str) -> bool:
    return RANK.get(new, 0) > RANK.get(current, 0)


def stars_price(code: str) -> int:
    return PRODUCTS[code]["stars"]


def usdt_price(code: str) -> float:
    return PRODUCTS[code]["usdt"]
