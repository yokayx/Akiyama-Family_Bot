# Сайт akiyama-5rp.ru

Сайт живёт внутри процесса бота (FastAPI + uvicorn в одном контейнере, общая SQLite-база).

## Что на сайте

Публичные страницы:

- `/` — главная: онлайн, состав, статистика войн
- `/roster` — состав семьи (из roster-бота)
- `/vzp` — история войн, статистика и топ игроков (VZP)
- `/online` — онлайн сервера (gta5masterlist.ru, публичный JSON)
- `/gatherings` — активные сборы

Панель стаффа (Discord OAuth, не пароли):

- `/staff` — дашборд
- `/staff/applications` — заявки (взять/освободить/принять/отклонить с причиной)
- `/staff/gatherings` — список сборов и создание через форму

## Подготовка

1. **DNS**: добавить A-запись `akiyama-5rp.ru` (и `www`) на сервер с Caddy.
2. **Discord OAuth-приложение**: Discord Developer Portal → OAuth2 → URL Generator
   - Scopes: `identify`, `guilds`
   - Redirect URL: `https://akiyama-5rp.ru/auth/callback`
   - Указать Client ID / Client Secret в `.env` (`OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`).
3. **`.env`** (см. `.env.example`):
   - `WEB_SECRET` — ключ сессии панели: `openssl rand -hex 32`
   - `ONLINE_SERVER_ID=8`, `ONLINE_SERVER_NAME=Richman` (GTA5RP)
   - `PLUS_DEF_CHANNEL_ID` — канал, где создаются сборы из панели.

## Запуск

```bash
docker compose up -d --build
```

Сайт слушает `127.0.0.1:8080` в контейнере (`docker-compose.yml` — `ports`).

## Caddy

Файл `Caddyfile` в репозитории — плейлист для домена: TLS через Let's Encrypt,
проксирование на `127.0.0.1:8080`. Сюда же виться `www`.

Скопировать `Caddyfile` на сервер (в `~/.config/caddy/Caddyfile` или `/etc/caddy/Caddyfile`)
и перезагрузить:

```bash
caddy reload    # или systemctl reload caddy
```

## Тесты и проверки

```bash
python -m pytest -q
python -m ruff check bot/ tests/
```
