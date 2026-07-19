## Task Group A — Spec

Priority: highest
Goal: lock the downstream integration boundary before deeper implementation.

- [x] A1 Finalize the condition-review platform contract for RAGFlow retrieval and OpenAI-compatible chat usage.
- [x] A2 Define the dataset preparation baseline: allowed document classes, preferred formats, metadata strategy, and stale rules.
- [x] A3 Finalize provider health/readiness envelope with capability discovery, safe diagnostics, and audit correlation.
- [x] A4 Finalize the source-of-truth rule: RAGFlow remains a retrieval provider, never the workflow state owner or compliance fact store.

## Task Group B — Implementation

Priority: high
Goal: turn the contract into a minimal runnable integration path.

- [x] B1 Add provider-neutral knowledge-base adapter types for dataset refs, document refs, chunk refs, ingestion status, and retrieval hits.
- [x] B2 Add or confirm local/mock adapter behavior so development and tests do not depend on production-only providers.
- [x] B3 Add a minimal RAGFlow adapter path behind explicit configuration, using server-side API key handling only.
- [x] B4 Normalize RAGFlow dataset/document/chunk identifiers into platform provider refs without elevating provider metadata into formal facts.
- [x] B5 Expose safe readiness summaries for the RAG provider through backend connectivity and operations views.
- [x] B6 Provide one minimal downstream integration example covering health, auth, retrieval test, and OpenAI-compatible chat.

## Task Group C — Archive

Priority: medium
Goal: make the verified path reusable and hard to misuse.

- [x] C1 Archive required environment variables, disabled/degraded behavior, and local bootstrap rules for RAGFlow integration.
- [x] C2 Archive dataset operating guidance for the condition-review platform, including ownership, sync, and stale handling.
- [x] C3 Archive local troubleshooting for login, proxy mode, API key bootstrap, and service smoke testing.
- [x] C4 Archive the Ascend migration constraint: keep the external contract stable and swap only the model-serving backend later.

## Verification

- [x] V1 Add focused tests for provider config normalization and safe diagnostic redaction.
- [x] V2 Add focused tests for retrieval hit normalization, provider refs, and conflict/stale handling.
- [ ] V3 Run targeted validation for changed backend/frontend modules and smoke-test the external service path.

## Task Group D — MaxKB Pilot Positioning

Priority: highest for the next local development stage
Goal: run through a MaxKB-based private knowledge-base pilot for construction supervision review before Linux/Ascend migration.

- [x] D1 Confirm MaxKB is the platform owner for knowledge base, workflow, review state, audit, and report assets.
- [x] D2 Confirm Ascend servers provide model-service endpoints only; they do not own MaxKB business state.
- [x] D3 Confirm the first pilot scenario: opening-condition review plus construction-plan review for one project and one施工 / 分包队伍.
- [x] D4 Confirm first-stage dataset grain: project-level logical knowledge base with metadata filtering.
- [ ] D5 Prepare a first pilot document pack with 10-30 representative files.
- [ ] D6 Run MaxKB locally on Windows with Docker Desktop and validate knowledge-base upload/search/chat.
- [ ] D7 Configure an initial LLM provider, embedding model, and optional reranker for the pilot.
- [ ] D8 Convert pilot learnings into formal OpenSpec/spec-kit requirements before backend customization.

## 本轮说明

- `A3`、`A4` 已通过 `provider-readiness-and-source-of-truth.md` 收口。
- `B1`、`B4` 当前以仓库内参考实现资产完成：`tools/ragflow-service/provider_contract.py` 与 `tools/ragflow-service/normalize_ragflow_retrieval.py`。
- `B2`、`B3`、`B5` 当前以仓库内双模式 adapter 和 readiness CLI 形式完成：`tools/ragflow-service/provider_adapter.py` 与 `tools/ragflow-service/provider_readiness_cli.py`。
- `V1`、`V2` 已通过 `test/ragflow_service/` 下 focused tests 覆盖当前参考实现。
- `B5` 当前完成到“后端接入前的参考实现层”，尚未进入真实业务平台的 backend connectivity 页面，但输出 shape 已固定。
- `V3` 已新增真实验收脚本 `tools/ragflow-service/run_validation_report.py`，并在 2026-07-17 本地执行通过 readiness；retrieval/chat 仍因缺少 `RAGFLOW_DATASET_IDS`、`RAGFLOW_CHAT_ID`、`RAGFLOW_MODEL` 保持 `blocked`，故暂不勾选完成。
- `D1` 到 `D4` 已通过 `docs/construction-supervision-private-kb-roadmap.md` 沉淀；下一步应先完成本地 MaxKB 知识库闭环，再进入源码级定制。
