# Node BFF 接 MaxKB 实施清单

## 1. 适用范围

本清单用于当前阶段的实际落地：
- 不从零新建独立 Knowledge-Service
- 优先复用现有 Node BFF / API Gateway
- 通过现有 `knowledgeBaseProvider` 抽象接入 MaxKB
- 先服务两个项目：
  - 资料审查平台（material review）
  - 安管平台（safety compliance）

本清单的目标是把“怎么开始改、先验证什么、哪些是 P0、哪些后补”讲清楚，减少架构讨论后的执行损耗。

## 2. 当前推荐路线

### 2.1 一句话路线
由现有 Node BFF 统一承载知识库能力，对外继续保持平台自己的 API 语义，对内通过 `knowledgeBaseProvider` 适配 MaxKB。

### 2.2 现在不要先做的事
- 不先重做一套独立 `/ai/**` 服务
- 不让前端直接调用 MaxKB
- 不把 MaxKB 的 `/admin/api` 和 `/chat/api` 暴露给业务系统
- 不重新选 multipart 方案（当前链路已有 `busboy` 与上传能力）

## 3. 本地联调基线

### 3.1 当前已知本地服务
按当前信息，本地已有：
- MaxKB：`http://127.0.0.1:8080`
- OCR worker：`http://127.0.0.1:8091`

建议补齐并确认：
- Redis
- MinIO
- Node BFF

### 3.2 推荐最小环境变量
建议先在 Node BFF 本地环境中明确以下配置：

```env
MAXKB_BASE_URL=http://127.0.0.1:8080
MAXKB_ADMIN_PREFIX=/admin/api
MAXKB_CHAT_PREFIX=/chat/api

MAXKB_ENABLED=true
MAXKB_PROVIDER=maxkb

MAXKB_ADMIN_TOKEN=xxxx
MAXKB_APPLICATION_API_KEY=application-xxxx

MAXKB_WORKSPACE_MATERIAL_REVIEW=material-review
MAXKB_WORKSPACE_SAFETY=safety

MAXKB_APP_MATERIAL_REVIEW=material-review-assistant
MAXKB_APP_SAFETY=safety-compliance-assistant

MAXKB_KNOWLEDGE_ID_MATERIAL_REVIEW=xxxx
MAXKB_KNOWLEDGE_ID_SAFETY=xxxx

MAXKB_APPLICATION_ID_MATERIAL_REVIEW=xxxx
MAXKB_APPLICATION_ID_SAFETY=xxxx
```

说明：
- token 与 key 建议存“裸值”，代码统一拼 `Bearer `
- `workspace_id / knowledge_id / application_id` 来自当前 MaxKB 实际资源

## 4. P0 改造清单（必须先完成）

### 4.1 provider 路由确认
先确认现有 `knowledgeBaseProvider` 是否已经满足以下能力：
- 支持根据环境变量切换到 MaxKB provider
- 支持按项目/业务场景映射到对应 workspace/application/knowledge
- 支持统一输出平台内部结果格式，而不是把 MaxKB 原始响应直接透给上层

如果没有，第一步先在 provider 层补齐，不要直接在业务路由里散写 MaxKB URL。

### 4.2 统一认证格式
Node BFF 调 MaxKB 时统一使用：

```http
Authorization: Bearer <token>
```

必须区分两类凭证：
- `admin_token`：用于 `/admin/api` 写知识库
- `application_api_key`：用于 `/chat/api` 生成结论

不要复用其它外部服务的 header 写法，不要把 OCR/Paddle 之类的鉴权格式混进 MaxKB 链路。

### 4.3 资料审查平台先打通
当前第一优先级建议只打通资料审查平台：
- `app_code = material-review-assistant`
- `workspace_id = material-review`

先不要同时改两个项目的全部细节，先把一条链路跑通。

### 4.4 先打通“查询证据/检查结论”链路
如果你们当前目标只是“让开工条件平台能查知识库”，优先顺序应为：
1. `knowledgeBaseProvider` -> MaxKB 检索/问答可用
2. `reviewIssueSupportingEvidence` 能消费 MaxKB 返回的证据
3. 开工条件平台页面/后端能展示结论 + 证据

不要一开始就把异步大批量入库、统一平台化门面、跨项目共享全都同时展开。

## 5. P1 改造清单（建议尽快完成）

### 5.1 上传与材料包入库链路
在 P0 查询链路稳定后，再做材料上传和入库：
- 复用现有 `busboy` 上传能力
- 文件先进 MinIO
- Node BFF 后台调用 MaxKB：
  - `document/split`
  - `document/batch_create`

