"""HMAC-подписанные cookies сессии (без сторонних зависимостей).

Формат cookie: base64url(payload_json) + "." + hmac_sha256_hex(payload).
payload — JSON: {"uid": int, "name": str, "is_staff": bool, "expires": float}.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

SESSION_COOKIE = "akiyama_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def create_session(
    *, uid: int, name: str, is_staff: bool, secret: str, ttl: int = SESSION_TTL_SECONDS
) -> str:
    payload = json.dumps(
        {"uid": uid, "name": name, "is_staff": is_staff, "expires": time.time() + ttl},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{body}.{_sign(payload, secret)}"


def read_session(cookie: str | None, secret: str) -> dict | None:
    """Восстановить сессию из cookie. None — если подпись/истечение/формат плохие."""
    if not cookie or "." not in cookie:
        return None
    body, _, signature = cookie.rpartition(".")
    payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("expires", 0) < time.time():
        return None
    return data
