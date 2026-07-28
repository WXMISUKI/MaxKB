# RAG 与知识图谱 / GraphRAG 市场与产品调研

更新时间：2026-07-28  
调研范围：GraphRAG 市场定位、向量检索与知识图谱结合的优缺点与适用场景、阿里云百炼 / Knowledge Studio 相关官方产品与架构思路  
方法说明：优先采用官方产品页、官方文档、官方帮助中心；尽量避免二手转载。本文只做外部调研与归纳，不涉及仓库业务代码修改。

## 结论摘要

1. **当前市场并不是“普遍建议所有 RAG 都必须上知识图谱 / GraphRAG”**。更准确的说法是：主流官方资料越来越把 GraphRAG 视为一个重要增强方向，但通常仍把普通文本/向量 RAG 作为默认起点，把 GraphRAG 放在“关系驱动、多跳、全局总结、实体消歧”这类问题上使用。微软 Agent Framework 仍提供 `TextSearchProvider` 作为开箱即用的 RAG provider，同时将 GraphRAG 单独放到 Neo4j provider；Azure HorizonDB 也明确区分了“何时用 graph-augmented RAG”与“何时用 vector-only RAG”。  
来源：<https://learn.microsoft.com/en-in/agent-framework/agents/rag> ，<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

2. **GraphRAG 的市场趋势是“从可选增强，逐步进入企业知识系统的高级能力层”，而不是完全替代向量检索。** 微软 Discovery Bookshelf 的官方描述就是“一个 KB 同时包含 vector database 和 knowledge graph”；Neo4j 也明确说 GraphRAG 可以与 vector RAG 结合使用。  
来源：<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases> ，<https://graphacademy.neo4j.com/courses/workshop-genai/1-generative-ai/2-graphrag/>

3. **向量检索 + 知识图谱的组合价值主要来自“语义相关性”与“结构关系”两种信号的融合。** 官方常见组合方式包括：向量召回、rerank、图遍历、结果融合（如 RRF），用以覆盖纯向量检索不擅长的关系链、引用链、层级、因果、多跳推理和实体消歧。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag> ，<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag>

4. **它的主要代价不是模型调用本身，而是图构建、图维护、数据治理、查询编排和系统复杂度。** Azure HorizonDB 官方文档直接把“是否值得承担图构建成本”作为是否采用 graph-augmented RAG 的判断条件之一。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

5. **阿里云百炼当前公开主线能力，官方对外强调的是 RAG 知识库、语义/向量检索、工作流编排、数据连接、业务空间权限、多种云服务集成，而不是把知识图谱 / GraphRAG 作为知识库默认主架构公开宣讲。** 本次检索到的百炼官方文档中，知识库工作原理明确强调语义检索；与 AnalyticDB PostgreSQL 的官方方案也强调高性能向量检索引擎。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base> ，<https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/use-cases/build-exclusive-large-model-applications-through-alibaba-cloud>

6. **从产品架构视角看，百炼的知识增强体系更像“RAG 平台化”而不是“KG-first 平台化”**：前台是知识库、工作流、智能体、高代码应用；中台是业务空间、权限、API Key、OpenAPI；数据面是知识库 / 数据连接 / OSS / DMS / 数据库；执行面通过服务关联角色接入 FC、OSS、ADB-PG、MNS、DTS 等云服务。  
来源：<https://help.aliyun.com/zh/model-studio/what-is-model-studio> ，<https://help.aliyun.com/zh/model-studio/workflow-application> ，<https://help.aliyun.com/zh/model-studio/permission-management-overview> ，<https://help.aliyun.com/zh/model-studio/data-import-instructions> ，<https://help.aliyun.com/zh/model-studio/bailian-service-linked-role>

## 1. 当前市面上，RAG 是否普遍推荐结合知识图谱 / GraphRAG？

### 1.1 简短判断

**不应下“普遍推荐所有 RAG 都要上 GraphRAG”的结论。更稳妥的市场判断是：**

