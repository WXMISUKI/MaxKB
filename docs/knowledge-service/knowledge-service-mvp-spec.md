# Knowledge-Service（内部版 Knowledge Studio）MVP 规范

> 重要修正：
> 当前团队现状不是“从零新建一套独立 AI 门面后再接 MaxKB”，而是“仓库内已存在 Node BFF / API Gateway + knowledgeBaseProvider 抽象，MaxKB 已进入既有后端适配层与部分业务链路”。
>
> 因此本规范采用两阶段策略：
> 1. 第一阶段：优先复用现有 Node BFF、knowledgeBaseProvider、证据检索链路，把 MaxKB 用顺。
> 2. 第二阶段：如果后续确实需要给多个产品统一暴露 `/ai/**` 门面，再把它抽象成独立的 Knowledge-Service。

## 1. 背景与目标

### 1.1 背景
团队需要把知识库能力做成“平台化服务”，供两个项目复用：
- 资料审查平台（material review）
- 安管平台（safety compliance）

底座使用 MaxKB（负责切分、向量化、检索、工作流/对话），平台侧新增一个接入与编排服务（下文称 Knowledge-Service），对外提供统一、稳定、可治理的 HTTP API，类似百炼 Knowledge Studio 的使用方式。

### 1.2 MVP 目标
- 第一阶段优先复用现有 Node BFF / API Gateway，对内通过 knowledgeBaseProvider 适配 MaxKB
- 使用 workspace 做项目隔离；内部按 app_code 路由到 workspace/knowledge/application
- 入库支持大批文件（>20）并发场景：异步任务 + 部分成功
- 具备最小治理：鉴权开关、限流、审计字段、错误码
- MaxKB 不直接暴露给业务系统；仅服务端适配层内网访问 MaxKB

### 1.2.1 阶段 0 兼容原则
在 Node BFF 新版本未完成前：
- 资料审查平台如果当前已经可以正常使用本地或 docker 部署的 MaxKB 服务，则允许继续沿用现有可用链路
- 当前阶段不强制要求资料审查平台立刻切换到新的统一门面或新路由
- 优先把服务端接入层、provider 路由、Bearer 认证、异步入库方案完善好
- 待新版本服务端稳定后，再安排资料审查平台切换到新版本接口

这意味着当前推荐顺序是：
1. 先不打断资料审查平台现有可用能力
2. 先改服务端接入与规格
3. 再安排新版本对接与切换

### 1.3 非目标（MVP 不做）
- 多租户产品化（面向大量外部团队）
- 复杂细分错误分类/自动纠错
- 统一密钥管理（prod 需 token_ref + Vault/KMS；dev 可明文）
- 高级评测与效果看板
- 一上来就重做一套脱离现有 Node BFF 的独立平台

## 2. 当前接入判断

### 2.1 当前正确的一句话描述
基于现有原生 Node.js BFF / API Gateway 架构，MaxKB 最合适的接入方式不是让前端直连，也不是第一步就新建独立 `/ai/**` 门面，而是由 Node 网关统一承载知识库能力，对外保持平台自己的 API 语义，对内通过 `knowledgeBaseProvider` 适配 MaxKB。

### 2.2 现阶段的首选路径
- 开工条件平台、安管平台、前端页面继续走同一条 Node 后端链路
- MaxKB 配置仅放在服务端，通过 `MAXKB_*` 环境变量或服务端配置管理
- 平台继续掌握任务、主数据、证据、报告等业务事实
- MaxKB 仅承担知识检索、材料切分、证据支撑与回答生成能力

### 2.3 为什么不是第一步就做独立 `/ai/**`
- 当前仓库已经存在 `knowledgeBaseProvider` 抽象与部分 MaxKB 消费链路
- 当前仓库已经存在上传链路与 `busboy`，不需要重新选型 multipart 方案
- 直接新增独立门面会让当前接入问题和下一层平台化设计混在一起，增加短期复杂度
- 当前目标如果只是“让开工条件平台能查知识库”，优先打通现有 provider 链路收益最大

