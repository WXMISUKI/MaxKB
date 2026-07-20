# 本地 MaxKB 知识库闭环验收 Runbook

## 1. 目标

在 Windows + Docker Desktop 环境中跑通：

1. MaxKB 启动
2. 模型 provider 配置
3. 项目级知识库创建
4. 模拟资料包上传
5. 开工条件审查和施工方案审查问答验证

本轮只验证现有能力，不立即做源码级深改。

## 2. 前置条件

- Docker Desktop 已启动，且使用 Linux containers
- 本机 `8080` 端口可用，或准备映射到其他端口
- 已准备可用 LLM provider，推荐先用 OpenAI-compatible 服务
- 已生成并校验模拟资料包

## 3. 资料包校验

运行：

```powershell
python docs\construction-supervision-local-validation\scripts\validate_pilot_dataset.py
```

脚本会生成：

- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/validation-report.json`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/validation-report.md`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/maxkb-upload-plan.csv`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/review-question-set.md`

只有 `validation-report.md` 中阻塞错误为 0 时，才进入 MaxKB 上传验证。

## 4. MaxKB 启动建议

优先使用官方容器启动 MaxKB。若本机 8080 未占用，可使用：

```powershell
docker run -d --name=maxkb --restart=always -p 8080:8080 -v C:/maxkb:/opt/maxkb registry.fit2cloud.com/maxkb/maxkb
```

默认登录信息以当前 MaxKB 镜像说明为准。首次启动需要等待数据库初始化、模型文件和服务进程就绪。

## 5. 知识库创建

建议创建知识库：

```text
南江至东岭高速公路改扩建工程 JD-A1 监理审查知识库
```

建议描述：

```text
用于验证 LJ-01 路基土石方分包作业队开工条件审查和 K12+000-K18+500 路基填筑施工方案审查。
```

上传顺序参考：

```text
00_manifest/maxkb-upload-plan.csv
```

## 6. 模型配置

第一阶段推荐：

- LLM：外部 OpenAI-compatible 服务
- Embedding：MaxKB 内置本地 embedding 或可用外部 embedding
- Rerank：可先关闭；如果召回噪声明显，再配置

不要第一轮就在 Windows 本机部署大模型。后续迁移到昇腾时，只替换模型服务 endpoint。

### 6.1 API 自动配置与上传

本地验证优先走 API，而不是人工模拟前端点击。当前脚本会：

- 登录本地 MaxKB
- 创建或复用 OpenAI-compatible LLM
- 创建或复用项目级知识库
- 按 `00_manifest/maxkb-upload-plan.csv` 上传资料包
- 输出 `00_manifest/maxkb-upload-result.csv`

在 PowerShell 中运行：

```powershell
$env:MIMO_API_KEY = "<你的 TokenPlan API Key>"
python docs\construction-supervision-local-validation\scripts\configure_and_upload_maxkb.py
Remove-Item Env:\MIMO_API_KEY
```

默认本地 MaxKB：

```text
URL: http://localhost:8080/admin/api
用户名：admin
密码：Admin123@
工作空间：default
LLM Provider：OpenAI
模型：mimo-v2.5-pro
API Base：https://token-plan-cn.xiaomimimo.com/v1
```

如果你修改过 MaxKB 管理员密码：

```powershell
$env:MAXKB_PASSWORD = "<当前 MaxKB 管理员密码>"
$env:MIMO_API_KEY = "<你的 TokenPlan API Key>"
python docs\construction-supervision-local-validation\scripts\configure_and_upload_maxkb.py
Remove-Item Env:\MAXKB_PASSWORD
Remove-Item Env:\MIMO_API_KEY
```

资料类型映射：

- `.docx` / 文本型 `.pdf`：文本文件，脚本使用 `document/split` 预览分段后再调用 `document/batch_create`
- `.xlsx`：表格，脚本调用 `document/table`
- QA 问答对：仅适用于 MaxKB QA 模板文件，本轮 29 份模拟资料包不需要走 QA 上传

扫描件 PDF 暂不直接进入 MaxKB 原生上传流。当前已具备 PaddleOCR-VL 的 endpoint、model 和 token 获取方式，先通过独立脚本完成 OCR 派生 Markdown 归档与可选入库；等本地链路稳定后，再决定是否把 PDF/OCR 入口产品化到前置审查平台或 MaxKB 插件层。

