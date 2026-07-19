# Provider Readiness 与事实边界定稿

本文用于把条件审查平台接入 RAGFlow 时最容易跑偏的两件事定稿：

- provider readiness / health 到底应该返回什么
- 哪些数据属于平台事实，哪些只能算 provider refs 或支持性召回

这份文档用于收口 Task A3、A4，并作为后续实现 B1、B4、B5 的统一边界。

## 1. 结论先行

对于条件审查平台：

- `RAGFlow` 是外部知识库与检索 provider
- `RAGFlow` 不是流程状态 owner
- `RAGFlow` 不是正式事实库
- `RAGFlow` 不是合规结论来源

因此平台需要两套并存但不混淆的数据：

1. 平台自有事实
2. provider 可替换引用

readiness 只报告 provider 当前是否可安全调用，不能借机泄露密钥、原文、提示词或私有内部实现细节。

## 2. Provider readiness 定稿

### 2.1 ProviderCapability

建议平台内部统一以下能力声明：

```ts
type ProviderCapability = {
  retrieval: boolean;
  ingestion: boolean;
  documentStatus: boolean;
  chunkListing: boolean;
  metadataFilter: boolean;
  rerank: boolean;
  openaiCompatibleChat: boolean;
  modelListing: boolean;
  streaming: boolean;
};
```

说明：

- `retrieval`: 是否支持检索召回
- `ingestion`: 是否支持文档入库或同步
- `documentStatus`: 是否支持文档解析/索引状态查询
- `chunkListing`: 是否支持 chunk 级引用或枚举
- `metadataFilter`: 是否支持 metadata 过滤
- `rerank`: 是否具备重排能力
- `openaiCompatibleChat`: 是否开放 OpenAI-compatible chat
- `modelListing`: 是否可列出模型或 provider 能力
- `streaming`: 是否支持流式输出

### 2.2 ProviderHealth

建议平台统一以下 readiness envelope：

```ts
type ProviderHealth = {
  provider: "ragflow" | "ocr" | "llm" | "minio" | "agent_worker" | "queue";
  configured: boolean;
  ready: boolean;
  status: "ready" | "disabled" | "degraded" | "error" | "stale" | "unreachable";
  summary: string;
  version?: string;
  capabilities?: ProviderCapability;
  correlationId?: string;
  safeDiagnostics?: Record<string, unknown>;
};
```

### 2.3 状态语义

- `disabled`: 当前环境未启用该 provider
- `ready`: 已配置且满足当前场景所需最小能力
- `degraded`: 可达，但部分能力不可用或结果不完整
- `error`: 配置错误、鉴权错误或 provider 业务错误
- `stale`: provider 数据或索引副本可能过期
- `unreachable`: 网络、容器、DNS、反向代理或上游服务不可达

### 2.4 条件审查平台最小 ready 标准

对 `ragflow` provider，第一阶段 `ready=true` 的最小标准建议为：

1. API 可达
2. API key 可用
3. 至少能成功执行一次模型/能力探测
4. 至少具备 `retrieval=true`
5. 若下游要走解释性对话，再额外要求 `openaiCompatibleChat=true`

## 3. Safe diagnostics 定稿

### 3.1 允许暴露的安全信息

建议只允许以下信息进入 `safeDiagnostics`：

- provider 名称
- 部署模式标签
- provider 版本
- timeout 配置
- 最近一次成功时间
- 最近一次探测延迟
- 已配置数据集数量
- 当前能力布尔值
- 模型名列表或安全标签
- 错误类型和安全错误码
- 当前是否命中 stale / degraded / unreachable

### 3.2 禁止暴露的信息

以下内容不得进入 readiness、前端可见接口、操作台摘要、审计摘要或报表：

- API keys
- Bearer tokens
- cookies / sessions
- 原始 Authorization headers
- 原始 prompt
- 原始用户提问
- 原始 retrieval payload
- 文档全文
- chunk 原文
- 私有下载 URL
- presigned URL
- 内部 trace 原文
- provider 原始异常堆栈全文

### 3.3 推荐做法

- diagnostics 用 allowlist，而不是 denylist
- 错误只保留 `errorType`、`errorCode`、`summary`
- URL 只保留逻辑标签，例如 `ragflow-local-dev`、`ragflow-prod-cn`
- 模型信息优先暴露模型名，不暴露供应商私有凭据