## 3. 核心概念与命名

### 2.1 app_code（对外主入口，稳定契约）
- 资料审查平台：material-review-assistant
- 安管平台：safety-compliance-assistant

规范：小写 + 短横线；对外稳定；不要使用 UUID。

### 2.2 workspace_id（项目分区/隔离边界）
- material-review
- safety

workspace 用于权限隔离、资源隔离、管理与排障；对外接口默认不要求业务方直接使用 workspace（但可提供内部调试入口）。

### 2.3 MaxKB 资源映射
每个 app_code 对应：
- workspace_id
- knowledge_id（该项目唯一知识库）
- application_id（该项目唯一应用/工作流，用于输出结论）
- admin_token（调用 MaxKB /admin/api 写入知识库）
- application_api_key（调用 MaxKB /chat/api 输出检查结论）

## 4. 架构与数据流

### 4.1 第一阶段推荐组件边界
- Node BFF / API Gateway：当前主承载层，对外保持平台自身 API 语义
- knowledgeBaseProvider：服务端知识库适配抽象，MaxKB 应优先通过这一层接入
- MaxKB：知识库与智能体平台内核（仅内网可达）
- Nacos：配置中心（路由表）；服务发现按团队现状选用
- MinIO：文件暂存（job 级对象存储）
- Redis：队列、进度、并发控制、幂等映射
- DB：任务与文件明细归档（审计）

### 4.2 第二阶段可选演进
- 如果后续多个产品确实需要统一 `/ai/**` 门面，可将 Node BFF 中已有知识能力模块抽出，演进为独立 Knowledge-Service
- 该阶段应视为“平台层二级抽象”，不是 MaxKB 接入第一步

### 4.3 安全边界
- MaxKB 的 /admin 与 /chat 路径不得对业务系统开放
- 业务系统只访问平台后端（当前为 Node BFF；后续可演进为独立 Knowledge-Service）
- 服务端调用 MaxKB 必须带 Authorization: Bearer <token>

### 4.4 入库（ingest）数据流
1) 客户端调用平台后端上传多个文件
2) Node BFF / 平台后端创建 job、写 DB、上传文件到 MinIO
3) Redis 入队（按 app_code 分队列）并标记 app 活跃
4) 调度器轮询活跃 app，按每个 app 并发上限启动 worker
5) worker 逐文件执行：
   - 从 MinIO 读取对象流
   - 调 MaxKB split（单文件，保证部分成功）
   - 汇总成功的文档结构
6) worker 按批次（默认 20）调用 MaxKB batch_create（触发 embedding/refresh）
7) 更新 Redis 进度；最终写 DB job 状态与明细

### 4.5 查询（query）数据流
1) 客户端调用平台后端的知识库/证据/审查接口
2) 平台后端通过 app_code 或业务配置路由到对应 application_id
3) mode=answer：调用 MaxKB chat/completions 返回结构化结论（带引用）
4) mode=retrieval：返回检索证据（MVP 可先返回简化结果/引用）

## 5. 阶段划分与实施优先级

### 5.1 第一阶段（现在就做）
- 复用现有 Node BFF / API Gateway
- 复用 `knowledgeBaseProvider`
- 优先打通资料审查平台的知识库查询与证据支撑链路
- 把 MaxKB 配置、Bearer 鉴权、provider 路由、任务入库链路稳定下来

### 5.1.1 资料审查平台当前处理原则
- 如果当前资料审查平台已能正常连接 docker 中的 MaxKB，则本阶段默认“不先改前端/业务调用方式”
- 资料审查平台本轮主要作为消费方保留现状
- 本轮工作的主要改动面应放在服务端适配层、provider、任务编排、配置与文档
- 切换动作作为单独步骤，在服务端新版本准备完成后进行

### 5.2 第二阶段（后续再做）
- 抽象统一 `/ai/**` 门面
- 统一多产品接入契约
- 将知识能力模块从现有 Node BFF 中拆为独立 Knowledge-Service（如果确有必要）

