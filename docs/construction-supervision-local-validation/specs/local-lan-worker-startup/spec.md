# Local LAN Worker Startup Specification

## ADDED Requirements

### Requirement: Quickstart does not persist secrets

The local LAN quickstart SHALL explain how to start MaxKB and OCR Worker without committing real provider credentials.

#### Scenario: Startup commands are documented

- **WHEN** `quickstart.md` documents `PREFLIGHT_API_KEY`, `PADDLEOCR_TOKEN`, or MaxKB credentials
- **THEN** it uses placeholders for real secrets
- **AND** it explains that values are set in the current PowerShell session

#### Scenario: A worker API key is generated

- **WHEN** a Worker bearer key is needed for LAN integration
- **THEN** the key is generated outside repository files
- **AND** the preflight platform uses that key as `MAXKB_API_KEY`

### Requirement: LAN startup exposes Worker proxy

The OCR Worker SHALL be started in a way that the preflight platform host can reach it over the LAN.

#### Scenario: The preflight platform runs on another computer

- **WHEN** the Worker host is `192.168.0.219` and the preflight platform host is `192.168.0.219`
- **THEN** Worker startup uses `--host 0.0.0.0` or an equivalent LAN-bind address
- **AND** the preflight platform uses `MAXKB_BASE_URL=http://192.168.0.219:8091`
- **AND** `127.0.0.1` is used only for same-machine checks

#### Scenario: Windows blocks the port

- **WHEN** `192.168.0.219` cannot reach `http://192.168.0.219:8091/api/health`
- **THEN** the operator checks Windows firewall and allows inbound TCP `8091`
