# 安全监管平台后端网关对接说明

版本：1.0  
适用服务：`safety-platform-kb-gateway`  
默认地址：`http://192.168.1.85:8092`  
更新时间：2026-07-27

## 1. 给后端 AI 的执行指令

你是安全监管平台后端开发 AI。实现本对接时必须遵守以下规则：

1. 安全监管平台数据库 `zhgdx` 是业务事实源。
2. `biz_work_team.id` 是队伍知识库绑定的唯一主键。
3. 网关是平台后端与 MaxKB 之间的唯一调用边界。
4. 后端不得直接调用 MaxKB 管理接口。
5. 后端不得让网关连接 `zhgdx`。
6. 后端必须在调用网关前解析文件内容，并以 `multipart/form-data` 上传。
7. 无法可靠归属到某个队伍的资料，不得上传到队伍知识库。
8. MaxKB 检索结果只能作为支持性资料，不能直接生成正式审查结论。

## 2. 服务职责

### 2.1 安全监管平台后端负责

- 读取 `zhgdx` 业务数据。
- 校验租户、项目、队伍和逻辑删除状态。
- 解析 `sys_file.id`、`file_url`、`attachment_url` 和 `biz_attachment`。
- 保存原始文件、文件版本和内容哈希。
- 决定什么时候同步新增、更新和删除资料。
- 保存网关返回的 `knowledgeBaseId`、`providerDocumentId` 和同步状态。
- 向巡检仪提供最终业务接口。

### 2.2 网关负责

- Bearer 鉴权。
- 按 `teamId` 自动创建或复用 MaxKB 队伍知识库。
- 接收文件并上传 MaxKB。
- 返回结构化 provider 引用和资料元数据。
- 代理队伍知识库检索。
- 删除指定 provider 文档。

### 2.3 MaxKB 负责

- 文档解析。
- 文档切分。
- 向量化。
- 检索召回。

## 3. 队伍和资料映射

### 3.1 队伍主键

```text
teamId = biz_work_team.id
projectId = biz_work_team.project_id
```

不要使用以下字段作为唯一绑定键：

- `team_code`，因为允许为空。
- `team_name`，因为可能修改或重名。
- 队伍负责人姓名，可能发生变更。

### 3.2 队伍专属资料

| 资料 | 数据来源 | `documentType` |
| --- | --- | --- |
| 队伍基础信息 | `biz_work_team` | `team_profile` |
| 营业执照 | `biz_work_team.biz_license_file_id` + `sys_file` | `business_license` |
| 施工/分包资质 | `biz_work_team.qualification_file_id` + `sys_file` | `qualification` |
| 施工合同 | `biz_work_team.contract_file_id` + `sys_file` | `construction_contract` |
| 安全生产协议 | `biz_work_team.safety_agreement_file_id` + `sys_file` | `safety_agreement` |
| 队伍人员 | `biz_project_org_user.team_id` | `team_person` |
| 人员证书 | `biz_project_person_certificate.project_person_id` | `person_certificate` |
| 人员合同 | `biz_project_person_contract.project_person_id` | `person_contract` |
| 人员进退场 | `biz_project_person_entry_exit.project_person_id` | `person_entry_exit` |
| 人员体检 | `biz_project_person_health_report.project_person_id` | `person_health_report` |
| 队伍班组 | `biz_work_group.team_id` | `work_group` |
| 队伍设备 | `biz_equipment.team_id` | `equipment` |
| 设备附件 | `biz_device_file.device_id` | `equipment_file` |
| 设备检查 | `biz_equipment_inspection.equipment_id` | `equipment_inspection` |

### 3.3 项目共享资料

项目共享资料可以复制到每个队伍知识库，但必须使用：

```text
scope = project_shared
```

主要资料：

| 资料 | 数据来源 | `documentType` |
| --- | --- | --- |
| 体系文件 | `biz_system_document` | `system_document` |
| 体系文件工程结构关联 | `biz_system_document_structure` | `system_document_structure` |
| 安全策划文件 | `biz_safety_plan_doc` | `safety_plan` |
| 项目应急预案 | `biz_emergency_plan` | `emergency_plan` |
| 风险源清单 | `biz_risk_source` / `biz_monthly_risk_source_doc` | `risk_basis` |

必须保留 `projectId`、`sourceTable` 和 `sourceObjectId`。

### 3.4 暂不上传到队伍库

以下资料当前缺少稳定的队伍归属，不得直接上传到队伍库：

- `biz_safety_inspection`
- `biz_safety_inspection_issue`
- `biz_hazard_ledger`
- `biz_training_record`
- `biz_startup_condition`
- `biz_major_dangerous`
- `biz_special_plan`
- `biz_supervisor_side_record`

