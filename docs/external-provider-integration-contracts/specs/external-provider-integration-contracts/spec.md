## ADDED Requirements

### Requirement: Provider adapter boundary
The system SHALL integrate external providers through platform-owned adapters that preserve platform records as the source of truth.

#### Scenario: Provider output is received
- **WHEN** an external provider returns OCR, LLM, RAG, worker, storage, or queue output
- **THEN** the system normalizes the output into platform-owned records or safe summaries before it affects workflow state, review results, readiness, or reports

#### Scenario: Provider is unavailable
- **WHEN** an optional provider is disabled, not configured, or unavailable
- **THEN** the platform reports degraded or disabled readiness without exposing secrets and without corrupting existing platform records

### Requirement: Provider health and safe diagnostics
The system SHALL expose safe readiness summaries for configured external providers.

#### Scenario: Provider health is requested
- **WHEN** backend connectivity or diagnostics request provider readiness
- **THEN** the system returns provider type, configured flag, ready flag, status, source, summary, and bounded safe diagnostics

#### Scenario: Provider diagnostics contain unsafe data
- **WHEN** provider diagnostics include API keys, auth headers, raw document text, prompts, provider traces, private URLs, cookies, sessions, or unbounded payloads
- **THEN** the system omits or redacts those fields before persistence, logging, or frontend display

### Requirement: Knowledge-base provider references
The system SHALL allow platform knowledge-base records to reference external provider datasets, documents, and chunks without delegating fact ownership to the provider.

#### Scenario: Knowledge base is indexed externally
- **WHEN** a subcontract-team knowledge base is indexed in RAGFlow or another RAG provider
- **THEN** the platform stores provider dataset, document, and chunk references alongside the platform knowledge-base id, workspace id, organization id, contract package id, and subcontract team id

#### Scenario: Retrieval hit supports a review item
- **WHEN** the RAG provider returns a retrieval hit for a review query
- **THEN** the platform records only safe snippet, locator, provider refs, score, and related platform evidence or master-data ids as supporting recall

#### Scenario: Retrieval conflicts with platform facts
- **WHEN** RAG provider recall conflicts with the active basis version, published master data, evidence record, or human decision
- **THEN** the platform preserves the conflict and treats platform facts as authoritative for formal conclusions

### Requirement: Provider invocation traceability
The system SHALL make external provider calls traceable without exposing unsafe payloads.

#### Scenario: Provider call is made
- **WHEN** the platform invokes a provider for ingestion, parse status, retrieval, OCR, LLM, or worker execution
- **THEN** the request includes platform workspace/task identifiers and a correlation id that can be linked to safe task events or diagnostics

#### Scenario: Provider call is retried
- **WHEN** a provider call is retried after a timeout or transient failure
- **THEN** the platform uses idempotency keys or stable platform identifiers to avoid duplicate platform records

### Requirement: External provider configuration
The system SHALL keep provider configuration server-side and optional until the provider is explicitly enabled.

#### Scenario: Provider config is missing
- **WHEN** required provider environment variables are absent
- **THEN** the backend reports that provider as disabled or unconfigured without failing unrelated platform features

#### Scenario: Provider config is present
- **WHEN** required provider environment variables are present
- **THEN** the backend can run a bounded readiness check without returning raw configuration values to the frontend
