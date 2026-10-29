# HTTPS не работает: «Сайт отправил недействительный ответ»

Симптом (Chrome/Edge/Яндекс.Браузер): **«Этот сайт не может обеспечить безопасное
подключение. Сайт akiyama-5rp.ru отправил недействительный ответ»**
(`ERR_SSL_PROTOCOL_ERROR`). По `http://akiyama-5rp.ru` сайт тоже не открывается.

Это **не** просроченный и не самоподписанный сертификат — для них другие коды
(`NET::ERR_CERT_DATE_INVALID`, `NET::ERR_CERT_AUTHORITY_INVALID`) и другая
формулировка. `ERR_SSL_PROTOCOL_ERROR` означает: TCP-соединение установилось,
но **TLS-рукопожатие не состоялось** — сервер не прислал ни сертификат, ни
ошибку, а просто закрыл соединение.

Caddy не может отдать сайт по HTTPS без сертификата, а сертификат Let's Encrypt
он выпускает только когда снаружи до него доходят проверки (HTTP-01 — порт 80,
TLS-ALPN-01 — порт 443). Поэтому проблема не в коде сайта, а в **сетевой
доступности хоста**.

> **Коротко:** сайт стоит за домашним подключением, до которого из интернета
> запросы не доходят. Быстрое и надёжное решение — Cloudflare Tunnel
> (вариант A ниже): без проброса портов, без белого IP, TLS на стороне
> Cloudflare. Если нужен «классический» Caddy — вариант B.

## Что показала проверка домена (29.10.2026)

| Проверка | Результат |
|---|---|
| NS | `yahir.ns.cloudflare.com`, `diana.ns.cloudflare.com` — DNS на Cloudflare |
| A `akiyama-5rp.ru` | `92.124.130.182` (AS12389 Rostelecom, Омск), TTL 300 — **DNS-only**, оранжевое облако Cloudflare выключено |
| AAAA / CAA / TXT | нет |
| A `www.akiyama-5rp.ru` | **нет записи (NXDOMAIN)**, при этом имя указано в `Caddyfile` |
| TCP :443 с 4 внешних узлов | соединение устанавливается (0.12–0.28 с), но TLS-ответа нет: `SSL_ERROR_SYSCALL`, прочитано 0 байт |
| HTTP :80 снаружи | `Empty reply from server` — соединение принимают и молча закрывают |
| Certificate Transparency (`crt.sh`) | ни одного сертификата для домена → Let's Encrypt **ни разу** не смог пройти проверку |
| :22, :8080, :8443 снаружи | тоже «connect ok», но ни одного байта в ответ — похоже на промежуточный фильтр |

Картина: TCP кто-то принимает, но **до Caddy запрос не доходит**. Так выглядит
одно из четырёх:

1. **CGNAT** — провайдер выдаёт «серый» IP, проброс портов на роутере
   бесполезен в принципе;
2. **проброса портов нет** или он указывает на старый адрес (динамический IP
   сменился, A-запись осталась прежней);
3. **провайдер режет входящие 80/443** (у Rostelecom на домашних тарифах бывает);
4. **Caddy не запущен**, а SYN принимает роутер/файрвол и молча роняет.

Вариант A спасает от всех четырёх; вариант B — только если у провайдера
публичный IP и входящие 80/443 не режутся.

## Шаг 1. Проверить, что происходит на самом сервере

```bash
bash tools/diagnose_site.sh            # внутри репозитория
bash tools/diagnose_site.sh akiyama-5rp.ru
```

Скрипт (только чтение, ничего не меняет) покажет: какой IP видит интернет,
совпадает ли он с A-записью, кто слушает 80/443, отвечает ли бот на 8080,
выпускал ли Caddy сертификаты и что в его логе по ACME.

Ключевой вопрос — **совпадает ли `curl -s https://api.ipify.org` с A-записью**.
Если нет — DNS указывает не туда, и никакой проброс не поможет.

Отдельно проверьте, что сам сайт жив (это работает всегда, даже без DNS и TLS):

