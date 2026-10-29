# Akiyama Family Bot

Discord-бот семьи Akiyama (GTA5RP): состав, сборы, заявки, логи и итоги войн
с сервера Blaine через vzp-launcher.pro.

## Стек

Python 3.11+ · discord.py 2.x · SQLite (SQLAlchemy 2.0 async) · pydantic-settings
· Ruff · pytest · Docker.

## Что внутри

| Ког | Что делает |
|-----|-------------|
| Roster | Канал состава: rebuild из ролей, без пингов (точки → edit), переотправка в 00:00 МСК, `/refresh` |
| Plus | Сборы `/плюсы` с кнопками ➕/➖, опциональный статик, авто-сбор на деф |
| Applications | Заявки в семью: тикеты, форма, принять/отклонить, панель управления набором, ДР |
| VZP | Итоги войн Akiyama/Blaine, приём JSON от внешнего инструмента, авто-уведомление о дефе |
| AutoRole | Роль при входе на сервер |
| Logs | Логи сервера по категориям, инвайт-трекер, live-консоль |
| Core | Синхронизация слэш-команд, `/синк` |

Доки по логике каждого модуля — в `docs/`.

## Запуск

1. Создать бота в Discord Developer Portal, включить интенты
   `Server Members`, `Message Content` (привилегированный), дать права
   «Управлять сервером» (инвайты) и «Просматривать журнал аудита».
2. Скопировать `.env.example` в `.env`, указать `DISCORD_TOKEN` и
   настроить каналы/роли (см. comments в `.env.example`). Roles семьи и
   сервера уже в `bot/config.py`.
3. Запустить:

```bash
pip install -e ".[dev]"
python -m bot
```

Или Docker (SQLite остаётся на хосте в `data/`):

```bash
mkdir -p data
docker compose up -d --build
docker compose logs -f bot
```

## Сайт и HTTPS

Сайт (`akiyama-5rp.ru`) живёт в том же процессе, что и бот: FastAPI на
`127.0.0.1:8080`, снаружи его отдаёт Caddy (проброс 80/443) или Cloudflare
Tunnel (белый IP и порты не нужны).

- Браузер пишет **«Сайт отправил недействительный ответ»** →
  [docs/https.md](docs/https.md): разбор, почему так, и варианты починки.
- Быстрая диагностика на сервере: `bash tools/diagnose_site.sh` (sudo не нужен).
- Проверка живости сайта: `curl -I https://akiyama-5rp.ru/api/health`.

Если Caddy на хосте правится только через sudo, а Docker доступен — HTTPS
поднимает **Caddy в контейнере** на 443 (порт 80 не трогает, сертификат по
TLS-ALPN-01):

```bash
docker compose --profile caddy up -d
docker compose logs -f caddy
```

Конфиг — `deploy/caddy/Caddyfile`, сертификаты — `data/caddy/`.

## Тесты

```bash
pip install -e ".[dev]"
pytest tests/ -q
ruff check bot tests tools
```
