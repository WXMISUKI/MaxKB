# 安管后端对接网关 `.env` 示例

本文给安全监管平台后端同学直接复制使用。

## 1. 本地联调

当前本机联调口径：

- 网关地址：`http://192.168.0.219:8092`
- 鉴权方式：`Authorization: Bearer <GATEWAY_API_KEY>`
- 本地隔离：`default` workspace + `safety-team` 知识库前缀

```env
SAFETY_KB_GATEWAY_BASE_URL=http://192.168.0.219:8092
SAFETY_KB_GATEWAY_API_KEY=replace-with-safety-gateway-local-key

# 调用方超时建议
SAFETY_KB_GATEWAY_TIMEOUT_MS=15000

# 推荐调用路径
SAFETY_KB_GATEWAY_UPLOAD_PATH=/api/teams/:teamId/documents
SAFETY_KB_GATEWAY_KB_STATUS_PATH=/api/teams/:teamId/knowledge-base
SAFETY_KB_GATEWAY_SEARCH_PATH=/api/teams/:teamId/search
SAFETY_KB_GATEWAY_FIELD_SEARCH_PATH=/api/teams/:teamId/search/field
SAFETY_KB_GATEWAY_SYNC_BASIS_PATH=/api/teams/:teamId/knowledge-base/sync-basis
```

## 2. 线上部署

如果后续网关独立部署到服务器，请只替换：

```env
SAFETY_KB_GATEWAY_BASE_URL=https://your-gateway-host
SAFETY_KB_GATEWAY_API_KEY=replace-with-prod-api-key
```

其余调用路径保持不变。

## 3. 上传调用示例

请求头：

```http
Authorization: Bearer <SAFETY_KB_GATEWAY_API_KEY>
```

`multipart/form-data` 字段建议：

- `file`: 实际文件
- `teamName`: 队伍名称
- `projectName`: 项目名称
- `documentType`: 如 `business_license`
- `scope`: `team_private` 或 `project_shared`
- `projectId`: 项目标识
- `sourceTable`: 如 `biz_work_team`
- `sourceObjectId`: 业务主键
- `basisVersionId`: 可选
- `contentHash`: 可选；不传则网关自动计算

## 4. 检索调用示例

普通检索 body：

```json
{
  "query": "统一社会信用代码 91310115515002X94",
  "searchMode": "blend",
  "topK": 5,
  "similarity": 0
}
```

字段检索 body：

```json
{
  "fieldName": "统一社会信用代码",
  "fieldValue": "91310115515002X94",
  "searchMode": "keywords",
  "topK": 5,
  "similarity": 0
}
```

## 5. 接入注意事项

- 后端只调用 `8092` 网关，不直接调用 MaxKB `8080`
- 不要把 MaxKB 管理员账号密码下发给业务前端或浏览器
- 上传成功后，请落库保存：
  - `knowledgeBaseId`
  - `providerDocumentId`
  - `metadata.contentHash`
  - `teamId`
  - `sourceTable`
  - `sourceObjectId`
- 删除知识库时，线上建议显式传 `knowledgeBaseId`