```bash
curl -s http://127.0.0.1:8080/api/health     # {"ok":true,"service":"akiyama-site"}
```

Если тут `{"ok":true}` — бот и сайт в порядке, проблема только в доставке
трафика снаружи. Порт 8080 опубликован только на `127.0.0.1`, поэтому с
другого компьютера в локальной сети по `http://192.168.x.x:8080` сайт не
откроется — это ожидаемо, а не поломка.

## Частый случай: порт 443 никто не слушает

Вывод `tools/diagnose_site.sh`, который сразу ставит диагноз:

```
== 3. Локальные слушатели 80 / 443 ==
       LISTEN 0 4096 0.0.0.0:80 0.0.0.0:*
       LISTEN 0 4096 127.0.0.1:8080 127.0.0.1:*
== 5. Что отдаёт HTTP на порту 80 ==
       HTTP-код: 308   Location: https://akiyama-5rp.ru/
== 9. Проверка снаружи ==
       http://akiyama-5rp.ru  → 308
       https://akiyama-5rp.ru → 000
```

Читается так:

| Факт | Что значит |
|---|---|
| A-запись = внешний IP | DNS и IP в порядке, CGNAT нет — сеть тут не виновата |
| порт **80 слушает**, 443 — **нет** | кто-то (роутер или сервер) принимает TCP на 443 и молча закрывает: TLS-рукопожатие вести некому |
| `http` отдаёт **308** на `https` | HTTP-сервер жив и сам зовёт на HTTPS, которого не существует |
| `https` → `000` | ни сертификата, ни TLS — отсюда «отправил недействительный ответ» |

То есть сертификат тут вообще не при чём: **на 443 некому говорить по TLS**.

Проверки снаружи (4 узла в Иране, Словении, Испании, Австрии) уточняют картину:

| Что | Снаружи |
|---|---|
| `http://akiyama-5rp.ru/` | **308** с трёх узлов → входящий **80 доходит до хоста** |
| `https://akiyama-5rp.ru/` | TCP соединяется, **0 байт в ответ** → на 443 отвечает не ваш сервер |

Значит проброс работает хотя бы для 80, а 443 принимает кто-то другой
(скорее всего сам роутер или правило на другой порт). Отсюда порядок действий:

1. **Добавить сайт в свой Caddy от Apella.ru** — он уже на этом хосте и
   правится без sudo, см. раздел «Свой Caddy (Apella.ru)». Затем
   **проброс 443 на роутере** → IP хоста.
2. **Cloudflare Tunnel** (вариант A) — если 443 пробросить не получается.
3. **Caddy службой + sudo** (вариант B) — если своего контейнера нет.

Что проверить руками (всё работает без sudo):

```bash
ss -lnt | grep -E ':(80|443)\b'                         # свободен ли 443
curl -sI http://127.0.0.1/ | grep -i '^server'        # кто отвечает на 80
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' | grep -i caddy
ls -l /etc/caddy/Caddyfile                             # читается? править всё равно нужен root
```

- 443 свободен → сейчас его никто не слушает; блок в Caddy начнёт слушать;
- 443 занят другим сервисом → освободите или пробросьте 443 на другой порт;
- на 80 отвечает Caddy, запущенный **контейнером** → это ваш Caddy (Apella),
  его Caddyfile правится без sudo: добавляйте блок туда, отдельный сервер
  не нужен.

Проверить, что сайт-источник жив, можно независимо от всего этого:

```bash
curl -s http://127.0.0.1:8080/api/health      # {"ok":true,"service":"akiyama-site"}
```

Если здесь вместо JSON пришёл HTML (`<!doctype html>`) — в контейнере
**старая сборка** (SPA-фолбэк перехватывает `/api/*`), пересоберите:
`git pull && docker compose up -d --build`.

## Вариант A. Cloudflare Tunnel (рекомендуется)