- **普通 RAG / 向量 RAG 仍是默认基础形态。** 微软 Agent Framework 把 `TextSearchProvider` 作为开箱即用实现，并说明搜索函数可接任意搜索技术；Graph RAG 作为单独章节，指向 Neo4j GraphRAG Provider，而不是默认替代文本/向量搜索。  
  来源：<https://learn.microsoft.com/en-in/agent-framework/agents/rag>

- **GraphRAG 正在被主流厂商明确产品化，但定位通常是场景增强。** 微软提供 GraphRAG 相关产品页、Neo4j 提供 GraphRAG provider 与教程，微软 Discovery 直接把 KB 设计成“vector database + knowledge graph”。这说明 GraphRAG 已经不是纯研究概念，而是企业知识系统的重要高级能力。  
  来源：<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag> ，<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases> ，<https://graphacademy.neo4j.com/courses/workshop-genai/1-generative-ai/2-graphrag/>

- **官方材料普遍强调“按问题类型选择”，而不是“一刀切”。** Azure HorizonDB 明确给出“Use graph-augmented RAG when / Use vector-only RAG when”的对照表：需要关系、多跳、结构权威性、实体消歧时用 graph-augmented；简单事实查找、单跳相似性、追求快速上线时用 vector-only。  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

### 1.2 市场信号如何解读

从官方资料看，GraphRAG 至少有三层市场信号：

1. **研究已进入产品化阶段。** 微软不仅有研究论文与开源 GraphRAG 项目，其产品文档已把 graph-based retrieval 变成实际产品能力或模式说明。  
来源：<https://graphrag.com/appendices/research/2404.16130/> ，<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases> ，<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

2. **图数据库厂商把它作为差异化主张。** Neo4j 官方强调 GraphRAG 的核心价值在于 graph traversal、hybrid search 和自定义 Cypher 查询，把它定位为比“孤立文本块召回”更丰富的上下文获取方式。  
来源：<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag>

3. **但通用 AI 平台仍保留 vector/text RAG 的主入口。** 这表明市场共识更接近“分层检索架构”而不是“GraphRAG 统治一切”。  
来源：<https://learn.microsoft.com/en-in/agent-framework/agents/rag> ，<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

## 2. 向量检索与知识图谱结合的优缺点、适用场景

### 2.1 主要优点

1. **能回答“关系决定答案”的问题。**  
纯向量检索擅长找语义相近文本，但当答案依赖实体间关系、层级、因果、引用链时，图遍历更合适。Azure HorizonDB 明确列出 citations、causal chains、organizational hierarchy、multihop reasoning、entity disambiguation 等场景。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

2. **更适合多跳推理与结构化权威性判断。**  
图可以把“谁依赖谁、谁引用谁、谁属于谁”显式化；这类结构重要但语义上可能并不相近的信息，纯向量检索容易漏掉。Azure HorizonDB 直接指出某些“结构上重要但语义距离较远”的结果，向量检索会低估。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

3. **更适合全局总结、主题归纳、语料级洞察。**  
Microsoft Discovery Bookshelf 官方写得很直接：其 Knowledge Base 同时包含 vector database 和 knowledge graph，并且当前更适合 global-level queries，如主题、含义、关系、跨整个语料的总结；而 local-level lookup 问题则建议 Azure AI Search 或其他 vector-based search tools。  
来源：<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases>

4. **融合后能同时覆盖结构化与非结构化信号。**  
Azure Cosmos DB 官方示例指出，knowledge graphs 擅长复杂关系查询，vector search 擅长处理非结构化数据和相似性查找；两者结合可扩大可回答问题的范围。  
来源：<https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/cosmos-ai-graph>

5. **适合做 hybrid retrieval。**  
Neo4j 官方 provider 直接支持 vector、fulltext、hybrid，以及通过 Cypher 自定义图遍历；这说明成熟落地通常不是“只图不用向量”，而是混合式检索。  
来源：<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag>

