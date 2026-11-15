"""Конфигурация бота. Все значения — из переменных окружения / .env"""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Админы — полный доступ + управление ключами (создание, рассылка, статистика).
ADMIN_IDS = {
    int(x)
    for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",")
    if x
}

# Мастер-ключ всегда активирует доступ и не расходуется. Пустой = выключен:
# дефолтного значения нет, иначе ключ из исходников открыл бы Pro любому.
MASTER_KEY = os.getenv("MASTER_KEY", "").strip()

# Режим «только по приглашению» (закрытый тест, 09.09.2026): без ключа бот
# не даёт функционала — предлагает прислать ключ GRL-XXXX-XXXX или встать
# в лист ожидания. Выключить: INVITE_ONLY=0. Те, кто был в базе до включения,
# доступ сохраняют (разовая миграция в db.init_invites).
INVITE_ONLY = os.getenv("INVITE_ONLY", "1").strip().lower() not in ("0", "", "false", "no", "off")

# Сколько дней Pro даёт инвайт-ключ (по умолчанию для новых ключей).
INVITE_TRIAL_DAYS = int(os.getenv("INVITE_TRIAL_DAYS", "14"))

# Посев ключей при старте: «GRL-XXXX-XXXX:14:partner,GRL-…» (дни и метка
# необязательны). Нужен, чтобы выдать ключи без захода в админку — например,
# сгенерировать заранее и раздать до выкатки. Уже существующие не трогает.
INVITE_SEED_KEYS = os.getenv("INVITE_SEED_KEYS", "").strip()

# Сколько неудачных попыток ввести ключ в час на пользователя — антиперебор.
KEY_ATTEMPTS_PER_HOUR = int(os.getenv("KEY_ATTEMPTS_PER_HOUR", "5"))

# Сколько РАЗНЫХ людей должны попытаться ввести один и тот же уже занятый ключ
# за сутки, чтобы админу пришёл сигнал «ключ гуляет по чатам».
KEY_SHARE_ALERT_USERS = int(os.getenv("KEY_SHARE_ALERT_USERS", "3"))

# Путь к SQLite. На хостинге указать путь на томе (/data/vinted.db), иначе база слетит при редеплое.
DB_PATH = os.getenv("DB_PATH", "vinted.db").strip()

# Интервал опроса по умолчанию (сек) и минимально допустимый.
DEFAULT_INTERVAL = int(os.getenv("DEFAULT_INTERVAL", "120"))
MIN_INTERVAL = int(os.getenv("MIN_INTERVAL", "30"))

# Опциональный прокси для запросов к Vinted (socks5://user:pass@host:port или http://...).
# Полезно на хостинге, если Cloudflare/Datadome режет датацентровый IP.
VINTED_PROXY = os.getenv("VINTED_PROXY", "").strip() or None

# Домен Vinted по умолчанию, если не удалось распарсить из ссылки.
DEFAULT_HOST = os.getenv("VINTED_HOST", "vinted.pl").strip()

# Сколько объявлений тянуть за один опрос (берём самые новые).
PER_PAGE = int(os.getenv("PER_PAGE", "20"))

# Лимит фото в одной медиагруппе Telegram.
MAX_PHOTOS = 10

# Сколько максимум уведомлений слать за один опрос (остальное — сводкой).
MAX_NOTIFY_PER_POLL = int(os.getenv("MAX_NOTIFY_PER_POLL", "8"))

# Бейдж «🔥 дешевле похожих»: цена ≤ DEAL_RATIO × медианы свежей выдачи поиска,
# медиана считается только если в пачке ≥ DEAL_MIN_SAMPLES объявлений с ценой.
DEAL_RATIO = float(os.getenv("DEAL_RATIO", "0.6"))
DEAL_MIN_SAMPLES = int(os.getenv("DEAL_MIN_SAMPLES", "8"))

# Сколько независимых сессий Vinted держим на домен (пул против очереди на локе)
VINTED_POOL = int(os.getenv("VINTED_POOL", "3"))

# Минимальный зазор между запросами к одному домену Vinted (сек) — анти-бан.
REQUEST_GAP = float(os.getenv("REQUEST_GAP", "0.8"))

# Сколько дней Pro выдать разово тем, кто пользовался ботом до появления тарифов.
LEGACY_GRANT_DAYS = int(os.getenv("LEGACY_GRANT_DAYS", "30"))

# Юзернейм бота — из него собирается ссылка-приглашение.
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username").lstrip("@")

# Размер страницы в списке поисков.
PAGE_SIZE = 8

# Аккаунт поддержки — показывается в справке.
SUPPORT_HANDLE = os.getenv("SUPPORT_HANDLE", "@your_support").strip()

# Публичный адрес сервиса — из него собирается ссылка на пульт (Mini App).
# Не задан — пульт просто не показывается.
APP_URL = os.getenv("APP_URL", "").strip().rstrip("/")

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN обязателен — задай его в .env")