Сайт уходит наружу через исходящее соединение к Cloudflare: **не нужны ни
белый IP, ни проброс портов, ни открытые 80/443**. TLS-сертификат на
`akiyama-5rp.ru` держит Cloudflare, домашний IP в DNS не светится.
DNS домена уже на Cloudflare — этим и пользуемся.

Порядок:

1. **Zero Trust → Networks → Tunnels → Create a tunnel** (тип `Cloudflared`),
   имя, например, `akiyama`. Скопировать **токен** из команды установки
   (`eyJhIjoi...`).
2. В туннеле → **Public hostname → Add a public hostname**:
   - Subdomain: пусто, Domain: `akiyama-5rp.ru`
   - Service: **HTTP**, URL: `localhost:8080`
   - при желании второй хост: `www` → тот же `localhost:8080`
3. В Cloudflare **DNS** удалить старую A-запись `akiyama-5rp.ru → 92.124.130.182`
   (иначе будет конфликт с записью, которую создаст туннель) и включить
   оранжевое облако у созданного CNAME `…cfargotunnel.com`.
4. В `.env` на сервере:

   ```bash
   CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...
   ```

5. Запустить профиль `tunnel` вместе с ботом:

   ```bash
   docker compose --profile tunnel up -d
   docker compose logs -f tunnel      # ждём "Registered tunnel connection"
   ```

6. Проверить:

   ```bash
   curl -I https://akiyama-5rp.ru/api/health     # 200 OK
   ```

Caddy для этого домена больше не нужен: его блок из `Caddyfile` можно убрать
(`caddy reload`), а проброс портов 80/443 на роутере закрыть. Бот остаётся
опубликованным только на `127.0.0.1:8080`, туннель ходит к нему по
внутренней сети контейнера (`network_mode: service:bot`).

Что меняется на сервере: контейнер `akiyama-tunnel` (образ
`cloudflare/cloudflared`), профиль `tunnel` в `docker-compose.yml`, строка
`CLOUDFLARE_TUNNEL_TOKEN` в `.env`.

Плюсы: работает за CGNAT, не зависит от смены домашнего IP, DDoS-защита и
кэш Cloudflare, не нужно открывать порты. Минусы: сайт зависит от Cloudflare
и требует исходящего соединения с сервера (обычно оно есть).

Про обновления: контейнер туннеля делит сеть с ботом (`network_mode: service:bot`),
поэтому после `docker compose up -d --build` перезапускайте **вместе с профилем**,
иначе туннель останется в сети старого контейнера:

```bash
docker compose --profile tunnel up -d --build
```

## Свой Caddy (Apella.ru) — добавить сайт в него

Если Caddy, который обслуживает `apella.ru`, ваш и запущен контейнером (правится
без sudo) — второй Caddy не нужен. Добавляем блок для `akiyama-5rp.ru` в тот же
Caddy: он уже держит 80/443, у него уже есть ACME-аккаунт, оба домена
обслуживаются одним процессом на одних портах.

### 1. Найти, где лежит конфиг вашего Caddy

```bash
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i caddy
# NAME  IMAGE
# apella-caddy  caddy:2.8

docker inspect apella-caddy -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
# /home/user/apella/Caddyfile -> /etc/caddy/Caddyfile
# /home/user/apella/caddy_data -> /data

docker inspect apella-caddy -f 'network={{.HostConfig.NetworkMode}} ports={{.HostConfig.PortBindings}}'
# network=host   → reverse_proxy 127.0.0.1:8080
# network=bridge → нужна общая сеть с ботом, см. шаг 3
```

### 2. Добавить блок

Положите `deploy/caddy/akiyama.caddyfile` из репозитория рядом с Caddyfile
Apella и добавьте в конец Caddyfile одну строку:

```caddyfile
import /etc/caddy/akiyama.caddyfile
```

Либо просто скопируйте содержимое блока `akiyama-5rp.ru { … }` в Caddyfile
рядом с блоком Apella. Порт 80/443 у Caddyfile один на все домены — ничего
не конфликтует.

### 3. Прописать, куда проксировать (зависит от сети)