### 2.2 主要缺点与代价

1. **系统复杂度更高。**  
除了 embedding、chunk、rerank，还要考虑图模式设计、实体抽取、关系抽取、图更新、图质量校验、查询编排。Azure HorizonDB 把“Accuracy improvement of 20-30% justifies graph construction cost”直接放进是否采用的判断表里，已经非常说明问题。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

2. **数据治理要求更高。**  
GraphRAG 的效果依赖实体与关系质量；如果实体归一、关系抽取或 schema 设计不好，图会放大噪声，而不是放大价值。微软 GraphRAG 研究与 GraphRAG pattern 资料都强调 graph index / community summary / pattern design 本身就是系统的一部分。  
来源：<https://graphrag.com/appendices/research/2404.16130/> ，<https://graphrag.com/concepts/intro-to-graphrag/>

3. **不是所有问题都值得承担建图成本。**  
官方最明确的反例就是简单 factual lookup。对于“某一两段文本就能回答”的问题，vector-only 通常更快、更便宜、更容易上线。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag> ，<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases>

4. **查询链路更长，调优点更多。**  
典型 graph-augmented RAG 往往包含向量召回、语义重排、图遍历、结果融合、最终生成，链路长于普通 RAG，意味着延迟、稳定性与成本控制要更仔细。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

### 2.3 适用场景

更适合采用“向量检索 + 知识图谱 / GraphRAG”的场景：

- 企业知识管理里存在明确实体关系：组织、人、系统、接口、项目、流程、法规、合同、供应链等。  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag> ，<https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/cosmos-ai-graph>

- 问题经常要求多跳推理：`A 导致 B，B 影响 C，所以风险在哪？`  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

- 需要跨整个语料做主题总结、关系分析、归因或态势理解。  
  来源：<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases> ，<https://graphrag.com/appendices/research/2404.16130/>

- 同名实体很多，需要实体消歧。  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

- 需要保留引用链、监管链、审批链、知识出处链。  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

更适合先采用普通向量 RAG 的场景：

- FAQ、客服问答、产品手册检索、知识助手这类以局部文本片段回答为主的问题。  
  来源：<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases> ，<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

- 需要快速验证价值、快速上线、低维护成本。  
  来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

## 3. 阿里云百炼 / Knowledge Studio 在知识库管理、应用编排、检索增强、工作流、权限 / 多租户、数据接入方面的产品与架构思路

## 3.1 产品定位：一站式平台，前台应用化，中台平台化

阿里云百炼官方把自己定义为**一站式大模型开发与应用平台**：  

- 面向开发者，提供兼容 OpenAI 的 API 和全链路模型服务。  
- 面向业务人员，提供可视化应用构建能力，可快速创建智能体、知识库问答等 AI 应用。  
- 应用形态覆盖智能体应用、工作流应用、高代码应用。  
来源：<https://help.aliyun.com/zh/model-studio/what-is-model-studio>

从产品设计上看，百炼不是单点 RAG 服务，而是一个平台层：

- **模型层**：Qwen 与第三方模型。  
- **应用层**：智能体、工作流、高代码应用。  
- **增强层**：知识库（RAG）、插件、MCP。  
- **治理层**：业务空间、权限、API Key、OpenAPI。  
- **数据层**：知识库、数据连接、OSS、数据库、外部系统。  
来源：<https://help.aliyun.com/zh/model-studio/what-is-model-studio>

## 3.2 知识库管理：主线是 RAG 知识库平台化

百炼知识库的官方主叙事很清楚：

1. **知识库用于给大模型补充私有数据和最新信息。**  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

2. **工作原理公开强调语义检索。** 文档明确写到“知识库支持对私有数据或文件进行语义检索，可找出语义相同或相近的内容，即使关键词匹配度极低甚至为零”。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

3. **知识库可被同一业务空间下的智能体应用、工作流应用或外部应用复用。**  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

