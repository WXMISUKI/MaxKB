# ZHGDX 队伍知识库数据映射规格

## 1. 目的

本文定义安全监管平台数据库 `zhgdx` 到 MaxKB 队伍知识库的资料映射、归属边界和同步契约。

本文是网关实现和安全监管平台后端联调的共同依据。它不改变安全监管平台的业务事实模型，也不要求 MaxKB 直接连接 `zhgdx`。

## 2. 系统边界

```text
安全监管平台 / zhgdx
  - 业务事实源
  - 项目、组织、队伍、人员、设备、审查状态
  - 文件原件和文件地址
          |
          | 事件驱动，平台后端主动调用
          v
Safety Platform KB Gateway
  - Bearer 鉴权
  - 队伍知识库发现/创建
  - 文件接收和上传代理
  - 归属元数据校验
  - 结构化检索结果
          |
          v
MaxKB
  - 文档解析
  - 分段和向量化
  - 召回
```

MaxKB、网关和 OCR 服务都不是项目、队伍、人员、审查结论的事实源。

## 3. 知识库粒度

首版采用：

> 一个 `biz_work_team.id` 对应一个 MaxKB 知识库。

队伍知识库的绑定主键必须是 `teamId = biz_work_team.id`。`team_code` 可用于展示和检索，但不能作为绑定唯一键，因为该字段允许为空。

项目共享资料允许同步到每个队伍知识库，但必须携带：

```text
scope = project_shared
projectId = biz_work_team.project_id
teamId = biz_work_team.id
```

队伍专属资料必须携带：

```text
scope = team_private
teamId = biz_work_team.id
projectId = biz_work_team.project_id
```

## 4. ZHGDX 核心关系

```text
biz_project
  └─ biz_project_org
       └─ biz_project_org_user
            ├─ biz_project_person_certificate
            ├─ biz_project_person_contract
            ├─ biz_project_person_entry_exit
            └─ biz_project_person_health_report

biz_work_team
  ├─ biz_project_org_user.team_id
  ├─ biz_work_group.team_id
  ├─ biz_equipment.team_id
  ├─ biz_training_sign.team_id
  └─ biz_structure_work_team.work_team_id
```

数据库当前没有显式外键约束，因此同步查询必须同时校验：

- `tenant_id`
- `project_id`
- `del_flag`
- 业务表自身的有效状态
- 关联对象是否仍然属于目标队伍

## 5. 资料归属分类

### 5.1 队伍专属资料

| 资料分类 | 主要来源 | 归属方式 |
| --- | --- | --- |
| 队伍基础信息 | `biz_work_team` | `id = teamId` |
| 营业执照 | `biz_work_team.biz_license_file_id` + `sys_file` | 文件 ID |
| 分包/施工资质 | `biz_work_team.qualification_file_id` + `sys_file` | 文件 ID |
| 施工合同 | `biz_work_team.contract_file_id` + `sys_file` | 文件 ID |
| 安全生产协议 | `biz_work_team.safety_agreement_file_id` + `sys_file` | 文件 ID |
| 队伍人员 | `biz_project_org_user.team_id` | 队伍 ID |
| 人员证书 | `biz_project_person_certificate.project_person_id` | 先回溯项目人员 |
| 人员合同 | `biz_project_person_contract.project_person_id` | 先回溯项目人员 |
| 人员进退场和体检 | 对应项目人员关联表 | 先回溯项目人员 |
| 队伍班组 | `biz_work_group.team_id` | 队伍 ID |
| 队伍设备 | `biz_equipment.team_id` | 队伍 ID |
| 设备附件 | `biz_device_file.device_id` | 先回溯设备 |
| 设备检查 | `biz_equipment_inspection.equipment_id` | 先回溯设备 |

### 5.2 项目共享资料

| 资料分类 | 主要来源 | 说明 |
| --- | --- | --- |
| 体系文件 | `biz_system_document` | 项目/机构范围，需保留 `projectId` 和 `orgId` |
| 体系文件关联 | `biz_system_document_structure` | 用于补充工程结构范围 |
| 安全策划文件 | `biz_safety_plan_doc` | 项目或机构范围 |
| 项目应急预案 | `biz_emergency_plan` | 项目或机构范围 |
| 风险源规则 | `biz_risk_source` | 作为项目共享依据，不作为队伍事实 |
| 月度风险源清单 | `biz_monthly_risk_source_doc` | 项目/机构范围 |