| Как запущен Caddy | `reverse_proxy` |
|---|---|
| `network_mode: host` | `127.0.0.1:8080` — бот опубликован как `127.0.0.1:8080` на хосте |
| bridge-сеть compose | `akiyama-bot:8080` — бот должен быть в **той же** сети |
| Caddy службой на хосте | `127.0.0.1:8080` |

Для bridge-сети: добавьте бота в сеть Apella (имя сети смотрите в
`docker network ls`, обычно `<папка-проекта>_default`):

```yaml
# docker-compose.yml бота
services:
  bot:
    networks: [apella]

networks:
  apella:
    external: true
    name: apella_default     # ← из docker network ls
```

`ports: 127.0.0.1:8080:8080` можно оставить — для локальных проверок.

### 4. Применить без простоя и без sudo

```bash
# проверка синтаксиса, затем hot-reload (старые соединения не рвутся)
docker exec apella-caddy caddy validate --config /etc/caddy/Caddyfile
docker exec apella-caddy caddy reload  --config /etc/caddy/Caddyfile

# либо, если reload недоступен:
docker compose -f ~/apella/docker-compose.yml restart caddy
```

В логе:

```bash
docker logs -f apella-caddy
```

```
"msg":"certificate obtained successfully","identifier":"akiyama-5rp.ru"
```

Проверка:

```bash
curl -I https://akiyama-5rp.ru/api/health      # HTTP/2 200
docker exec apella-caddy wget -qO- http://127.0.0.1:8080/api/health
```

### Что будет с 443

Сейчас на хосте 443 никто не слушает (`ss -lnt | grep :443` пусто), а снаружи
соединение принимает роутер и молча закрывает. Когда Caddy получит блок для
`akiyama-5rp.ru`, он начнёт слушать 443 — **после этого нужен проброс TCP 443
на роутере** (см. следующий раздел). Порт 80 уже проброшен: снаружи
`http://akiyama-5rp.ru` отдаёт `308`, значит HTTP-01 пройдёт без проблем.

Если Caddy в контейнере не публикует 443 — добавьте в его сервис:

```yaml
ports:
  - "80:80"
  - "443:443"
```

### Если порт 443 на роутере недоступен

Тогда вместо проброса можно спрятать сайт за Cloudflare (DNS домена уже там):
оранжевое облако у `akiyama-5rp.ru`, режим SSL/TLS **Full (strict)** или
**Flexible**, origin — тот же Caddy. Сертификат для origin можно взять
Cloudflare Origin CA (бесплатно, 15 лет) и подключить его в Caddy через
`tls /etc/caddy/origin.pem /etc/caddy/origin.key`. Это отдельный путь,
нужен только если 443 наружу не открывается.

## Проброс 443 на роутере

Это не про sudo, а про админку роутера (192.168.0.1 / 192.168.1.1 — адрес
шлюза вашей сети, логин/пароль обычно на наклейке). Нужно:

1. **Port forwarding / Virtual Server**: правило
   `TCP 443 → <LAN-IP хоста>:443`.
   LAN-IP хоста: `hostname -I | awk '{print $1}'`.
2. Если роутер сам сидит на 443 (веб-админка по HTTPS) — перевесить её на
   другой порт (например, 8443) в разделе Administration/System, иначе
   правило не заработает.
3. Правило для 80 уже есть: снаружи `http://akiyama-5rp.ru` отдаёт `308`,
   значит 80 до хоста доходит.

После правила проверьте с телефона по мобильному интернету (Wi-Fi выключить):
`https://akiyama-5rp.ru/api/health`. С домашнего Wi-Fi проверка не показательна
(hairpin NAT).

## Вариант B. Классика: белый IP + проброс 80/443 + Caddy

Годится, если у провайдера **публичный** IP и он не блокирует входящие 80/443.

1. **Сверка IP**: `curl -s https://api.ipify.org` на сервере должен совпадать
   с A-записью в Cloudflare. Если IP динамический — либо статический IP
   у провайдера, либо DDNS-скрипт, обновляющий A-запись через API Cloudflare.