### 5.3 当前仓库的推荐动作
- 如果目标只是“让开工条件平台能查知识库”，优先走现有 `knowledgeBaseProvider` + 证据检索链路
- 如果目标是“做统一 `/ai/**` 门面给多个产品共用”，再进入第二阶段设计

## 6. 对外 API 规范（第二阶段可选）

> 说明：
> 本章描述的是“统一 `/ai/**` 门面”形态，属于第二阶段平台抽象。
> 第一阶段可继续保持平台现有 API 语义，只在服务端通过 provider 适配 MaxKB。

### 4.1 统一约定
Headers（建议）：
- X-Caller-System：调用方系统标识（MVP 可放宽）
- X-Request-Id：幂等与审计 ID（建议强制）

返回结构建议统一携带：
- request_id
- app_code 或 workspace_id

### 4.2 主入口（对外主推）：app_code

#### 4.2.1 创建入库任务（异步）
POST /ai/apps/{app_code}/kb/ingest

Content-Type: multipart/form-data
- file：可重复多次

Response: 202
{
  "request_id": "...",
  "app_code": "...",
  "job_id": "...",
  "status": "queued",
  "summary": { "total_files": 57 }
}

#### 4.2.2 查询任务状态
GET /ai/jobs/{job_id}

Response: 200（running）
{
  "job_id": "...",
  "status": "running",
  "progress": 0.42,
  "summary": {
    "total_files": 57,
    "processed_files": 24,
    "success_files": 22,
    "failed_files": 2,
    "created_documents": 22
  }
}

Response: 200（partial_success/success/failed）
{
  "job_id": "...",
  "status": "partial_success",
  "progress": 1.0,
  "summary": {
    "total_files": 57,
    "processed_files": 57,
    "success_files": 53,
    "failed_files": 4,
    "created_documents": 53
  },
  "failed": [
    { "filename": "a.zip", "reason": "unsupported", "code": 40011, "message": "Unsupported file type", "retryable": false },
    { "filename": "b.pdf", "reason": "too_large", "code": 40012, "message": "File too large", "retryable": false },
    { "filename": "c.docx", "reason": "parse_failed", "code": 40013, "message": "Parse failed", "retryable": false },
    { "filename": "d.pdf", "reason": "upstream_error", "code": 50011, "message": "Upstream error, retry later", "retryable": true }
  ]
}

#### 4.2.3 RAG 查询/检查
POST /ai/apps/{app_code}/rag/query?mode=answer|retrieval

Request（示例）
{
  "query": "请检查开工条件是否满足？",
  "options": {
    "return_citations": true
  }
}

Response（mode=answer 示例）
{
  "request_id": "...",
  "app_code": "...",
  "mode": "answer",
  "result": {
    "conclusion": "不满足",
    "risk_level": "high",
    "summary": "缺少监理签章与安全交底记录",
    "items": [
      { "code": "C-001", "name": "监理签章", "pass": false, "reason": "未检索到签章页" }
    ]
  },
  "citations": [
    { "title": "...", "snippet": "...", "score": 0.78, "meta": { "page": 12 } }
  ]
}

### 4.3 内部调试入口（可开关）：workspace_id
默认建议关闭（生产环境 allow_workspace_api=false）。

#### 4.3.1 workspace 入库
POST /ai/workspaces/{workspace_id}/kb/ingest

#### 4.3.2 workspace 查询
POST /ai/workspaces/{workspace_id}/rag/query?mode=answer|retrieval

## 7. 错误码规范（MVP）

### 5.1 接口级错误码
- 40001：参数错误
- 40101：鉴权失败
- 40301：调用方无权限（不在 allow_callers）
- 40401：app_code 未配置
- 41301：上传体过大
- 42901：限流
- 50001：上游（MaxKB）错误
- 50002：依赖不可用（Nacos/Redis/MinIO/DB）

### 5.2 文件级失败子码（failed[] 中使用）
- 40011：unsupported
- 40012：too_large
- 40013：parse_failed
- 50011：upstream_error

