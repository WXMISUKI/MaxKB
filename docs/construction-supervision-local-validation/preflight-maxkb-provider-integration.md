# MaxKB Provider Integration for Preflight Review

更新时间：2026-07-20

## 目标定位

MaxKB 是开工条件核查前置平台的外部知识库 provider，用于保存项目级检索副本、文档分段、向量索引和命中验收结果。平台仍然拥有项目、合同段、标段、施工/分包队伍、审查任务、证据原件、人工结论、审查状态和报告资产。

```text
Platform facts
  Project / ContractPackage / Section / SubcontractTeam
  ReviewTask / Evidence / KnowledgeBinding / OcrIngestionLink
  BasisVersion / MasterData / HumanDecision / ReportAsset

MaxKB provider support
  knowledgeId / documentId / chunkId
  safe snippet / locator / score
  retrieval-check result
  sync status
```

MaxKB 命中结果只能作为支持性证据召回，不得直接写入正式通过、驳回或补正结论。

## 服务端配置

平台后端通过 `KNOWLEDGE_PROVIDER` 选择知识库 provider。

```env
KNOWLEDGE_PROVIDER=maxkb
MAXKB_ENABLED=true
MAXKB_BASE_URL=http://192.168.0.219:8091
MAXKB_API_KEY=<PREFLIGHT_API_KEY>
MAXKB_DEFAULT_KNOWLEDGE_ID=019f787c-644e-7162-bfe5-f4ee02a91539
MAXKB_TIMEOUT_MS=5000
```

本地局域网联调时，`192.168.0.219` 是 MaxKB/OCR Worker 所在电脑，`8091` 是 OCR Worker 代理端口。前置项目电脑为
`192.168.0.219` 时不能把 `MAXKB_BASE_URL` 写成 `http://127.0.0.1:8091`，否则会指向前置项目自己的电脑。

当前 MaxKB 部署只有管理员账号密码，没有独立 provider API key。本项目已在 OCR Worker 侧补充 MaxKB provider proxy：

- 前置平台使用 `MAXKB_API_KEY=<PREFLIGHT_API_KEY>` 调用 Worker。
- Worker 使用服务端 `MAXKB_USERNAME` / `MAXKB_PASSWORD` 登录 MaxKB 并换取内部 token。
- MaxKB 管理员密码、内部 token、provider trace 不返回给前置平台和浏览器。

可覆盖路径：

```env
MAXKB_HEALTH_PATH=/api/health
MAXKB_STATUS_PATH=/api/knowledge-base/provider/status
MAXKB_RETRIEVAL_PATH=/api/knowledge/:knowledgeId/search
```

当前 Worker proxy 首批只提供 readiness 和检索代理。知识库创建、文档入库、OCR 入库仍通过 OCR Worker 的
`/api/preflight/ocr-ingestions/*` 链路完成。

## KnowledgeBinding

第一阶段推荐一个项目绑定一个 MaxKB 逻辑知识库。

平台应保存：

| 字段 | 说明 |
| --- | --- |
| `id` | 平台知识库绑定 ID |
| `workspaceId` | 平台工作区 ID |
| `projectId` | 项目 ID |
| `organizationId` | 组织或企业 ID |
| `contractPackageId` | 合同段或合同包 ID |
| `subcontractTeamId` | 分包队伍 ID；第一阶段可与 teamId 一致 |
| `provider` | `maxkb` |
| `knowledgeId` | MaxKB 项目级知识库 ID |
| `syncStatus` | `ready` / `provisional` / `stale` / `unreachable` / `disabled` |
| `lastSyncedAt` | 最近同步时间 |
| `summary` | 安全摘要 |

平台不得把 MaxKB workspace、folder 或 document 当作项目、队伍、审查任务主表。

## Evidence 到 MaxKB 的链路

推荐链路：

```text
Evidence uploaded
  -> platform stores sourceObjectId/sourceUri/contentHash
  -> platform calls OCR Worker with metadata
  -> OCR Worker performs OCR and postprocess
  -> platform approves ingestion
  -> OCR Worker ingests safe Markdown/CSV/JSON summary to MaxKB
  -> OCR Worker returns providerDocumentId/retrieval-check
  -> platform stores OcrIngestionLink and audit event
```

