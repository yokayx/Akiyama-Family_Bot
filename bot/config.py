from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env читаем на уровне модуля: константы ниже переопределяются через окружение.
load_dotenv()


def _env_int(name: str, default: int = 0) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_ids(name: str) -> tuple[int, ...]:
    raw = os.environ.get(name, "").strip()
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return tuple(ids)


# --- Сервер и руководство ------------------------------------------------------
GUILD_ID = 1426244196246749347

LEADER_ROLE_ID = 1426244421623615498
DEPUTY_ROLE_ID = 1426244452623847575
HEAD_VZP_ROLE_ID = 1534898714601328670
HEAD_RECRUITMENT_ROLE_ID = 1515648107315204269
RECRUIT_ROLE_ID = 1515765421587042405
HIGH_STAFF_ROLE_ID = 1426244480662507680
MAIN_STAFF_ROLE_ID = 1426244505388056757
YOUNG_STAFF_ROLE_ID = 1446666205787197542

# Ранги состава сверху вниз: (role_id, заголовок секции).
# Порядок и список — под family; реkrut-роли можно убрать, если не нужны.
RANK_ROLES: tuple[tuple[int, str], ...] = (
    (LEADER_ROLE_ID, "Leader of Akiyama"),
    (DEPUTY_ROLE_ID, "Deputy Leader of Akiyama"),
    (HIGH_STAFF_ROLE_ID, "High Staff of Akiyama"),
    (MAIN_STAFF_ROLE_ID, "Main Staff of Akiyama"),
    (YOUNG_STAFF_ROLE_ID, "Young Staff of Akiyama"),
    (HEAD_VZP_ROLE_ID, "Head VZP"),
    (HEAD_RECRUITMENT_ROLE_ID, "Head Recruitment"),
    (RECRUIT_ROLE_ID, "Recruit"),
)

RANK_ROLE_IDS: frozenset[int] = frozenset(role_id for role_id, _ in RANK_ROLES)

# Руководство: /refresh, тег при ошибке, панель управления, синк команд.
LEADERSHIP_ROLE_IDS: tuple[int, ...] = (
    LEADER_ROLE_ID,
    DEPUTY_ROLE_ID,
)

# Категории стула, которые считаются «стаффом» для заявок (взять/отклонить).
STAFF_ROLE_IDS: tuple[int, ...] = (
    HEAD_RECRUITMENT_ROLE_ID,
    RECRUIT_ROLE_ID,
)

FAMILY_NAME = "Akiyama"
PLACEHOLDER = "."
ERROR_CHANNEL_TEXT = "Возникла проблема при отправке состава"
MAX_SEND_ATTEMPTS = 3
DISCORD_MESSAGE_LIMIT = 2000
SEND_GAP_SECONDS = 0.4
MOSCOW_TZ = "Europe/Moscow"

# --- Каналы (0 = не настроен, модуль молчит) -----------------------------------
# Настроить в .env: см. .env.example. ROSTER_CHANNEL_ID — обязателен для состава.
ROSTER_CHANNEL_ID = _env_int("ROSTER_CHANNEL_ID")
OWNER_CHANNEL_ID = _env_int("OWNER_CHANNEL_ID")
VZP_CHANNEL_ID = _env_int("VZP_CHANNEL_ID")
# Служебный канал: сюда внешний инструмент кладёт JSON с данными войн.
VZP_INGEST_CHANNEL_ID = _env_int("VZP_INGEST_CHANNEL_ID", 0)
APPLICATIONS_CHANNEL_ID = _env_int("APPLICATIONS_CHANNEL_ID")
TICKETS_CATEGORY_ID = _env_int("TICKETS_CATEGORY_ID")
CLOSED_TICKETS_CATEGORY_ID = _env_int("CLOSED_TICKETS_CATEGORY_ID")
CONTROL_PANEL_CHANNEL_ID = _env_int("CONTROL_PANEL_CHANNEL_ID")
# Канал для авто-уведомления и авто-сбора на деф. 0 → VZP_CHANNEL_ID.
PLUS_DEF_CHANNEL_ID = _env_int("PLUS_DEF_CHANNEL_ID") or VZP_CHANNEL_ID

