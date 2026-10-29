#!/usr/bin/env bash
# Диагностика доступности сайта (обычно akiyama-5rp.ru).
#
# Только читает и ничего не меняет: не правит DNS, не перезапускает Caddy,
# не трогает контейнеры. Запускать на самом сервере с сайтом, лучше с sudo —
# иначе не видно, какой процесс держит порт:
#
#   sudo bash tools/diagnose_site.sh
#   sudo bash tools/diagnose_site.sh akiyama-5rp.ru
#
# Зачем: при ошибке браузера «Сайт отправил недействительный ответ»
# (ERR_SSL_PROTOCOL_ERROR) нужно понять, где обрывается цепочка
# «DNS → проброс портов → TLS-терминатор → бот:8080». Разбор — docs/https.md.

set -uo pipefail

DOMAIN="${1:-akiyama-5rp.ru}"
LOCAL_PORT="${LOCAL_PORT:-8080}"

if [ -t 1 ]; then
    C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_BAD=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
    C_OK=''; C_WARN=''; C_BAD=''; C_DIM=''; C_OFF=''
fi

section() { printf '\n%s== %s ==%s\n' "$C_DIM" "$1" "$C_OFF"; }
ok()      { printf '%s[ OK ]%s %s\n'   "$C_OK"   "$C_OFF" "$1"; }
warn()    { printf '%s[WARN]%s %s\n'   "$C_WARN" "$C_OFF" "$1"; }
bad()     { printf '%s[FAIL]%s %s\n'   "$C_BAD"  "$C_OFF" "$1"; }
info()    { printf '       %s\n' "$1"; }
have()    { command -v "$1" >/dev/null 2>&1; }
is_root() { [ "$(id -u)" -eq 0 ]; }

TIPS=()
tip() { TIPS+=("$1"); }

http_code() { # http_code URL [доп. аргументы curl]
    local url="$1"; shift
    curl -s -o /dev/null -w '%{http_code}' --max-time 6 "$@" "$url" 2>/dev/null
}

printf 'Домен: %s   локальный порт сайта: %s   хост: %s   права: %s\n' \
    "$DOMAIN" "$LOCAL_PORT" "$(hostname 2>/dev/null || echo '?')" \
    "$(is_root && echo root || echo "uid $(id -u) (процессы портов не видны)")"

# --- 1. DNS -------------------------------------------------------------------
section "1. DNS"
IP_DNS=""
if have dig; then
    IP_DNS="$(dig +short A "$DOMAIN" 2>/dev/null | grep -E '^[0-9.]+$' | tr '\n' ' ')"
elif have host; then
    IP_DNS="$(host -t A "$DOMAIN" 2>/dev/null | awk '/has address/{print $4}' | tr '\n' ' ')"
elif have getent; then
    IP_DNS="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ')"
fi
IP_DNS="$(echo "$IP_DNS" | xargs 2>/dev/null)"

if [ -z "$IP_DNS" ]; then
    bad "A-запись для $DOMAIN не найдена — сайт не откроется ни по http, ни по https."
    tip "Добавьте A-запись домена на IP сервера (или CNAME на туннель Cloudflare)."
else
    ok "A: $IP_DNS"
fi

if have dig; then
    NS="$(dig +short NS "$DOMAIN" 2>/dev/null | tr '\n' ' ' | xargs)"
    [ -n "$NS" ] && info "NS: $NS"
    AAAA="$(dig +short AAAA "$DOMAIN" 2>/dev/null | tr '\n' ' ' | xargs)"
    [ -n "$AAAA" ] && info "AAAA: $AAAA (если IPv6 у сервера не настроен — уберите запись)"
    WWW="$(dig +short A "www.$DOMAIN" 2>/dev/null | xargs)"
    if [ -z "$WWW" ]; then
        info "www.$DOMAIN без A-записи — нормально, если это имя нигде не рекламируется"
        tip "Не указывайте www.$DOMAIN в Caddyfile без DNS-записи: Caddy будет вечно пытаться выпустить на него сертификат."
    fi
fi