## 4. 审计关联定稿

每次 provider 调用都建议携带并回收以下关联字段：

- `correlationId`: 平台生成，贯穿一次业务请求
- `knowledgeBaseId`: 平台知识库主键
- `providerDatasetIds`: 仅作为 provider refs
- `workspaceId` / `organizationId`
- `basisVersionId`
- `subcontractTeamId`

允许记录的 provider 侧附加摘要：

- `providerRequestId`
- `latencyMs`
- `providerVersion`
- `resultCount`
- `status`

不建议记录：

- 原始文本输入
- 原始文本输出
- 未裁剪 provider 响应

## 5. Source of truth 边界定稿

### 5.1 平台是正式事实 owner

以下内容必须由条件审查平台持有并负责：

- 审查流程状态
- 已发布依据版本
- 项目主数据
- 证据对象引用
- 人工审核结论
- 检查项结果
- 报告资产

### 5.2 RAGFlow 只持有可替换副本和引用

RAGFlow 可以持有：

- dataset
- document
- chunk
- embedding
- rerank score
- snippet
- provider-side metadata

但这些内容只能作为：

- 支持性召回
- 检索证据引用
- provider refs
- 解释性上下文

### 5.3 边界矩阵

| 数据项 | 平台是否权威 | RAGFlow 是否可保存 | 备注 |
| --- | --- | --- | --- |
| 审查流程状态 | 是 | 否 | provider 不得持有正式流程状态 |
| 依据版本发布状态 | 是 | 否 | provider metadata 不能替代 basis fact |
| 项目主数据 | 是 | 可保存副本 | 仅供过滤与检索 |
| 证据对象引用 | 是 | 可保存副本 | 以平台对象存储记录为准 |
| dataset/document/chunk id | 否 | 是 | 只能作为 provider refs |
| 检索分数 | 否 | 是 | 不得直接成为审查结论 |
| 模型回答 | 否 | 是 | 仅用于解释辅助 |
| 报告资产 | 是 | 否 | 最终报告由平台持有 |

## 6. Provider refs 定稿

平台应显式区分：

- 平台主键
- provider refs

建议 provider refs 至少覆盖：

```ts
type DatasetRef = {
  provider: "ragflow";
  providerDatasetId: string;
};

type DocumentRef = {
  provider: "ragflow";
  providerDatasetId: string;
  providerDocumentId: string;
  sourceObjectId?: string;
};

type ChunkRef = {
  provider: "ragflow";
  providerDatasetId: string;
  providerDocumentId?: string;
  providerChunkId?: string;
  locator?: string;
  contentHash?: string;
  pageNumber?: number;
  chunkIndex?: number;
};
```

这些 ref 用来：

- 追踪召回来源
- 做 stale 判断
- 做重索引与对账

这些 ref 不能用来：

- 替代平台事实主键
- 代替正式证据记录
- 直接生成最终审查结论

## 7. 与昇腾迁移的关系

这份合同对后续昇腾迁移的约束是：

> 保持外部服务合同稳定，只替换模型服务后端。

也就是说后续切到昇腾时，只允许变化：

- LLM endpoint
- embedding endpoint
- rerank endpoint
- OCR / multimodal endpoint
- 部署容器与运行时

不允许变化：

- 平台对 RAGFlow 的 provider 接入边界
- provider health 返回语义
- provider refs 语义
- source-of-truth 归属

## 8. 当前仓库中的参考实现资产

本仓库已提供对应参考资产：

- `tools/ragflow-service/provider_contract.py`
- `tools/ragflow-service/normalize_ragflow_retrieval.py`
- `tools/ragflow-service/provider-health.example.json`
- `tools/ragflow-service/normalized-retrieval-hits.example.json`

这些资产用于让后续下游项目在不直接复制平台代码的前提下，对齐：

- readiness DTO
- provider refs
- retrieval hit 归一化
- safe diagnostics 边界

## 9. 本轮定稿结论

到这一版为止，Task A3 与 A4 的边界可视为收口：

- readiness 不是“能不能访问一个 URL”这么简单，而是“能否安全地完成当前最小业务能力”
- RAGFlow 不是事实 owner，任何 provider 数据都必须先经过平台归一化，才能进入业务链路

后续实现如果偏离本文，优先回到本文做收敛，而不是继续引入新的临时口径。
