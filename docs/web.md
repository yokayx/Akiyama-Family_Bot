# Сайт akiyama-5rp.ru

Сайт живёт внутри процесса бота: **React SPA** (Vite) + **FastAPI JSON API**
в одном контейнере, общая SQLite-база. SPA отдаётся FastAPI из `frontend/dist`.

## Стек

- Фронт: React 19 + TypeScript + Vite + React Router (без UI-китов — ручная
  темная тема в `src/styles.css`)
- Бэк: FastAPI + uvicorn (в `bot/cogs/web.py`), Python 3.12
- SPA: `bot/web/app.py` монтирует `frontend/dist` и отдаёт index.html для
  клиентских маршрутов (catch-all)

## Что на сайте

Публичные страницы:

- `/` — главная: онлайн, состав, статистика войн
- `/roster` — состав семьи (из roster-бота)
- `/vzp` — история войн, статистика и топ игроков (VZP)
- `/online` — онлайн сервера (gta5masterlist.ru, /api/servers, фильтр по serverId)
- `/gatherings` — активные сборы

Панель стаффа (Discord OAuth, не пароли):

- `/staff` — дашборд
- `/staff/applications` — заявки (взять/освободить/принять/отклонить с причиной)
- `/staff/gatherings` — список сборов и создание через форму

## LOCAL DEV

1. Бот с API на 8080: `python -m bot` (нужен `.env`).
2. Фронт с прокси на 8080:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, /api/* и /auth/* проксируются в 8080
```

3. Сборка: `npm run build` → `frontend/dist`.

## Подготовка продакшена

> Если браузер пишет «Сайт отправил недействительный ответ» — это не код сайта,
> а сеть: до Caddy/до контейнера не доходят запросы. Разбор и починка —
> [https.md](https.md).

1. **DNS**: добавить A-запись `akiyama-5rp.ru` (и `www`) на сервер с Caddy.
2. **Discord OAuth-приложение**: Discord Developer Portal → OAuth2 → URL Generator
   - Scopes: `identify`, `guilds`
   - Redirect URL: `https://akiyama-5rp.ru/auth/callback`
   - Client ID / Secret в `.env` (`OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`).
3. **`.env`** (см. `.env.example`):
   - `WEB_SECRET` — ключ сессии панели: `openssl rand -hex 32`
   - `ONLINE_SERVER_ID=27`, `ONLINE_SERVER_NAME=Blaine` (GTA5RP Blaine, gta5masterlist.ru)
   - `PLUS_DEF_CHANNEL_ID` — канал, где создаются сборы из панели.

## Запуск (Docker)

```bash
docker compose up -d --build
```

Dockerfile мультистаг: сначала `npm run build` (frontend), потом dist кладётся
в образ бота — сайт и API в одном контейнере на `127.0.0.1:8080`.

Без белого IP / с CGNAT сайт отдаётся через Cloudflare Tunnel — профиль
`tunnel` в compose (порты 80/443 не нужны):

```bash
# CLOUDFLARE_TUNNEL_TOKEN=... в .env
docker compose --profile tunnel up -d
docker compose logs -f tunnel
curl -I https://akiyama-5rp.ru/api/health     # 200
```

Пошагово (Zero Trust, публичный хостнейм, что делать со старой A-записью) —
[https.md](https.md).

## Caddy

Ваш Caddy уже проксирует другой проект на этом хосте (`http://:80`, SPA +
`/api/*`). Не трогайте его — **добавьте блок для домена** из файла
`Caddyfile` в репозитории (он берёт приоритет по Host заголовку над
catch-all `:80`). Там же есть комментарии.

Предварительное условие: A-запись `akiyama-5rp.ru` → IP хоста И входящие
80/443 реально доходят до Caddy. Проверка — скрипт `tools/diagnose_site.sh`
(сверяет внешний IP с DNS, смотрит слушателей портов, сертификаты и лог ACME).

После добавления блока:

```bash
caddy validate --config /etc/caddy/Caddyfile
caddy reload    # или systemctl reload caddy
```

`www.akiyama-5rp.ru` в конфиге — только если для него есть DNS-запись
(сейчас её нет: Caddy будет вечно пытаться выпустить на это имя сертификат).

Если провайдер режет входящий 80 — Caddy не получит сертификат по HTTP-01;
нужен DNS-01 через Cloudflare API или туннель, см. docs/https.md.

## Тесты

```bash
python -m pytest -q
python -m ruff check bot/ tests/
cd frontend && npm run build    # проверка TS-сборки
```