### 6.2 PaddleOCR-VL 扫描件入口

扫描件 PDF 或图片类资料先走 OCR 派生物归档，再选择性上传 MaxKB。

官方异步 API 约束：

- 参考文档：[PaddleOCR-VL 服务化部署调用示例及 API 介绍](https://ai.baidu.com/ai-doc/AISTUDIO/2mh4okm66)
- 单次请求最大支持 1000 页 PDF
- 文件 URL 最大 200 MB
- 本地文件上传最大 50 MB
- 提交任务：`POST /api/v2/ocr/jobs`
- 查询任务：`GET /api/v2/ocr/jobs/{jobId}`
- 完成后结果中包含 `resultUrl.jsonUrl` / `resultUrl.markdownUrl`

PowerShell 示例：

```powershell
$env:PADDLEOCR_TOKEN = "<你的 PaddleOCR Token>"
$env:PADDLEOCR_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
$env:PADDLEOCR_MODEL = "PaddleOCR-VL-1.6"

python docs\construction-supervision-local-validation\scripts\paddleocr_vl_ingest.py "D:\path\scanned.pdf"

Remove-Item Env:\PADDLEOCR_TOKEN
Remove-Item Env:\PADDLEOCR_JOB_URL
Remove-Item Env:\PADDLEOCR_MODEL
```

如果确认 OCR Markdown 内容可入库，再加 `--upload-to-maxkb`：

```powershell
$env:PADDLEOCR_TOKEN = "<你的 PaddleOCR Token>"
python docs\construction-supervision-local-validation\scripts\paddleocr_vl_ingest.py "D:\path\scanned.pdf" --upload-to-maxkb
Remove-Item Env:\PADDLEOCR_TOKEN
```

脚本会生成：

- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/00_ocr_outputs/<source>-<jobId>/page_*.md`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/00_ocr_outputs/<source>-<jobId>/<source>-ocr-derived.md`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/paddleocr-vl-result.json`

这些 Markdown 是 OCR 派生物，不替代原始证据文件。正式审查时仍应保留原始 PDF/图片对象引用。

上传后建议立即做 OCR 入库命中验收：

```powershell
python docs\construction-supervision-local-validation\scripts\validate_ocr_ingest_hit.py `
  --query "统一社会信用代码 91310115515002x94" `
  --query "营业执照 正照编号 1200000202112250104"
```

脚本会生成：

- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/paddleocr-vl-retrieval-check.csv`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/paddleocr-vl-retrieval-check.md`

验收重点是“OCR 派生文档能否被召回”，不是判断营业执照是否合格。

### 6.3 OCR 后处理与证照结构化

下一阶段优先方向建议：

1. OCR 证照结构化后处理：最能推进真实资料入库，直接服务前置核查平台上传入口。
2. 审查任务工作流原型：在资料可稳定召回后再做，避免工作流被脏数据拖偏。
3. 前置服务 API 合同适配：适合在 OCR/上传/命中验收稳定后，把脚本能力沉到服务接口。
4. UI 上传入口：等 API 合同稳定后再补，避免先做页面后改接口。

营业执照、人员证书、安全许可证等扫描件不建议把 OCR 原文直接作为最终入库文本。推荐先生成结构化派生物：

```powershell
python docs\construction-supervision-local-validation\scripts\postprocess_ocr_document.py `
  --source-markdown "D:\path\ocr-output\combined.md"
```

脚本默认使用 `--certificate-type auto` 自动识别证照类型。自动识别不足时可以显式指定：

```powershell
python docs\construction-supervision-local-validation\scripts\postprocess_ocr_document.py `
  --source-markdown "D:\path\ocr-output\combined.md" `
  --certificate-type safety_production_license

python docs\construction-supervision-local-validation\scripts\postprocess_ocr_document.py `
  --source-markdown "D:\path\ocr-output\combined.md" `
  --certificate-type personnel_certificate
```

如果要把结构化后的 Markdown 上传 MaxKB：

```powershell
python docs\construction-supervision-local-validation\scripts\postprocess_ocr_document.py `
  --source-markdown "D:\path\ocr-output\combined.md" `
  --project-id "project-njdl-jd-a1" `
  --team-id "team-lj-01" `
  --review-task-id "opening-condition-lj01" `
  --document-type "business_license" `
  --upload-to-maxkb
```

脚本会生成：

- `postprocessed/cleaned.md`
- `postprocessed/<certificate-type>-fields.json`
- `postprocessed/<certificate-type>-fields.csv`
- `postprocessed/<certificate-type>-ingest.md`
- `postprocessed/postprocess-report.md`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/paddleocr-vl-postprocess-result.json`

当前支持：

- `business_license`：营业执照，抽取统一社会信用代码、企业名称、类型、法定代表人、正照编号、登记日期和经营范围。
- `safety_production_license`：安全生产许可证，抽取许可证编号、企业名称、主要负责人、许可范围、有效期和发证机关。
- `personnel_certificate`：人员证书，抽取姓名、岗位、证书编号、发证机关、所属单位、有效期和到岗状态。

`*-ingest.md` 是推荐入库文件；它保留结构化字段、范围摘录、后处理告警和清洗后 OCR 原文。字段抽取只作为审查证据整理，不替代原件真实性核验。

证照编号、统一社会信用代码、人员证书编号等精确字段检索，建议验收时优先使用 `search_mode=keywords`；审查依据、方案条文、措施描述等语义问题再使用 `blend`。本地实测中，营业执照结构化文档在 `keywords` 模式下两个关键查询均排第 1。

推荐入库元数据字段：

| 字段 | 说明 |
| --- | --- |
| `organization_id` | 监理/企业组织标识 |
| `project_id` | 项目标识 |
| `project_name` | 项目名称 |
| `contract_package_id` | 合同段标识 |
| `section_id` | 施工标段或工程划分标识 |
| `supervision_section_id` | 监理标段标识 |
| `team_id` | 施工/分包队伍标识 |
| `team_name` | 施工/分包队伍名称 |
| `subcontract_team_id` | 分包队伍标识；第一阶段可与 `team_id` 保持一致 |
| `review_task_id` | 审查任务标识，例如 `opening-condition-lj01` |
| `basis_version_id` | 审查依据版本标识 |
| `document_type` | 资料类型，例如 `business_license`、`safety_production_license`、`personnel_certificate` |
| `source_object_id` | 前置平台或对象存储中的原始资料标识 |
| `source_object_type` | 原始资料类型，例如 `pdf`、`image`、`office`、`url` |
| `source_file_path` | 原始 PDF/图片路径或对象地址 |
| `content_hash` | 原始资料内容 hash |
| `master_data_ids` | 关联的平台主数据 ID 列表 |
| `evidence_ids` | 关联的平台证据 ID 列表 |
| `effective_status` | 资料有效状态，例如 `current`、`expired`、`superseded` |
| `effective_date` | 资料生效日期 |

这些字段会写入 `*-fields.json`、`*-fields.csv`、`*-ingest.md` 和 `postprocess-report.md`。后续前置服务 API 应把这些字段作为上传请求的一部分。

前置服务接口草案见：

- `docs/construction-supervision-local-validation/preflight-ocr-ingestion-api-contract.md`
- `docs/construction-supervision-local-validation/preflight-platform-worker-call-guide.md`
- `docs/construction-supervision-local-validation/preflight-organization-knowledge-design.md`
- `docs/construction-supervision-local-validation/preflight-platform-handoff.md`

### 6.4 独立 FastAPI OCR Worker

当前已将 OCR、证照后处理、MaxKB 入库和命中验收封装为独立 Worker，不修改 MaxKB Django 核心。

前置条件：

- Python 3.11
- MaxKB 已在 `http://localhost:8080` 运行
- PaddleOCR 和 MaxKB 凭据通过环境变量注入
- `PREFLIGHT_ALLOWED_SOURCE_ROOTS` 只配置允许 Worker 读取的资料目录

在仓库根目录启动：

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

服务入口：

- 健康检查：`http://127.0.0.1:8091/health`
- 前置平台健康检查别名：`http://127.0.0.1:8091/api/health`
- MaxKB provider 状态：`http://127.0.0.1:8091/api/knowledge-base/provider/status`
- MaxKB 检索代理：`http://127.0.0.1:8091/api/knowledge/{knowledgeId}/search`
- Swagger：`http://127.0.0.1:8091/docs`
- OpenAPI：`http://127.0.0.1:8091/openapi.json`

核心接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/api/preflight/ocr-ingestions` | 注册资料并启动 OCR |
| `GET` | `/api/preflight/ocr-ingestions/{ingestionId}` | 查询处理状态和安全结果 |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/postprocess` | 重新执行证照后处理 |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge` | 人工确认后上传 MaxKB |
| `POST` | `/api/preflight/ocr-ingestions/{ingestionId}/retrieval-check` | 执行精确字段命中验收 |

`PREFLIGHT_API_KEY`、`PADDLEOCR_TOKEN` 或 `MAXKB_PASSWORD` 未设置时，服务仍可启动用于检查，但
`/health` 返回 `degraded`。Worker 鉴权未配置时业务 API 返回 `503`；凭据错误返回 `401`。

平台调用业务 API：

```powershell
$headers = @{
  Authorization = "Bearer $env:PREFLIGHT_API_KEY"
  "Idempotency-Key" = "opening-condition:evidence-001:v1"
  "X-Correlation-ID" = "review-task-opening-condition-lj01"
}
```

创建任务时必须使用稳定 `Idempotency-Key`。同 key、同请求只返回已有任务；同 key、不同请求返回 `409`。
Worker 不会在 API 响应中返回 provider token、密码、内部请求指纹或 `resolved_source` 路径。

本地验证：

```powershell
uv run --project services\preflight-ocr-worker --extra test pytest
```

当前版本仍是单机原型：进程内 BackgroundTasks + 原子 JSON 状态文件。进入 Linux 多实例部署前，再替换为
PostgreSQL、Redis/Celery 和对象存储；API schema 与状态语义保持不变。

如果前置平台运行在另一台局域网电脑，例如前置平台电脑 `192.168.0.219`，本机 MaxKB/OCR Worker 电脑
`192.168.0.235`，则 Worker 启动时需要监听局域网地址：

```powershell
uv run --project services\preflight-ocr-worker `
  uvicorn preflight_ocr_worker.main:app `
  --app-dir services\preflight-ocr-worker `
  --host 0.0.0.0 `
  --port 8091
```

前置平台填写：

```env
KNOWLEDGE_PROVIDER=maxkb
MAXKB_ENABLED=true
MAXKB_BASE_URL=http://192.168.0.235:8091
MAXKB_API_KEY=<PREFLIGHT_API_KEY>
MAXKB_DEFAULT_KNOWLEDGE_ID=019f787c-644e-7162-bfe5-f4ee02a91539
MAXKB_TIMEOUT_MS=5000
MAXKB_HEALTH_PATH=/api/health
MAXKB_STATUS_PATH=/api/knowledge-base/provider/status
MAXKB_RETRIEVAL_PATH=/api/knowledge/:knowledgeId/search
```

前置平台不应填写 `http://127.0.0.1:8091`，除非它和 Worker 运行在同一台电脑。

前置平台联调时优先阅读：

- `docs/construction-supervision-local-validation/preflight-platform-handoff.md`
- `docs/construction-supervision-local-validation/preflight-platform-worker-call-guide.md`
- `docs/construction-supervision-local-validation/preflight-organization-knowledge-design.md`
- `docs/construction-supervision-local-validation/specs/preflight-platform-alignment/spec.md`
- `docs/construction-supervision-local-validation/specs/preflight-maxkb-provider-proxy/spec.md`

## 7. 验收问题

使用：

```text
00_manifest/review-question-set.md
```

每个问题记录：

- 是否召回正确资料
- 是否遗漏关键资料
- 是否召回其他队伍或其他审查任务资料
- 是否能标注来源
- 是否把支持性召回误写成正式结论

可先运行自动命中验收：

```powershell
python docs\construction-supervision-local-validation\scripts\validate_retrieval_hits.py
```

脚本会生成：

- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/retrieval-hit-validation.csv`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/retrieval-hit-validation.md`

默认策略：

- `search_mode=blend`
- `top_number=5`
- `similarity=0.1`
- 每题至少 3 条召回且最高相似度不低于 0.25 时标为 `pass`

`pass/review/fail` 只代表召回质量分级，不代表审查批准、退回或合格结论。

## 8. 进入源码改造的判断

只有出现以下问题，才进入源码级改造：

- MaxKB 无法稳定解析 `docx` / `xlsx`
- 无法实现项目 / 队伍 / 审查任务过滤
- 引用来源不足以支撑人工复核
- 工作流无法表达“支持性召回 + 人工确认”

否则下一阶段优先做工作流应用原型，而不是后端模型大改。
