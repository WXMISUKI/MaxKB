# 前置平台调用 OCR Worker 说明

本文面向开工条件核查前置平台，说明如何调用独立 FastAPI OCR Worker，把扫描件资料经 OCR、结构化后处理、MaxKB 入库和命中验收形成可检索证据副本。

## 1. 服务定位

调用链路：

```text
前置平台事实库
  -> OCR Worker
  -> PaddleOCR-VL
  -> 证照结构化后处理
  -> MaxKB 项目知识库
  -> 命中验收
```

边界：

- 前置平台管理项目、合同段、标段、施工/分包队伍、审查任务、原始证据、人工结论和报告。
- OCR Worker 管理 OCR 任务状态、后处理产物、MaxKB provider refs 和检索验收结果。
- MaxKB 管理知识库、文档、分段、向量和命中测试，只作为检索 provider。
- OCR 派生 Markdown、JSON、CSV 和检索结果是支持性证据，不替代原始文件和人工审查结论。

## 2. 环境变量

在 Worker 进程所在机器配置：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `PREFLIGHT_API_KEY` | 是 | 前置平台调用 Worker 的 Bearer 凭据 |
| `PREFLIGHT_ALLOWED_SOURCE_ROOTS` | 是 | 允许 Worker 读取的本地资料根目录，多个路径用系统路径分隔符 |
| `PREFLIGHT_STATE_FILE` | 否 | 单机原型 JSON 状态文件路径 |
| `PADDLEOCR_TOKEN` | 是 | PaddleOCR-VL token |
| `PADDLEOCR_JOB_URL` | 否 | 默认 `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` |
| `PADDLEOCR_MODEL` | 否 | 默认 `PaddleOCR-VL-1.6` |
| `MAXKB_BASE_URL` | 是 | 默认 `http://localhost:8080/admin/api` |
| `MAXKB_USERNAME` | 是 | 默认 `admin` |
| `MAXKB_PASSWORD` | 是 | MaxKB 管理员密码 |
| `MAXKB_WORKSPACE_ID` | 否 | 默认 `default` |
| `MAXKB_KNOWLEDGE_NAME` | 否 | 默认试点知识库名称 |

启动示例：

```powershell
$env:PREFLIGHT_ALLOWED_SOURCE_ROOTS = "D:\AI\知识库"
$env:PREFLIGHT_API_KEY = "<Worker API Key>"
$env:PADDLEOCR_TOKEN = "<PaddleOCR Token>"
$env:MAXKB_PASSWORD = "<MaxKB Password>"

uv run --project services\preflight-ocr-worker `
  uvicorn preflight_ocr_worker.main:app `
  --app-dir services\preflight-ocr-worker `
  --host 127.0.0.1 `
  --port 8091
```

## 3. 通用请求头

`GET /health` 不需要鉴权。其他业务接口必须携带：

```http
Authorization: Bearer <PREFLIGHT_API_KEY>
```

创建 OCR 任务必须额外携带：

```http
Idempotency-Key: <平台稳定幂等键>
X-Correlation-ID: <平台审计关联 ID>
```

建议幂等键格式：

```text
ocr:<projectId>:<reviewTaskId>:<sourceObjectId>:<contentHash>
```

规则：

- 同一个 `Idempotency-Key` + 同一个请求体：返回既有 `ingestionId`，不重复 OCR。
- 同一个 `Idempotency-Key` + 不同请求体：返回 `409 Conflict`。
- `X-Correlation-ID` 可省略；省略时 Worker 自动生成。
- 业务接口未带 Bearer 或凭据错误：返回 `401`。
- Worker 未配置 `PREFLIGHT_API_KEY`：返回 `503`。

## 4. 健康检查

```http
GET http://127.0.0.1:8091/health
```

成功示例：

```json
{
  "service": "preflight-ocr-worker",
  "ready": true,
  "status": "ready",
  "authentication": {
    "configured": true,
    "scheme": "bearer"
  },
  "capabilities": {
    "ocr": true,
    "certificatePostprocess": true,
    "knowledgeIngestion": true,
    "retrievalCheck": true,
    "idempotentSubmission": true,
    "correlationPropagation": true
  },
  "providers": {
    "paddleocr_vl": {
      "provider": "paddleocr_vl",
      "configured": true,
      "ready": true,
      "status": "ready",
      "model": "PaddleOCR-VL-1.6"
    },
    "maxkb": {
      "provider": "maxkb",
      "configured": true,
      "ready": true,
      "status": "ready",
      "workspaceId": "default"
    }
  }
}
```

联调门槛：

- `ready=true` 才进入真实 OCR。
- `ready=false` 时先看 `authentication`、`paddleocr_vl`、`maxkb` 哪一项未配置。
- 健康检查不返回 token、密码、私有 URL、原文或内部请求体。

## 5. 创建 OCR 入库任务

```http
POST /api/preflight/ocr-ingestions
```

请求体：