# --- 2. Внешний IP против DNS --------------------------------------------------
section "2. Внешний IP сервера"
IP_PUBLIC=""
for url in https://api.ipify.org https://ifconfig.me/ip https://icanhazip.com; do
    IP_PUBLIC="$(curl -4 -s --max-time 6 "$url" 2>/dev/null | tr -d '[:space:]')"
    [ -n "$IP_PUBLIC" ] && break
done

if [ -z "$IP_PUBLIC" ]; then
    warn "не удалось узнать внешний IP (нет выхода в интернет или блокируются запросы)"
    tip "Проверьте исходящий интернет: curl -sI https://cloudflare.com"
else
    ok "внешний IP: $IP_PUBLIC"
    if [ -n "$IP_DNS" ]; then
        if echo " $IP_DNS " | grep -q " $IP_PUBLIC "; then
            ok "A-запись указывает на этот сервер"
        else
            bad "A-запись ($IP_DNS) не совпадает с внешним IP ($IP_PUBLIC)"
            tip "IP динамический или DNS указывает на старый адрес: обновите A-запись."
            tip "Либо уходите на Cloudflare Tunnel — тогда IP и порты не важны (docs/https.md, вариант A)."
        fi
    fi
    case "$IP_PUBLIC" in
        10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*|100.6[4-9].*|100.[7-9][0-9].*|100.1[01][0-9].*|100.12[0-7].*)
            bad "внешний адрес $IP_PUBLIC — приватный/CGNAT: проброс портов снаружи не заработает"
            tip "Нужен Cloudflare Tunnel (docs/https.md, вариант A) или статический IP у провайдера."
            ;;
    esac
fi

# --- 3. Кто слушает порты ------------------------------------------------------
section "3. Локальные слушатели 80 / 443"
if have ss || have netstat; then
    show_ports() {
        if have ss; then ss -lntp 2>/dev/null; else netstat -lntp 2>/dev/null; fi \
            | grep -E ':(80|443)\b' | sed 's/^/       /'
    }
    LISTENERS="$(show_ports)"
    [ -n "$LISTENERS" ] && printf '%s\n' "$LISTENERS"

    if have ss; then
        P80="$(ss -lnt 2>/dev/null | grep -cE ':80\b.*LISTEN')"
        P443="$(ss -lnt 2>/dev/null | grep -cE ':443\b.*LISTEN')"
    else
        P80="$(netstat -lnt 2>/dev/null | grep -cE ':80\b')"
        P443="$(netstat -lnt 2>/dev/null | grep -cE ':443\b')"
    fi

    if [ "${P80:-0}" -gt 0 ]; then
        ok "порт 80 слушает"
    else
        bad "порт 80 никто не слушает — HTTP тоже не работает, ACME по HTTP-01 невозможен"
        tip "Поднимите TLS-терминатор (Caddy) или уходите на Cloudflare Tunnel — docs/https.md."
    fi

    if [ "${P443:-0}" -gt 0 ]; then
        ok "порт 443 слушает"
    else
        bad "порт 443 НИКТО НЕ СЛУШАЕТ — это и есть «сайт отправил недействительный ответ»"
        info "TCP кто-то принимает (роутер), но TLS-рукопожатие некому вести:"
        info "сервер молча закрывает соединение, браузер получает 0 байт."
        tip "Поднимите HTTPS-сервер на 443: Caddy с блоком для $DOMAIN (docs/https.md, вариант B)."
        tip "Или не занимайте 443 вообще: Cloudflare Tunnel (docs/https.md, вариант A) — 10 минут, без проброса портов."
        if ! is_root; then
            tip "Запустите скрипт через sudo: без root не видно, какой процесс держит порты."
        fi
    fi
else
    warn "нет ss/netstat — пропускаю"
fi

# --- 4. Бот внутренне ---------------------------------------------------------
section "4. Бот (FastAPI) на 127.0.0.1:$LOCAL_PORT"
BODY="$(curl -s --max-time 6 "http://127.0.0.1:$LOCAL_PORT/api/health" 2>/dev/null)"
CODE="$(http_code "http://127.0.0.1:$LOCAL_PORT/api/health")"
if printf '%s' "$BODY" | grep -q '"ok"'; then
    ok "/api/health → 200, JSON: $(printf '%s' "$BODY" | head -c 120)"
