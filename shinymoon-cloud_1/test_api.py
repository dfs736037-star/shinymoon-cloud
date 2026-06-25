"""Run after deploy: python test_api.py [base_url]"""
from __future__ import annotations

import sys
import time

from fastapi.testclient import TestClient

from app.auth import sign_payload
from app.main import app

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200, health.text
    assert health.json()["status"] == "ok"
    print("health ok")

    listing = client.get("/v1/configs")
    assert listing.status_code == 200, listing.text
    print("list ok", listing.json().get("total"))

    ts = str(int(time.time()))
    user, xuid = "testuser", "123"
    sig = sign_payload(ts, user, xuid)
    upload = client.post(
        "/v1/configs",
        json={
            "name": "ApiTest",
            "description": "automated",
            "author_username": user,
            "author_xuid": xuid,
            "script_build": "0.03b",
            "cfg_version": 1,
            "snapshot": {"version": 1, "pui": {"ok": True}},
        },
        headers={
            "X-Shinymoon-User": user,
            "X-Shinymoon-Xuid": xuid,
            "X-Shinymoon-Timestamp": ts,
            "X-Shinymoon-Signature": sig,
        },
    )
    assert upload.status_code == 200, upload.text
    cfg_id = upload.json()["id"]
    print("upload ok", cfg_id)

    detail = client.get(f"/v1/configs/{cfg_id}")
    assert detail.status_code == 200, detail.text
    print("detail ok")

    ts = str(int(time.time()))
    sig = sign_payload(ts, user, xuid)
    deleted = client.post(
        "/v1/configs/delete",
        json={"id": cfg_id},
        headers={
            "X-Shinymoon-User": user,
            "X-Shinymoon-Xuid": xuid,
            "X-Shinymoon-Timestamp": ts,
            "X-Shinymoon-Signature": sig,
        },
    )
    assert deleted.status_code == 200, deleted.text
    print("delete ok")
    print("all tests passed for", BASE)


if __name__ == "__main__":
    main()
