import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status

from .config import (
    BOT_TOKEN,
    INTERNAL_API_KEY,
    WEB_SESSION_COOKIE,
    WEB_SESSION_SECRET,
    WEB_SESSION_SECURE,
    WEB_SESSION_TTL_SECONDS,
)


def _encode_session(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    encoded_body = base64.urlsafe_b64encode(body).decode().rstrip("=")
    signature = hmac.new(
        WEB_SESSION_SECRET.encode(),
        encoded_body.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"{encoded_body}.{signature}"


def _decode_session(token: str) -> dict[str, Any]:
    try:
        encoded_body, signature = token.split(".", 1)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.") from error

    expected_signature = hmac.new(
        WEB_SESSION_SECRET.encode(),
        encoded_body.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session signature.")

    padded_body = encoded_body + "=" * (-len(encoded_body) % 4)

    try:
        payload = json.loads(base64.urlsafe_b64decode(padded_body).decode())
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed session.") from error

    if int(payload.get("exp", 0)) <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

    return payload


def set_authenticated_session(response: Response, telegram_user: dict[str, Any]) -> None:
    issued_at = int(time.time())
    payload = {
        "user_id": int(telegram_user["id"]),
        "first_name": telegram_user.get("first_name"),
        "username": telegram_user.get("username"),
        "photo_url": telegram_user.get("photo_url"),
        "iat": issued_at,
        "exp": issued_at + WEB_SESSION_TTL_SECONDS,
    }

    response.set_cookie(
        key=WEB_SESSION_COOKIE,
        value=_encode_session(payload),
        max_age=WEB_SESSION_TTL_SECONDS,
        httponly=True,
        secure=WEB_SESSION_SECURE,
        samesite="lax",
    )


def clear_authenticated_session(response: Response) -> None:
    response.delete_cookie(key=WEB_SESSION_COOKIE, httponly=True, samesite="lax")


def require_authenticated_user_id(request: Request) -> int:
    token = request.cookies.get(WEB_SESSION_COOKIE)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    payload = _decode_session(token)
    return int(payload["user_id"])


def require_internal_api_key(request: Request) -> None:
    if not INTERNAL_API_KEY:
        return

    provided_key = request.headers.get("x-internal-api-key", "")
    if not provided_key or not hmac.compare_digest(provided_key, INTERNAL_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal API key required.")


def verify_telegram_login(payload: dict[str, Any]) -> dict[str, Any]:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required on the backend to verify Telegram login.")

    received_hash = payload.get("hash")
    auth_date = payload.get("auth_date")
    telegram_id = payload.get("id")

    if not received_hash or not auth_date or not telegram_id:
        raise ValueError("Missing Telegram login fields.")

    fields = {}
    for key, value in payload.items():
        if key == "hash" or value in (None, ""):
            continue
        fields[key] = str(value)

    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), digestmod=hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, str(received_hash)):
        raise ValueError("Telegram auth hash mismatch.")

    if int(time.time()) - int(auth_date) > 86400:
        raise ValueError("Telegram auth payload is too old.")

    return {
        "id": int(telegram_id),
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "username": payload.get("username"),
        "photo_url": payload.get("photo_url"),
        "auth_date": int(auth_date),
    }
