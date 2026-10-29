#!/usr/bin/env bash
# Диагностика доступности сайта (обычно akiyama-5rp.ru).
#
# Только читает и ничего не меняет: не правит DNS, не перезапускает Caddy,
# не трогает контейнеры. Запускать на самом сервере с сайтом.
#
#   bash tools/diagnose_site.sh                # домен по умолчанию
#   bash tools/diagnose_site.sh akiyama-5rp.ru
#
# Зачем: при ошибке браузера «Сайт отправил недействительный ответ»
# (ERR_SSL_PROTOCOL_ERROR) нужно понять, где обрывается цепочка
# «DNS → проброс портов → Caddy → бот:8080». Подробности — docs/https.md.

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

TIPS=()
tip() { TIPS+=("$1"); }

http_code() { # http_code URL [доп. аргументы curl]
    local url="$1"; shift
    curl -s -o /dev/null -w '%{http_code}' --max-time 6 "$@" "$url" 2>/dev/null
}

printf 'Домен: %s   локальный порт сайта: %s   хост: %s\n' \
    "$DOMAIN" "$LOCAL_PORT" "$(hostname 2>/dev/null || echo '?')"

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
        warn "у www.$DOMAIN нет A-записи — не указывайте это имя в Caddyfile"
        tip "Либо создайте CNAME www → $DOMAIN, либо уберите www из адресов сайта в Caddy."
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
section "3. Локальные слушатели"
if have ss; then
    LISTENERS="$(ss -lntp 2>/dev/null | grep -E ':((80|443|8080))\b' || true)"
elif have netstat; then
    LISTENERS="$(netstat -lntp 2>/dev/null | grep -E ':((80|443|8080))\b' || true)"
else
    LISTENERS=""
    warn "нет ss/netstat — пропускаю"
fi
if [ -n "$LISTENERS" ]; then
    printf '%s\n' "$LISTENERS" | sed 's/^/       /'
else
    bad "на 80/443/8080 ничего не слушает"
    tip "Caddy не запущен (systemctl status caddy) или контейнер бота упал (docker compose ps)."
fi

# --- 4. Бот внутренне ---------------------------------------------------------
section "4. Бот (FastAPI) на 127.0.0.1:$LOCAL_PORT"
CODE="$(http_code "http://127.0.0.1:$LOCAL_PORT/api/health")"
if [ "$CODE" = "200" ]; then
    ok "/api/health → 200"
    info "$(curl -s --max-time 6 "http://127.0.0.1:$LOCAL_PORT/api/health" 2>/dev/null | head -c 200)"
else
    CODE_ALT="$(http_code "http://127.0.0.1:$LOCAL_PORT/api/online")"
    if [ "$CODE_ALT" = "200" ]; then
        ok "/api/online → 200 (эндпоинта /api/health ещё нет в этой версии)"
    else
        bad "сайт внутри контейнера не отвечает (health=$CODE, online=$CODE_ALT)"
        tip "docker compose ps / docker compose logs --tail=80 bot — процесс бота жив?"
    fi
fi

# --- 5. Caddy на localhost -----------------------------------------------------
section "5. Caddy как TLS-терминатор"
if have curl; then
    CODE_TLS="$(http_code "https://$DOMAIN/" --resolve "$DOMAIN:443:127.0.0.1" -k)"
    if [ "$CODE_TLS" = "200" ]; then
        ok "Caddy локально отдаёт HTTPS (200)"
    elif [ "$CODE_TLS" = "000" ]; then
        bad "локально по https://127.0.0.1:443 c SNI $DOMAIN никто не отвечает"
        tip "Caddy не запущен или не слушает 443: systemctl status caddy; ss -lntp | grep :443"
    else
        warn "Caddy ответил кодом $CODE_TLS (ожидался 200)"
    fi
fi

if have openssl; then
    CERT="$(echo | timeout 8 openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" 2>/dev/null \
        | openssl x509 -noout -subject -issuer -dates 2>/dev/null)"
    if [ -n "$CERT" ]; then
        printf '%s\n' "$CERT" | sed 's/^/       /'
        if echo "$CERT" | grep -qi "issuer.*\(Let's Encrypt\|R11\|R10\|E5\|E6\|Cloudflare\|Google Trust\)"; then
            ok "сертификат публичного УЦ выдан"
        else
            warn "сертификат не от публичного УЦ (самоподписанный/внутренний CA) — браузер ругнётся"
        fi
    else
        bad "сертификат не предъявляется — это и есть «сайт отправил недействительный ответ»"
    fi
fi

# --- 6. Хранилище сертификатов и лог ACME --------------------------------------
section "6. Сертификаты Caddy и попытки ACME"
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
fi

if have journalctl; then
    LOG="$(journalctl -u caddy --no-pager -n 200 2>/dev/null \
        | grep -iE 'acme|challenge|certificate|obtain|error' | tail -n 12)"
    if [ -n "$LOG" ]; then
        info "последние строки про сертификаты:"
        printf '%s\n' "$LOG" | sed 's/^/       /'
        if echo "$LOG" | grep -qiE 'challenge failed|connection refused|timeout|unauthorized'; then
            bad "ACME-проверка не проходит → снаружи до Caddy не доходят 80/443"
            tip "Проверьте проброс 80/443 на роутере и файрвол хоста; либо DNS-01 / Cloudflare Tunnel."
        fi
    else
        info "в логе caddy нет строк про ACME (или лог недоступен без sudo)"
    fi
fi

# --- 7. Docker -----------------------------------------------------------------
section "7. Контейнеры"
if have docker; then
    docker compose ps 2>/dev/null | sed 's/^/       /' || warn "docker compose ps не выполнился"
else
    warn "docker не найден — бот запущен иначе?"
fi

# --- 8. Что видно снаружи -------------------------------------------------------
section "8. Проверка снаружи (со стороны сервера)"
CODE_HTTP="$(http_code "http://$DOMAIN/")"
OUT_TLS="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "https://$DOMAIN/" 2>/dev/null)"
info "http://$DOMAIN            → $CODE_HTTP"
info "https://$DOMAIN           → $OUT_TLS"
info "000 — ответа нет, 200 — сайт ответил."
info "С домашнего роутера запрос может не выходить наружу и не возвращаться"
info "(hairpin NAT), поэтому надёжнее проверить с телефона по мобильному интернету."

# --- Итог ----------------------------------------------------------------------
section "Итог"
if [ ${#TIPS[@]} -eq 0 ]; then
    ok "явных проблем не найдено — смотрите лог Caddy и проверьте снаружи (мобильный интернет)"
else
    printf 'Что делать:\n'
    printf '%s\n' "${TIPS[@]}" | awk '!seen[$0]++' | sed 's/^/  • /'
    printf '\nПолный разбор вариантов — docs/https.md\n'
fi
