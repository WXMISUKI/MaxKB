# MaxKB 统一网关接入规范（Nacos + OpenAI + MCP）

## Context

当前项目已经明确采用以下平台化路线：

- MaxKB 作为统一智能体平台内核
- 单实例部署，按 `workspace` 做业务域隔离
- 对外默认按 `app_code` 路由，必要时保留 `workspace` 维度辅助治理
- 网关统一鉴权，MaxKB 作为内网能力服务
- 对外同时提供：
  - OpenAI-Compatible 接口
  - MCP 工具接口
- 路由映射与限流策略统一由 Nacos 配置中心维护

本规范的目标，是在 **不修改 MaxKB 核心代码** 的前提下，先完成企业级统一接入的 M0 版本。

---

## Goals / Non-Goals

**Goals**

- 定义 Nacos 中 `app_code -> MaxKB 应用` 的配置规范
- 定义网关对 OpenAI 与 MCP 的统一对外路由规则
- 定义网关到 MaxKB 的鉴权透传方式
- 定义限流、审计、调用方隔离的最低要求
- 给接入方提供统一的接入说明书

**Non-Goals**

- 本阶段不新增 MaxKB 核心 API
- 本阶段不引入独立 AI Gateway 业务服务
- 本阶段不建设“纯知识库级”统一开放平台
- 本阶段不改变 MaxKB 现有工作流、知识库、应用模型

---

## Confirmed Decisions

1. **平台定位**
   - 采用“统一智能体平台”模式，不再按业务系统长期维护多个分支。

2. **对外协议**
   - 同时支持 `OpenAI-Compatible` 与 `MCP`。

3. **隔离模型**
   - 单实例 + `workspace` 隔离。

4. **能力粒度**
   - 应用级能力为主，知识库级能力为辅。

5. **鉴权模型**
   - 网关统一鉴权，内部信任转发。

6. **路由模型**
   - 默认按 `app_code` 路由，必要时可按 `workspace` 做治理与排障。

7. **配置中心**
   - 使用 Nacos 维护路由映射、协议开关、限流策略与调用方约束。

8. **落地方式**
   - 纯网关配置起步，不先改 MaxKB 代码。

---

## MaxKB 现有真实入口

### 1. 全局聊天 API 前缀

MaxKB 将聊天 API 挂载在：

- 默认前缀：`/chat/api/`

代码位置：

