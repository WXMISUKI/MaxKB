# MaxKB + OCR Worker + 前置平台联调 Quickstart

本文用于在本机 `192.168.0.235` 启动 MaxKB 和独立 OCR Worker，并让前置平台电脑 `192.168.0.219` 通过局域网调用。

注意：

- 不要把真实 `PADDLEOCR_TOKEN`、`PREFLIGHT_API_KEY`、MaxKB 管理员密码提交到仓库。
- 本文只写占位符。真实值在 PowerShell 当前会话中设置。
- 前置平台在另一台电脑上运行时，不能把 provider 地址写成 `127.0.0.1`。

## 1. 启动 MaxKB

如果容器不存在，执行：

```powershell
docker run -d `
  --name=maxkb `
  --restart=always `
  -p 8080:8080 `
  -v C:/maxkb:/opt/maxkb `
  registry.fit2cloud.com/maxkb/maxkb
```

如果提示容器名已存在，查看状态：

```powershell
docker ps -a --filter "name=maxkb"
```

如果已存在但未启动：

```powershell
docker start maxkb
```

启动日志：

```powershell
docker logs -f maxkb
```

本机访问：

```text
http://localhost:8080
```

本地默认管理员账号：

```text
用户名：admin
密码：Admin123@
```

## 2. 设置本机 Worker 环境变量

在仓库根目录 `D:\AI\AIcode\MaxKB` 打开 PowerShell，设置本次联调环境变量：

```powershell
$env:PREFLIGHT_API_KEY = "e500ad0e33f6561028df6db730b571d84e8abe9f2df368641ef5c73dcd0a2fe2"
$env:PADDLEOCR_TOKEN = "ee3aed324748722b37c741aa0215471a4e34f9fa"
$env:PADDLEOCR_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
$env:PADDLEOCR_MODEL = "PaddleOCR-VL-1.6"

$env:MAXKB_BASE_URL = "http://localhost:8080/admin/api"
$env:MAXKB_USERNAME = "admin"
$env:MAXKB_PASSWORD = "Admin123@"
$env:MAXKB_WORKSPACE_ID = "default"
$env:MAXKB_DEFAULT_KNOWLEDGE_ID = "019f787c-644e-7162-bfe5-f4ee02a91539"

$env:PREFLIGHT_ALLOWED_SOURCE_ROOTS = "D:\AI\知识库"
```

`PREFLIGHT_API_KEY` 由我们自己生成并提供给前置平台后端。前置平台把它配置为 `MAXKB_API_KEY`，浏览器不应接触这个值。

## 3. 启动 OCR Worker

让 Worker 监听局域网地址，供 `192.168.0.219` 调用：

```powershell
uv run --project services\preflight-ocr-worker `
  uvicorn preflight_ocr_worker.main:app `
  --app-dir services\preflight-ocr-worker `
  --host 0.0.0.0 `
  --port 8091
```

本机检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8091/api/health
```

局域网检查：

```powershell
Invoke-RestMethod http://192.168.0.235:8091/api/health
```

如果 `192.168.0.219` 访问失败，优先检查 Windows 防火墙是否放行 `8091`。

## 4. 前置平台配置

前置平台电脑 `192.168.0.219` 填写：

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

其中：

- `MAXKB_BASE_URL` 指向本机 OCR Worker proxy，不是 MaxKB 容器地址。
- `MAXKB_API_KEY` 使用本机 Worker 的 `PREFLIGHT_API_KEY`。
- 前置平台不得使用 MaxKB 管理员账号密码。

## 5. Provider 状态测试

在前置平台电脑或本机执行：

```powershell
$headers = @{ Authorization = "Bearer <PREFLIGHT_API_KEY>" }
Invoke-RestMethod `
  -Uri "http://192.168.0.235:8091/api/knowledge-base/provider/status" `
  -Headers $headers
```

期望返回：

```json
{
  "provider": "maxkb",
  "ready": true,
  "status": "ready",
  "workspaceId": "default",
  "defaultKnowledgeId": "019f787c-644e-7162-bfe5-f4ee02a91539"
}
```

## 6. MaxKB 检索代理测试

```powershell
$headers = @{ Authorization = "Bearer <PREFLIGHT_API_KEY>" }
$body = @{
  queryText = "统一社会信用代码"
  searchMode = "keywords"
  topNumber = 8
  similarity = 0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://192.168.0.235:8091/api/knowledge/019f787c-644e-7162-bfe5-f4ee02a91539/search" `
  -Headers $headers `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

检索结果只作为支持性召回，不代表正式审查结论。

## 7. OCR 入库链路

OCR 入库仍使用 Worker 的前置接口：

```text
POST /api/preflight/ocr-ingestions
GET  /api/preflight/ocr-ingestions/{ingestionId}
POST /api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge
POST /api/preflight/ocr-ingestions/{ingestionId}/retrieval-check
```

创建 OCR 任务时必须带：

```http
Authorization: Bearer <PREFLIGHT_API_KEY>
Idempotency-Key: ocr:<projectId>:<reviewTaskId>:<sourceObjectId>:<contentHash>
X-Correlation-ID: <platform-correlation-id>
```

## 8. 关闭本次 PowerShell 会话中的密钥

联调结束后可清理当前会话环境变量：

```powershell
Remove-Item Env:\PREFLIGHT_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\PADDLEOCR_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:\PADDLEOCR_JOB_URL -ErrorAction SilentlyContinue
Remove-Item Env:\PADDLEOCR_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_USERNAME -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_PASSWORD -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_WORKSPACE_ID -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_DEFAULT_KNOWLEDGE_ID -ErrorAction SilentlyContinue
Remove-Item Env:\PREFLIGHT_ALLOWED_SOURCE_ROOTS -ErrorAction SilentlyContinue
```

