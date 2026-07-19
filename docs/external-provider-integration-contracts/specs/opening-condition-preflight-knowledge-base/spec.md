## ADDED Requirements

### Requirement: External knowledge-base provider binding
Opening-condition subcontract-team knowledge-base records SHALL support external RAG provider references while preserving platform-owned preflight facts.

#### Scenario: External dataset is bound
- **WHEN** a knowledge base is linked to RAGFlow or another external RAG provider
- **THEN** the platform stores provider name, provider dataset ids, optional provider document or chunk refs, and safe sync status on the platform knowledge-base record

#### Scenario: External provider is not ready
- **WHEN** the bound provider dataset is missing, stale, parsing, degraded, or unreachable
- **THEN** the readiness summary reports the knowledge-base support source as provisional or blocked according to workflow policy

#### Scenario: Knowledge-base retrieval supports material review
- **WHEN** formal material review uses external RAG recall
- **THEN** the system treats retrieved chunks as supporting evidence recall and still evaluates formal conclusions against published basis, published or human-approved master data, platform evidence, and human decisions
