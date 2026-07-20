# Preflight Platform Alignment Specification

## ADDED Requirements

### Requirement: Platform remains the source of truth

The preflight platform SHALL own construction review business facts, task state, reviewer decisions, report assets, and audit records.

#### Scenario: A project review context is created

- **WHEN** a project, contract package, section, subcontract team, workspace, basis version, master-data record, review task, evidence record, human decision, or report asset is created
- **THEN** it is persisted by the preflight platform in its platform-owned storage
- **AND** MaxKB, OCR Worker, Dify, RAGFlow, LLM providers, or vector indexes are not treated as the authoritative source for those records

#### Scenario: Provider output conflicts with platform facts

- **WHEN** OCR, MaxKB retrieval, RAGFlow retrieval, Dify workflow output, or LLM output conflicts with published basis, approved master data, evidence records, or human decisions
- **THEN** the platform facts remain authoritative
- **AND** the conflict is preserved as a review note or human-review item
- **AND** no provider output automatically overwrites a formal review conclusion

### Requirement: Node BFF owns frontend-facing integration

The preflight platform SHALL keep the Node BFF as the frontend-facing API gateway for the pilot.

#### Scenario: The frontend starts or resumes a review task

- **WHEN** the browser lists, opens, initializes, refreshes, matches, reviews, reports, or archives an opening-condition task
- **THEN** it calls the Node BFF platform API
- **AND** the browser does not call MaxKB, OCR Worker, PaddleOCR, RAGFlow, Dify, MinIO private endpoints, or Python worker services directly

#### Scenario: A provider requires credentials

- **WHEN** the platform uses MaxKB, OCR Worker, PaddleOCR, RAGFlow, LLM, MinIO, queue, or Python agent service credentials
- **THEN** those credentials are stored and used server-side
- **AND** API keys, passwords, Authorization headers, private object URLs, raw provider traces, prompts, and unbounded OCR text are never exposed to the browser

### Requirement: MaxKB is an optional knowledge provider

The preflight platform SHALL integrate MaxKB as an optional knowledge-base provider selected by server-side configuration.

#### Scenario: MaxKB provider is enabled

- **WHEN** `KNOWLEDGE_PROVIDER=maxkb` and MaxKB configuration is present
- **THEN** the platform exposes a safe provider readiness summary
- **AND** stores `workspaceId`, `knowledgeId`, optional folder/document/chunk refs, sync status, safe snippets, locators, scores, source object refs, evidence refs, and master-data refs as provider support metadata

#### Scenario: Evidence is indexed through MaxKB

- **WHEN** OCR-derived or platform-approved evidence content is ingested into MaxKB
- **THEN** the platform stores provider refs in `KnowledgeBinding` and `OcrIngestionLink`
- **AND** MaxKB retrieval hits are used only as supporting recall
- **AND** formal pass, reject, supplement, archive, and report decisions remain platform decisions

#### Scenario: MaxKB is disabled or unreachable

- **WHEN** MaxKB is disabled, misconfigured, stale, degraded, or unreachable
- **THEN** the platform reports a bounded provider status
- **AND** review task business state remains readable
- **AND** formal review actions that require retrieval support are blocked or routed to manual handling with safe diagnostics

### Requirement: OCR Worker is a backend capability service

The preflight platform SHALL call OCR Worker from the server side to perform OCR, certificate post-processing, MaxKB ingestion, and retrieval checks.

#### Scenario: The platform registers OCR ingestion

- **WHEN** an evidence record needs OCR processing
- **THEN** the platform calls `POST /api/preflight/ocr-ingestions` with `Authorization: Bearer <PREFLIGHT_API_KEY>`
- **AND** supplies `Idempotency-Key` using `ocr:<projectId>:<reviewTaskId>:<sourceObjectId>:<contentHash>`
- **AND** supplies or records `X-Correlation-ID`
- **AND** persists the returned `ingestionId` in `OcrIngestionLink`

#### Scenario: OCR Worker is retried

- **WHEN** the same OCR registration request is retried with the same idempotency key
- **THEN** the platform expects the same ingestion record
- **AND** does not create duplicate evidence, provider refs, or review findings

#### Scenario: OCR Worker returns provider refs

- **WHEN** OCR post-processing, MaxKB ingestion, or retrieval-check completes
- **THEN** the platform stores only safe provider ids, document names, sync status, timestamps, retrieval summaries, and diagnostics
- **AND** secrets, raw provider traces, private URLs, unbounded raw OCR text, and full prompts are not persisted in platform-facing provider refs

### Requirement: Opening-condition pilot follows explicit execution gates

The preflight platform SHALL operate the opening-condition pilot through explicit readiness and execution gates.

#### Scenario: A pilot task is initialized

- **WHEN** the platform receives workspace context, published basis records, approved master data, optional MaxKB binding, checklist object reference, and material packet references
- **THEN** `POST /api/opening-condition/pilot-tasks/intake-init` initializes or reinitializes the task
- **AND** stores task-bound checklist definition and packet inventory manifest when available
- **AND** returns readiness plus bounded diagnostics

#### Scenario: Required basis or master data is missing

- **WHEN** no published basis version is available
- **THEN** the task enters `blocked_missing_basis`
- **AND** formal material matching is not started

- **WHEN** required master data is missing or not approved
- **THEN** the task enters `blocked_missing_master_data`
- **AND** formal material matching is not started

#### Scenario: Formal matching is requested

- **WHEN** an operator explicitly starts formal matching
- **THEN** the platform uses the task-bound checklist definition, packet inventory entries, approved master data, evidence refs, and optional MaxKB retrieval support
- **AND** uncertain signatures, stamps, checkboxes, handwritten dates, ambiguous matches, missing authorization, and visual assertions are routed to human review
- **AND** workspace synchronization alone never silently triggers formal matching

### Requirement: Review decisions and reports are durable platform records

The preflight platform SHALL persist human decisions and report assets as durable records before deeper workflow automation is considered production-ready.

#### Scenario: A reviewer acts on an issue

- **WHEN** a reviewer accepts, rejects, edits, adds, deletes, defers, or resolves an issue
- **THEN** the platform stores a bounded activity event with actor, time, action type, issue/result references, decision, mode, and safe message
- **AND** the activity event excludes secrets, private URLs, raw provider traces, full prompts, and unbounded document text

#### Scenario: A report is generated or archived

- **WHEN** blocking human-review items have been resolved and a report is generated
- **THEN** the platform stores the report asset reference, evidence summary, human decisions, task status, and event chain
- **AND** the report remains an internal auxiliary review asset unless the business explicitly promotes it through platform workflow

### Requirement: Provider lifecycle remains replaceable

The preflight platform SHALL keep provider integrations replaceable behind stable contracts.

#### Scenario: A production queue or Python agent service is introduced

- **WHEN** local Node fallback, local file queue, OCR Worker JSON state, or mock knowledge provider is replaced by Redis, BullMQ, Celery, RQ, PostgreSQL-backed queues, Temporal, Dify, RAGFlow, MaxKB, or a Python agent service
- **THEN** frontend task APIs, task state replay, safe provider summaries, idempotency semantics, and provider refs remain stable
- **AND** the browser-facing contract does not need to change

#### Scenario: A local prototype adapter is used

- **WHEN** local files, SQLite, JSON state, or mock provider adapters are used during development
- **THEN** they are treated as prototype storage only
- **AND** production migration requires platform-owned relational state, object storage, queue semantics, audit records, and server-side provider credentials
