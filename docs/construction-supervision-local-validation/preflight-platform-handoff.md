# 前置平台联调交接说明

本文面向开工条件核查前置平台团队，用于说明当前 MaxKB 知识库与 OCR Worker 侧已完成内容、系统职责边界、前置平台需要补齐的问题，以及建议的联调顺序。

更新时间：2026-07-20

## 1. 一句话结论

当前项目已经完成“MaxKB 项目级知识库 + 独立 OCR Worker”的本地闭环原型。下一步应由前置平台建立自己的业务数据库和接口，管理项目、合同段、标段、施工/分包队伍、审查任务、证据原件、人工结论和报告状态，再调用 OCR Worker 把扫描件资料结构化并写入 MaxKB 检索副本。

职责边界必须保持清晰：

```text
前置平台数据库：正式业务事实和审批状态
MaxKB：项目级知识库、文档、分段、向量和命中测试
OCR Worker：OCR、证照后处理、入库 MaxKB、检索命中验收
对象存储：原始资料、OCR 产物、报告附件
```

MaxKB 和 OCR Worker 都不应成为项目组织结构、施工队伍、审查任务或人工审批结论的事实库。

## 2. 当前已完成内容

### 2.1 MaxKB 本地知识库闭环

已完成：

- 明确知识库粒度：第一阶段采用“一个项目一个逻辑知识库”，合同段、队伍、审查任务通过 metadata 绑定。
- 已形成模拟资料包校验、上传计划、审查问题集和本地验证 runbook。
- 已支持通过 MaxKB API 创建或复用知识库、上传文本/表格资料，并进行命中测试。
- 已验证结构化证照资料可进入 MaxKB 并通过精确字段召回。

当前试点知识库：

| 项 | 值 |
| --- | --- |
| 知识库名称 | 南江至东岭高速公路改扩建工程 JD-A1 监理审查知识库 |
| MaxKB knowledgeId | `019f787c-644e-7162-bfe5-f4ee02a91539` |
| 推荐粒度 | `project` |

### 2.2 独立 FastAPI OCR Worker

服务目录：

```text
services/preflight-ocr-worker
```

