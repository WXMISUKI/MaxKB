# Preflight OCR Worker

独立 FastAPI Worker，用于：

- 提交 PaddleOCR-VL 扫描件任务
- 生成 OCR 归档
- 执行营业执照、安全生产许可证、人员证书结构化后处理
- 将结构化 `*-ingest.md` 上传 MaxKB
- 执行精确字段命中验收

## 本地启动

Worker 使用独立 Python 3.11 依赖，不依赖 MaxKB Django 运行环境。在仓库根目录执行：

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

`PREFLIGHT_API_KEY`、`PADDLEOCR_TOKEN` 或 `MAXKB_PASSWORD` 缺失时，服务仍可启动，但 `/health` 返回
`degraded`。`PREFLIGHT_API_KEY` 缺失时业务 API 返回 `503`。

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8091/health
```

API 文档：

```text
http://127.0.0.1:8091/docs
```

## 关键环境变量

| 环境变量 | 默认值 / 说明 |
| --- | --- |
| `PREFLIGHT_PROJECT_ROOT` | 自动解析当前 MaxKB 仓库根目录 |
| `PREFLIGHT_STATE_FILE` | `var/preflight-ocr-worker/state.json` |
| `PREFLIGHT_ALLOWED_SOURCE_ROOTS` | 默认只允许项目根目录，多个路径用系统路径分隔符 |
| `PREFLIGHT_API_KEY` | 必填，前置平台调用 Worker 的 Bearer 凭据 |
| `PADDLEOCR_TOKEN` | 必填，PaddleOCR-VL token |
| `PADDLEOCR_JOB_URL` | PaddleOCR-VL jobs endpoint |
| `PADDLEOCR_MODEL` | 默认 `PaddleOCR-VL-1.6` |
| `MAXKB_BASE_URL` | 默认 `http://localhost:8080/admin/api` |
| `MAXKB_USERNAME` | 默认 `admin` |
| `MAXKB_PASSWORD` | 必填，MaxKB 管理员密码，无默认值 |
| `MAXKB_WORKSPACE_ID` | 默认 `default` |
| `MAXKB_KNOWLEDGE_NAME` | 默认试点知识库名称 |
| `MAXKB_DEFAULT_KNOWLEDGE_ID` | 可选，默认项目级知识库 ID |

## 平台调用约束

除 `/health` 外，业务 API 必须携带：

```http
Authorization: Bearer <PREFLIGHT_API_KEY>
```

创建 OCR 任务还必须携带：

```http
Idempotency-Key: <平台稳定任务键>
X-Correlation-ID: <平台审计关联标识>
```

`X-Correlation-ID` 可省略，Worker 会自动生成。`Idempotency-Key` 不可省略：

- 同 key、同请求：返回已有任务，不重复启动 OCR。
- 同 key、不同请求：返回 `409`。
- Worker 鉴权未配置：返回 `503`。
- Bearer 凭据错误：返回 `401`。

## 给前置平台的 MaxKB Provider 配置

本地局域网联调时，前置平台电脑 `192.168.0.219` 应通过本机 Worker proxy 访问 MaxKB 支持能力。本机 IP 为
`192.168.0.235`，Worker 默认端口为 `8091`：

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

注意：`MAXKB_BASE_URL` 只有在前置平台服务也运行在本机时才可以写 `http://127.0.0.1:8091`。前置平台运行在
`192.168.0.219` 时，`127.0.0.1` 会指向前置平台自己的电脑。

Worker proxy 提供：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/health` | 前置平台风格健康检查别名 |
| `GET` | `/api/knowledge-base/provider/status` | MaxKB provider readiness 安全摘要 |
| `POST` | `/api/knowledge/{knowledgeId}/search` | MaxKB hit-test 安全检索代理 |

检索代理只返回安全 hit 摘要；正式审查结论仍由前置平台保存。

## 测试

```powershell
uv run --project services\preflight-ocr-worker --extra test pytest
```

正式验证使用 Python 3.11。当前锁定并验证的核心组合为 FastAPI `0.115.0`、Pydantic `2.10.6`。

## 当前边界

当前版本是单机原型：

- 使用进程内后台任务
- 使用原子 JSON 状态文件
- 复用仓库现有 OCR / 后处理 / MaxKB 脚本

进入多实例或生产部署前，应替换为 PostgreSQL、Redis/Celery 和对象存储，但保持 API schema 与状态语义稳定。