除非后端能够提供经过校验的 `teamId` 或明确责任单位/工程结构归属。

## 4. 文件解析要求

后端调用网关前必须将数据库中的文件引用解析为实际文件内容。

### 4.1 `sys_file.id`

适用于队伍基础文件和部分设备附件：

```text
biz_work_team.biz_license_file_id
  -> sys_file.id
  -> 文件对象存储
  -> multipart file
```

### 4.2 URL 文件

适用于人员证书、人员合同、体系文件和方案：

```text
attachment_url / file_url
  -> 后端服务下载或读取
  -> multipart file
```

不要把只能在内网访问的数据库 URL 原样发送给网关。

### 4.3 通用附件

适用于 `biz_attachment`：

```text
biz_type + biz_id
  -> biz_attachment.file_id
  -> sys_file
  -> 文件对象存储
  -> multipart file
```

## 5. 环境配置

网关服务端配置：

```powershell
$env:GATEWAY_API_KEY = "<平台后端专用Bearer密钥>"
$env:GATEWAY_PORT = "8092"
$env:MAXKB_BASE_URL = "http://127.0.0.1:8080/admin/api"
$env:MAXKB_USERNAME = "<MaxKB管理员账号>"
$env:MAXKB_PASSWORD = "<MaxKB管理员密码>"
$env:MAXKB_WORKSPACE_ID = "<MaxKB工作空间ID>"
```

平台后端只保存：

```text
GATEWAY_BASE_URL
GATEWAY_API_KEY
```

MaxKB 账号密码不得下发到平台后端，也不得发送到巡检仪。

## 6. 上传队伍资料

接口：

```http
POST /api/teams/{teamId}/documents
Authorization: Bearer <GATEWAY_API_KEY>
Content-Type: multipart/form-data
```

### 6.1 必填字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file` | file | 实际文件内容 |
| `scope` | string | `team_private` 或 `project_shared` |
| `projectId` | string | `biz_work_team.project_id` |
| `documentType` | string | 资料类型 |

### 6.2 推荐字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `teamName` | string | 展示名称 |
| `projectName` | string | 展示名称 |
| `sourceType` | string | `pdf`、`image`、`office` 等 |
| `sourceTable` | string | 原始表名 |
| `sourceObjectId` | string | 原始记录 ID |
| `basisVersionId` | string | 依据版本 |
| `contentHash` | string | 原文件 SHA-256 |
| `effectiveStatus` | string | 有效状态 |
| `effectiveDate` | string | 生效日期 |
| `knowledgeBaseId` | string | 已知时显式传入 |
| `createIfMissing` | boolean | 是否允许自动建库 |

### 6.3 PowerShell 示例

```powershell
$headers = @{
  Authorization = "Bearer $env:GATEWAY_API_KEY"
}

Invoke-RestMethod `
  -Method Post `
  -Uri "$env:GATEWAY_BASE_URL/api/teams/1001/documents" `
  -Headers $headers `
  -Form @{
    file = Get-Item "D:\files\person-certificate.pdf"
    scope = "team_private"
    projectId = "2001"
    documentType = "person_certificate"
    sourceType = "pdf"
    sourceTable = "biz_project_person_certificate"
    sourceObjectId = "3001"
    contentHash = "optional-sha256"
    createIfMissing = "true"
  }
```

### 6.4 Python 示例

```python
import requests

with open("person-certificate.pdf", "rb") as file_obj:
    response = requests.post(
        f"{gateway_base_url}/api/teams/1001/documents",
        headers={"Authorization": f"Bearer {gateway_api_key}"},
        files={"file": ("person-certificate.pdf", file_obj, "application/pdf")},
        data={
            "scope": "team_private",
            "projectId": "2001",
            "documentType": "person_certificate",
            "sourceType": "pdf",
            "sourceTable": "biz_project_person_certificate",
            "sourceObjectId": "3001",
        },
        timeout=300,
    )
response.raise_for_status()
result = response.json()
```

### 6.5 成功响应

```json
{
  "teamId": "1001",
  "knowledgeBaseId": "kb-uuid",
  "providerDocumentId": "document-uuid",
  "fileName": "person-certificate.pdf",
  "metadata": {
    "scope": "team_private",
    "projectId": "2001",
    "documentType": "person_certificate",
    "sourceType": "pdf",
    "sourceTable": "biz_project_person_certificate",
    "sourceObjectId": "3001",
    "contentHash": "sha256"
  },
  "autoCreatedKb": true
}
```

后端必须保存：

- `teamId`
- `projectId`
- `knowledgeBaseId`
- `providerDocumentId`
- `sourceTable`
- `sourceObjectId`
- `contentHash`
- 当前同步状态

## 7. 项目共享依据批量同步

接口：