项目共享资料复制到队伍库时，必须使用 `scope=project_shared`，不能伪装成队伍专属资料。

### 5.3 暂不投影到队伍库的资料

以下数据当前没有稳定的队伍归属字段，首版留在项目范围：

- `biz_safety_inspection`
- `biz_safety_inspection_issue`
- `biz_hazard_ledger`
- `biz_training_record`
- `biz_startup_condition`
- `biz_major_dangerous`
- `biz_special_plan`
- `biz_supervisor_side_record`

只有当平台后端能够提供明确的 `teamId`、责任单位 ID 或可验证的工程结构归属时，才允许将其投影到队伍知识库。

## 6. 文件来源策略

ZHGDX 当前存在三种文件表示方式，平台后端必须在调用网关前统一解析成文件内容：

1. `sys_file.id`
   - 适用于队伍基础文件、部分设备附件和通用附件。
2. `file_url` / `attachment_url`
   - 适用于人员证书、人员合同、体系文件、方案和报告。
3. `biz_attachment.biz_type + biz_id + file_id`
   - 适用于检查、交底、会议、培训、危险作业、风险等通用业务附件。

网关首版接收 `multipart/form-data` 文件内容，不直接连接 ZHGDX，也不负责下载平台内部 URL。

## 7. 同步契约

### 7.1 单文件上传

`POST /api/teams/{teamId}/documents`

请求必须包含：

- `Authorization: Bearer <GATEWAY_API_KEY>`
- `file`
- `scope`: `team_private` 或 `project_shared`
- `projectId`
- `documentType`

建议包含：

- `teamName`
- `projectName`
- `sourceType`
- `sourceTable`
- `sourceObjectId`
- `basisVersionId`
- `contentHash`
- `effectiveStatus`
- `effectiveDate`

### 7.2 项目共享依据批量同步

`POST /api/teams/{teamId}/knowledge-base/sync-basis`

请求必须包含：

- `files[]`
- `scope=project_shared`
- `projectId`

建议包含：

- `projectName`
- `basisVersionId`
- `sourceTable`
- `contentHash`

### 7.3 平台绑定

首版允许网关按 `teamId` 自动发现或创建知识库。

平台绑定关系稳定后，平台后端应优先传入 `knowledgeBaseId`。网关保留 `teamId` 作为兼容兜底。

### 7.4 上传响应

网关成功上传后必须返回：

- `teamId`
- `knowledgeBaseId`
- `providerDocumentId`
- `fileName`
- `metadata.scope`
- `metadata.projectId`
- `metadata.documentType`
- `metadata.contentHash`

当平台未传入 `contentHash` 时，网关使用上传文件内容计算 SHA-256 并返回。该哈希用于平台后端去重、版本追踪和后续幂等设计。

本阶段不在网关内持久化同步状态，也不承诺跨进程幂等。生产环境的幂等键、版本状态和 provider ref 应由安全监管平台事实库持久化。

## 8. 生命周期规则

- 队伍创建：可预建知识库，也可在首次上传时自动创建。
- 资料新增：平台后端主动上传。
- 资料变更：按新版本上传，旧文档由平台后端根据 provider document ref 删除或标记失效。
- 资料删除：平台后端调用网关删除对应 provider document。
- 队伍停用：停止新增同步，不自动删除历史知识库。
- 队伍逻辑删除：进入归档流程，是否删除知识库必须由平台明确调用。

网关不轮询数据库，不猜测资料版本，不生成正式审查结论。

## 9. 安全与数据质量

- 不把数据库密码、MaxKB 密码、Bearer token 写入代码或日志。
- 不把身份证号、银行卡号、病史等人员敏感字段作为知识库资料默认内容。
- 所有跨表同步查询必须限制租户、项目和逻辑删除状态。
- `teamId` 必须来自平台业务路径或显式绑定，不能只根据队伍名称匹配。
- 无法可靠归属队伍的资料不得写入队伍知识库。
- 检索命中只是支持性证据，不直接等价于合格/不合格结论。

## 10. 首版验收

1. 使用真实 `biz_work_team.id` 上传一个队伍 PDF/Office/图片资料。
2. 网关自动创建或复用对应知识库。
3. 使用同一 `teamId` 检索，返回结构化命中结果。
4. 项目共享依据可复制到队伍库，并保留 `project_shared` 归属。
5. 不可归属的项目级审查数据不会被误写入队伍库。
6. 资料更新和删除可通过 provider document ref 管理。