```json
{
  "metadata": {
    "organizationId": "org-supervision-demo",
    "projectId": "project-njdl-jd-a1",
    "projectName": "南江至东岭高速公路改扩建工程",
    "contractPackageId": "contract-jd-a1",
    "sectionId": "section-lj",
    "supervisionSectionId": "supervision-jd-a1",
    "teamId": "team-lj-01",
    "teamName": "LJ-01 路基土石方分包作业队",
    "subcontractTeamId": "team-lj-01",
    "reviewTaskId": "opening-condition-lj01",
    "basisVersionId": "basis-opening-condition-2026-07",
    "documentType": "business_license",
    "sourceObjectId": "evidence-001",
    "sourceObjectType": "pdf",
    "sourceFileName": "人员-营业执照.pdf",
    "sourceFilePath": "minio://preflight/project-njdl-jd-a1/evidence-001.pdf",
    "contentHash": "sha256:...",
    "masterDataIds": ["master-subcontract-team-lj01"],
    "evidenceIds": ["evidence-001"],
    "effectiveStatus": "current",
    "effectiveDate": "2026-07-19"
  },
  "source": {
    "mode": "local_path",
    "path": "D:\\AI\\知识库\\开工条件核查\\条件核查(1)\\人员-营业执照.pdf"
  },
  "ocr": {
    "provider": "paddleocr_vl",
    "model": "PaddleOCR-VL-1.6",
    "optionalPayload": {
      "useDocOrientationClassify": false,
      "useDocUnwarping": false,
      "useChartRecognition": false
    }
  },
  "runAsync": true
}
```

返回：

```json
{
  "ingestionId": "ocring_...",
  "correlationId": "review-task-opening-condition-lj01",
  "status": "ocr_pending",
  "metadata": {
    "projectId": "project-njdl-jd-a1",
    "teamId": "team-lj-01",
    "reviewTaskId": "opening-condition-lj01"
  },
  "history": [
    {
      "status": "registered",
      "at": "2026-07-19T..."
    },
    {
      "status": "ocr_pending",
      "at": "2026-07-19T..."
    }
  ]
}
```

注意：

- `source.mode=local_path` 时，`path` 必须位于 `PREFLIGHT_ALLOWED_SOURCE_ROOTS` 下。
- 正式平台建议先把原件上传到对象存储，再由 Worker 读取受控共享目录或后续改为对象存储下载。
- 当前 Worker 不返回内部 `resolvedSource` 和 `requestFingerprint`。

PowerShell 示例：

```powershell
$headers = @{
  Authorization = "Bearer $env:PREFLIGHT_API_KEY"
  "Idempotency-Key" = "ocr:project-njdl-jd-a1:opening-condition-lj01:evidence-001:sha256-demo"
  "X-Correlation-ID" = "review-task-opening-condition-lj01"
}

$body = @{
  metadata = @{
    organizationId = "org-supervision-demo"
    projectId = "project-njdl-jd-a1"
    projectName = "南江至东岭高速公路改扩建工程"
    contractPackageId = "contract-jd-a1"
    sectionId = "section-lj"
    supervisionSectionId = "supervision-jd-a1"
    teamId = "team-lj-01"
    subcontractTeamId = "team-lj-01"
    reviewTaskId = "opening-condition-lj01"
    basisVersionId = "basis-opening-condition-2026-07"
    documentType = "business_license"
    sourceObjectId = "evidence-001"
    sourceObjectType = "pdf"
    sourceFileName = "人员-营业执照.pdf"
    contentHash = "sha256:demo"
    evidenceIds = @("evidence-001")
  }
  source = @{
    mode = "local_path"
    path = "D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf"
  }
  runAsync = $true
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8091/api/preflight/ocr-ingestions" `
  -Headers $headers `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

Python 示例：

```python
import requests

base_url = "http://127.0.0.1:8091"
api_key = "<Worker API Key>"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Idempotency-Key": "ocr:project-njdl-jd-a1:opening-condition-lj01:evidence-001:sha256-demo",
    "X-Correlation-ID": "review-task-opening-condition-lj01",
}

payload = {
    "metadata": {
        "organizationId": "org-supervision-demo",
        "projectId": "project-njdl-jd-a1",
        "contractPackageId": "contract-jd-a1",
        "teamId": "team-lj-01",
        "subcontractTeamId": "team-lj-01",
        "reviewTaskId": "opening-condition-lj01",
        "basisVersionId": "basis-opening-condition-2026-07",
        "documentType": "business_license",
        "sourceObjectId": "evidence-001",
        "sourceObjectType": "pdf",
        "sourceFileName": "人员-营业执照.pdf",
    },
    "source": {
        "mode": "local_path",
        "path": r"D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf",
    },
    "runAsync": True,
}

response = requests.post(f"{base_url}/api/preflight/ocr-ingestions", json=payload, headers=headers, timeout=30)
response.raise_for_status()
print(response.json())
```

## 6. 查询任务状态

```http
GET /api/preflight/ocr-ingestions/{ingestionId}
```

状态流：

```text
registered
  -> ocr_pending
  -> ocr_running
  -> ocr_done
  -> postprocessed
  -> ready_for_ingest
  -> ingested
  -> retrieval_checked
