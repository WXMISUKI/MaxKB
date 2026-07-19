## Context

The platform already has server-side provider configuration for LLM, OCR, and MinIO, and the opening-condition pilot now has platform-owned basis, master-data, evidence, human-review, report, preflight readiness, and subcontract-team knowledge-base records.

RAGFlow is a good candidate for the external knowledge-base provider because its official API/docs cover dataset management, document upload, chunk creation/management, and retrieval. Its product model also includes parsing, chunking, embedding, full-text indexes, and manual chunk intervention, which fits our need to reuse verified material evidence without making the RAG system the compliance source of truth.

The main design pressure is not "which vector database wins"; it is preserving platform control. External providers can accelerate parsing, retrieval, OCR, LLM reasoning, and worker execution, but formal review state must remain in the platform.

## Goals / Non-Goals

**Goals:**

- Define which external provider categories should be prepared now.
- Define a common provider adapter envelope for health checks, invocation, safe diagnostics, idempotency, and audit correlation.
- Define a RAG/knowledge-base provider contract suitable for RAGFlow or equivalent systems.
- Specify the configuration keys the platform will need when implementation starts.
- Keep provider output normalized into platform-owned records.

**Non-Goals:**

- Build a production RAGFlow adapter in this change.
- Pick a final vector database for all future deployments.
- Let RAGFlow, Dify, or another provider own opening-condition workflow state.
- Store raw OCR text, prompts, provider traces, presigned URLs, secrets, or full documents in frontend-visible summaries.
- Replace database planning for basis, master data, evidence, human decisions, and report assets.

## Decisions

1. **Provider categories are prioritized by production value.**

   Near-term required:
   - Object storage provider: MinIO/OSS for original files, OCR outputs, evidence attachments, and reports.
   - OCR provider: PaddleOCR or equivalent for scanned documents and visual/text extraction.
   - LLM provider: OpenAI-compatible gateway/NewAPI for structured extraction and reasoning.
   - RAG provider: RAGFlow or equivalent for dataset ingestion, retrieval, chunk references, and citation support.

   Near-term optional:
   - Agent worker provider: Python/FastAPI worker for heavy document parsing, package decompression, long-running OCR, and future LangGraph-style orchestration.
   - Queue provider: Redis/BullMQ/Celery/RQ for durable async jobs once local development is no longer enough.

   Deferred:
   - Enterprise identity provider, e-signature provider, CAD/BIM parser, third-party regulatory data feeds, and full evidence authenticity services.

   Alternative considered: build all provider integrations at once. Rejected because it would slow the single-project trial.

2. **RAG provider is a retrieval adapter, not a fact store.**

   The platform should create and maintain its own `subcontract_knowledge_base` record with organization, contract package, subcontract team, status, safe summary, master-data references, and provider references. RAGFlow may hold datasets, documents, chunks, embeddings, and retrieval scores.

   Platform facts remain:
   - Published basis versions.
   - Published or human-approved project master data.
   - Evidence records and object references.
   - Human-review decisions.
   - Check item outcomes and report assets.

   Alternative considered: store all knowledge-base facts only in RAGFlow metadata. Rejected because metadata retrieval is not an auditable compliance fact model.

3. **Use a provider-neutral adapter contract with provider-specific mapping below it.**

   The platform-facing contract should be:

   ```ts
   type ProviderHealth = {
     provider: "ragflow" | "ocr" | "llm" | "minio" | "agent_worker" | "queue";
     configured: boolean;
     ready: boolean;
     status: "ready" | "disabled" | "degraded" | "error" | "stale" | "unreachable";
     summary: string;
     version?: string;
     capabilities?: ProviderCapability;
     correlationId?: string;
     safeDiagnostics?: Record<string, unknown>;
   };

   type ProviderCapability = {
     retrieval?: boolean;
     ingestion?: boolean;
     documentStatus?: boolean;
     chunkListing?: boolean;
     metadataFilter?: boolean;
     rerank?: boolean;
     openaiCompatibleChat?: boolean;
     modelListing?: boolean;
     streaming?: boolean;
   };

   type RetrievalRequest = {
     workspaceId: string;
     knowledgeBaseId: string;
     providerDatasetIds: string[];
     query: string;
     filters?: {
       organizationId?: string;
       contractPackageId?: string;
       subcontractTeamId?: string;
       basisVersionId?: string;
       masterDataIds?: string[];
       documentTypes?: string[];
     };
     topK: number;
     correlationId: string;
   };

   type RetrievalHit = {
     provider: string;
     providerDatasetId: string;
     providerDocumentId?: string;
     providerChunkId?: string;
     score?: number;
     title: string;
     safeSnippet: string;
     locator?: string;
     sourceObjectId?: string;
     masterDataIds?: string[];
     evidenceIds?: string[];
   };
   ```

   RAGFlow-specific IDs map into `providerDatasetId`, `providerDocumentId`, and `providerChunkId`.

   `safeDiagnostics` must use an allowlist and may only contain safe operational summaries such as timeout, latency, safe error code, model labels, dataset count, deployment mode, and provider version.

