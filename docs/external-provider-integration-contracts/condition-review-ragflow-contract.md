# 条件审查平台接入 RAGFlow 契约

本文把条件审查平台接入 RAGFlow 的第一阶段契约写成可执行边界，供后续规格、实现、联调、验收统一使用。

provider readiness、安全诊断和 source-of-truth 定稿细则见：

- `provider-readiness-and-source-of-truth.md`

## 1. 目标

第一阶段的目标不是让 RAGFlow 接管条件审查流程，而是让它稳定承担以下职责：

- 知识库数据集承载
- 文档解析、分块、索引
- 检索召回
- 引用片段与来源返回
- 可选的 OpenAI-compatible 对话接口

平台自身继续承担：

- 流程状态
- 事实模型
- 人工结论
- 报告资产
- 审计记录

一句话约束：

> RAGFlow 是检索与知识库 provider，不是条件审查平台的事实库、流程引擎或合规结论来源。

## 2. 第一阶段推荐能力边界

下游项目第一阶段只接这四类能力：

### 2.1 健康检查

- `GET /api/v1/system/ping`
- `GET /api/v1/system/healthz`

### 2.2 鉴权后的模型与配置检查

- `GET /api/v1/models`

### 2.3 检索测试

- `POST /api/v1/searchbots/retrieval_test`

### 2.4 OpenAI-compatible Chat

- `POST /api/v1/openai/{chat_id}/chat/completions`

## 3. Source of Truth 边界

以下内容必须由条件审查平台持有并负责：

- 审查流程状态
- 发布后的依据版本
- 项目主数据
- 材料事实记录
- 人工审核结论
- 检查项结果
- 报告资产

RAGFlow 允许持有：

- dataset
- document
- chunk
- embedding
- retrieval score
- snippet
- provider-side metadata

但这些内容只能作为：

- 支持性召回
- 解释性引用
- provider refs

不能直接作为正式事实或最终结论。

## 4. 推荐接入方式

### 4.1 平台侧维护

平台需要持有自己的知识库绑定记录，例如：

```ts
type KnowledgeBaseBinding = {
  knowledgeBaseId: string;
  organizationId: string;
  contractPackageId: string;
  subcontractTeamId: string;
  provider: "ragflow";
  providerDatasetIds: string[];
  syncStatus: "ready" | "provisional" | "stale" | "blocked" | "unreachable";
  updatedAt: string;
};
```

### 4.2 RAGFlow 侧维护

RAGFlow 内部维护：

- dataset 本体
- 文档索引副本
- 分块与向量
- 检索接口

### 4.3 推荐调用路径

1. 平台根据 `knowledgeBaseId` 找到 `providerDatasetIds`
2. 平台发起 retrieval test 或 chat 请求
3. 平台接收返回片段、来源和 provider refs
4. 平台把结果归一化为安全摘要，供人工审核或规则引擎使用

## 5. 鉴权与环境变量

第一阶段统一使用 API Key，服务端保存：

- `RAGFLOW_BASE_URL`
- `RAGFLOW_API_KEY`
- `RAGFLOW_ENABLED`
- `RAGFLOW_TIMEOUT_MS`

推荐保持以下约束：

- API key 只在服务端使用
- 不暴露给浏览器端
- 不进入前端日志
- 不进入报表输出
- 不进入 provider diagnostics 明文

## 6. 请求契约

## 6.1 Retrieval 请求

推荐平台内部统一成这样的调用语义：

```ts
type RetrievalRequest = {
  workspaceId: string;
  knowledgeBaseId: string;
  providerDatasetIds: string[];
  query: string;
  topK: number;
  correlationId: string;
  filters?: {
    organizationId?: string;
    contractPackageId?: string;
    subcontractTeamId?: string;
    basisVersionId?: string;
    documentTypes?: string[];
    masterDataIds?: string[];
  };
};
```

映射到当前 RAGFlow 第一阶段接口时，最小请求体可为：

```json
{
  "kb_ids": ["dataset_id_1", "dataset_id_2"],
  "question": "请说明该分包队伍是否满足开工条件，并给出最相关的依据材料",
  "top_k": 5
}
```

### 6.2 Retrieval 返回归一化

平台侧建议把 provider 响应归一化为：

