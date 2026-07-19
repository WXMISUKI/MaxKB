# 前置平台组织结构与知识库绑定设计

## 1. 结论

我们需要数据库，而且数据库应属于前置核查平台，不应放在 MaxKB 或 OCR Worker 里。

原因：

- 公路工程资料核查要管理项目、合同段、标段、参建单位、分包队伍、人员、证照、审查任务、审查表、原件、版本和人工结论。
- MaxKB 的强项是知识库、文档、分段、向量、命中测试和应用工作流，不是公路工程业务事实管理。
- OCR Worker 的强项是异步 OCR、证照结构化、入库和命中验收，不应成为项目组织和审批状态的事实库。

推荐边界：

```text
前置平台数据库：正式事实
MaxKB：项目级检索副本
OCR Worker：provider 任务状态与 OCR 派生物
对象存储：原始文件、OCR 产物、报告资产
```

## 2. 市面与行业做法

从公开规范和案例看，公路工程资料管理通常不是简单按“文件夹”管理，而是围绕工程建设全过程、合同段、参建单位、施工/监理资料分类、分项工程和档案移交来组织。

可参考依据：

- 交通运输部《公路工程竣（交）工验收办法》要求项目建成后施工单位、监理单位、项目法人分别负责编制竣工文件、图表、资料，验收后还涉及档案资料移交。[交通运输部](https://xxgk.mot.gov.cn/jigou/glj/202006/t20200623_3312907.html)
- 《公路建设项目文件材料立卷归档管理办法》覆盖项目立项审批至竣工验收全过程，强调质量、进度、费用和安全管理资料的归档价值。[交通运输部](https://xxgk.mot.gov.cn/2020/jigou/bgt/202006/t20200623_3307217.html)
- 公路工程质量验收和质量评定体系强调单位工程、分部工程、分项工程等划分，资料与工程实体、施工任务和验收单元天然绑定。[交通运输部标准 PDF](https://xxgk.mot.gov.cn/jigou/glj/202204/P020220425579065328485.pdf)
- 施工和监理文件材料通常会区分开工前资料、开工后资料、试验、施检、质评、验收、开工类等类别，并按分项工程、分部工程、桩号或工程实体顺序整理。[新疆交通运输厅示例](https://jtyst.xinjiang.gov.cn/xjjtysj/zwgg/201511/88b8574a626548d7982a8f185034d5d3.shtml)
- 重庆高速电子档案案例强调统一数据格式、元数据标准、编码规则，并把档案管理与计量、质量、进度等建设过程管理结合。[重庆市交通运输委员会](https://jtj.cq.gov.cn/sy_240/bmdt/202501/t20250120_14187070.html)

对我们的启发：

- 必须有平台数据库保存组织结构和资料状态。
- 必须有统一 metadata，支持项目、合同段、标段、施工队伍、依据版本、资料类型和审查任务过滤。
- 知识库粒度可以先用“项目级逻辑知识库”，但资料必须带队伍和审查任务 metadata。
- 正式审查结论不能来自检索分数或模型回答。

## 3. 我们当前已有能力

### 3.1 MaxKB 已有能力

MaxKB 当前可通过 API 管理：

| 能力 | 说明 |
| --- | --- |
| 知识库 | 可创建项目级基础知识库 |
| 文件夹 | 可创建知识库文件夹或资源文件夹 |
| 文档 | 可上传文本、表格、QA、Web 等文档 |
| 分段 | 可预览和创建段落 |
| 向量检索 | 通过 pgvector 和全文索引进行召回 |
| 命中测试 | 可验证 query 是否命中文档 |
| `knowledge.meta` | 可保存 JSON 扩展信息 |

但 MaxKB 没有内建这些公路工程业务对象：

- 项目
- 合同段
- 标段
- 监理标段
- 施工/分包队伍
- 开工条件审查任务
- 施工方案审查任务
- 审查表状态
- 原始证据文件
- 人工审核结论

所以 MaxKB 可以被平台调用来创建知识库和上传资料，但不能作为这些业务对象的主数据库。

### 3.2 OCR Worker 已有能力

OCR Worker 当前可处理：

- `GET /health`
- `POST /api/preflight/ocr-ingestions`
- `GET /api/preflight/ocr-ingestions/{ingestionId}`
- `POST /api/preflight/ocr-ingestions/{ingestionId}/postprocess`
- `POST /api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge`
- `POST /api/preflight/ocr-ingestions/{ingestionId}/retrieval-check`

Worker 已支持：

- Bearer 鉴权
- 幂等创建
- correlationId
- allowed roots
- PaddleOCR-VL
- 证照后处理
- MaxKB 入库
- 命中验收

Worker 现在也支持接收以下组织 metadata：

- `organizationId`
- `projectId`
- `contractPackageId`
- `sectionId`
- `supervisionSectionId`
- `teamId`
- `subcontractTeamId`
- `reviewTaskId`
- `basisVersionId`
- `documentType`
- `sourceObjectId`
- `contentHash`
- `masterDataIds`
- `evidenceIds`
- `effectiveStatus`
- `effectiveDate`

## 4. 推荐数据库模型

### 4.1 Project

项目表。

| 字段 | 说明 |
| --- | --- |
| `id` | 平台项目 ID |
| `organization_id` | 组织 ID |
| `name` | 项目名称 |
| `code` | 项目编码 |
| `route_name` | 路线或工程名称 |
| `status` | `active` / `archived` |

### 4.2 ContractPackage

合同段或合同包。

| 字段 | 说明 |
| --- | --- |
| `id` | 合同段 ID |
| `project_id` | 所属项目 |
| `name` | 合同段名称 |
| `code` | 合同段编码 |
| `type` | `construction` / `supervision` / `design` / `test` |
| `status` | 状态 |

### 4.3 Section

施工标段、单位工程、分部/分项工程可逐步细化。第一阶段可以只建施工标段，后续再扩展工程划分树。

| 字段 | 说明 |
| --- | --- |
| `id` | 标段或工程划分 ID |
| `project_id` | 项目 ID |
| `contract_package_id` | 合同段 ID |
| `parent_id` | 上级工程划分 |
| `type` | `section` / `unit` / `division` / `subdivision` / `item` |
| `name` | 名称 |
| `stake_start` | 起点桩号 |
| `stake_end` | 终点桩号 |

### 4.4 SubcontractTeam

施工队伍或分包队伍。

| 字段 | 说明 |
| --- | --- |
| `id` | 队伍 ID |
| `project_id` | 项目 ID |
| `contract_package_id` | 合同段 ID |
| `section_id` | 负责标段或工程划分 |
| `name` | 队伍名称 |
| `company_name` | 企业名称 |
| `credit_code` | 统一社会信用代码 |
| `team_type` | `labor` / `professional_subcontract` / `supplier` |
| `status` | `active` / `suspended` / `exited` |

### 4.5 ReviewTask

审查任务。

| 字段 | 说明 |
| --- | --- |
| `id` | 审查任务 ID |
| `project_id` | 项目 ID |
| `contract_package_id` | 合同段 ID |
| `subcontract_team_id` | 队伍 ID |
| `task_type` | `opening_condition` / `construction_plan` |
| `basis_version_id` | 使用的依据版本 |
| `status` | `draft` / `submitted` / `reviewing` / `passed` / `rejected` / `supplement_required` |
| `created_by` | 创建人 |
| `submitted_at` | 提交时间 |

### 4.6 Evidence

原始资料或证据。

| 字段 | 说明 |
| --- | --- |
| `id` | 证据 ID |
| `review_task_id` | 审查任务 ID |
| `subcontract_team_id` | 队伍 ID |
| `document_type` | 资料类型 |
| `source_object_id` | 对象存储 ID |
| `source_uri` | 对象存储 URI |
| `file_name` | 原文件名 |
| `content_hash` | 内容 hash |
| `status` | `uploaded` / `ocr_processing` / `ready_for_review` / `rejected` |

### 4.7 KnowledgeBinding

平台知识库绑定表。

| 字段 | 说明 |
| --- | --- |
| `id` | 绑定 ID |
| `project_id` | 项目 ID |
| `contract_package_id` | 合同段 ID |
| `subcontract_team_id` | 可为空；为空表示项目级共享知识库 |
| `provider` | `maxkb` |
| `workspace_id` | MaxKB workspace |
| `knowledge_base_id` | MaxKB knowledge ID |
| `folder_id` | 可选 MaxKB folder |
| `grain` | `project` / `contract_package` / `team` |
| `sync_status` | `ready` / `provisional` / `stale` / `blocked` |
| `provider_refs` | JSON，保存 document/chunk/provider refs |

### 4.8 OcrIngestionLink

平台和 Worker 的任务映射。

| 字段 | 说明 |
| --- | --- |
| `id` | 平台映射 ID |
| `evidence_id` | 原始证据 ID |
| `worker_ingestion_id` | Worker 返回的 `ingestionId` |
| `idempotency_key` | 平台幂等键 |
| `correlation_id` | 审计关联 ID |
| `status` | Worker 状态快照 |
| `provider_job_id` | PaddleOCR job id |
| `provider_document_id` | MaxKB document id |
| `last_checked_at` | 最近同步时间 |

## 5. 推荐平台接口

这些接口属于前置平台，不属于 MaxKB，也不属于 OCR Worker。

### 5.1 创建项目

```http
POST /api/preflight/projects
```

```json
{
  "organizationId": "org-supervision-demo",
  "code": "NJDL",
  "name": "南江至东岭高速公路改扩建工程"
}
```

### 5.2 创建合同段

```http
POST /api/preflight/projects/{projectId}/contract-packages
```

```json
{
  "code": "JD-A1",
  "name": "JD-A1 监理合同段",
  "type": "supervision"
}
```

### 5.3 创建施工/分包队伍

```http
POST /api/preflight/projects/{projectId}/subcontract-teams
```

```json
{
  "contractPackageId": "contract-jd-a1",
  "sectionId": "section-lj",
  "name": "LJ-01 路基土石方分包作业队",
  "companyName": "上海旭日集团有限公司",
  "creditCode": "91310115515002x94",
  "teamType": "professional_subcontract"
}
```

### 5.4 创建审查任务

```http
POST /api/preflight/review-tasks
```

```json
{
  "projectId": "project-njdl-jd-a1",
  "contractPackageId": "contract-jd-a1",
  "subcontractTeamId": "team-lj-01",
  "taskType": "opening_condition",
  "basisVersionId": "basis-opening-condition-2026-07"
}
```

### 5.5 上传原始资料

```http
POST /api/preflight/review-tasks/{reviewTaskId}/evidence
```

返回平台 `evidenceId`、对象存储 `sourceObjectId`、`contentHash`。随后平台调用 OCR Worker。

### 5.6 创建或绑定 MaxKB 知识库

```http
POST /api/preflight/projects/{projectId}/knowledge-bindings
```

```json
{
  "provider": "maxkb",
  "grain": "project",
  "workspaceId": "default",
  "knowledgeBaseId": "019f787c-644e-7162-bfe5-f4ee02a91539"
}
```

第一阶段推荐 `grain=project`。如果后续权限或噪声要求更高，再创建 `grain=team`。

## 6. 知识库粒度设计

第一阶段建议：

```text
一个项目 = 一个逻辑知识库
队伍 / 合同段 / 审查任务 = metadata 过滤条件
```

原因：

- 监理通常围绕一个项目掌握合同依据、管理制度、审查口径。
- 同项目下多个队伍会共享项目依据，但证照、人员、设备、施工方案属于队伍或审查任务。
- 项目级知识库可以避免重复维护依据类资料。
- 队伍维度通过 metadata 和平台审查任务控制访问与检索范围。

升级条件：

- 多队伍资料互相干扰严重。
- 不同队伍权限隔离要求强。
- 项目资料量超过单知识库可控规模。
- MaxKB metadata 过滤能力不足以满足审查隔离。

升级后可改为：

```text
项目共享依据库 + 队伍资料库
```

或：

```text
合同段知识库 + 队伍 metadata 过滤
```

## 7. 数据流

```text
1. 平台创建 Project / ContractPackage / SubcontractTeam
2. 平台创建 ReviewTask
3. 平台上传 Evidence 原件到对象存储
4. 平台创建或复用 KnowledgeBinding
5. 平台调用 OCR Worker，传入 EvidenceMetadata
6. Worker 生成结构化 OCR 派生物
7. 平台确认后调用 Worker 入库 MaxKB
8. Worker 返回 provider refs
9. 平台保存 OcrIngestionLink 和 KnowledgeBinding.providerRefs
10. 审查时平台组合规则、人工确认和 MaxKB 支持性召回
```

## 8. 不建议的做法

- 不建议把一个施工队伍直接等同于一个 MaxKB workspace。
- 不建议把 MaxKB folder 当作项目/队伍主表。
- 不建议让 OCR Worker 创建项目、队伍和审查任务。
- 不建议只靠文件名区分队伍资料。
- 不建议把 OCR 结果直接当作证照真实性结论。
- 不建议在未完成平台数据库建模前进入自动审批工作流。

## 9. 下一步任务

1. 按本文设计在前置平台创建数据库表或等价业务模型。
2. 先实现项目、合同段、队伍、审查任务、证据和知识库绑定的 CRUD。
3. 使用 `preflight-platform-worker-call-guide.md` 进行 OCR Worker 联调。
4. 用真实安全生产许可证和人员证书验证 metadata 能否贯穿到 MaxKB 命中结果。
5. 联调稳定后再设计生产化队列、对象存储下载和 PostgreSQL Worker 状态表。

