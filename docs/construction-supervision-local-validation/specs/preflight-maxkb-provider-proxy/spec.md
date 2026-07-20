# Preflight MaxKB Provider Proxy Specification

## ADDED Requirements

### Requirement: Worker exposes a server-side MaxKB provider proxy

The preflight OCR Worker SHALL expose a small MaxKB provider proxy for the preflight platform when MaxKB itself only has administrator username/password authentication.

#### Scenario: Preflight platform checks provider health

- **WHEN** the platform calls `GET /api/health` or `GET /api/knowledge-base/provider/status` on the Worker proxy
- **THEN** the Worker returns a bounded readiness summary for authentication, PaddleOCR, and MaxKB
- **AND** the response does not expose MaxKB username, password, bearer token, PaddleOCR token, or internal provider traces

#### Scenario: Preflight platform searches MaxKB through Worker

- **WHEN** the platform calls `POST /api/knowledge/{knowledgeId}/search` with `Authorization: Bearer <PREFLIGHT_API_KEY>`
- **THEN** the Worker logs in to MaxKB using server-side `MAXKB_USERNAME` and `MAXKB_PASSWORD`
- **AND** executes MaxKB hit-test against the requested knowledge base
- **AND** returns only safe hit metadata, title, locator, score, and bounded snippets

#### Scenario: Provider proxy is called without valid token

- **WHEN** the platform omits or sends an invalid bearer credential
- **THEN** the Worker returns `401`
- **AND** no MaxKB login, retrieval, or state mutation occurs

### Requirement: LAN integration configuration

The preflight platform SHALL point MaxKB provider configuration at the Worker proxy during local LAN integration.

#### Scenario: Preflight platform runs on another LAN host

- **WHEN** the MaxKB/OCR Worker host IP is `192.168.0.235` and the preflight platform host IP is `192.168.0.219`
- **THEN** the preflight platform uses `MAXKB_BASE_URL=http://192.168.0.235:<worker-port>`
- **AND** uses `MAXKB_API_KEY=<PREFLIGHT_API_KEY>`
- **AND** does not use `127.0.0.1` unless the platform process runs on the same machine as the Worker

#### Scenario: MaxKB admin password rotates

- **WHEN** the MaxKB administrator password changes
- **THEN** only the Worker-side `MAXKB_PASSWORD` configuration is updated
- **AND** the preflight platform continues using the same Worker proxy bearer credential until that credential is intentionally rotated