- [apps/maxkb/urls/web.py](file:///c:/project/tool/MaxKB/apps/maxkb/urls/web.py)
- [apps/chat/urls.py](file:///c:/project/tool/MaxKB/apps/chat/urls.py)

### 2. OpenAI-Compatible 真实入口

```text
POST /chat/api/{application_id}/chat/completions
```

代码位置：

- [apps/chat/urls.py](file:///c:/project/tool/MaxKB/apps/chat/urls.py)
- [apps/chat/views/chat.py](file:///c:/project/tool/MaxKB/apps/chat/views/chat.py)

说明：

- `application_id` 必须与 Bearer Token 对应的应用一致
- 认证类为 `ChatTokenAuth`
- 当前可直接使用 `ApplicationApiKey.secret_key` 作为 Bearer Token

### 3. MCP 真实入口

```text
POST /chat/api/mcp
```

代码位置：

- [apps/chat/views/mcp.py](file:///c:/project/tool/MaxKB/apps/chat/views/mcp.py)
- [apps/chat/mcp/tools.py](file:///c:/project/tool/MaxKB/apps/chat/mcp/tools.py)

说明：

- MCP 入口通过 `Authorization: Bearer {application_api_key}` 完成认证
- 每个 API Key 对应一个已发布应用

### 4. 应用 API Key 认证能力

MaxKB 现有认证逻辑已支持：

- `Bearer application-*`
- `Bearer agent-*`

代码位置：

- [apps/common/auth/authenticate.py](file:///c:/project/tool/MaxKB/apps/common/auth/authenticate.py)
- [apps/common/auth/handle/impl/application_key.py](file:///c:/project/tool/MaxKB/apps/common/auth/handle/impl/application_key.py)

结论：

**M0 阶段网关无需自定义 MaxKB 认证逻辑，只需要在转发时自动注入 `ApplicationApiKey` 即可。**

---

## 对外统一契约

### 1. OpenAI-Compatible

对外统一暴露：

```text
POST /ai/apps/{app_code}/openai/v1/chat/completions
```

说明：

- `app_code` 为业务可读、稳定的应用标识
- 业务系统不得感知 MaxKB 的 `application_id`

### 2. MCP

对外统一暴露：

```text
POST /ai/apps/{app_code}/mcp
```

说明：

- 面向 Agent 编排、工具调用、IDE 集成场景
- 外部系统不直接访问 MaxKB 的 `/chat/api/mcp`

### 3. 保留的内部治理接口

内部可以保留：

```text
/ai/workspaces/{workspace}/...
```

但该路径仅用于：

- 内部调试
- 运维排障
- 后续知识库级能力扩展

不建议作为业务系统主接入契约。

---

## app_code 规范

### 1. 命名规则

建议采用：

- 全小写
- 单词间用 `-`
- 语义清晰、可长期稳定

示例：

- `sec-guard-assistant`
- `construction-plan-assistant`
- `construction-kb-search`

### 2. 管理原则

- `app_code` 对外稳定，不随 MaxKB 应用重建而变化
- `app_code -> application_id` 的映射由平台维护
- 调用方系统只允许使用 `app_code`

---

## Nacos 配置规范

### 1. 建议 DataId

```text
ai-gateway-app-routing.yaml
```

可按环境拆分：

```text
ai-gateway-app-routing-dev.yaml
ai-gateway-app-routing-test.yaml
ai-gateway-app-routing-prod.yaml
```

### 2. 建议 Group

```text
AI_GATEWAY
```

### 3. YAML 结构

```yaml
version: 1
maxkb:
  base_url: "http://maxkb-web:8080"
  chat_api_prefix: "/chat/api"

apps:
  - app_code: "sec-guard-assistant"
    workspace_id: "security"
    maxkb_application_id: "3f0b7d5e-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    maxkb_api_key: "${enc:xxxx}"
    protocols:
      openai: true
      mcp: true
    route_policy:
      enabled: true
      gray_tags: []
    rate_limit:
      rps: 20
      burst: 40
    allow_callers:
      - "sec-platform"
      - "audit-platform"

  - app_code: "construction-plan-assistant"
    workspace_id: "construction"
    maxkb_application_id: "a18c9f22-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    maxkb_api_key: "${enc:yyyy}"
    protocols:
      openai: true
      mcp: true
    route_policy:
      enabled: true
      gray_tags: []
    rate_limit:
      rps: 10
      burst: 20
    allow_callers:
      - "construction-platform"
```

### 4. 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `version` | 是 | 配置版本号，便于后续兼容 |
| `maxkb.base_url` | 是 | MaxKB 内网访问地址 |
| `maxkb.chat_api_prefix` | 是 | 聊天 API 前缀，默认 `/chat/api` |
| `apps[].app_code` | 是 | 对外稳定应用标识 |
| `apps[].workspace_id` | 是 | 所属业务域 |
| `apps[].maxkb_application_id` | 是 | MaxKB 应用 UUID |
| `apps[].maxkb_api_key` | 是 | MaxKB 应用 API Key，建议密文 |
| `apps[].protocols.openai` | 是 | 是否开放 OpenAI 接口 |
| `apps[].protocols.mcp` | 是 | 是否开放 MCP 接口 |
| `apps[].route_policy.enabled` | 是 | 是否可路由 |
| `apps[].rate_limit` | 是 | 限流策略 |
| `apps[].allow_callers` | 否 | 允许调用的系统列表 |

### 5. 安全要求

- `maxkb_api_key` 必须使用加密配置，不允许明文写入仓库
- Nacos 中涉及密钥的配置，必须开启访问控制
- 生产环境仅允许网关读取该配置

---

## 网关路由规则

### 1. OpenAI-Compatible 路由

#### 外部入口

```text
POST /ai/apps/{app_code}/openai/v1/chat/completions
```

#### 内部转发目标

```text
POST {maxkb.base_url}{maxkb.chat_api_prefix}/{maxkb_application_id}/chat/completions
```

#### 转发时必须注入的 Header

```text
Authorization: Bearer {maxkb_api_key}
X-Caller-System: {caller_system}
X-Request-Id: {request_id}
```

#### 可选 Header

```text
X-User-Id: {user_id}
X-User-Name: {user_name}
X-Trace-Id: {trace_id}
```

### 2. MCP 路由

#### 外部入口

```text
POST /ai/apps/{app_code}/mcp
```

#### 内部转发目标

```text
POST {maxkb.base_url}{maxkb.chat_api_prefix}/mcp
```

#### 转发时必须注入的 Header

```text
Authorization: Bearer {maxkb_api_key}
X-Caller-System: {caller_system}
X-Request-Id: {request_id}
```

### 3. 路由前校验规则

网关收到请求后，应按以下顺序处理：

1. 校验外部 JWT / 签名
2. 解析 `app_code`
3. 从 Nacos 获取路由配置
4. 校验：
   - `app_code` 是否存在
   - 路由是否启用
   - 协议是否允许
   - `caller_system` 是否在白名单中
5. 注入内部鉴权 Header
6. 转发到 MaxKB

---

## 鉴权与信任链

### 1. 外部鉴权

外部系统仅对接网关：

- JWT
- HMAC 签名
- 企业统一身份网关

三者任选其一，但都在网关完成校验。

### 2. 内部信任

MaxKB 不对外开放，只信任来自网关的内网流量。

建议至少满足以下任一项：

- 内网白名单
- mTLS
- WAF / Ingress 内部路由隔离

### 3. 推荐原则

- 外部身份不直接透传为 MaxKB 用户 Token
- 网关转发时统一使用 MaxKB 的 `ApplicationApiKey`
- 用户身份只作为审计补充信息，不作为 M0 主鉴权模型

---

## 限流规范

### 1. 限流维度

建议至少支持：

- `app_code`
- `caller_system`
- `workspace_id`

### 2. 限流策略建议

优先按：

```text
app_code + caller_system
```

做组合限流。

### 3. 建议行为

- 超限返回标准网关错误码
- 响应中返回 `request_id`
- 网关记录限流命中日志

---

## 审计字段规范

建议网关统一记录以下字段：

- `request_id`
- `trace_id`
- `caller_system`
- `app_code`
- `workspace_id`
- `protocol` (`openai` / `mcp`)
- `status_code`
- `latency_ms`
- `request_time`
- `response_time`
- `rate_limit_hit`
- `upstream_target`

如果能从响应中采集，可补充：

- `token_usage`
- `model_name`

### 安全要求

- 不记录明文 `Authorization`
- 不记录完整 prompt 与知识库原文
- 如需调试，只记录脱敏摘要或开关式采样日志

---

## 接入说明书

### 1. 面向业务系统接入方

#### OpenAI-Compatible 接入

调用地址：

```text
POST /ai/apps/{app_code}/openai/v1/chat/completions
```

业务方只需要提供：

- 业务系统身份凭证（JWT / 签名）
- `app_code`
- 标准 OpenAI 风格请求体

业务方不需要知道：

- MaxKB 的 `application_id`
- MaxKB 的 `ApplicationApiKey`
- MaxKB 的内部部署地址

#### MCP 接入

调用地址：

```text
POST /ai/apps/{app_code}/mcp
```

支持标准 JSON-RPC：

- `initialize`
- `tools/list`
- `tools/call`

### 2. 面向平台运维方

新增一个可接入应用时，流程如下：

1. 在 MaxKB 中创建并发布应用
2. 为该应用生成 `ApplicationApiKey`
3. 确定对外 `app_code`
4. 在 Nacos 中新增映射配置
5. 为网关配置对应限流、调用方白名单
6. 验证：
   - OpenAI 路由是否正常
   - MCP 路由是否正常
   - 审计日志是否完整

### 3. 面向 MaxKB 平台管理员

需要维护的不是“每个业务项目一套分支”，而是：

- workspace 规划
- 应用发布管理
- API Key 生命周期管理
- Nacos 中的 `app_code` 映射

---

## M0 / M1 边界

### M0（当前阶段）

特点：

- 不改 MaxKB 核心代码
- 以应用级能力输出为主
- 通过 Nacos + 网关完成统一接入

### M1（后续增强）

以下场景再考虑改 MaxKB：

1. 纯知识库级统一开放 API
2. 基于内部 Header 的可信网关直通认证
3. 更稳定的 MCP 工具名管理
4. 更细粒度的应用级审计回传

---

## Recommended Rollout

### Phase 1

- 先打通两个示范应用：
  - `sec-guard-assistant`
  - `construction-plan-assistant`

### Phase 2

- 纳入统一审计与限流
- 接入 2~3 个真实业务系统

### Phase 3

- 评估是否需要建设 M1 能力
- 决定是否需要自研轻量 AI Gateway 服务

---

## Final Recommendation

在当前已确认的组织与技术决策下，**MaxKB 可以作为企业级统一智能体平台内核使用**。  
当前最应该优先做的不是继续开业务分支，而是先落实：

1. `app_code` 统一契约  
2. Nacos 路由配置  
3. 网关统一鉴权与转发  
4. 限流与审计  

只要这四块到位，你们就已经从“项目化接入”进入“平台化接入”。
