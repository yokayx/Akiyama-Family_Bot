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

## Тесты

```bash
pip install -e ".[dev]"
pytest tests/ -q
ruff check bot tests tools
```