平台调用 OCR Worker 时必须携带：

```http
Authorization: Bearer <PREFLIGHT_API_KEY>
Idempotency-Key: ocr:<projectId>:<reviewTaskId>:<sourceObjectId>:<contentHash>
X-Correlation-ID: <platform-correlation-id>
```

## Metadata Contract

入库 MaxKB 的 OCR 派生产物必须携带平台 metadata，便于检索过滤、追溯和审计。

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `organizationId` | 是 | 组织或企业标识 |
| `projectId` | 是 | 项目标识 |
| `projectName` | 是 | 项目名称 |
| `contractPackageId` | 是 | 合同段或合同包 |
| `sectionId` | 建议 | 标段或工程划分 |
| `supervisionSectionId` | 建议 | 监理标段 |
| `teamId` | 建议 | 施工队伍 |
| `teamName` | 建议 | 队伍名称 |
| `subcontractTeamId` | 是 | 分包队伍 |
| `reviewTaskId` | 是 | 审查任务 |
| `basisVersionId` | 是 | 审查依据版本 |
| `documentType` | 是 | 资料类型 |
| `sourceObjectId` | 是 | 原始证据对象 ID |
| `sourceObjectType` | 是 | `pdf` / `image` / `office` / `url` |
| `sourceFileName` | 是 | 原始文件名 |
| `contentHash` | 是 | 原始资料 hash |
| `masterDataIds` | 建议 | 关联主数据 |
| `evidenceIds` | 建议 | 关联证据 |
| `effectiveStatus` | 建议 | 有效状态 |
| `effectiveDate` | 建议 | 生效日期 |

## Provider Refs

平台保存的 MaxKB provider ref 应保持安全、短小、可追溯：

```json
{
  "provider": "maxkb",
  "id": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "datasetId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "knowledgeId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "documentId": "doc-1",
  "chunkId": "chunk-1",
  "syncStatus": "ready",
  "summary": "安全生产许可证 OCR 入库摘要",
  "lastSyncedAt": "2026-07-20T00:00:00.000Z"
}
```

不得保存：

- API key、密码、Authorization header。
- 原始全文、完整 OCR raw text、provider trace。
- 私有文件 URL 或预签名 URL。
- 未截断的大模型 prompt 或模型回答。

## Retrieval Usage Policy

MaxKB retrieval hit 只能进入支持证据层：

```json
{
  "provider": "maxkb",
  "providerDatasetId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "knowledgeId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "providerDocumentId": "doc-1",
  "providerChunkId": "chunk-1",
  "score": 0.87,
  "title": "安全生产许可证",
  "safeSnippet": "安全生产许可证有效期应与平台主数据一致。",
  "locator": "安全生产许可证.pdf 第 1 页",
  "sourceObjectId": "source-1",
  "masterDataIds": ["md-license-1"],
  "evidenceIds": ["ev-1"]
}
```

正式审查结论必须继续由平台的 `BasisVersion`、`MasterData`、`Evidence`、`HumanDecision` 和 `ReviewTask` 状态决定。MaxKB 命中与平台事实冲突时，平台事实优先，冲突项进入人工复核说明。

## Readiness and Status

平台后端提供：

- `GET /api/health`
- `GET /api/knowledge-base/provider/status`

MaxKB readiness 可能状态：

| 状态 | 含义 |
| --- | --- |
| `ready` | MaxKB 已配置并健康检查通过 |
| `degraded` | 已启用但配置缺失、超时或健康检查失败 |
| `disabled` | 未启用 |
| `provisional` | 已绑定但同步状态尚未确认 |
| `stale` | 已绑定但资料过期，需要重新入库或验收 |
| `unreachable` | provider 不可达 |

`ready` 只代表知识库支持能力可用，不代表资料已自动通过审查。

## 下一阶段任务

1. 在平台侧实现 `KnowledgeBinding` 与 `OcrIngestionLink` 的正式持久化。
2. 平台服务端封装 OCR Worker 调用，浏览器不得直接持有 Worker key。
3. 将 Evidence 原件、OCR 产物、MaxKB provider refs 和 retrieval-check 结果串成审计链。
4. 审查页面展示 MaxKB 命中作为支持证据，并由人工形成正式结论。