else
    ONLINE="$(curl -s --max-time 6 "http://127.0.0.1:$LOCAL_PORT/api/online" 2>/dev/null | head -c 160)"
    if printf '%s' "$ONLINE" | grep -q '{'; then
        ok "/api/online отдаёт JSON — бот жив"
        warn "но /api/health вернул HTML/код $CODE — в контейнере старая сборка без этого эндпоинта"
        tip "Пересоберите: git pull && docker compose up -d --build"
    elif [ "$CODE" = "200" ]; then
        bad "порт $LOCAL_PORT отвечает, но отдаёт HTML вместо JSON API"
        info "похоже, SPA-фолбэк перехватывает /api/* — контейнер старой сборки"
        tip "Пересоберите: git pull && docker compose up -d --build"
    else
        bad "сайт внутри контейнера не отвечает (код $CODE)"
        tip "docker compose ps / docker compose logs --tail=80 bot — процесс бота жив?"
    fi
fi

# --- 5. Кто отвечает на :80 и куда ведёт редирект --------------------------------
section "5. Что отдаёт HTTP на порту 80"
HEADERS="$(curl -sI --max-time 6 "http://$DOMAIN/" 2>/dev/null | tr -d '\r')"
H_CODE="$(printf '%s' "$HEADERS" | awk 'NR==1{print $2}')"
H_LOC="$(printf '%s' "$HEADERS" | awk 'tolower($1)=="location:"{print $2}' | head -1)"
H_SRV="$(printf '%s' "$HEADERS" | awk 'tolower($1)=="server:"{print $2}' | head -1)"

[ -n "$H_CODE" ] && info "HTTP-код: $H_CODE"
[ -n "$H_SRV" ]  && info "Server: $H_SRV"
[ -n "$H_LOC" ]  && info "Location: $H_LOC"

case "$H_CODE" in
    000|"")
        bad "на http://$DOMAIN никто не отвечает"
        tip "Порт 80 не доходит до сервера или слушатель :80 не настроен на этот Host."
        ;;
    30[1278])
        if printf '%s' "$H_LOC" | grep -q '^https://'; then
            warn "HTTP редиректит на HTTPS ($H_LOC), а на 443 никто не слушает → браузер видит обрыв"
            tip "Это и есть весь симптом: сначала поднимаем HTTPS на 443, редирект остаётся как есть."
        else
            info "редирект на $H_LOC — проверьте, что это ожидаемое поведение"
        fi
        ;;
    200) ok "HTTP отвечает 200 — сайт доступен хотя бы по http" ;;
    *)   info "код $H_CODE" ;;
esac

if [ -z "$H_SRV" ] && [ -n "$H_CODE" ]; then
    info "заголовка Server нет — часто признак Cloudflare Tunnel или Caddy"
fi

# --- 6. Что за сервер 80/443: службы и бинарники --------------------------------
section "6. Службы, которые могут держать TLS"
if have systemctl; then
    for svc in caddy nginx apache2 httpd traefik haproxy; do
        STATE="$(systemctl is-active "$svc" 2>/dev/null)"
        case "$STATE" in
            active)
                ok "$svc: active"
                if [ "$svc" = "caddy" ] && have journalctl; then
                    ERR="$(journalctl -u caddy --no-pager -n 120 2>/dev/null \
                        | grep -iE 'listen|bind|permission|acme|challenge|certificate' | tail -n 6)"
                    [ -n "$ERR" ] && printf '%s\n' "$ERR" | sed 's/^/       /'
                fi
                ;;
            inactive|failed)
                info "$svc: $STATE"
                [ "$svc" = "caddy" ] && tip "Запустите и проверьте: sudo systemctl start caddy && sudo journalctl -u caddy -n 50 --no-pager"
                ;;
            *)
                ;;
        esac
    done
else
    warn "systemctl нет — службы не проверить"
fi

