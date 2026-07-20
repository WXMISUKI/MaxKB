# Architecture Evolution Decisions

Decision date: 2026-07-14

## Positioning

The platform is not a single-shot AI conclusion generator. It is a human-in-the-loop construction plan review platform that must support traceable document ingestion, recoverable AI review generation, reviewer decisions, review records, report assets, and future knowledge-base grounding.

The current Node.js backend is a deliberate BFF layer for MVP integration. It is suitable for frontend-facing upload, MinIO, OCR status, LLM connectivity, SSE progress, safe provider diagnostics, and review-generation run bridging. It is not intended to be the final long-running intelligent-agent runtime.

## Architecture Decision

Do not replace the Node BFF with Python immediately. Instead, evolve the system in layers:

```text
Frontend React
  -> Node BFF / API Gateway
       - auth and permission gate
       - upload and object-storage bridge
       - stable review task interface
       - SSE/WebSocket fan-out
       - safe provider summaries
       - no durable long-running workflow ownership
  -> Durable storage
       - documents
       - review tasks
       - review generation runs
       - review issues
       - activity/audit events
       - report assets
  -> Queue / workflow runtime
       - retry
       - idempotency
       - worker leasing
       - resumable status events
  -> Python Worker / Agent Service
       - OCR result parsing
       - document structure recovery
       - LLM review agents
       - RAG and knowledge retrieval
       - report/export generation
```

The next architectural priority is backend-owned durable review task state. Once review documents, tasks, runs, issues, and activities have a stable backend persistence contract, Python workers can be introduced behind the same interface without disrupting the workbench.

## Near-Term Iteration Order

1. Backend task persistence foundation
   - backend-owned document/task/run/issue/activity snapshots
   - localStorage kept only as a compatibility fallback
   - stable frontend service interface for list/open/update review tasks

2. Worker queue foundation
   - durable review runs
   - retry and terminal states
   - event replay for loading pages
   - worker-safe idempotency
   - local file-backed queue adapter as a development bridge
   - explicit lease, heartbeat, retry, and dead-letter semantics before production queue adoption

3. Python agent service bridge
   - OCR/layout/RAG/review/report execution
   - small backend-facing interface
   - Node BFF remains the frontend-facing contract

4. Audit and compliance hardening
   - immutable activity log
   - organization/project scoping
   - permission checks
   - exportable review records

## Why This Order

Moving straight to a Python agent runtime would still leave the system without durable review state. Mature review platforms need persistence, recovery, traceability, permissions, and audit trails before a complex worker layer can safely carry production work.

The current run snapshot, activity trail, preparation package, draft issue provenance, and backend generation run bridge are already shaped to support this migration. The next step is to make that state backend-owned.

## Queue Foundation Decision

After backend-owned task snapshots and replayable run events, the next implementation layer is a local worker queue adapter behind the Node BFF. This is still not the final production worker runtime. It is a development bridge that introduces the contracts a production queue and Python worker must later honor:

- enqueue review-generation work when a run is created;
- claim jobs through a worker lease instead of executing directly in the request path;
- heartbeat active work so interrupted jobs can be retried;
- mark jobs succeeded, retryable failed, dead-lettered, skipped, or canceled;
- keep run status and event replay as the frontend-facing source of truth;
- persist only safe job summaries and diagnostics.

This keeps the Node BFF as the frontend-facing API seam while making execution ownership replaceable. Redis, PostgreSQL-backed queues, Temporal, Celery, BullMQ, or Python workers can later replace the local adapter without changing the review-loading UI contract.

## Python Agent Service Bridge Decision

After the local worker queue foundation, the next implementation layer is a backend-facing Python agent service bridge. This is still not the final production agent runtime. It is a small contract that lets the Node worker delegate review-generation execution to a configured Python service when ready, while preserving the existing local Node fallback path.

The bridge introduces the runtime shape future Python services must honor:

- expose a safe health/readiness endpoint;
- accept bounded review-generation context with run id, task id, mode, structure summary, paragraph excerpts, max issue count, and safe provider summaries;
- return schema-valid stage events, preparation package output, draft issue generation output, completion metadata, and safe diagnostics;
- never require the browser to know service URLs, auth headers, prompts, raw provider traces, private object URLs, or unbounded OCR text;
- degrade to local fallback when the service is disabled, unavailable, timed out, or returns invalid payloads;
- keep run status, run events, replayable SSE, and worker queue ownership as the frontend-facing source of truth.

This keeps the current Node BFF valuable as the API gateway and review-loading contract while making the long-running intelligent-agent execution layer replaceable.

## Review Decision Completion Decision

After backend generation run materialization, the next production-critical layer is backend-owned reviewer decisions and completion. OCR and AI generation only create value after a human reviewer can accept, reject, edit, add manual findings, and complete the task through a durable backend contract.