```ts
type RetrievalHit = {
  provider: "ragflow";
  providerDatasetId: string;
  providerDocumentId?: string;
  providerChunkId?: string;
  title: string;
  safeSnippet: string;
  score?: number;
  locator?: string;
  sourceObjectId?: string;
  contentHash?: string;
  pageNumber?: number;
  chunkIndex?: number;
  indexedAt?: string;
  providerUpdatedAt?: string;
  evidenceIds?: string[];
  masterDataIds?: string[];
};
```

### 6.3 Chat 请求

当需要做解释性对话时，统一使用：

```json
{
  "model": "your-model-name",
  "messages": [
    {
      "role": "user",
      "content": "请根据当前知识库，解释这家分包队伍在资质、材料和依据版本上的主要风险点。"
    }
  ],
  "stream": false
}
```

第一阶段要求：

- 只作为解释辅助
- 不直接替代审查结论
- 最终结果仍由平台规则和人工审核确认

## 7. Metadata 约束

为了后续 stale 判定、追溯和过滤，建议文档/分块 metadata 至少保留：

- `organization_id`
- `contract_package_id`
- `subcontract_team_id`
- `basis_version_id`
- `document_type`
- `source_object_id`
- `content_hash`
- `master_data_ids`
- `evidence_ids`

第一阶段即便当前 RAGFlow 页面或脚本未完全显式写全，也应先在契约中固化这些字段。

## 8. Dataset 粒度建议

第一阶段优先推荐：

### 小规模试点

- 一个分包队伍一个 dataset

优点：

- 隔离简单
- 权限和范围更直观
- 联调成本低

### 后续扩展

- 一个项目 / 合同包一个 dataset
- 使用 metadata 过滤 `subcontract_team_id`、`basis_version_id`、`document_type`

不论哪种方式，平台都必须保存自己的：

- `knowledgeBaseId -> providerDatasetIds`

映射关系。

## 9. Stale 判定规则

以下情况应把平台知识库绑定标记为 `stale`：

- 平台原始材料更新，但 RAGFlow 尚未重新索引
- 主数据更新后，provider metadata 未同步
- 依据版本更新后，旧 dataset 仍参与召回
- provider document/chunk 不存在
- 解析失败或部分索引失败
- embedding/rerank 模型切换导致旧索引需要重建

## 10. 错误语义

平台应统一将 provider 状态归为：

- `ready`
- `disabled`
- `degraded`
- `error`
- `stale`
- `unreachable`

建议含义：

- `disabled`: 未启用 provider
- `degraded`: 可用但能力不完整
- `error`: provider 配置或调用出错
- `stale`: 数据可能过期
- `unreachable`: 网络或服务不可达

## 10.1 Provider readiness 补充要求

除状态本身外，第一阶段还应补充：

- `configured`
- `ready`
- `version`
- `capabilities`
- `correlationId`
- `safeDiagnostics`

其中：

- `capabilities` 用于表达当前 provider 是否具备 retrieval、ingestion、documentStatus、metadataFilter、rerank、openaiCompatibleChat 等能力
- `safeDiagnostics` 只能包含安全摘要，不能携带密钥、原始文本、原始 payload 或私有 URL

## 11. 第一阶段非目标

这一轮明确不做：

- 让 RAGFlow 直接输出正式审查结论
- 让 RAGFlow 持有流程状态
- 多 provider 自动路由
- 复杂 SDK 封装
- RAGFlow Agent 直接接管审查流程
- 昇腾专属业务代码改造

## 12. 验收标准

满足以下条件视为第一阶段契约成立：

1. 平台知道应该调用哪些接口
2. 平台知道 dataset 如何组织
3. 平台知道哪些字段属于 provider refs，哪些属于平台事实
4. 平台知道何时标记 stale / degraded / unreachable
5. 后续只替换模型后端，不推翻接入方式

## 13. 与昇腾迁移的稳定性约束

后续迁移到昇腾时，允许替换的是模型服务后端，不允许推翻的是对外集成契约。

也就是说：

- 可替换：LLM / Embedding / Rerank / OCR 的实际部署形态
- 不替换：provider health 语义、provider refs 语义、平台事实边界

这样才能保证本地联调、下游接入、后续上昇腾三者使用同一套外部合同。