4. **Provider configuration must be explicit and server-only.**

   Expected near-term RAG configuration:
   - `RAG_PROVIDER=ragflow`
   - `RAGFLOW_BASE_URL`
   - `RAGFLOW_API_KEY`
   - `RAGFLOW_DEFAULT_DATASET_ID` optional for development only
   - `RAGFLOW_TIMEOUT_MS`
   - `RAGFLOW_ENABLED=true|false`

   Future worker configuration:
   - `AGENT_SERVICE_BASE_URL`
   - `AGENT_SERVICE_API_KEY`
   - `AGENT_SERVICE_TIMEOUT_MS`

   Provider keys must never be exposed through frontend APIs, task events, report assets, or logs.

5. **External provider writes must be idempotent and traceable.**

   Dataset creation, document registration, chunk upsert, and retrieval calls should carry platform ids and correlation ids. The adapter should tolerate retries without creating duplicate platform records. Provider calls should return safe summaries and provider refs, not raw provider traces.

6. **Source-of-truth is fixed before implementation deepens.**

   Platform-owned facts remain the only formal source for workflow status, basis versions, master data, evidence object references, human decisions, and report assets.

   Provider-owned data remains replaceable support data only:

   - dataset/document/chunk ids
   - embeddings
   - retrieval scores
   - snippets
   - provider metadata

   Alternative considered: allowing provider metadata to stand in for formal facts. Rejected because it weakens auditability and makes later provider swaps expensive.

## Risks / Trade-offs

- [Risk] RAGFlow metadata and platform records drift. -> Mitigation: platform stores provider refs plus its own authoritative status and can re-sync or mark provider refs stale.
- [Risk] Provider retrieval returns convincing but outdated chunks. -> Mitigation: filter by workspace, active basis, subcontract team, and current master-data refs; preserve conflicts for human review.
- [Risk] Provider API versions change. -> Mitigation: isolate provider-specific calls behind a `knowledgeBaseProvider` adapter and expose provider version in health diagnostics.
- [Risk] Uploading files to both MinIO and RAGFlow duplicates storage. -> Mitigation: keep MinIO as canonical object storage; RAGFlow stores retrieval copies or linked documents only for indexing.
- [Risk] RAG provider becomes a hidden workflow engine. -> Mitigation: only allow ingestion, parse status, chunk listing/upsert, and retrieval; do not accept formal review decisions from provider state.

## Migration Plan

1. Add provider config/readiness contract without enabling RAG by default.
2. Add a local/mock knowledge-base provider implementing the same interface.
3. Add RAGFlow adapter behind feature flag.
4. Bind provider dataset refs to platform knowledge-base records.
5. Use retrieval hits only inside evidence support and human-review explanations.
6. Add reconciliation diagnostics showing provider dataset status vs platform knowledge-base status.
7. Keep the external contract stable when model-serving backends later move to Ascend; swap endpoints and deployment runtime only.

## Open Questions

- Should the first RAGFlow deployment use one dataset per subcontract team, or one dataset per project/contract package with metadata filters?
- Should RAGFlow ingest files directly, or should the platform upload to MinIO first and then send indexed copies/links to RAGFlow?
- Which embedding/reranker model will you configure in RAGFlow for Chinese construction documents?
- Do we want the first trial to call RAGFlow retrieval only during matching, or also during basis/master-data confirmation?
