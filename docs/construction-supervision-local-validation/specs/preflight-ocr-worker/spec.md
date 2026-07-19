# Preflight OCR Worker Specification

## ADDED Requirements

### Requirement: Standalone worker boundary

The preflight OCR worker SHALL run as a standalone FastAPI service without modifying the MaxKB Django runtime.

#### Scenario: Worker starts independently

- **WHEN** the worker is started
- **THEN** it exposes its own HTTP port and health endpoint
- **AND** it can call PaddleOCR-VL and MaxKB through provider adapters
- **AND** MaxKB can be upgraded or redeployed without embedding worker-specific business code

### Requirement: Safe provider configuration

The worker SHALL read provider credentials and deployment settings from environment variables.

#### Scenario: Secrets are configured

- **WHEN** PaddleOCR or MaxKB credentials are supplied
- **THEN** the worker reads them from environment variables
- **AND** tokens, passwords, authorization headers, and provider result URLs are not persisted in state files or API responses

#### Scenario: Provider is not configured

- **WHEN** a required provider credential is missing
- **THEN** health reports the provider as not configured
- **AND** provider operations fail with a safe error summary

### Requirement: Source access control

The worker SHALL restrict local source files to configured allowed roots.

#### Scenario: Local source is allowed

- **WHEN** a local source path resolves under an allowed root
- **THEN** the worker accepts the source for OCR processing

#### Scenario: Local source escapes allowed roots

- **WHEN** a local source path resolves outside every allowed root
- **THEN** the worker rejects the request before reading or uploading the file

### Requirement: OCR ingestion state machine

The worker SHALL persist an ingestion record and expose safe status transitions.

#### Scenario: OCR ingestion is created

- **WHEN** the platform submits source and evidence metadata
- **THEN** the worker creates an ingestion id and correlation id
- **AND** the initial state is `registered` or `ocr_pending`

#### Scenario: OCR processing succeeds

- **WHEN** PaddleOCR completes and post-processing succeeds
- **THEN** the worker transitions through `ocr_pending`, `ocr_running`, `ocr_done`, `postprocessed`, and `ready_for_ingest`
- **AND** it persists artifact paths and safe provider refs

#### Scenario: Processing fails

- **WHEN** OCR, post-processing, MaxKB ingestion, or retrieval checking fails
- **THEN** the state becomes `failed`
- **AND** the persisted error contains only type, summary, and safe diagnostics

### Requirement: Certificate post-processing

The worker SHALL reuse the local certificate post-processing capability.

#### Scenario: Supported certificate is processed

- **WHEN** OCR markdown contains a business license, safety production license, or personnel certificate
- **THEN** the worker generates cleaned Markdown, structured JSON/CSV, ingestion Markdown, and a report
- **AND** evidence metadata is included in the structured artifacts

### Requirement: MaxKB provider ingestion

The worker SHALL upload only the certificate-specific ingestion Markdown as the preferred searchable document.

#### Scenario: Operator confirms ingestion

- **WHEN** the ingestion is `ready_for_ingest`
- **THEN** the worker uploads `*-ingest.md` to the configured MaxKB knowledge base
- **AND** it stores provider document refs without treating MaxKB as the platform source of truth

### Requirement: Retrieval smoke test

The worker SHALL support focused retrieval validation after MaxKB ingestion.

#### Scenario: Exact certificate fields are checked

- **WHEN** the platform submits exact-field queries
- **THEN** the worker calls MaxKB hit-test
- **AND** it reports expected document rank, similarity, top document, and pass/fail classification
- **AND** `keywords` is the default search mode for certificate identifiers

### Requirement: Prototype persistence

The first worker prototype SHALL use an atomic local JSON state store while preserving a replaceable repository boundary.

#### Scenario: State is written

- **WHEN** an ingestion record changes
- **THEN** the worker writes state atomically
- **AND** concurrent access is guarded within the process

#### Scenario: Production persistence is introduced

- **WHEN** the worker moves beyond single-instance deployment
- **THEN** the JSON repository can be replaced by PostgreSQL/Redis-backed persistence without changing API schemas