# --- Заявки ----------------------------------------------------------------------
APPLICATION_KIND_MAIN = "main"
APPLICATION_KIND_VZP = "vzp"
APPLICATION_KIND_LABELS = {
    APPLICATION_KIND_MAIN: "Main",
    APPLICATION_KIND_VZP: "VZP",
}
APPLICATION_KIND_PANEL_LABELS = {
    APPLICATION_KIND_MAIN: "Main",
    APPLICATION_KIND_VZP: "VZP",
}
# Как состав называется в меню заявок и в панели управления.
APPLICATION_KIND_COMPOSITIONS = {
    APPLICATION_KIND_MAIN: "Состав фракционных мероприятий + при желании VZP",
    APPLICATION_KIND_VZP: "Состав играющий онли VZP",
}
APPLICATION_KIND_REQUIREMENTS = {
    APPLICATION_KIND_MAIN: "Нужны откаты с Арены.",
    APPLICATION_KIND_VZP: "Нужны откаты с VZP и Арены.",
}
# Роли составов. Main по умолчанию — Young Staff; role для VZP-состава через .env.
APPLICATION_KIND_ROLE_IDS = {
    APPLICATION_KIND_MAIN: _env_int("APPLICATION_KIND_MAIN_ROLE_ID", YOUNG_STAFF_ROLE_ID),
    APPLICATION_KIND_VZP: _env_int("APPLICATION_KIND_VZP_ROLE_ID"),
}
APPLICATION_MEMBER_ROLE_ID = _env_int("APPLICATION_MEMBER_ROLE_ID")
# Роли, которые выдаются при принятии (по умолчанию — Young Staff).
APPLICATION_ACCEPT_ROLE_IDS = _env_ids("APPLICATION_ACCEPT_ROLE_IDS") or (YOUNG_STAFF_ROLE_ID,)
# Кого тегаем, когда заявитель написал в тикете.
APPLICATION_PING_ROLE_IDS = (HEAD_RECRUITMENT_ROLE_ID, RECRUIT_ROLE_ID)
APPLICATIONS_MESSAGE_KEY = "applications_menu"
CONTROL_MESSAGE_KEY = "control_panel"
# Кастомные эмодзи статуса набора; 0 → обычные ✅/❌.
APPLICATION_OPEN_EMOJI_ID = _env_int("APPLICATION_OPEN_EMOJI_ID")
APPLICATION_CLOSED_EMOJI_ID = _env_int("APPLICATION_CLOSED_EMOJI_ID")
if APPLICATION_OPEN_EMOJI_ID:
    APPLICATION_OPEN_EMOJI = f"<:on:{APPLICATION_OPEN_EMOJI_ID}>"
else:
    APPLICATION_OPEN_EMOJI = "✅"
if APPLICATION_CLOSED_EMOJI_ID:
    APPLICATION_CLOSED_EMOJI = f"<:off:{APPLICATION_CLOSED_EMOJI_ID}>"
else:
    APPLICATION_CLOSED_EMOJI = "❌"

# --- Сборы -----------------------------------------------------------------------
# Роль, которую бот выдаёт человеку при заходе на сервер (0 = не настроен).
JOIN_ROLE_ID = _env_int("JOIN_ROLE_ID")
PLUS_PING_GENERAL_ROLE_ID = _env_int("PLUS_PING_GENERAL_ROLE_ID")
PLUS_PING_VZP_ROLE_ID = _env_int("PLUS_PING_VZP_ROLE_ID")
PLUS_KIND_GENERAL = "general"
PLUS_KIND_VZP = "vzp"
PLUS_KIND_LABELS = {
    PLUS_KIND_GENERAL: "Общий",
    PLUS_KIND_VZP: "VZP",
}
PLUS_KIND_PINGS = {
    PLUS_KIND_GENERAL: PLUS_PING_GENERAL_ROLE_ID,
    PLUS_KIND_VZP: PLUS_PING_VZP_ROLE_ID,
}
# Кто может ставить плюсы на сборах VZP сверх состава и руководства.
# По умолчанию — Head VZP; тег VZP и состав «онли VZP» — через .env.
PLUS_VZP_ROLE_IDS = _env_ids("PLUS_VZP_ROLE_IDS") or (HEAD_VZP_ROLE_ID,)
# Кто может откидывать (закрывать) сборы VZP: Head VZP.
PLUS_VZP_CANCEL_ROLE_IDS = (HEAD_VZP_ROLE_ID,)

