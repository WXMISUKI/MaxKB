# Preflight Platform Integration Hardening Specification

## ADDED Requirements

### Requirement: Worker API authentication

The preflight OCR worker SHALL protect business APIs with a server-side bearer credential.

#### Scenario: Health is requested

- **WHEN** a caller requests `GET /health`
- **THEN** the worker returns a safe readiness summary without requiring authentication
- **AND** the response reports whether worker API authentication is configured

#### Scenario: Business API is called without worker credential configuration

- **WHEN** `PREFLIGHT_API_KEY` is absent
- **THEN** business API calls fail with `503`
- **AND** health reports the worker as degraded

#### Scenario: Business API is called with an invalid credential

- **WHEN** the `Authorization` header is missing, malformed, or does not match `Bearer <PREFLIGHT_API_KEY>`
- **THEN** the worker returns `401`
- **AND** no provider operation or state mutation occurs

#### Scenario: Business API is called with a valid credential

- **WHEN** the caller supplies the configured bearer credential
- **THEN** the worker processes the request
- **AND** the credential is not persisted, logged, or returned

### Requirement: Idempotent ingestion registration

The preflight OCR worker SHALL make ingestion registration safe to retry.

#### Scenario: A new ingestion is registered

- **WHEN** the platform submits `POST /api/preflight/ocr-ingestions` with a new `Idempotency-Key`
- **THEN** the worker creates one ingestion record
- **AND** it stores the idempotency key and a stable request fingerprint
- **AND** it starts at most one OCR pipeline for that registration

#### Scenario: The same request is retried

- **WHEN** the platform repeats the same request with the same `Idempotency-Key`
- **THEN** the worker returns the existing ingestion record
- **AND** it does not create another record
- **AND** it does not start another OCR pipeline

#### Scenario: An idempotency key is reused for a different request

- **WHEN** the platform sends a different request body with an existing `Idempotency-Key`
- **THEN** the worker returns `409`
- **AND** the original ingestion record remains unchanged

### Requirement: Platform correlation propagation

The preflight OCR worker SHALL preserve platform audit correlation.

#### Scenario: Platform correlation is supplied

- **WHEN** the platform supplies `X-Correlation-ID`
- **THEN** the ingestion record and all subsequent status responses use that correlation id

#### Scenario: Platform correlation is absent

- **WHEN** `X-Correlation-ID` is not supplied
- **THEN** the worker generates a correlation id
- **AND** returns it in the ingestion record

### Requirement: Worker capability readiness

The preflight OCR worker SHALL expose bounded capability and provider readiness information.

#### Scenario: Health is ready

- **WHEN** worker authentication, PaddleOCR, and MaxKB are configured
- **THEN** health returns `ready=true`
- **AND** declares OCR, certificate post-processing, knowledge ingestion, retrieval checking, idempotency, and correlation capabilities

#### Scenario: A required integration is missing

- **WHEN** worker authentication, PaddleOCR, or MaxKB is not configured
- **THEN** health returns `ready=false` and `status=degraded`
- **AND** identifies only the missing configuration category
- **AND** does not expose credential values