if have caddy; then
    info "caddy: $(caddy version 2>/dev/null | head -1)"
    for cfg in /etc/caddy/Caddyfile "$HOME/Caddyfile" ./Caddyfile; do
        [ -f "$cfg" ] || continue
        info "конфиг: $cfg"
        if grep -q "$DOMAIN" "$cfg" 2>/dev/null; then
            ok "в конфиге есть $DOMAIN"
        else
            bad "в $cfg НЕТ блока для $DOMAIN → Caddy не будет слушать 443 за этот домен"
            tip "Добавьте блок из Caddyfile репозитория и: sudo systemctl reload caddy"
        fi
        TEST="$(caddy validate --config "$cfg" --adapter caddyfile 2>&1 | tail -n 3)"
        [ -n "$TEST" ] && printf '%s\n' "$TEST" | sed 's/^/       /'
    done
else
    info "бинарника caddy в PATH нет — возможно, не установлен"
fi

# --- 7. Хранилище сертификатов и лог ACME --------------------------------------
section "7. Сертификаты и попытки ACME"
STORAGE_FOUND=""
for path in \
    /var/lib/caddy/.local/share/caddy \
    /root/.local/share/caddy \
    "$HOME/.local/share/caddy" \
    /data/caddy; do
    if [ -d "$path/certificates" ]; then
        STORAGE_FOUND="$path"
        break
    fi
done
if [ -n "$STORAGE_FOUND" ]; then
    info "хранилище: $STORAGE_FOUND"
    find "$STORAGE_FOUND/certificates" -maxdepth 4 -name '*.crt' 2>/dev/null | sed 's/^/       /'
    if ! find "$STORAGE_FOUND/certificates" -maxdepth 4 -name "*$DOMAIN*" 2>/dev/null | grep -q .; then
        bad "для $DOMAIN сертификата нет — ACME ни разу не прошёл"
    fi
else
    info "папка сертификатов не найдена (нет прав или Caddy не используется)"
    ! is_root && info "запустите с sudo, чтобы увидеть /var/lib/caddy"
fi

if have journalctl && have systemctl && systemctl is-active --quiet caddy 2>/dev/null; then
    LOG="$(journalctl -u caddy --no-pager -n 200 2>/dev/null \
        | grep -iE 'acme|challenge|certificate|obtain|error' | tail -n 10)"
    if [ -n "$LOG" ]; then
        printf '%s\n' "$LOG" | sed 's/^/       /'
        if echo "$LOG" | grep -qiE 'challenge failed|connection refused|unauthorized'; then
            bad "ACME-проверка не проходит → снаружи до Caddy не доходят 80/443"
            tip "Проверьте проброс 80/443 на роутере и файрвол хоста; либо DNS-01 / Cloudflare Tunnel."
        fi
    fi
fi

# --- 8. Docker -----------------------------------------------------------------
section "8. Контейнеры"
if have docker; then
    docker compose ps 2>/dev/null | sed 's/^/       /' || warn "docker compose ps не выполнился"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qi cloudflared; then
        ok "туннель cloudflared запущен"
    fi
else
    warn "docker не найден — бот запущен иначе?"
fi

# --- 9. Что видно снаружи -------------------------------------------------------
section "9. Проверка снаружи (со стороны сервера)"
CODE_HTTP="$(http_code "http://$DOMAIN/")"
CODE_TLS="$(http_code "https://$DOMAIN/")"
info "http://$DOMAIN   → $CODE_HTTP"
info "https://$DOMAIN  → $CODE_TLS"
info "000 — ответа нет; с домашнего роутера запрос может не выходить наружу"
info "и не возвращаться (hairpin NAT), надёжнее проверить с телефона по мобильному интернету."

# --- Итог ----------------------------------------------------------------------
section "Итог"
if [ ${#TIPS[@]} -eq 0 ]; then
    ok "явных проблем не найдено — смотрите лог Caddy и проверьте снаружи (мобильный интернет)"
else
    printf 'Что делать:\n'
    printf '%s\n' "${TIPS[@]}" | awk '!seen[$0]++' | sed 's/^/  • /'
    printf '\nПолный разбор вариантов — docs/https.md\n'
fi
