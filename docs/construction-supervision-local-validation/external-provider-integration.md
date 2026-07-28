# 外部 Provider 接入边界

本项目采用“平台拥有事实与状态，外部 provider 提供能力”的集成方式。外部 provider 可以承担 OCR、LLM、对象存储、知识召回、异步 worker 等能力，但不能直接成为判定依据、项目主数据、人工决策、审查结论或报告资产的事实源。

## 推荐优先级

### 近期优先准备

1. **MaxKB / RAGFlow / RAG 知识库 provider**
   - 用途：资料模板、历史证据、人工修正、chunk 召回和引用辅助。
   - 不做：正式事实源、任务状态机、自动通过结论。
   - 平台保存：workspace、组织、合同包、分包队伍、知识库状态、provider dataset/document/chunk refs、同步状态。
   - MaxKB 当前作为前置平台优先联调 provider；RAGFlow 保留为同类可选 provider。

2. **Agent Worker provider**
   - 用途：资料包解压、长时间 OCR、复杂文档解析、后续可恢复智能体编排。
   - 当前状态：已有 `AGENT_SERVICE_BASE_URL` 与 readiness summary，未配置时使用本地 fallback。

3. **Queue provider**
   - 用途：任务增多后承载 OCR、RAG、LLM、报告生成等异步任务。
   - 当前状态：已有本地 worker queue 摘要；生产化时再切 Redis/BullMQ/Celery/RQ。

### 已有基础 provider

- LLM / NewAPI：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
- PaddleOCR：`PADDLEOCR_TOKEN`、`PADDLEOCR_JOB_URL`、`PADDLEOCR_MODEL`。
- MinIO：`MINIO_ENDPOINT`、`MINIO_PUBLIC_ENDPOINT`、`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY`、`MINIO_BUCKET`、`MINIO_REGION`。

## RAGFlow 配置项

RAGFlow 默认是可选 provider。没有配置时，平台健康检查不会因此失败。

```env
RAGFLOW_ENABLED=true
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_API_KEY=your-server-side-api-key
RAGFLOW_DEFAULT_DATASET_ID=optional-dataset-id
RAGFLOW_TIMEOUT_MS=5000
```

如果你的 RAGFlow 部署 API 路径与默认值不同，可以显式覆盖：

```env
RAGFLOW_HEALTH_PATH=/api/v1/health
RAGFLOW_DATASET_PATH=/api/v1/datasets
RAGFLOW_DOCUMENT_PATH=/api/v1/datasets/:datasetId/documents
RAGFLOW_CHUNK_PATH=/api/v1/documents/:documentId/chunks
RAGFLOW_RETRIEVAL_PATH=/api/v1/retrieval
```

这些路径只在服务端使用，前端不会接触 API key、Authorization header、raw text、provider trace 或私有 URL。

## MaxKB 配置项

MaxKB 默认也是可选 provider。当前前置平台联调推荐显式选择 MaxKB：

```env
KNOWLEDGE_PROVIDER=maxkb
MAXKB_ENABLED=true
MAXKB_BASE_URL=http://192.168.0.219:8091
MAXKB_API_KEY=<PREFLIGHT_API_KEY>
MAXKB_DEFAULT_KNOWLEDGE_ID=019f787c-644e-7162-bfe5-f4ee02a91539
MAXKB_TIMEOUT_MS=5000
```

本地局域网联调时，前置平台电脑 `192.168.0.219` 应访问 MaxKB/OCR Worker 电脑 `192.168.0.219` 暴露的
Worker proxy。`MAXKB_API_KEY` 使用 Worker 的 `PREFLIGHT_API_KEY`，不要把 MaxKB 管理员账号密码交给前置项目。

如果 MaxKB 部署 API 路径与默认值不同，可以显式覆盖：

```env
MAXKB_HEALTH_PATH=/api/health
MAXKB_STATUS_PATH=/api/knowledge-base/provider/status
MAXKB_RETRIEVAL_PATH=/api/knowledge/:knowledgeId/search
```

更详细的 MaxKB 对接约束见 [preflight-maxkb-provider-integration.md](./preflight-maxkb-provider-integration.md)。

## 平台记录与外部索引的关系

```text
Platform source of truth
  ├─ basis version
  ├─ project master data
  ├─ evidence records
  ├─ human decisions
  ├─ check item results
  └─ report assets

External provider support
  └─ MaxKB/RAGFlow knowledge or dataset/document/chunk refs
       ├─ safe snippet
       ├─ locator
       ├─ score
       └─ related evidence/master-data ids
```

当 MaxKB/RAGFlow 召回结果与平台已发布依据或主数据冲突时，平台保留冲突并以平台事实为准。冲突项应进入人工复核或证据解释，不应自动覆盖结论。

## 调试入口

- `/api/health`：返回核心 provider、知识库 provider、Agent Service、Queue 等安全摘要。
- `/api/knowledge-base/provider/status`：返回当前知识库 provider readiness。

## 下一步建议

1. 先跑通单项目真实试点闭环：任务、依据、主数据、知识库绑定、资料包、人工复核、报告归档。
2. 再用 MaxKB 建一个项目级 knowledge base，或用 RAGFlow 建一个项目/合同包/分包队伍级 dataset。
3. 把合同边界、核查表模板、历史人工修正、已确认主数据摘要作为首批索引资料。
4. 平台侧只保存 dataset/document/chunk refs 和 safe snippet。
5. 正式核查时只把 MaxKB/RAGFlow 作为召回辅助，仍以平台 basis/master-data/evidence/human-decision 为准。
