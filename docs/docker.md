# Docker

Бот в контейнере, SQLite на хосте в `./data`.

## Запуск

```bash
cp .env.example .env
# в .env — DISCORD_TOKEN
mkdir -p data
docker compose up -d --build
docker compose logs -f bot
```

Стоп: `docker compose down`. База остаётся в `data/akiyama.db`.

Если контейнер не может писать в `data/` (permission denied):

```bash
sudo chown -R 1000:1000 data
```

В контейнере пользователь `akiyama` (uid 1000).

## Что внутри

| Файл | Зачем |
|------|--------|
| `Dockerfile` | Python 3.12-slim, `pip install .`, non-root |
| `docker-compose.yml` | restart, том `./data`, логи с ротацией, `init` |
| `.dockerignore` | не тащить `.venv`, `.git`, `.env`, тесты в образ |

Токен только через `.env` / `env_file`, в образ не копируется.

`DATABASE_URL` в compose зашит на `sqlite+aiosqlite:///data/akiyama.db` — путь внутри контейнера, это том.

## Наружу: HTTPS

Порт 8080 опубликован только на `127.0.0.1` — в интернет его отдаёт Caddy или
туннель Cloudflare:

```bash
# обычно: блок для сайта добавляется в уже работающий Caddy (Apella.ru)
#   docker exec <caddy> caddy reload --config /etc/caddy/Caddyfile

# вариант без белого IP и проброса портов (CLOUDFLARE_TUNNEL_TOKEN в .env)
docker compose --profile tunnel up -d
```

Подробности и диагностика «сайт не открывается по https» — [https.md](https.md).