2. **Роутер**: проброс **TCP 80 → 192.168.x.x:80** и **TCP 443 → 192.168.x.x:443**
   на хост с Caddy. Ничего другого пробрасывать не нужно (8080 наружу не
   публикуем).
3. **Файрвол хоста**: `sudo ufw allow 80,443/tcp` (или аналог).
4. **Caddyfile**: добавить блок для `akiyama-5rp.ru` из `Caddyfile` в
   репозитории к вашему существующему конфигу, затем:

   ```bash
   sudo caddy validate --config /etc/caddy/Caddyfile   # проверка синтаксиса
   sudo systemctl reload caddy
   sudo journalctl -u caddy -f                          # смотрим ACME
   ```

   В логе должно появиться `certificate obtained successfully` для
   `akiyama-5rp.ru`. Если там `challenge failed` / `connection refused` —
   порты всё ещё не доходят, возвращаемся к шагу 1.
5. **`www`**: либо добавьте в Cloudflare `CNAME www → akiyama-5rp.ru`
   (proxied) и раскомментируйте блок в `Caddyfile`, либо **не** указывайте
   `www.akiyama-5rp.ru` в адресах сайта. Сейчас записи нет, а имя в конфиге
   есть — Caddy будет бесконечно пытаться выпустить на него сертификат и
   сыпать ошибками в лог.

### Если провайдер режет порт 80

HTTP-01 не пройдёт, нужна проверка через DNS (DNS-01) — Caddy умеет это с
плагином `caddy-dns/cloudflare` (штатный образ плагин не содержит):

```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

Глобальный блок Caddyfile (он должен быть **один** и в начале файла):

```caddyfile
{
    email admin@akiyama-5rp.ru
}

akiyama-5rp.ru {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
    reverse_proxy 127.0.0.1:8080
}
```

API-токен Cloudflare: шаблон «Edit zone DNS» — права `Zone → DNS → Edit` и
`Zone → Zone → Read` на зону `akiyama-5rp.ru`, передавать через
`Environment=CLOUDFLARE_API_TOKEN=…` в systemd-юните Caddy.

## Вариант C. Сайт на VPS, бот дома

Если позже появится VPS — домен смотрит на VPS, там Caddy с обычным Let's
Encrypt, а на домашний бот он ходит по WireGuard/frp. Туннель Cloudflare —
это по сути тот же приём, только не нужно администрировать VPS.

## Чего делать НЕ надо

- **Не включайте «оранжевое облако» на текущей A-записи** в надежде на
  бесплатный HTTPS: Cloudflare тогда сам пойдёт на `92.124.130.182:443`,
  упрётся в ту же пустоту и отдаст `521`/`522`. Оранжевое облако помогает
  только если origin уже доступен *или* если используется туннель.
- **Не оставляйте в `Caddyfile` имена без DNS-записей** (`www`): каждый
  такой адрес — отдельная неудачная попытка ACME и ошибки в логе.
- **Не публикуйте 8080 в интернет** «чтобы проверить»: это FastAPI без TLS
  и без защиты от перебора; для проверки достаточно `curl` на самом сервере.

## Чек-лист «готово»

- [ ] `curl -I https://akiyama-5rp.ru/api/health` → `HTTP/2 200`
- [ ] `docker exec <caddy> caddy reload` прошёл без ошибок, в логе
      `certificate obtained successfully` для `akiyama-5rp.ru`
- [ ] В браузере зелёный замок, сертификат выдан Let's Encrypt (вариант B) или
      Google Trust Services / Cloudflare (вариант A)
- [ ] `https://akiyama-5rp.ru/staff` открывается, вход через Discord работает
      (`OAUTH_REDIRECT_URI=https://akiyama-5rp.ru/auth/callback` не менялся —
      в Discord Developer Portal должен быть прописан ровно этот адрес)
- [ ] `https://www.akiyama-5rp.ru` отвечает (или имя вообще не используется)
- [ ] `docker compose logs --tail=100 bot` без ошибок, `data/akiyama.db` на месте