## 8. Nacos 配置规范（路由表）

DataId（建议）：
- dev：knowledge-service-routing-dev.yaml
- prod：knowledge-service-routing-prod.yaml

Group：
- KNOWLEDGE_SERVICE

字段（MVP 必须）：
- apps[].app_code
- apps[].workspace_id
- apps[].knowledge_id
- apps[].application_id
- apps[].allow_callers
- apps[].auth.admin_token（dev 可明文；prod 使用 token_ref）
- apps[].auth.application_api_key（dev 可明文；prod 使用 token_ref）

workspace 调试入口映射：
- workspaces[].workspace_id
- workspaces[].default_app_code
- workspaces[].default_knowledge_id

## 9. Redis 规范（MVP）

### 7.1 队列与调度（按 app_code 分队列 + 活跃轮询）
- ingest:queue:{app_code}（List，job_id FIFO）
- ingest:apps:rr（List，活跃 app_code 轮询队列）
- ingest:apps:rr:lock:{app_code}（String，SETNX 去重锁，TTL）
- ingest:apps:active（ZSet，score=最近活跃时间，用于清理陈旧 app）
- ingest:sem:{app_code}（String，运行中 job 计数，限制 per_app_running_jobs）
- ingest:req:{caller_system}:{request_id}（String，SETNX 幂等映射，TTL）

### 7.2 Job 进度缓存
- ingest:job:{job_id}（Hash：status/progress/summary/updated_at，TTL 24h）

## 10. DB 规范（MVP）

### 8.1 ingest_job（主表）
建议字段：
- job_id
- app_code
- workspace_id
- knowledge_id
- caller_system
- request_id
- status
- total_files/processed_files/success_files/failed_files/created_documents
- created_at/updated_at

### 8.2 ingest_job_file（明细表）
建议字段：
- id
- job_id
- filename/size/sha256
- storage_uri（MinIO 对象定位）
- status（PENDING/SUCCESS/FAILED）
- error_code/error_message
- source_file_id（可选）
- document_id（成功后回填）
- created_at/updated_at

## 11. MaxKB 内部调用规范

### 11.1 认证格式（必须统一）
- MaxKB 链路统一使用：Authorization: Bearer <token>
- 不要混用其它外部服务的 header 写法
- dev 配置建议存“裸 token”，由服务端代码统一拼接 `Bearer `

### 11.2 写入知识库（admin）
- split：
  POST {MAXKB_BASE_URL}/admin/api/workspace/{workspace_id}/knowledge/{knowledge_id}/document/split
- batch_create：
  PUT  {MAXKB_BASE_URL}/admin/api/workspace/{workspace_id}/knowledge/{knowledge_id}/document/batch_create

Authorization：Bearer <admin_token>

### 11.3 输出结论（chat）
- chat/completions：
  POST {MAXKB_BASE_URL}/chat/api/{application_id}/chat/completions

Authorization：Bearer <application_api_key>

## 12. 本地开发（dev-local）

### 12.1 端口建议
- MaxKB：127.0.0.1:8080
- Knowledge-Service：127.0.0.1:9000
- Nginx：127.0.0.1:8088（/ai/* -> 9000）
- Nacos：127.0.0.1:8848
- MinIO：127.0.0.1:9001
- Redis：127.0.0.1:6379

### 12.2 dev 安全建议
- dev 可使用明文 token/key，但不得提交仓库、不得截图传播
- 生产必须 token_ref + 密钥管理（Vault/KMS）与最小权限服务账号

## 13. 上线检查项（MVP）
- MaxKB 不暴露 /admin 与 /chat 给业务系统（仅内网）
- 平台网关禁止外部访问 MaxKB 内部管理路径
- 平台后端限流开启（按 app_code + caller_system）
- 幂等键 request_id 生效（防止重试风暴）
- worker 并发受控（per_app_running_jobs 生效）
- MinIO 生命周期策略设置（防止 job 文件无限增长）