# --- ВЗП (vzp-launcher.pro) --------------------------------------------------------
VZP_API_BASE = "https://vzp-launcher.pro/api"
VZP_FAMILY_NAME = "Akiyama"
VZP_SERVER_NAME = "Blaine"
VZP_POLL_SECONDS = 300
VZP_FETCH_LIMIT = 100
VZP_FETCH_PAGES = 3
VZP_HTTP_TIMEOUT = 25
VZP_RETRIES = 3
# Окно, в котором считаем активную войну «свежим забивом» (список иногда
# хранит протухшие active-записи за несколько дней).
VZP_DEF_WINDOW_MINUTES = 45
VZP_SOURCE_NOTE = "vzp-launcher.pro · не официальный API GTA5RP"

# --- Логи (ког bot/cogs/logs.py) ---------------------------------------------------
# 0 = канал не настроен, лог для него просто не отправляется.
LOG_TEXT_CHANNEL_ID = _env_int("LOG_TEXT_CHANNEL_ID")
LOG_VOICE_CHANNEL_ID = _env_int("LOG_VOICE_CHANNEL_ID")
LOG_MEMBER_CHANNEL_ID = _env_int("LOG_MEMBER_CHANNEL_ID")
LOG_MODERATION_CHANNEL_ID = _env_int("LOG_MODERATION_CHANNEL_ID")
LOG_SERVER_CHANNEL_ID = _env_int("LOG_SERVER_CHANNEL_ID")
LOG_INVITE_CHANNEL_ID = _env_int("LOG_INVITE_CHANNEL_ID")
LOG_AUDIT_CHANNEL_ID = _env_int("LOG_AUDIT_CHANNEL_ID")
# «Живая консоль»: сюда транслируется журнал Python.
LOG_BOT_LIVE_CHANNEL_ID = _env_int("LOG_BOT_LIVE_CHANNEL_ID")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_token: str
    database_url: str = "sqlite+aiosqlite:///data/akiyama.db"
    # Привилегированный интент «Message Content»: без него Discord не присылает
    # текст сообщений и логи удаления/правки пустые. Включён по умолчанию.
    # Выключить принудительно: MESSAGE_CONTENT_INTENT=false
    message_content_intent: bool = True

    # --- Веб-сайт (бот и сайт в одном процессе, общая БД) ---
    # ОAuth-приложение в Discord Developer Portal: «OAuth2 → URL Generator»,
    # scopes: identify, guilds. Redirect URL — https://akiyama-5rp.ru/auth/callback.
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_redirect_uri: str = "https://akiyama-5rp.ru/auth/callback"
    # Домен для canonical URL (links в панели). Пусто → localhost.
    site_url: str = "https://akiyama-5rp.ru"
    # HMAC-ключ для подписи cookie сессии сайта (WEB_SECRET в .env).
    web_secret: str = ""

    # --- Онлайн-статистика сервера (gta5masterlist.ru, публичный JSON) ---
    # GTA5RP Blaine = serverId 27. Имя для отображения — как в конфиге.
    online_server_id: int = 27
    online_server_name: str = "Blaine"
    # /api/servers — лист всех серверов (gta5rp/majestic/...), фильтруем по
    # serverId. Можно переопределить URL целиком.
    online_api_url: str = "https://gta5masterlist.ru/api/servers"


def load_settings() -> Settings:
    return Settings()