4. **检索调优是产品显式能力。** 官方文档公开支持相似度阈值与多知识库权重，用于筛选召回结果和干预多知识库召回顺序。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

5. **知识库具备 API 化能力。** 文档提供知识库 API 指南，强调可快速接入现有业务系统，实现自动化操作，并应对复杂检索需求。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base-api-guide>

### 对架构的解读

百炼当前官方公开能力，更像：

`文档/数据接入 -> 语义/向量检索 -> 参数调优 -> 应用挂接 -> OpenAPI 对外调用`

而不是：

`显式知识图谱建模 -> 图查询/图遍历 -> GraphRAG`

**也就是说，百炼现阶段公开文档主线是 RAG-first，而非 KG-first。** 本次调研未在百炼知识库官方文档中看到“知识图谱 / GraphRAG 是知识库默认内部架构”的直接证据。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base> ，<https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/use-cases/build-exclusive-large-model-applications-through-alibaba-cloud>

## 3.3 检索增强：公开主线是语义检索 / 向量检索能力

百炼公开材料对检索增强的表述主要包括：

- 知识库通过 RAG 在回答前检索相关内容，提高准确性。  
  来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

- 官方案例与文档明确使用 embedding 模型与语义相似度概念解释召回。  
  来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>

- 官方功能动态说明知识库支持调整“初步向量检索 TopK”和“初步关键词检索 TopK”，用于减少送入排序模型的 token 量、降低成本。这意味着其公开产品链路并非只有单一向量召回，而是至少包含“初步召回 + 排序 / 排名”这类分阶段检索思路。  
  来源：<https://help.aliyun.com/document_detail/2679100.html>

- 与 AnalyticDB PostgreSQL 的官方集成方案，强调的是“高性能向量检索引擎”支撑企业专属知识库。  
  来源：<https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/use-cases/build-exclusive-large-model-applications-through-alibaba-cloud>

### 对架构的解读

百炼在公开资料中已经体现出典型企业 RAG 平台的几个特征：

- 语义召回是主干。  
- 关键词 / TopK / 权重 / 阈值这些检索参数是产品级调优面板。  
- 知识库可以被多个应用形态复用。  
- 检索能力可通过 API 接入业务系统。  

但截至本次调研，**没有查到百炼官方公开强调图遍历、实体关系图、图融合检索作为知识库的标准能力表述**。这与微软 / Neo4j 对 GraphRAG 的公开说法有明显差异。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base> ，<https://help.aliyun.com/zh/model-studio/rag-knowledge-base-api-guide> ，<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag>

## 3.4 应用编排与工作流：低代码编排是百炼的重要产品主轴

百炼官方明确把**工作流应用**作为复杂任务拆解与编排能力：

- 通过组合大模型、API、函数计算等节点降低编码成本。  
- 通过可视化画布定义步骤顺序、责任与依赖关系，实现自动化与优化。  
- 使用场景覆盖报告分析、客服支持、内容创作、教育培训、医疗问诊等。  
来源：<https://help.aliyun.com/zh/model-studio/workflow-application>

从产品更新看，工作流能力还在持续增强：

- 支持异步运行模式。  
- 支持多模态生成节点。  
- 支持 Dify 工作流一键导入。  
来源：<https://help.aliyun.com/document_detail/2679100.html> ，<https://help.aliyun.com/zh/model-studio/getting-started/2024-release-notes>

### 对架构的解读

百炼的应用层不是“只有一个聊天入口”，而是明显在做：

- **知识增强**：知识库  
- **动作编排**：工作流  
- **工具集成**：API / 插件 / MCP / FC  
- **多形态交付**：控制台可视化 + OpenAPI + 高代码应用

这说明百炼更偏向企业 AI 应用平台，而不是单点模型网关。  
来源：<https://help.aliyun.com/zh/model-studio/what-is-model-studio> ，<https://help.aliyun.com/zh/model-studio/workflow-application>

