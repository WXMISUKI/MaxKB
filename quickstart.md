# MaxKB + OCR Worker + 前置平台联调 Quickstart

本文用于在本机 `192.168.0.219` 启动 MaxKB 和独立 OCR Worker，并让前置平台电脑 `192.168.0.219` 通过局域网调用。

注意：

- 不要把真实 `PADDLEOCR_TOKEN`、`PREFLIGHT_API_KEY`、MaxKB 管理员密码提交到仓库。
- 本文只写占位符。真实值在 PowerShell 当前会话中设置。
- 前置平台在另一台电脑上运行时，不能把 provider 地址写成 `127.0.0.1`。

## 1. 启动 MaxKB

### 1.1 推荐：Compose 同时启动 MaxKB + OCR Worker

官方 MaxKB 镜像端口 `8080`，Worker 端口 `8091`。密钥放在本机 `.env.docker.local`（已 gitignore），不要提交仓库。

```powershell
# 首次：准备目录与本地密钥
New-Item -ItemType Directory -Force -Path C:\maxkb, C:\maxkb-data\sources | Out-Null
Copy-Item .env.docker.local.example .env.docker.local
# 编辑 .env.docker.local，填入 PREFLIGHT_API_KEY / PADDLEOCR_TOKEN / MAXKB_PASSWORD

docker compose -f docker-compose.preflight.yml --env-file .env.docker.local up -d --build
docker compose -f docker-compose.preflight.yml ps
docker logs -f maxkb
```

本机检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8091/api/health
Invoke-RestMethod http://127.0.0.1:8091/health
```

停止：

```powershell
docker compose -f docker-compose.preflight.yml down
```

### 1.2 仅 MaxKB 官方容器

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
密码：MaxKB@123..
```

## 2. 设置本机 Worker 环境变量

> 若已用 `docker-compose.preflight.yml` 启动 Worker，可跳过本节与第 3 节的宿主机 `uv` 启动，密钥以 `.env.docker.local` 为准。

在仓库根目录打开 PowerShell，设置本次联调环境变量：

```powershell
$env:PREFLIGHT_API_KEY = "e500ad0e33f6561028df6db730b571d84e8abe9f2df368641ef5c73dcd0a2fe2"
$env:PADDLEOCR_TOKEN = "ee3aed324748722b37c741aa0215471a4e34f9fa"
$env:PADDLEOCR_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
$env:PADDLEOCR_MODEL = "PaddleOCR-VL-1.6"

$env:MAXKB_BASE_URL = "http://localhost:8080/admin/api"
$env:MAXKB_USERNAME = "admin"
$env:MAXKB_PASSWORD = "MaxKB@123.."
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
Invoke-RestMethod http://192.168.0.219:8091/api/health
```

如果 `<HOST_IP>` 访问失败，优先检查 Windows 防火墙是否放行 `8091`。

## 3.1 启动安全监管知识网关（8092）

如果要让安管后端直接调用“上传存储文件 + RAG 检索”接口，需要额外启动安全监管知识网关：

```text
http://127.0.0.1:8092
```

说明：

- 当前 `8092` 网关默认是直接在宿主机用 `python -m uvicorn` 启动，因此 `docker ps` 里看不到对应容器或镜像
- 当前仓库里没有为 `services/safety-platform-kb-gateway/` 单独提供 Dockerfile
- 也就是说：**现在能跑，但当前默认不是 Docker 部署**
- 如果后续要部署到服务器，建议再补该服务专用 Dockerfile 和 compose 配置

当前这套本机 MaxKB 运行态，`admin` 账户在 `/admin/api/user/profile` 中只暴露 `default` workspace。

因此本地联调请使用：

- `MAXKB_WORKSPACE_ID=default`
- `MAXKB_TEAM_KB_PREFIX=safety-team`

也就是用“默认 workspace + 安管专属知识库前缀”完成本地隔离；等后续 MaxKB 侧具备额外 workspace 权限能力后，再切回 `safety_platform`。