```

失败时：

```text
failed
```

失败响应只返回安全摘要：

```json
{
  "status": "failed",
  "error": {
    "type": "ocr_pipeline_error",
    "summary": "provider request failed",
    "safeDiagnostics": {
      "exceptionType": "RuntimeError"
    }
  },
  "correlationId": "review-task-opening-condition-lj01"
}
```

## 7. 重新后处理

OCR 已完成但证照类型识别不准时可重新执行：

```http
POST /api/preflight/ocr-ingestions/{ingestionId}/postprocess
```

请求：

```json
{
  "certificateType": "safety_production_license"
}
```

支持值：

- `auto`
- `business_license`
- `safety_production_license`
- `personnel_certificate`

## 8. 确认入库 MaxKB

```http
POST /api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge
```

请求：

```json
{
  "provider": "maxkb",
  "workspaceId": "default",
  "knowledgeBaseId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "confirmPostprocessWarnings": true
}
```

规则：

- 只上传后处理生成的 `*-ingest.md`。
- 后处理存在 warnings 时，必须设置 `confirmPostprocessWarnings=true`。
- 返回的 `providerDocumentId` 是 MaxKB 文档引用，不是平台原始证据主键。

## 9. 命中验收

```http
POST /api/preflight/ocr-ingestions/{ingestionId}/retrieval-check
```

请求：

```json
{
  "searchMode": "keywords",
  "queries": [
    "上海旭日集团有限公司 统一社会信用代码 91310115515002x94",
    "法定代表人 林建华 正照编号 1200000202112250104"
  ],
  "expectedDocumentName": "business-license-ingest.md",
  "topNumber": 8,
  "similarity": 0.0
}
```

建议：

- 证照编号、统一社会信用代码、人员证书编号等精确字段优先用 `keywords`。
- 审查依据、方案措施、施工方法类问题再用 `blend`。
- 命中验收只判断“能否召回”，不判断资料是否合格。

## 10. 错误码

| HTTP 状态 | 场景 | 平台处理建议 |
| --- | --- | --- |
| `200` | 查询、后处理、入库或验收成功 | 更新平台任务状态 |
| `202` | 创建 OCR 任务成功或返回已有任务 | 保存 `ingestionId` |
| `400` | 请求字段错误、本地路径不存在、路径越权 | 标记资料待修正 |
| `401` | Bearer 凭据缺失或错误 | 检查平台服务端配置 |
| `404` | `ingestionId` 不存在 | 检查平台映射或重试策略 |
| `409` | `Idempotency-Key` 被不同请求复用 | 生成新的平台任务或修正调用方幂等键 |
| `422` | FastAPI 参数校验失败 | 检查 JSON、header 和字段名 |
| `503` | Worker API 鉴权未配置 | 先修复 Worker 部署配置 |

## 11. MaxKB 侧接口映射

当前 Worker 通过 MaxKB 管理 API 完成：

| 能力 | MaxKB API |
| --- | --- |
| 登录 | `POST /admin/api/user/login` |
| 知识库列表 | `GET /admin/api/workspace/{workspaceId}/knowledge` |
| 创建基础知识库 | `POST /admin/api/workspace/{workspaceId}/knowledge/base` |
| 文本分段预览 | `POST /admin/api/workspace/{workspaceId}/knowledge/{knowledgeId}/document/split` |
| 批量创建文档 | `POST /admin/api/workspace/{workspaceId}/knowledge/{knowledgeId}/document/batch_create` |
| 表格文档 | `POST /admin/api/workspace/{workspaceId}/knowledge/{knowledgeId}/document/table` |
| 命中测试 | `POST /admin/api/workspace/{workspaceId}/knowledge/{knowledgeId}/hit_test` |
| 文件夹 | `workspace/{workspaceId}/{source}/folder` |

这些接口可以创建知识库、文件夹、文档和检索副本，但不负责创建公路项目、合同段、施工队伍、审查任务、证据原件或人工结论。

## 12. 联调顺序

1. 前置平台创建项目、合同段、施工/分包队伍、审查任务和原始证据记录。
2. 前置平台创建或复用项目级 MaxKB 知识库，并保存 `knowledgeBaseId` 到平台知识库绑定表。
3. 前置平台把原始 PDF/图片放入对象存储或 Worker 可访问目录。
4. 前置平台调用 `POST /api/preflight/ocr-ingestions`。
5. 前置平台轮询 `GET /api/preflight/ocr-ingestions/{ingestionId}`。
6. 状态到 `ready_for_ingest` 后，由平台规则或人工确认是否入库。
7. 调用 `ingest-to-knowledge`。
8. 调用 `retrieval-check`。
9. 前置平台保存 provider refs、命中验收结果和审计事件。

## 13. 生产化注意事项

单机原型：

- JSON 状态文件只适合本地联调。
- 进程内 BackgroundTasks 只适合单实例。
- 本地路径适合 Windows 开发机，不适合多机部署。

生产建议：

- 平台事实库使用 PostgreSQL 或既有业务数据库。
- 原始文件和 OCR 产物进入对象存储。
- Worker 任务状态进入 PostgreSQL 或由平台任务表承接。
- 长任务切到 Redis/Celery/RQ 等持久队列。
- 保持本说明中的 API schema、状态语义、幂等键和 correlationId 不变。