## 3.5 权限 / 多租户：业务空间是核心租户与治理单元

百炼官方关于权限与多租户的设计思路非常清晰：

1. **业务空间是最小管理单元。** 官方原文：单个业务空间是进行精细化权限管理（模型、用户）和账单分账的最小管理单元。  
来源：<https://help.aliyun.com/zh/model-studio/permission-management-overview>

2. **角色分层明确。** 包括超级管理员、业务空间管理员、普通用户。超级管理员可跨空间统一管理用户权限、空间可用模型、模型限流和 API Key。  
来源：<https://help.aliyun.com/zh/model-studio/permission-management-overview>

3. **知识库 API 也绑定业务空间。** 知识库 API 指南明确要求子账号加入业务空间后方可操作，并且子账号只能操作已加入业务空间中的知识库；主账号可操作所有业务空间下的知识库。  
来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base-api-guide>

### 对架构的解读

这基本可以视为百炼的**多租户边界设计**：

- 空间 = 资源与权限的隔离边界  
- 角色 = 管理权限分层  
- API Key / OpenAPI = 对外调用边界  
- 分账 = 成本治理边界

这对企业落地很关键，因为它意味着百炼不是“账号级单体产品”，而是支持组织级治理。  
来源：<https://help.aliyun.com/zh/model-studio/permission-management-overview>

## 3.6 数据接入：统一数据连接入口，兼顾托管与实时访问

百炼官方把**数据连接**定义为管理外部数据源的统一入口，目标是让百炼应用能安全访问企业数据库、文档系统和对象存储中的数据，并在对话中实时查询和引用。  
来源：<https://help.aliyun.com/zh/model-studio/data-import-instructions>

当前官方文档显示其数据接入至少有两大模式：

- **平台托管**：文件、表格，存储在百炼平台或自有 OSS。  
- **流处理 / 实时访问**：MySQL、PostgreSQL、PolarDB-X 2.0、语雀、OSS。  
来源：<https://help.aliyun.com/zh/model-studio/data-import-instructions>

此外，百炼功能动态还披露：

- 新增统一数据管理模块。  
- 支持本地上传、OSS 导入、大批量非结构化文档导入。  
- 知识库创建时可直接导入文件或数据。  
- 知识库数据源支持 DMS、自建 MySQL 等。  
来源：<https://help.aliyun.com/zh/model-studio/getting-started/2024-release-notes>

### 对架构的解读

百炼的数据接入策略不是把所有数据都先离线搬进同一库，而是采用：

- **托管数据**：适合标准 RAG、文件知识库、受控数据管理  
- **实时访问数据**：适合数据库查询、联邦式接入、保持数据留存在源系统

这说明其平台架构兼顾“统一入口”和“数据不必全部迁移”的企业现实。  
来源：<https://help.aliyun.com/zh/model-studio/data-import-instructions>

## 3.7 云服务集成与底层架构：通过服务关联角色连接 FC / OSS / ADB-PG / MNS / DTS

服务关联角色文档能反推出百炼的后端集成思路：

- 工作流应用 / 流程编排可访问函数计算 FC。  
- 数据管理可访问 OSS。  
- 知识库与安全存储空间可访问 ADB-PG。  
- 数据管理可访问 MNS 中的 OSS 变更消息。  
- 平台可访问 DTS，用于从指定数据源接入数据。  
来源：<https://help.aliyun.com/zh/model-studio/bailian-service-linked-role>

### 对架构的解读

这说明百炼不是一个封闭的“纯 SaaS 前端”，而是：

- **控制面**：控制台、权限、API Key、业务空间  
- **数据面**：知识库、数据连接、OSS、数据库  
- **执行面**：工作流、FC、异步任务、外部调用  
- **云集成面**：ADB-PG、MNS、DTS、OSS、SLS、CMS、内容安全等

