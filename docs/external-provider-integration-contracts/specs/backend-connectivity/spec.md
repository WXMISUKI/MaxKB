## ADDED Requirements

### Requirement: External provider readiness summary
The backend connectivity surface SHALL include safe readiness summaries for optional external provider adapters including RAG and agent-worker providers.

#### Scenario: RAG provider is configured
- **WHEN** backend connectivity is requested and a RAG provider such as RAGFlow is configured
- **THEN** the response includes configured, ready, status, source, provider type, and safe summary fields for the RAG provider

#### Scenario: RAG provider is disabled
- **WHEN** no RAG provider is enabled
- **THEN** the response reports the RAG provider as disabled or unconfigured without treating the backend as unhealthy

#### Scenario: Agent worker provider is configured
- **WHEN** a separate agent worker service is configured
- **THEN** the response includes a safe readiness summary for the worker service without exposing auth headers, raw payloads, or service internals
