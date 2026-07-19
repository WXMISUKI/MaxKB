## Why

The platform is reaching the point where OCR, LLM, object storage, knowledge retrieval, and future agent workers may be developed or deployed as separate provider services. Without explicit integration contracts, external systems such as RAGFlow can become accidental fact stores or workflow owners, which would weaken auditability and slow enterprise delivery.

This change defines the provider boundary before the next implementation stage: the platform owns workflow state and compliance facts, while external providers expose safe, replaceable APIs for retrieval, extraction, storage, and agent execution.

## What Changes

- Define a provider integration contract capability covering health, credentials, scoped identifiers, request/response envelopes, safe diagnostics, idempotency, and audit correlation.
- Define the knowledge-base/RAG provider contract needed for RAGFlow or equivalent systems.
- Classify external providers into near-term required, near-term optional, and deferred categories.
- Preserve the current architectural rule that vector recall and RAG output support evidence retrieval only; they do not become basis, master-data, human-decision, or report fact sources.
- Extend backend connectivity requirements so each configured provider can report safe readiness without exposing secrets or raw document payloads.
- Extend opening-condition preflight knowledge-base requirements so a bound subcontract-team knowledge base may point to an external dataset/provider while the platform keeps its own structured record.

## Capabilities

### New Capabilities

- `external-provider-integration-contracts`: Provider adapter contracts for RAG/knowledge-base services, future agent workers, OCR/LLM/storage readiness, safe diagnostics, and platform-owned source-of-truth boundaries.

### Modified Capabilities

- `backend-connectivity`: Add safe readiness summaries for external provider adapters beyond LLM/OCR/MinIO, especially RAG and agent-worker providers.
- `opening-condition-preflight-knowledge-base`: Allow knowledge-base records to bind an external provider dataset/index reference while preserving platform records as the source of truth.

## Impact

- Affected docs: provider architecture, opening-condition pilot workflow, backend connectivity notes, and future deployment/configuration documentation.
- Affected specs: new provider contract spec plus deltas for backend connectivity and opening-condition preflight knowledge base.
- Likely future implementation areas: `server/config.mjs`, provider health helpers, backend connectivity DTOs, knowledge-base adapter module, opening-condition pilot store references, and provider configuration docs.
- Potential external systems: RAGFlow or equivalent RAG service, future Python/FastAPI agent worker, OCR service, OpenAI-compatible LLM gateway, MinIO/OSS, and later queue/database providers.
- No production dependency is introduced by this proposal; implementation should keep all external providers optional until explicitly configured.

## Recommended Next Stage

From the perspective of highest value, fastest production progress, and lowest delivery risk, the next stage should not start from deep Ascend specialization or broad provider expansion. It should start from:

**stabilizing the external integration contract for the condition-review platform and turning the current RAGFlow service boundary into a callable MVP.**

The recommended order is:

1. Finalize the contract the downstream project actually needs.
2. Prove the contract through a minimal runnable integration path.
3. Archive the verified path and the deployment constraints.

This keeps the project focused on a production-oriented boundary instead of drifting into local-only optimization or hardware-first over-design.