已完成接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查和 provider readiness |
| `POST` | `/api/preflight/ocr-ingestions` | 注册资料并启动 OCR |
| `GET` | `/api/preflight/ocr-ingestions/{ingestionId}` | 查询 OCR/后处理/入库状态 |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/postprocess` | 重新执行证照后处理 |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge` | 确认入库 MaxKB |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/retrieval-check` | 执行命中验收 |

已完成能力：

- PaddleOCR-VL 异步 OCR 调用。
- 营业执照、安全生产许可证、人员证书结构化后处理框架。
- OCR 派生 Markdown、结构化 JSON/CSV、推荐入库 Markdown 产出。
- MaxKB 入库和精确字段命中验收。
- Bearer 鉴权：`PREFLIGHT_API_KEY`。
- 幂等创建：`Idempotency-Key`。
- 审计链路：`X-Correlation-ID`。
- 本地文件 allowed roots 校验。
- API 输出隐藏 provider token、内部解析路径和请求指纹。

### 2.3 已固化的资料 metadata

前置平台调用 OCR Worker 时，应把以下字段作为资料上下文传入：

| 字段 | 说明 |
| --- | --- |
| `organizationId` | 组织或企业标识 |
| `projectId` | 项目标识 |
| `projectName` | 项目名称 |
| `contractPackageId` | 合同段或合同包标识 |
| `sectionId` | 施工标段或工程划分标识 |
| `supervisionSectionId` | 监理标段标识 |
| `teamId` | 队伍标识 |
| `teamName` | 队伍名称 |
| `subcontractTeamId` | 分包队伍标识；第一阶段可与 `teamId` 一致 |
| `reviewTaskId` | 审查任务标识 |
| `basisVersionId` | 审查依据版本标识 |
| `documentType` | 资料类型，例如 `business_license` |
| `sourceObjectId` | 原始资料对象 ID |
| `sourceObjectType` | `pdf` / `image` / `office` / `url` |
| `sourceFileName` | 原始文件名 |
| `sourceFilePath` | 原始文件路径或对象存储地址 |
| `contentHash` | 原始资料内容 hash |
| `masterDataIds` | 关联主数据 ID 列表 |
| `evidenceIds` | 关联证据 ID 列表 |
| `effectiveStatus` | 有效状态 |
| `effectiveDate` | 生效日期 |

这些 metadata 会进入 OCR 后处理产物和 MaxKB 入库 Markdown，用于后续审查、过滤、追溯和证据链关联。

## 3. 前置平台必须解决的问题

### 3.1 必须建设业务数据库

前置平台需要成为业务事实 owner。建议最小表模型如下：

| 表 | 用途 |
| --- | --- |
| `Project` | 项目主表 |
| `ContractPackage` | 合同段、监理合同段、施工合同包 |
| `Section` | 标段、单位工程、分部/分项工程；第一阶段可只做到标段 |
| `SubcontractTeam` | 施工队伍或分包队伍 |
| `ReviewTask` | 开工条件审查、施工方案审查等任务 |
| `Evidence` | 原始资料和证据文件 |
| `KnowledgeBinding` | 前置平台对象与 MaxKB 知识库/文件夹/文档引用的绑定 |
| `OcrIngestionLink` | 前置平台证据与 OCR Worker 任务、PaddleOCR job、MaxKB document 的映射 |

第一阶段不要急着做自动审批。先把 CRUD、唯一键、状态流、provider refs 和审计字段打通。

### 3.2 必须提供前置平台接口

建议前置平台先实现这些接口，供业务页面、资料上传和 Worker 联调用：

| 接口 | 用途 |
| --- | --- |
| `POST /api/preflight/projects` | 创建项目 |
| `POST /api/preflight/projects/{projectId}/contract-packages` | 创建合同段 |
| `POST /api/preflight/projects/{projectId}/sections` | 创建施工标段或工程划分 |
| `POST /api/preflight/projects/{projectId}/subcontract-teams` | 创建施工/分包队伍 |
| `POST /api/preflight/review-tasks` | 创建审查任务 |
| `POST /api/preflight/review-tasks/{reviewTaskId}/evidence` | 上传原始资料 |
| `POST /api/preflight/projects/{projectId}/knowledge-bindings` | 创建或绑定 MaxKB 项目级知识库 |
| `POST /api/preflight/evidence/{evidenceId}/ocr-ingestions` | 由平台封装调用 OCR Worker |
| `GET /api/preflight/ocr-ingestion-links/{id}` | 查询 OCR/入库/命中验收状态 |

这些接口属于前置平台，不属于 MaxKB，也不属于 OCR Worker。

### 3.3 必须明确知识库绑定策略

第一阶段推荐：

```text
一个项目 = 一个 MaxKB 逻辑知识库
项目依据、合同依据、审查口径共享
施工/分包队伍资料通过 metadata 绑定到队伍和审查任务
```

后续只有在以下情况出现时，才升级为团队级知识库：

- 多队伍资料互相干扰严重。
- 权限隔离要求强。
- 单项目资料量超过项目级知识库可控规模。
- MaxKB metadata 过滤不能满足审查隔离。

可升级方案：

```text
项目共享依据库 + 队伍资料库
```

或：

```text
合同段知识库 + 队伍 metadata 过滤
```

### 3.4 必须管理正式审查状态

OCR 结果、结构化字段、MaxKB 检索命中、模型回答都只能作为支持性证据。正式审查结论必须由前置平台保存，并能追溯到：

- 原始证据文件。
- OCR 后处理产物。
- MaxKB document/provider refs。
- 命中验收结果。
- 审查依据版本。
- 人工审核人、审核时间、审核意见。

建议 `ReviewTask.status` 首版包含：

```text
draft
submitted
reviewing
supplement_required
passed
rejected
archived
```

建议 `Evidence.status` 首版包含：

```text
uploaded
ocr_processing
ocr_failed
ready_for_review
ingested
retrieval_checked
rejected
superseded
```

## 4. 推荐联调流程

### 4.1 前置条件

前置平台联调前，需要准备：

- MaxKB 本地或测试环境可访问。
- OCR Worker 可启动，默认本地端口 `8091`。
- PaddleOCR-VL token 通过环境变量注入。
- MaxKB 管理员账号密码通过环境变量注入。
- `PREFLIGHT_API_KEY` 由前置平台服务端安全保存。
- 原始 PDF/图片进入对象存储，或放入 Worker allowed roots 目录。

不要把任何 token、API key、MaxKB 密码写入代码仓库、前端配置或文档。

### 4.2 联调主链路

```text
1. 前置平台创建 Project / ContractPackage / Section / SubcontractTeam
2. 前置平台创建 ReviewTask
3. 前置平台上传 Evidence 原件并计算 contentHash
4. 前置平台创建或复用 KnowledgeBinding
5. 前置平台调用 OCR Worker 创建 ingestion
6. 前置平台轮询 Worker 状态
7. Worker 完成 OCR 和证照后处理
8. 前置平台确认是否允许入库
9. 前置平台调用 Worker 入库 MaxKB
10. 前置平台调用 Worker retrieval-check
11. 前置平台保存 OcrIngestionLink、provider refs、命中结果和审计事件
12. 审查页面展示支持性证据，由人工形成正式结论
```

### 4.3 Worker 调用关键约束

业务接口必须携带：

```http
Authorization: Bearer <PREFLIGHT_API_KEY>
```

创建 OCR 任务必须携带：

```http
Idempotency-Key: ocr:<projectId>:<reviewTaskId>:<sourceObjectId>:<contentHash>
X-Correlation-ID: <平台审计关联 ID>
```

幂等语义：

- 同 key、同请求：返回已有 `ingestionId`，不重复 OCR。
- 同 key、不同请求：返回 `409 Conflict`。
- 缺失或错误 Bearer：返回 `401`。
- Worker 未配置 `PREFLIGHT_API_KEY`：返回 `503`。

## 5. 当前未完成事项

这些事项应作为前置平台下一阶段任务，而不是继续在 MaxKB 或 OCR Worker 里堆业务逻辑：

1. 前置平台最小数据库模型和迁移脚本。
2. 项目、合同段、标段、施工/分包队伍、审查任务、证据、知识库绑定 CRUD。
3. 原始资料上传到对象存储，并生成 `sourceObjectId`、`sourceUri`、`contentHash`。
4. 平台封装 Worker 调用，不让浏览器直接持有 Worker API key。
5. 保存 Worker `ingestionId`、PaddleOCR `jobId`、MaxKB `providerDocumentId`。
6. 保存命中验收结果，不把命中结果当正式结论。
7. 用真实安全生产许可证和人员证书回归 OCR 结构化质量。
8. 设计设备合格证、检定证书等下一批资料类型的结构化规则。
9. 单机联调稳定后，再决定是否把 Worker 状态从 JSON 升级到 PostgreSQL，并把后台任务切到 Redis/Celery/RQ。

## 6. 不建议前置平台这样做

- 不建议把 MaxKB workspace 当成项目或队伍租户模型。
- 不建议把 MaxKB folder 当作项目、合同段、队伍主表。
- 不建议让 OCR Worker 创建项目、队伍、审查任务。
- 不建议只用文件夹或文件名区分施工队资料。
- 不建议让模型回答直接写入正式审批结论。
- 不建议在原始资料、审查依据版本、人工确认链路没有打通前做全自动审批。

## 7. 交接给前置平台的推荐任务拆分

### 任务组 A：平台事实库

- 建立 `Project`、`ContractPackage`、`Section`、`SubcontractTeam`、`ReviewTask`、`Evidence`、`KnowledgeBinding`、`OcrIngestionLink`。
- 明确唯一键，例如同项目下合同段编码唯一、同审查任务下证据 contentHash 可去重。
- 明确状态流和审计字段。

### 任务组 B：资料上传与对象存储

- 前端或平台服务上传原始文件。
- 平台服务写入 Evidence。
- 平台服务生成 `sourceObjectId`、`sourceUri`、`contentHash`。
- Worker 首轮可读本地 shared path；生产环境建议改为对象存储下载或签名 URL。

### 任务组 C：Worker 联调封装

- 平台服务端调用 `POST /api/preflight/ocr-ingestions`。
- 保存 `ingestionId`、`Idempotency-Key`、`X-Correlation-ID`。
- 轮询 Worker 状态并同步到 `OcrIngestionLink`。
- 支持失败重试和 `409` 幂等冲突处理。

### 任务组 D：MaxKB 知识库绑定

- 项目创建后创建或绑定 MaxKB 项目级知识库。
- 保存 `workspaceId`、`knowledgeBaseId`、可选 `folderId`。
- 入库完成后保存 `providerDocumentId`。

### 任务组 E：审查页面最小闭环

- 展示项目、队伍、审查任务、证据列表。
- 展示 OCR 结构化字段和原始文件入口。
- 展示 MaxKB 命中验收结果。
- 由人工填写审查意见和结论。

## 8. 相关文档入口

前置平台团队应优先阅读：

- `docs/preflight-maxkb-provider-integration.md`
- `docs/construction-supervision-local-validation/preflight-platform-worker-call-guide.md`
- `docs/construction-supervision-local-validation/preflight-organization-knowledge-design.md`
- `docs/construction-supervision-local-validation/preflight-ocr-ingestion-api-contract.md`
- `docs/construction-supervision-local-validation/runbook.md`
- `services/preflight-ocr-worker/README.md`

其中 `docs/preflight-maxkb-provider-integration.md` 是当前仓库内的平台侧 MaxKB provider 对接契约；其余路径来自前置平台或 OCR Worker 交接目录，如果当前工作区未包含这些文件，应以对应外部仓库为准。

## 9. 当前验收状态

最近一轮本地验证结果：

- Worker API 回归：12 项通过。
- Ruff：通过。
- Python 语法编译：通过。
- Git diff 空白检查：通过。
- 敏感 token 扫描：无命中。
- 测试缓存已清理。

该状态说明当前项目已经具备“前置平台联调”的基础，但还不具备“前置平台正式上线”的业务事实库、对象存储、持久任务队列和审查状态管理能力。
