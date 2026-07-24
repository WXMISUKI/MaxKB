# 安全监管平台知识网关运行说明

## 1. 服务位置

服务目录：

`services/safety-platform-kb-gateway/`

首版服务默认监听：

`8092`

## 2. 环境变量

启动前至少设置以下变量：

```powershell
$env:GATEWAY_API_KEY = "replace-with-platform-bearer-token"
$env:GATEWAY_PORT = "8092"
$env:MAXKB_BASE_URL = "http://localhost:8080/admin/api"
$env:MAXKB_USERNAME = "admin"
$env:MAXKB_PASSWORD = "replace-with-maxkb-password"
$env:MAXKB_WORKSPACE_ID = "default"
```

如果你已经明确要固定 embedding 模型，也可以补充：

```powershell
$env:MAXKB_DEFAULT_EMBEDDING_MODEL_ID = "embedding-model-id"
```

## 3. 启动方式

在仓库根目录执行：

```powershell
uvicorn safety_platform_kb_gateway.main:app --app-dir services/safety-platform-kb-gateway --host 0.0.0.0 --port 8092
```

## 4. 健康检查

匿名健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8092/health
```

返回重点看：

- `ready`
- `authentication.configured`
- `providers.maxkb.ready`

## 5. 平台后端接入顺序

推荐调用顺序：

1. 平台后端创建或更新一个队伍
2. 平台后端上传队伍资料时，调用：
   `POST /api/teams/{teamId}/documents`
3. 平台后端查询队伍知识库状态时，调用：
   `GET /api/teams/{teamId}/knowledge-base`
4. 平台后端检索队伍资料时，调用：
   `POST /api/teams/{teamId}/search`
5. 精确字段检索时，调用：
   `POST /api/teams/{teamId}/search/field`

## 6. 上传示例

```powershell
$headers = @{ Authorization = "Bearer $env:GATEWAY_API_KEY" }

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8092/api/teams/team-lj-01/documents" `
  -Headers $headers `
  -Form @{
    file = Get-Item "D:\AI\知识库\LJ-01\营业执照.docx"
    teamName = "LJ-01 路基土石方分包作业队"
    projectName = "南江至东岭高速公路改扩建工程"
    documentType = "business_license"
  }
```

## 7. 检索示例

```powershell
$headers = @{
  Authorization = "Bearer $env:GATEWAY_API_KEY"
  "Content-Type" = "application/json"
}

$body = @{
  query = "LJ-01队伍安全生产许可证是否有效"
  searchMode = "blend"
  topK = 8
  similarity = 0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8092/api/teams/team-lj-01/search" `
  -Headers $headers `
  -Body $body
```

## 8. 字段检索示例

```powershell
$headers = @{
  Authorization = "Bearer $env:GATEWAY_API_KEY"
  "Content-Type" = "application/json"
}

$body = @{
  fieldName = "统一社会信用代码"
  fieldValue = "91310115515002x94"
  searchMode = "keywords"
  topK = 5
  similarity = 0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8092/api/teams/team-lj-01/search/field" `
  -Headers $headers `
  -Body $body
```

## 9. 当前限制

- 首版不持久化 `teamId -> knowledgeBaseId` 映射
- 首版图片和扫描件不主动走 OCR Worker
- 首版只代理 MaxKB，不支持切换其他知识 provider
- 检索结果只作为支持性召回，不直接形成正式审查结论
