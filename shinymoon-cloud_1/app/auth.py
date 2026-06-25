import hashlib
import os
import time
from typing import Optional

from fastapi import Header, HTTPException

API_SECRET = os.getenv("SHINymoon_API_SECRET", "shinymoon-dev-secret-change-me")
MAX_SKEW_SECONDS = int(os.getenv("SHINymoon_AUTH_MAX_SKEW", "300"))


def sign_payload(timestamp: str, user: str, xuid: str) -> str:
    """MD5(secret + timestamp + user + xuid) — matches neverlose/md5 client."""
    message = f"{timestamp}{user}{xuid}"
    return hashlib.md5(f"{API_SECRET}{message}".encode("utf-8")).hexdigest()


def verify_auth_headers(
    user: Optional[str],
    xuid: Optional[str],
    timestamp: Optional[str],
    signature: Optional[str],
) -> tuple[str, str]:
    if not user or not xuid or not timestamp or not signature:
        raise HTTPException(status_code=401, detail="missing auth headers")

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid timestamp") from exc

    now = int(time.time())
    if abs(now - ts) > MAX_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="timestamp expired")

    expected = sign_payload(timestamp, user, xuid)
    if expected.lower() != signature.lower():
        raise HTTPException(status_code=401, detail="invalid signature")

    return user, xuid


def auth_dependency(
    x_shinymoon_user: Optional[str] = Header(default=None, alias="X-Shinymoon-User"),
    x_shinymoon_xuid: Optional[str] = Header(default=None, alias="X-Shinymoon-Xuid"),
    x_shinymoon_timestamp: Optional[str] = Header(default=None, alias="X-Shinymoon-Timestamp"),
    x_shinymoon_signature: Optional[str] = Header(default=None, alias="X-Shinymoon-Signature"),
) -> tuple[str, str]:
    return verify_auth_headers(
        x_shinymoon_user, x_shinymoon_xuid, x_shinymoon_timestamp, x_shinymoon_signature
    )