### 5.2 大批文件场景采用异步 job
如果存在一次上传超过 20 个文件：
- 必须改为异步 job
- 返回 `job_id`
- Node BFF 用 Redis + DB 管理状态
- 后台 worker 再调 MaxKB split / batch_create

### 5.3 文件级部分成功
失败文件按粗分类输出：
- `unsupported`
- `too_large`
- `parse_failed`
- `upstream_error`

这四类足够支持 MVP 联调和人工排障。

## 6. Node BFF 模块落点建议

建议不要把 MaxKB 接入逻辑散在业务 handler 中，而是按下面层次组织：

### 6.1 provider 层
职责：
- 屏蔽不同知识库后端差异
- 统一构造请求
- 统一处理 Bearer
- 统一做结果适配

### 6.2 service 层
职责：
- 结合业务语义调用 provider
- 组装资料审查/安管平台需要的请求体
- 规范化输出结论、证据、错误码

### 6.3 route 层
职责：
- 参数校验
- 请求头透传/生成 request_id
- 返回 HTTP 响应

## 7. MaxKB 调用清单

### 7.1 查询/生成结论
用于“审查结论/证据支撑”：

```http
POST {MAXKB_BASE_URL}/chat/api/{application_id}/chat/completions
Authorization: Bearer {application_api_key}
```

### 7.2 文档切分
用于材料包入库：

```http
POST {MAXKB_BASE_URL}/admin/api/workspace/{workspace_id}/knowledge/{knowledge_id}/document/split
Authorization: Bearer {admin_token}
```

### 7.3 批量创建文档
用于把 split 结果写入知识库：

```http
PUT {MAXKB_BASE_URL}/admin/api/workspace/{workspace_id}/knowledge/{knowledge_id}/document/batch_create
Authorization: Bearer {admin_token}
```

## 8. 联调顺序（推荐照这个执行）

### 步骤 1：只验证认证格式
先用最小脚本或 curl 验证：
- `Bearer {application_api_key}` 能打通 chat/completions
- `Bearer {admin_token}` 能打通 admin 路径

如果 Bearer 不通，后面所有链路都会是假问题。

### 步骤 2：只验证 provider 能通 MaxKB
先从 Node BFF 内部直接验证：
- `knowledgeBaseProvider` 是否能成功请求 MaxKB
- 是否能拿到结果并适配成平台内部格式

### 步骤 3：只验证证据消费链路
让 `reviewIssueSupportingEvidence` 消费 provider 结果，确认：
- 证据结构能被当前业务逻辑接受
- 页面或后端输出能正常展示

### 步骤 4：再接上传与入库
查询链路稳定后，再开始做材料包切分/入库。

### 步骤 5：最后再考虑统一 `/ai/**`
只有当两个项目都稳定使用 MaxKB 后，再考虑做统一平台门面。

## 9. 验收标准（当前阶段）

### 9.1 P0 验收
- Node BFF 能通过 provider 成功调用 MaxKB
- Bearer 认证格式明确且统一
- 开工条件平台能基于 MaxKB 返回审查结论
- `reviewIssueSupportingEvidence` 能展示或消费证据

### 9.2 P1 验收
- 材料上传后能进入 MinIO
- split 与 batch_create 可稳定执行
- 大批文件场景使用异步 job
- 失败文件能按粗分类返回

## 10. 常见误区

### 10.1 把当前问题误判成“必须先做统一 AI 门面”
不是。当前最优先问题是把现有 Node BFF + provider + MaxKB 用顺。

### 10.2 把 MaxKB 当作对外 API 产品
不是。MaxKB 当前角色是平台内部知识与检索底座。

### 10.3 把 OCR worker 的调用方式套到 MaxKB 上
不行。MaxKB 必须统一使用 `Authorization: Bearer <token>`。

### 10.4 直接让前端或业务系统打 MaxKB
不建议。应由 Node BFF 统一承载服务端适配与配置管理。

## 11. 下一步建议

如果现在开始落地，建议按下面顺序拆任务：

1. 梳理并确认 `knowledgeBaseProvider` 当前对 MaxKB 的支持边界
2. 统一 MaxKB 环境变量与 Bearer 认证拼接逻辑
3. 打通资料审查平台的证据/结论链路
4. 再补材料上传、MinIO、异步 job
5. 最后再讨论是否抽统一 `/ai/**` 门面
