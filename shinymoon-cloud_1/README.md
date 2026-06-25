# Shinymoon Cloud Config API

Public REST backend for the shinymoon Neverlose script cloud config library.

**Neverlose cannot call `localhost` or plain HTTP.** Deploy this API to Railway (HTTPS) and point `CLOUD_API_HOST` in `shinymoon_alpha.lua` to your public URL.

## Requirements

- Python 3.11+
- pip

## Setup (local dev only)

Use a tunnel (Cloudflare Tunnel / ngrok) to test from Neverlose — not `127.0.0.1`.

```bash
cd shinymoon-cloud
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Copy `.env.example` to `.env` for local runs.

## Deploy on Railway (production)

### 1. Create project

1. Open [railway.app](https://railway.app) and sign in.
2. **New Project → Deploy from GitHub repo** (recommended) or **Empty Project → deploy `shinymoon-cloud` folder**.
3. If the repo root is the parent folder, set **Root Directory** to `shinymoon-cloud`.

Railway reads [`Procfile`](Procfile) and [`railway.toml`](railway.toml) automatically.

### 2. Environment variables

In Railway → your service → **Variables**:

| Variable | Value |
|----------|--------|
| `SHINymoon_API_SECRET` | Strong random string (same value in `shinymoon_alpha.lua` as `CLOUD_API_SECRET`) |
| `DATABASE_URL` | `sqlite:////data/shinymoon_cloud.db` |
| `CORS_ORIGIN` | `*` |
| `SHINymoon_UPLOAD_LIMIT_PER_HOUR` | `10` (optional) |

Example secret (generate your own for production):

```text
sk_shinymoon_7k2m9p4x1q8w5e3r6t0y
```

### 3. Persistent volume

Railway → service → **Volumes** → Add volume:

- **Mount path:** `/data`
- **Size:** 1 GB

Without this, SQLite resets on redeploy.

### 4. Public domain

Railway → service → **Settings → Networking → Generate Domain**.

You get a URL like:

```text
https://shinymoon-cloud-production-a1b2.up.railway.app
```

### 5. Verify deployment

In a browser or curl:

```text
GET https://<your-domain>/health
→ {"status":"ok"}

GET https://<your-domain>/v1/configs
→ {"items":[],"total":0,"limit":50,"offset":0}
```

### 6. Update Neverlose script

In `shinymoon_alpha.lua` (~line 1639):

```lua
local CLOUD_API_HOST = "https://<your-domain>.up.railway.app"
local CLOUD_API_SECRET = "<same SHINymoon_API_SECRET>"
```

Reload the script in Neverlose → **Home → Cloud → Refresh**.

## API (v1)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/v1/configs` | No | List public configs (`limit`, `offset`, `sort=created_at\|downloads`) |
| GET | `/v1/configs/{id}` | No | Fetch config detail + snapshot (increments downloads) |
| POST | `/v1/configs` | Signed | Upload a new public config |
| POST | `/v1/configs/delete` | Signed | Delete own config (`{"id":"..."}`) |

### Auth headers (upload / delete)

```text
X-Shinymoon-User: <neverlose username>
X-Shinymoon-Xuid: <steam xuid or nl: hash fallback>
X-Shinymoon-Timestamp: <unix seconds>
X-Shinymoon-Signature: md5(secret + timestamp + user + xuid)
```

Dev signature helper:

```text
GET /v1/auth/sign-test?user=test&xuid=123
```

## Local dev with Neverlose (tunnel)

Neverlose blocks `127.0.0.1`. To test locally:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
cloudflared tunnel --url http://localhost:8080
```

Use the `https://*.trycloudflare.com` URL as `CLOUD_API_HOST` in the Lua script (temporary).

## Notes

- Snapshots must include `version` and non-empty `pui` (same format as local `CFG.export_snapshot()`).
- Upload rate limit defaults to 10 per hour per xuid.
- Delete uses POST because Neverlose `network` only exposes `get` and `post`.