```http
POST /api/teams/{teamId}/knowledge-base/sync-basis
Authorization: Bearer <GATEWAY_API_KEY>
Content-Type: multipart/form-data
```

字段：

- `files[]`
- `projectId`
- `projectName`
- `sourceTable`
- `basisVersionId`
- `knowledgeBaseId`（可选）
- `createIfMissing`（可选）

网关会将每个文件标记为：

```text
scope = project_shared
documentType = project_basis
```

## 8. 同步生命周期

后端建议保存以下状态：

```text
pending
uploading
succeeded
failed
superseded
deleted
```

### 8.1 新增

1. 写入平台资料记录，状态 `pending`。
2. 读取并计算文件 SHA-256。
3. 调用网关上传。
4. 保存 `providerDocumentId`。
5. 状态改为 `succeeded`。

### 8.2 更新

1. 计算新文件 SHA-256。
2. 如果哈希未变化，不重复上传。
3. 如果哈希变化，上传新文件。
4. 新上传成功后删除旧 `providerDocumentId`。
5. 旧版本标记 `superseded`。

不要先删除旧文档再上传新文档，避免更新期间知识库短暂缺资料。

### 8.3 删除

调用：

```http
DELETE /api/teams/{teamId}/documents/{providerDocumentId}
```

删除成功后将平台资料状态改为 `deleted`。

### 8.4 队伍停用或删除

- 队伍停用：停止新资料同步，保留知识库。
- 队伍逻辑删除：保留历史 provider ref，是否删除知识库必须由平台明确操作。

## 9. 幂等和重试

当前网关不持久化同步台账，因此幂等状态由平台后端保存。

推荐幂等业务键：

```text
teamId:sourceTable:sourceObjectId:contentHash
```

调用前后端先查询自己的同步记录：

```text
存在 succeeded 且 contentHash 相同 -> 不重复上传
存在 uploading -> 等待或恢复任务
存在 failed -> 允许重试
不存在 -> 创建上传任务
```

重试规则：

- `400`：修正请求后重试，不要盲目重试。
- `401`：检查网关密钥。
- `404`：检查队伍知识库或文档绑定。
- `500`：指数退避重试，最多 3 次。
- `503`：等待网关配置完成后重试。

## 10. 检索队伍资料

接口：

```http
POST /api/teams/{teamId}/search
Authorization: Bearer <GATEWAY_API_KEY>
Content-Type: application/json
```

请求：

```json
{
  "knowledgeBaseId": "optional-kb-uuid",
  "query": "该队伍的安全生产许可证是否有效",
  "searchMode": "blend",
  "topK": 8,
  "similarity": 0
}
```

返回内容：

- `teamId`
- `knowledgeBaseId`
- `query`
- `hits[].title`
- `hits[].snippet`
- `hits[].score`
- `hits[].documentId`
- `hits[].paragraphId`
- `diagnostics`

后端应将命中结果转换成自己的业务响应，再由巡检仪展示。不得把 MaxKB 原始响应直接暴露给巡检仪。

## 11. 字段检索

接口：

```http
POST /api/teams/{teamId}/search/field
```

请求：

```json
{
  "fieldName": "证书编号",
  "fieldValue": "CERT-001",
  "searchMode": "keywords",
  "topK": 5
}
```

字段检索适用于：

- 统一社会信用代码
- 资质证书编号
- 安全生产许可证编号
- 人员证书编号
- 设备编号
- 合同编号

## 12. 安全要求

- 网关 API Key 只放在后端服务端。
- 巡检仪不得持有网关 API Key。
- 不在日志打印文件内容、身份证号、手机号、密码或 token。
- 不把 MaxKB 管理账号密码发送给安全监管平台前端。
- 只上传目标队伍的资料。
- 不把项目级、其他队伍或无法确认归属的资料写入目标队伍库。
- 正式审查结论必须由安全监管平台保存，不能以 MaxKB 命中代替。

## 13. 后端实现验收

后端完成后必须验证：

1. 创建队伍后可上传第一份队伍资料。
2. 同一 `teamId` 再上传不会新建第二个知识库。
3. 相同 `contentHash` 不会重复上传。
4. 资料版本变化后，新文档先成功入库，旧文档再删除。
5. 平台保存 `providerDocumentId`。
6. 平台可按队伍发起检索。
7. 其他队伍资料不会出现在目标队伍检索结果中。
8. 网关不可用时，平台保留 `failed` 状态并可重试。
9. 网关密钥不出现在前端和巡检仪。

## 14. 当前明确不做

- 网关直接连接 `zhgdx`。
- 网关轮询安全监管平台数据库。
- 网关保存项目、队伍、人员和审查事实。
- 网关直接输出正式审查结论。
- 在平台后端未提供可靠队伍归属前，强行同步项目级检查和隐患数据。