先查询一个可用的 embedding 模型 id：

```powershell
docker exec -w /opt/maxkb-app maxkb python apps/manage.py shell -c "from models_provider.models.model_management import Model; m=Model.objects.filter(model_type='EMBEDDING').first(); print(getattr(m,'id',''))"
```

在仓库根目录打开新的 PowerShell，设置网关环境变量并启动：

```powershell
$env:GATEWAY_API_KEY = "replace-with-safety-platform-bearer-token"
$env:GATEWAY_PORT = "8092"
$env:MAXKB_BASE_URL = "http://127.0.0.1:8080/admin/api"
$env:MAXKB_USERNAME = "admin"
$env:MAXKB_PASSWORD = "MaxKB@123.."
$env:MAXKB_WORKSPACE_ID = "default"
$env:MAXKB_TEAM_KB_PREFIX = "safety-team"
$env:MAXKB_DEFAULT_EMBEDDING_MODEL_ID = "replace-with-embedding-model-id"
$env:REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE = "true"

python -m uvicorn safety_platform_kb_gateway.main:app `
  --app-dir services/safety-platform-kb-gateway `
  --host 0.0.0.0 `
  --port 8092
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8092/health
```

最小联调验证：

```powershell
$headers = @{ Authorization = "Bearer $env:GATEWAY_API_KEY" }

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8092/api/teams/team-demo-001/knowledge-base" `
  -Headers $headers
```

PowerShell 5 不支持 `Invoke-RestMethod -Form`，如果需要本机手工验证上传，请改用 `curl.exe`：

```powershell
curl.exe -s -X POST "http://127.0.0.1:8092/api/teams/team-demo-001/documents" `
  -H "Authorization: Bearer $env:GATEWAY_API_KEY" `
  -F "file=@C:\path\to\demo.txt" `
  -F "teamName=LJ-01 路基土石方分包作业队" `
  -F "projectName=南江至东岭高速公路改扩建工程" `
  -F "documentType=business_license" `
  -F "scope=team_private" `
  -F "projectId=project-demo-001" `
  -F "sourceTable=biz_work_team" `
  -F "sourceObjectId=team-demo-001"
```

检索验证：

```powershell
$headers = @{
  Authorization = "Bearer $env:GATEWAY_API_KEY"
  "Content-Type" = "application/json"
}

$body = @{
  query = "统一社会信用代码 91310115515002X94"
  searchMode = "blend"
  topK = 5
  similarity = 0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8092/api/teams/team-demo-001/search" `
  -Headers $headers `
  -Body $body
```

给安管后端同学的交付材料：

- `.env` 示例：[docs/safety-platform-kb-gateway/backend-env-example.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/backend-env-example.md)
- 联调清单：[docs/safety-platform-kb-gateway/backend-joint-debug-checklist.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/backend-joint-debug-checklist.md)

## 4. 前置平台配置

文档中的 `<HOST_IP>` 请替换为运行 `preflight-ocr-worker` 的宿主机 IP（同机调用也可用 `127.0.0.1`）。

前置平台电脑 `<HOST_IP>` 填写：

```env
KNOWLEDGE_PROVIDER=maxkb
MAXKB_ENABLED=true
MAXKB_BASE_URL=http://<HOST_IP>:8091
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
  -Uri "http://<HOST_IP>:8091/api/knowledge-base/provider/status" `
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
  -Uri "http://<HOST_IP>:8091/api/knowledge/019f787c-644e-7162-bfe5-f4ee02a91539/search" `
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
Remove-Item Env:\GATEWAY_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GATEWAY_PORT -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_TEAM_KB_PREFIX -ErrorAction SilentlyContinue
Remove-Item Env:\MAXKB_DEFAULT_EMBEDDING_MODEL_ID -ErrorAction SilentlyContinue
Remove-Item Env:\REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE -ErrorAction SilentlyContinue
```

