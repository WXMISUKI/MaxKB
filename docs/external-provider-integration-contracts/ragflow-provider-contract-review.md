# RAGFlow Provider Contract Review

本文评审 `external-provider-integration-contracts` 当前需求是否适合让条件审查平台接入 RAGFlow 能力。

## 结论

当前需求总体合理，且与本仓库对 RAGFlow 的服务化定位一致：

- 条件审查平台保留流程状态、事实模型、人工结论、报告资产和审计记录。
- RAGFlow 只作为外部 RAG/知识库 provider，负责数据集、文档、分块、索引、检索和引用支持。
- Provider 输出必须先被平台归一化为安全摘要、provider refs 或平台自有记录，不能直接成为正式审查结论。
- Provider 缺失或不可用时，平台应降级为 disabled/degraded，不影响无关功能。

这个边界是企业级集成里最重要的部分：RAGFlow 可以增强证据召回和材料解释，但不能成为条件审查平台的事实库、流程引擎或合规结论来源。

## 合理点

### 1. Source of truth 边界清晰

`design.md` 明确平台事实仍包括：

- Published basis versions。
- Published 或 human-approved project master data。
- Evidence records and object references。
- Human-review decisions。
- Check item outcomes and report assets。

这避免了把 RAGFlow metadata、检索分数或模型回答误用为正式事实。

### 2. Provider adapter 方向正确

统一的 `ProviderHealth`、`RetrievalRequest`、`RetrievalHit` 抽象是合理的。它能让 RAGFlow、OCR、LLM、agent worker、storage、queue 都走类似的健康检查、鉴权、诊断和审计链路。

### 3. 安全诊断要求必要

spec 要求隐藏 API keys、auth headers、raw document text、prompts、provider traces、private URLs、cookies、sessions 和 unbounded payloads。这一点必须保留，尤其是条件审查平台会处理合同、组织、人员和材料数据。

### 4. 外部知识库绑定方式合理

平台知识库记录保存 provider dataset/document/chunk refs，而不是把 RAGFlow dataset 当作平台知识库本体。这适合后续：

- 切换 RAGFlow 或其他 RAG provider。
- 重新索引。
- 标记 provider refs stale。
- 做审计和追溯。

### 5. 不默认启用外部 provider 是对的

`RAGFLOW_ENABLED=true|false`、缺失配置时报 disabled/unconfigured，这对本地开发、离线环境和分阶段交付都更稳。

## 建议补充

### 1. 增加 provider version 与 capability discovery

健康检查建议补充：

```ts
type ProviderCapability = {
  retrieval?: boolean;
  ingestion?: boolean;
  documentStatus?: boolean;
  chunkListing?: boolean;
  metadataFilter?: boolean;
  rerank?: boolean;
  streaming?: boolean;
};
```

原因：RAGFlow API、OpenAI-compatible 网关、rerank 服务和未来 agent worker 的能力并不完全一致。只判断 ready 不够，平台还需要知道当前 provider 支持哪些能力。

### 2. 明确数据集粒度策略

`Open Questions` 中“一个 subcontract team 一个 dataset，还是一个 project/contract package 一个 dataset + metadata filters”很关键。

建议第一阶段采用：

- 小规模试点：一个 subcontract team 一个 RAGFlow dataset，隔离最简单。
- 项目规模扩大后：一个 project/contract package 一个 dataset，使用 metadata 过滤 subcontract team、basis version、document type。

无论哪种方式，平台都必须保存自身的 `knowledgeBaseId -> providerDatasetIds` 映射。

### 3. 增加 provider refs stale 规则

建议定义何时把外部知识库标记为 stale：

- 平台证据文件更新但 RAGFlow 未完成重索引。
- 平台 master data 或 basis version 更新后，旧 dataset/chunk metadata 未同步。
- RAGFlow 文档解析失败、部分分块失败或 embedding 模型变更。
- providerDatasetId 不存在或 retrieval 健康检查失败。

### 4. 明确 MinIO 是 canonical object storage

当前 design 已提到“MinIO as canonical object storage”。建议在 spec 中也写成 requirement：

- 原始文件、正式证据附件和报告资产以平台对象存储为准。
- RAGFlow 中的文件副本只用于索引和检索。
- RAGFlow 返回的 providerDocumentId 不能替代平台 `sourceObjectId`。

### 5. 增加 retrieval hit 的引用完整性要求

`RetrievalHit` 建议补充：

```ts
contentHash?: string;
pageNumber?: number;
chunkIndex?: number;
providerUpdatedAt?: string;
indexedAt?: string;
```

原因：条件审查场景需要可追溯。只有 `safeSnippet` 和 `locator` 不一定足以复核。

### 6. 明确 LLM 与 RAG 的职责拆分

建议加入一条规则：

- RAG provider 负责 recall。
- LLM provider 负责 extraction/reasoning/drafting。
- 平台负责 validation/state/report。

这样能避免后续让 RAGFlow Chat/Agent 直接输出审查结论。

## 对 RAGFlow 侧的落地建议

RAGFlow 适合提供：

- Dataset 创建或绑定。
- Document 上传、解析、分块状态查询。
- Chunk refs 和 retrieval hits。
- 引用来源、页码、chunk id、文档 metadata。

RAGFlow 不应提供：

- 条件审查流程状态。
- 正式检查项结论。
- 人工审批状态。
- 报告事实源。
- 平台权限模型。

## 第一阶段推荐集成范围

第一阶段只做最小闭环：

1. 平台配置 `RAGFLOW_BASE_URL`、`RAGFLOW_API_KEY`、`RAGFLOW_ENABLED`。
2. 平台健康检查展示 RAGFlow configured/ready/status/version/capabilities。
3. 平台知识库记录绑定一个 RAGFlow dataset。
4. 平台上传或同步文档到 RAGFlow。
5. 平台调用 retrieval，只保存 safe snippet、provider refs、score、locator、sourceObjectId。
6. 平台把检索结果作为“支持性召回”，交给人工审查或平台规则使用。

暂不建议第一阶段做：

- 让 RAGFlow Agent 直接执行审查流程。
- 让 RAGFlow metadata 替代平台主数据。
- 多 provider 自动路由。
- 自动生成正式结论并跳过人工确认。

## 总体判断

这份需求可以作为条件审查平台接入 RAGFlow 的基础合同。需要补强的是 capability discovery、dataset 粒度策略、stale 判定、引用完整性和 MinIO canonical storage 的硬约束。只要这些点补上，整体架构方向是稳的。

## 下一阶段建议

从最能推进项目、最有价值、最能快速投产的角度看，下一阶段建议按下面的顺序推进：

1. **先做规格，不先扩实现面**
   - 先把条件审查平台真正要调用的接口、鉴权、dataset 约束、provider refs 和 stale 规则定稿。
   - 这是当前最短板，也是后续一切实现的边界条件。

2. **再做最小实现闭环**
   - 只做能证明接入成功的最小链路：
     - health
     - auth
     - retrieval
     - OpenAI-compatible chat
   - 不在这一轮做重型 SDK、复杂 agent orchestration 或多 provider 自动路由。

3. **最后做归档和迁移约束**
   - 把本地联调、数据准备、昇腾切换约束、provider bootstrap 和故障排查写清楚。
   - 这样下游项目接入不再依赖口头解释。

一句话收束：

> 先固定服务边界，再验证最小闭环，最后把验证过的路径沉淀成可复用资产。