This layer makes the current MVP closer to mature review platforms:

- AI-generated and manual issues become actionable business records, not only frontend-local state;
- review-mode completion can persist a supervisor report asset;
- review-revise mode can persist a revised-plan snapshot generated from accepted issue resolutions;
- the frontend may still use local fallback for MVP resilience, but backend task snapshots become the preferred source after successful reviewer actions;
- audit logs, permissions, tenant scoping, report export, and Python report agents can later build on the same stable task action contract.

This should be prioritized before deeper workflow-engine work because durable human decisions are the bridge between generated issues and production review records.

## Review Decision Activity Trail Decision

After backend-owned reviewer decisions and completion, the next production-critical layer is a safe reviewer activity trail. Mature review platforms need users and later auditors to understand which issue was accepted, rejected, edited, manually added, deleted, or used to complete a result asset.

This slice intentionally stops short of an immutable audit ledger. It records bounded, safe activity summaries on the review task aggregate and exposes task-scoped activity reads. That is enough to support result provenance, later audit UI, role-aware accountability, and report export preparation without forcing a premature authentication, tenancy, or database migration.

The activity trail must remain safe:

- store action type, time, actor placeholder, issue/result references, decision, mode, and short messages;
- exclude prompts, provider traces, secrets, tokens, private URLs, and unbounded document text;
- keep the Node BFF as the current task API boundary while leaving room for a future durable audit store.

## Opening Condition Review Direction Decision

Opening-condition review should be developed as an independent business portal beside construction plan review, not as a direct menu item inside the construction-plan review shell and not as a separate throwaway contest demo. It reuses the same platform principles: human-in-the-loop, traceable evidence, recoverable task state, safe provider summaries, and report assets.

The product topology is:

```text
Unified login
  -> Product launcher
      -> Construction Plan Review portal
      -> Opening Condition Review portal
```

Each portal owns its route namespace, sidebar, landing page, business context, and state machine. The shared platform layer owns identity, provider summaries, object storage, OCR, task status, Dify/agent gateways, report assets, and safe diagnostics.

The near-term implementation uses a typed platform-owned review packet and mock data to demonstrate the workflow. Dify remains valuable for workflow orchestration, OCR/LLM extraction, Human Input review nodes, and report drafting. However, durable business records must belong to the platform:

- basis versions and applicability confirmation;
- project personnel, equipment, certificate, company, and system-document master data;
- check item rule verdicts and semantic notes;
- evidence references and confidence summaries;
- human review triggers and decisions;
- auxiliary report summaries and audit records.

This direction supports rapid contest delivery while preserving the future migration path to backend persistence and Python/Dify agent service bridges. It also prevents local prompt optimization from becoming the architecture.

## Opening Condition Storage Decision

Opening-condition review requires structured records before deeper workflow automation becomes production-safe. The storage direction is:

- PostgreSQL or an equivalent relational store is the target source of truth for tenants, projects, contract packages, participating organizations, workspaces, basis-set versions, master data, review packets, check items, evidence references, human decisions, and audit events.
- MinIO or compatible object storage holds uploaded archives, contracts, OCR outputs, source evidence, report files, and exported ledgers.
- A vector index can support semantic retrieval and similarity matching, but it must not be the authoritative store for contracts, basis versions, pass/fail decisions, or reviewer approvals.
- SQLite is acceptable only for local prototype state, development snapshots, or automated tests.

This keeps Dify workflow output and embedding search useful without letting either become the compliance record.

## Opening Condition Pilot Operability Decision

For the next opening-condition milestone, prioritize a single-project real pilot loop before full multi-tenant permission management, production database migration, or provider-specific optimization.

The pilot loop should make one workspace operational end to end:

- select or create the project / contract package / participating organization context;
- confirm and publish basis records from the subcontract contract or supplemental agreements;
- initialize project master data for personnel, equipment, certificates, organizations, and system documents;
- create and bind an organization / subcontract-team knowledge base as a support source;
- upload the checklist and material packet;
- run formal material completeness matching only after preflight gates are ready;
- route uncertain signatures, stamps, checkboxes, handwritten dates, ambiguous matches, and missing authorization to human review;
- generate and archive an internal auxiliary report after blocking human-review items are reconciled.

This direction deliberately avoids local infinite optimization. RAGFlow, Dify-like workflows, OCR, and LLMs can improve extraction and recall quality, but the production value comes from platform-owned task state, readiness gates, evidence summaries, human decisions, and report assets becoming operable for a real trial user.

## Opening Condition Intake Orchestration Decision

For the pilot intake stage, add a domain-owned orchestration entry instead of rebuilding file upload inside the opening-condition module.

The chosen path is:

- keep generic upload and object-storage channels as shared platform capability;
- accept only safe object references at the opening-condition domain boundary;
- initialize or reinitialize the pilot task from workspace context, published basis, approved master data, optional knowledge-base selection, checklist object ref, and material packet refs in one backend mutation;
- return readiness plus bounded orchestration diagnostics so the frontend does not have to manually compose task upsert, packet bind, and knowledge-base binding flows.

This preserves a clean enterprise boundary: upload remains infrastructure, while intake/init becomes the business orchestration seam for the opening-condition pilot.

## Opening Condition Manual Execution Console Decision

After intake/init became a domain-owned backend seam, the next pilot priority is not deeper parsing first but explicit operator control.

The chosen direction is:

- workspace synchronization may hydrate basis, master data, knowledge-base records, and existing pilot task state;
- workspace synchronization must not silently trigger formal checklist matching;
- the portal should expose explicit actions for intake/init, formal matching, and task refresh;
- once a pilot task exists, backend task state becomes the preferred execution view over local demo summaries.

This keeps the pilot behavior understandable for enterprise users and reduces the risk of hidden auto-execution before the business is ready to trust it.

## Opening Condition Task-Bound Checklist Definition Decision

After the portal gained explicit execution controls, the next production-facing gap is checklist ownership. Formal matching should not depend on the frontend resending a transient checklist definition every time.

The chosen direction is:

- persist a normalized checklist definition on the pilot task during intake/init;
- let formal matching reuse the stored task-bound checklist definition by default;
- keep checklist file parsing itself as a later slice, so future DOCX/XLSX adapters only need to feed the same backend checklist-definition contract.

This gives the pilot a more durable execution boundary without prematurely expanding into heavy document parsing.

## Opening Condition Controlled Checklist Adapter Decision

After checklist definition became task-owned, the next fastest production-facing slice is not full DOCX/XLSX parsing. It is a controlled backend adapter from checklist object references to task-bound checklist definitions.

The chosen direction is:

- keep explicit request-level checklist definition input as an allowed override;
- let intake/init derive checklist definition from recognized checklist-object templates by default;
- fall back to an existing task definition when reinitialization happens against an unrecognized checklist object;
- return a safe manual-action diagnostic when no explicit, derived, or existing checklist definition is available;
- keep heavy document parsing, OCR recovery, and semantic checklist generation as later slices that feed the same backend checklist-definition contract.

This keeps the opening-condition pilot moving toward a real trial loop without forcing premature parser complexity into the critical path.

## Opening Condition Packet Inventory Manifest Decision

After checklist-object adaptation, the next fastest production-facing slice is not deep OCR or ZIP extraction yet. It is a task-owned packet inventory manifest that lets the platform describe what the submitted material packet actually contains.

The chosen direction is:

- let pilot packets persist bounded inventory entries alongside checklist and source object refs;
- accept direct inventory input when available from later upload or ZIP-manifest tooling;
- derive a default inventory from submitted source objects when no explicit inventory is available;
- make formal matching prefer inventory entries as deterministic candidates instead of only coarse packet object names;
- keep real ZIP traversal, OCR batch execution, and richer document metadata as later slices feeding the same manifest contract.

This keeps the project moving toward a real trial loop while preserving a clean seam for future archive parsing and evidence-grounding upgrades.

## Opening Condition ZIP Manifest Extraction Decision

After packet inventory became task-owned, the next highest-value slice is to replace coarse object-level inventory with real ZIP entry manifests where possible.

The chosen direction is:

- keep `inventoryEntries` as the single packet-owned manifest contract;
- let explicit inventory input remain the highest-priority override;
- when no explicit inventory is provided, read ZIP objects from object storage and extract bounded entry manifests directly from the archive central directory;
- fall back to source-object-derived inventory when ZIP storage keys are missing, extraction fails, or no ZIP source exists;
- keep OCR, file-content extraction, and entry-level independent evidence objects as later slices that build on the same manifest seam.

This moves the pilot from “packet object has been uploaded” to “platform can see the real file list inside the packet” without prematurely expanding into heavy asynchronous extraction architecture.

## Opening Condition MaxKB Provider Decision

After the external MaxKB project knowledge base and OCR Worker local loop were validated, the next platform step is to integrate MaxKB as an optional knowledge-base provider, not as a business source of truth.

The chosen direction is:

- select knowledge providers through `KNOWLEDGE_PROVIDER=mock|ragflow|maxkb`;
- keep MaxKB configuration server-side through `MAXKB_*` environment variables;
- store MaxKB `knowledgeId`, document refs, chunk refs, sync status, and safe snippets as provider support metadata;
- keep Project, ContractPackage, Section, SubcontractTeam, ReviewTask, Evidence, OcrIngestionLink, human decisions, and report status owned by the platform;
- treat MaxKB retrieval-check and retrieval hits as supporting recall only.

This lets the current MaxKB work become useful for the single-project pilot while preserving the enterprise boundary needed for later database migration, audit, permissions, and production review records.