从企业架构角度，这是比较典型的“AI 应用平台 + 云服务编排底座”思路。  
来源：<https://help.aliyun.com/zh/model-studio/bailian-service-linked-role> ，<https://help.aliyun.com/zh/model-studio/what-is-model-studio>

## 4. 对 MaxKB 这类企业知识产品的启发

基于这次调研，可以得出几个更务实的产品判断：

1. **不要把“是否上知识图谱”当成意识形态问题，而要当成问题类型选择。**  
简单问答、FAQ、手册检索，先把普通 RAG 做好；多跳关系、归因、全局总结，再考虑引入图增强。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag> ，<https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases>

2. **更现实的路线通常不是“纯图替代向量”，而是分层检索。**  
先保留向量召回主链路，再在特定问题类型中接入图遍历、关系扩展、结构化重排。  
来源：<https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag> ，<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>

3. **百炼的官方主线说明，企业平台更容易先卖通的是“RAG 平台化能力”**，即知识库、工作流、权限、数据接入、API 化、可观测，而不是先卖“图谱算法概念”。  
来源：<https://help.aliyun.com/zh/model-studio/what-is-model-studio> ，<https://help.aliyun.com/zh/model-studio/rag-knowledge-base> ，<https://help.aliyun.com/zh/model-studio/workflow-application>

4. **如果未来要引入 GraphRAG，更合理的产品形态应是“增强模式”而不是“替代模式”。**  
例如：按知识库类型、应用类型、问题类型或工作流节点，选择是否进入 graph-enhanced retrieval。  
来源：<https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag> ，<https://learn.microsoft.com/en-in/agent-framework/agents/rag>

## 参考来源清单

- Microsoft Agent Framework - RAG  
  <https://learn.microsoft.com/en-in/agent-framework/agents/rag>
- Microsoft Agent Framework - Neo4j GraphRAG Context Provider  
  <https://learn.microsoft.com/en-ca/agent-framework/integrations/neo4j-graphrag>
- Azure HorizonDB - Graph-augmented RAG patterns  
  <https://learn.microsoft.com/en-us/azure/horizondb/ai/graph-rag>
- Microsoft Discovery Bookshelf  
  <https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases>
- Azure Cosmos DB - Create AI knowledge graphs using RAG  
  <https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/cosmos-ai-graph>
- Neo4j GraphAcademy - GraphRAG  
  <https://graphacademy.neo4j.com/courses/workshop-genai/1-generative-ai/2-graphrag/>
- GraphRAG pattern / research aggregation  
  <https://graphrag.com/concepts/intro-to-graphrag/>  
  <https://graphrag.com/appendices/research/2404.16130/>
- 阿里云百炼 - 什么是阿里云百炼  
  <https://help.aliyun.com/zh/model-studio/what-is-model-studio>
- 阿里云百炼 - 知识库  
  <https://help.aliyun.com/zh/model-studio/rag-knowledge-base>
- 阿里云百炼 - 知识库 API 指南  
  <https://help.aliyun.com/zh/model-studio/rag-knowledge-base-api-guide>
- 阿里云百炼 - 工作流应用  
  <https://help.aliyun.com/zh/model-studio/workflow-application>
- 阿里云百炼 - 权限管理  
  <https://help.aliyun.com/zh/model-studio/permission-management-overview>
- 阿里云百炼 - 数据连接  
  <https://help.aliyun.com/zh/model-studio/data-import-instructions>
- 阿里云百炼 - 服务关联角色  
  <https://help.aliyun.com/zh/model-studio/bailian-service-linked-role>
- 阿里云 AnalyticDB PostgreSQL - 通过阿里云百炼搭建专属大模型应用  
  <https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/use-cases/build-exclusive-large-model-applications-through-alibaba-cloud>
- 阿里云百炼 - 应用功能动态  
  <https://help.aliyun.com/document_detail/2679100.html>  
  <https://help.aliyun.com/zh/model-studio/getting-started/2024-release-notes>
