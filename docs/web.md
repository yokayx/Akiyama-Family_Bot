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
   - `ONLINE_SERVER_ID=27`, `ONLINE_SERVER_NAME=Blaine` (GTA5RP Blaine, gta5masterlist.ru)
   - `PLUS_DEF_CHANNEL_ID` — канал, где создаются сборы из панели.

## Запуск

```bash
docker compose up -d --build
```

Сайт слушает `127.0.0.1:8080` в контейнере (`docker-compose.yml` — `ports`).

## Caddy

Ваш Caddy уже проксирует другой проект на этом хосте (`http://:80`, SPA +
`/api/*`). Не трогайте его — **добавьте блок для домена** из файла
`Caddyfile` в репозитории (он берёт приоритет по Host заголовку над
catch-all `:80`). Там же есть комментарии.

Предварительное условие: A-запись `akiyama-5rp.ru` → IP хоста.
После добавления блока:

```bash
caddy reload    # или systemctl reload caddy
```

## Тесты и проверки

```bash
python -m pytest -q
python -m ruff check bot/ tests/
```
