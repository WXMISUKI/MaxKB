# 安全监管平台知识网关服务设计

## 1. 目标

本服务用于在安全监管平台后端与 MaxKB 之间提供一个稳定、可联调、可替换的知识库代理层。

首版目标只有三件事：

1. 平台后端上传队伍资料时，网关自动创建或复用该队伍对应的知识库并完成入库。
2. 平台后端检索某个队伍资料时，网关代理 MaxKB 检索并返回结构化命中结果。
3. 平台后端可通过健康检查和简单管理接口判断该队伍知识库是否存在、是否可用。

## 2. 非目标

首版明确不做：

- 不做项目、队伍、人员、审查任务等业务事实存储
- 不做 OCR 编排与结构化后处理
- 不做自动审批、自动审查结论输出
- 不做数据库持久化 provider refs
- 不做多 provider 抽象，只先落 MaxKB

## 3. 服务边界

### 3.1 平台后端负责

- Project / ContractPackage / Section / Team / ReviewTask / Evidence 等业务事实
- 文件上传触发时机
- 资料版本、状态和人工审核结论
- 巡检仪最终展示与结论表达

### 3.2 知识网关负责

- Bearer 鉴权
- MaxKB 登录与 token 管理
- 队伍知识库的自动创建、查询、删除
- office/pdf/image 文件上传到对应队伍知识库
- 代理 hit-test 检索
- 返回安全、结构化的 hits

### 3.3 MaxKB 负责

- 文档切分
- 文档向量化
- 召回与命中测试

## 4. 当前阶段的关键决策

### 4.1 知识库粒度

首版采用：

> 一个队伍一个知识库

原因：

- 巡检仪最核心的问题是“某个队伍的资质/合同/人员/设备资料是否存在或是否匹配”
- 平台后端可直接按 `teamId` 路由到对应知识库
- 可以避免首版就把 metadata 过滤复杂性压到网关和平台后端

### 4.2 上传模式

首版采用：

> 平台后端直接以 `multipart/form-data` 传文件给网关

原因：

- 当前目标是先跑通联调，不先把对象存储链路变成前置依赖
- 便于快速验证 office / pdf / image 混合资料的接入

### 4.3 调用方式

首版采用：

> 平台后端事件驱动主动调用

即：

- 队伍创建后可选预建知识库
- 文件新增/变更时主动调用网关上传
- 检索时主动调用网关 search 接口

网关不做轮询，不反向拉平台数据。

### 4.4 检索返回

首版采用：

> 返回结构化 hits，不代替平台和巡检仪下结论

返回至少包含：

- `teamId`
- `knowledgeBaseId`
- `query`
- `hits[]`
- `diagnostics`

其中每个 hit 至少包含：

- `title`
- `snippet`
- `score`
- `documentId`
- `paragraphId`
- `sourceType`

## 5. 文件类型策略

首版支持：

- Word / 文本：`.docx` `.doc` `.txt` `.md`
- 表格：`.xlsx` `.xls` `.csv`
- 扫描件 / 图片：`.pdf` `.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.tif`

首版策略：

- 表格走 MaxKB table 文档接口
- 其他格式统一先走 split + batch_create 路径

说明：

- 图片和扫描件首版不额外编排 OCR
- 后续如果 MaxKB 对图片直接解析效果不稳定，再把 OCR Worker 接成前置路径

## 6. 接口草案

### 6.1 健康检查

`GET /health`

返回：

- 网关鉴权是否已配置
- MaxKB provider 是否已配置
- 当前 workspaceId
- 当前能力声明

### 6.2 上传队伍资料

`POST /api/teams/{teamId}/documents`

请求：

- Bearer token
- multipart file
- 可选字段：`teamName`、`projectName`、`documentType`

行为：

1. 查找该 `teamId` 对应知识库
2. 若不存在则自动创建
3. 根据文件类型选择上传通道
4. 返回知识库 ID 与 provider 文档 ID

### 6.3 查询队伍知识库

`GET /api/teams/{teamId}/knowledge-base`

返回：

- 是否存在
- `knowledgeBaseId`
- `knowledgeBaseName`

### 6.4 删除队伍知识库

`DELETE /api/teams/{teamId}/knowledge-base`

### 6.5 删除文档

`DELETE /api/teams/{teamId}/documents/{documentId}`

### 6.6 普通检索

`POST /api/teams/{teamId}/search`

请求：

- `query`
- `searchMode`
- `topK`
- `similarity`

### 6.7 字段检索

`POST /api/teams/{teamId}/search/field`

请求：

- `fieldName`
- `fieldValue`
- `searchMode`
- `topK`

说明：

字段检索内部用 `fieldName + fieldValue` 拼接查询串，优先走 `keywords`。

### 6.8 批量同步项目依据

`POST /api/teams/{teamId}/knowledge-base/sync-basis`

请求：

- 多文件上传

行为：

- 自动创建或复用该队伍知识库
- 批量上传项目依据类资料

## 7. 错误语义

- `401`：缺少或错误 Bearer token
- `400`：文件类型不支持、字段缺失
- `404`：队伍知识库不存在或文档不存在
- `500`：MaxKB API 调用失败
- `503`：网关未完成基础配置

## 8. 环境变量

- `GATEWAY_API_KEY`
- `GATEWAY_PORT`
- `MAXKB_BASE_URL`
- `MAXKB_USERNAME`
- `MAXKB_PASSWORD`
- `MAXKB_WORKSPACE_ID`
- `MAXKB_DEFAULT_EMBEDDING_MODEL_ID`

## 9. 验收标准

首版验收只看最小联调闭环：

1. 平台后端上传一个队伍的 Word 或 PDF 资料时，知识库可自动创建并成功入库
2. 同一 `teamId` 再次上传时会复用知识库
3. 平台后端按 `teamId + query` 检索时，可得到结构化 hits
4. 不支持文件类型时返回清晰 400
5. 鉴权缺失时返回 401
6. 健康检查可帮助平台判断 readiness

## 10. Phase 2 合同增强方向

首版跑通后，下一步优先增强“平台绑定显式化”，而不是继续扩展 provider 能力。

建议方向：

- 平台后端可在请求中显式传入 `knowledgeBaseId`
- `teamId` 保持兼容入口，作为知识库自动发现和首次创建的兜底路由
- 上传接口支持 `createIfMissing`
- 检索接口优先使用显式绑定的 `knowledgeBaseId`
- 队伍知识库查询接口支持按 `knowledgeBaseId` 或 `teamId` 两种方式定位

这样做的价值是：

- 平台数据库一旦落地，就能直接把绑定关系写死到业务事实里
- 网关从“自动猜测队伍知识库”逐步转向“执行平台显式绑定”
- 后续从局域网迁云或换 provider 时，平台契约更稳

## 11. ZHGDX 数据映射与归属边界

真实安全监管平台数据库 `zhgdx` 的映射、文件来源和项目/队伍资料边界见：

`specs/zhgdx-team-knowledge-mapping/spec.md`

关键约束：

- `biz_work_team.id` 是队伍知识库绑定主键。
- 人员资料通过 `biz_project_org_user.team_id` 归属队伍。
- 设备资料通过 `biz_equipment.team_id` 归属队伍。
- 项目共享依据使用 `scope=project_shared` 投影到队伍库。
- 无法可靠归属队伍的项目级审查数据不得直接进入队伍库。
- 网关接收平台后端解析后的文件内容，不直连 `zhgdx`。

后端完整接入流程和可交给后端 AI 执行的规范见：

`platform-backend-integration-guide.md`
