import json
import os
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth import sign_payload, verify_auth_headers
from app.db import get_db, init_db
from app.models import ConfigEntry
from app.schemas import (
    ConfigCreateRequest,
    ConfigCreateResponse,
    ConfigDeleteRequest,
    ConfigDetailResponse,
    ConfigListItem,
    ConfigListResponse,
    MessageResponse,
    SortField,
)
from pydantic import ValidationError

UPLOAD_LIMIT = int(os.getenv("SHINymoon_UPLOAD_LIMIT_PER_HOUR", "10"))
UPLOAD_WINDOW_SECONDS = 3600

app = FastAPI(title="Shinymoon Cloud Config API", version="1.0.0")

cors_origin = os.getenv("CORS_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cors_origin] if cors_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_upload_log: dict[str, deque[float]] = defaultdict(deque)


def _check_upload_rate(xuid: str) -> None:
    now = time.time()
    bucket = _upload_log[xuid]
    while bucket and now - bucket[0] > UPLOAD_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= UPLOAD_LIMIT:
        raise HTTPException(status_code=429, detail="upload rate limit exceeded")
    bucket.append(now)


def _entry_to_list_item(entry: ConfigEntry) -> ConfigListItem:
    return ConfigListItem(
        id=entry.id,
        name=entry.name,
        description=entry.description,
        author_username=entry.author_username,
        author_xuid=entry.author_xuid,
        script_build=entry.script_build,
        cfg_version=entry.cfg_version,
        downloads=entry.downloads,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/configs", response_model=ConfigListResponse)
def list_configs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: SortField = Query(default="created_at"),
    db: Session = Depends(get_db),
) -> ConfigListResponse:
    total = db.scalar(select(func.count()).select_from(ConfigEntry).where(ConfigEntry.visibility == "public")) or 0
    order = desc(ConfigEntry.created_at) if sort == "created_at" else desc(ConfigEntry.downloads)
    rows = (
        db.execute(
            select(ConfigEntry)
            .where(ConfigEntry.visibility == "public")
            .order_by(order)
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return ConfigListResponse(
        items=[_entry_to_list_item(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/v1/configs/{config_id}", response_model=ConfigDetailResponse)
def get_config(config_id: str, db: Session = Depends(get_db)) -> ConfigDetailResponse:
    entry = db.get(ConfigEntry, config_id)
    if not entry or entry.visibility != "public":
        raise HTTPException(status_code=404, detail="config not found")

    entry.downloads += 1
    db.commit()
    db.refresh(entry)

    try:
        snapshot = json.loads(entry.snapshot)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="stored snapshot is invalid") from exc

    base = _entry_to_list_item(entry)
    return ConfigDetailResponse(**base.model_dump(), snapshot=snapshot)


@app.post("/v1/configs", response_model=ConfigCreateResponse)
async def create_config(
    request: Request,
    db: Session = Depends(get_db),
    x_shinymoon_user: Optional[str] = Header(default=None, alias="X-Shinymoon-User"),
    x_shinymoon_xuid: Optional[str] = Header(default=None, alias="X-Shinymoon-Xuid"),
    x_shinymoon_timestamp: Optional[str] = Header(default=None, alias="X-Shinymoon-Timestamp"),
    x_shinymoon_signature: Optional[str] = Header(default=None, alias="X-Shinymoon-Signature"),
) -> ConfigCreateResponse:
    user, xuid = verify_auth_headers(
        x_shinymoon_user, x_shinymoon_xuid, x_shinymoon_timestamp, x_shinymoon_signature
    )

    raw_body = (await request.body()).decode("utf-8")
    try:
        body_data = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="request body must be JSON") from exc

    try:
        payload = ConfigCreateRequest.model_validate(body_data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    if payload.author_username != user or payload.author_xuid != xuid:
        raise HTTPException(status_code=403, detail="author identity mismatch")

    _check_upload_rate(xuid)

    snapshot_text = json.dumps(payload.snapshot, separators=(",", ":"), ensure_ascii=False)
    if len(snapshot_text) > 2_000_000:
        raise HTTPException(status_code=413, detail="snapshot too large")

    entry = ConfigEntry(
        name=payload.name.strip(),
        description=payload.description.strip(),
        author_username=user,
        author_xuid=xuid,
        script_build=payload.script_build,
        cfg_version=payload.cfg_version,
        snapshot=snapshot_text,
        visibility="public",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ConfigCreateResponse(id=entry.id, name=entry.name)


@app.post("/v1/configs/delete", response_model=MessageResponse)
async def delete_config(
    payload: ConfigDeleteRequest,
    db: Session = Depends(get_db),
    x_shinymoon_user: Optional[str] = Header(default=None, alias="X-Shinymoon-User"),
    x_shinymoon_xuid: Optional[str] = Header(default=None, alias="X-Shinymoon-Xuid"),
    x_shinymoon_timestamp: Optional[str] = Header(default=None, alias="X-Shinymoon-Timestamp"),
    x_shinymoon_signature: Optional[str] = Header(default=None, alias="X-Shinymoon-Signature"),
) -> MessageResponse:
    _, xuid = verify_auth_headers(
        x_shinymoon_user, x_shinymoon_xuid, x_shinymoon_timestamp, x_shinymoon_signature
    )

    entry = db.get(ConfigEntry, payload.id)
    if not entry:
        raise HTTPException(status_code=404, detail="config not found")
    if entry.author_xuid != xuid:
        raise HTTPException(status_code=403, detail="not the config owner")

    db.delete(entry)
    db.commit()
    return MessageResponse(ok=True, message="deleted")


@app.get("/v1/auth/sign-test")
def sign_test(
    user: str = Query(default="test"),
    xuid: str = Query(default="123"),
    timestamp: Optional[str] = Query(default=None),
) -> dict[str, str]:
    """Local dev helper to generate a valid signature."""
    ts = timestamp or str(int(time.time()))
    return {
        "timestamp": ts,
        "signature": sign_payload(ts, user, xuid),
    }
