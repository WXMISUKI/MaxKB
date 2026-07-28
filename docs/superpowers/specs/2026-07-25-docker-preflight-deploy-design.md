# Docker Preflight Deploy Design

Date: 2026-07-25

## Goal

On this Windows host, run MaxKB and the independent OCR Worker in Docker so other projects can call them over LAN.

## Confirmed facts

- `quickstart.md` deploys MaxKB via official image `registry.fit2cloud.com/maxkb/maxkb` on host port `8080` with volume `C:/maxkb:/opt/maxkb`.
- Port `8091` is the standalone FastAPI service `services/preflight-ocr-worker`, not MaxKB itself.
- Repo had no Worker Dockerfile or compose stack for this local preflight path.
- Docker Desktop is available; this host previously had no MaxKB/Worker containers or images.

## Decisions

1. MaxKB: official image only (no local MaxKB source build for this deploy).
2. OCR Worker: containerized with a new Dockerfile and compose service.
3. Topology: `docker-compose.preflight.yml` dual service stack.
4. Ports: MaxKB `8080`, Worker `0.0.0.0:8091`.
5. Secrets: host file `.env.docker.local` (gitignored); template `.env.docker.local.example` committed.
6. Source docs mount: `C:/maxkb-data/sources` -> `/data/sources:ro`.
7. Worker talks to MaxKB over compose network: `http://maxkb:8080/admin/api`.

## Topology

```text
Caller (same host or LAN)
  -> http://<host-ip>:8091  (preflight-ocr-worker proxy/API)
       -> http://maxkb:8080/admin/api  (compose DNS)
Caller browser/admin
  -> http://localhost:8080  (MaxKB UI)
```

## Files

| Path | Purpose |
| --- | --- |
| `docker-compose.preflight.yml` | MaxKB + Worker stack |
| `services/preflight-ocr-worker/Dockerfile` | Worker image |
| `.env.docker.local.example` | Secret placeholders |
| `.env.docker.local` | Local secrets, not committed |
| `.gitignore` | Ignore `.env.docker.local` |
| `quickstart.md` | Add compose start path |

## Worker image constraints

Worker reuses scripts under `docs/construction-supervision-local-validation/scripts` via `PREFLIGHT_PROJECT_ROOT`. Image must include:

- `services/preflight-ocr-worker`
- `docs/construction-supervision-local-validation/scripts`
- writable OCR artifact tree under `docs/simulated-pilot-dataset/...` (volume-mounted)

## Success criteria

- `docker compose -f docker-compose.preflight.yml ps` shows both services running.
- `http://localhost:8080` serves MaxKB.
- `http://127.0.0.1:8091/api/health` responds; with secrets configured, status is `ready` or clearly `degraded`.
- Secrets stay out of git.

## Non-goals

- No production multi-instance queue/DB rewrite.
- No MaxKB source image rebuild.
- No change to Worker public API contract.
