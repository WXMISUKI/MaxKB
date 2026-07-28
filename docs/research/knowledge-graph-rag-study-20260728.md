# Knowledge Graph 与 RAG 调研记录（2026-07-28）

## 1. 本项目现状判断

### 1.1 当前 MaxKB 的知识库主能力仍然是 RAG，不是知识图谱

从仓库实现看，MaxKB 当前知识库核心路径是：

1. 文档解析与切分
2. 向量化入库
3. 检索
4. 可选关键词/混合召回
5. 返回段落给下游模型生成答案

关键证据：

- README 明确把产品能力定义为“RAG 检索增强生成”，并注明向量数据库为 PostgreSQL/pgvector，而不是图数据库。  
  来源：`README_CN.md` 第 19、20、71 行。
- 知识模型中存在 `Paragraph`、`ProblemParagraphMapping`、`Termbase`、`Embedding`、`SearchMode(embedding/keywords/blend)` 等结构，但没有图实体、关系边、子图、图查询语言等知识图谱核心模型。  
  来源：`apps/knowledge/models/knowledge.py` 第 249、284、295、316、347 行。
- 检索节点 `BaseSearchKnowledgeNode.execute()` 通过 `embedding_model.embed_query(question)` + `vector.query(...)` 完成召回，并按 `SearchMode` 执行检索，没有图遍历或图推理链路。  
  来源：`apps/application/flow/step_node/search_knowledge_node/impl/base_search_knowledge_node.py` 第 76、102、113、117 行。
- pgvector 检索实现仅提供三类检索器：`EmbeddingSearch`、`KeywordsSearch`、`BlendSearch`。  
  来源：`apps/knowledge/vector/pg_vector.py` 第 249、276、308、349 行。
- 知识库命中测试接口也是围绕 `query_text/top_number/similarity/search_mode` 做召回验证。  
  来源：`apps/knowledge/serializers/knowledge.py` 第 1361、1364、1387、1389、1402 行。

### 1.2 现有“增强能力”更像轻量知识组织，不是知识图谱

当前比较接近“结构化增强”的能力主要有两类：

- `ProblemParagraphMapping`：问题与段落之间的映射，可帮助 FAQ/问题扩展召回。
- `Termbase`：术语表，可参与分词/关键词检索优化。

这两类能力对企业知识库是有价值的，但它们本质上仍然服务于 RAG 召回优化，不等于实体-关系-子图级别的 Knowledge Graph。  
来源：`apps/knowledge/models/knowledge.py` 第 284-318 行；`apps/knowledge/serializers/common.py` 第 83、106、120 行。

### 1.3 当前结论

MaxKB 现在更准确的定位应该是：

`企业级 RAG / Agent 平台 + 工作流编排 + 混合检索能力`

而不是：

`内置 Knowledge Graph / GraphRAG 平台`

---

## 2. 市面上是不是都推荐“向量 + 图谱”一起做？

### 2.1 结论先说

不是“所有场景都更好”，而是：

- **普通 FAQ、制度问答、文档问答**：向量 RAG 往往已经足够，成本更低、落地更快。
- **跨文档关系推理、根因分析、组织/系统依赖分析、全局综述类问题**：向量 + 图谱通常更强。

所以行业更成熟的判断不是“GraphRAG 替代 RAG”，而是：

`GraphRAG / knowledge graph 是对 baseline RAG 的增强层`

### 2.2 官方依据

Microsoft GraphRAG 官方文档明确指出：

- Baseline RAG 大多使用向量相似度检索。
- 当问题需要“connect the dots”（跨信息片段建立联系）时，baseline RAG 表现较差。
- 当问题需要对大规模语料做“holistic understanding”（全局理解/总结）时，baseline RAG 也会失效。
- GraphRAG 通过从文本中抽取知识图、构建社区层级与摘要，在这些问题上优于 baseline RAG。  
  来源：<https://microsoft.github.io/graphrag/>

Microsoft Agent Framework 与 Neo4j 的官方集成文档也明确说明：

- 标准向量检索返回的是孤立文本块。
- 图遍历可以返回相关实体及其关系，形成更丰富的上下文。
- 可将 vector、fulltext、hybrid 与 graph traversal 组合在同一次检索中。  
  来源：<https://learn.microsoft.com/en-au/agent-framework/integrations/neo4j-graphrag>

### 2.3 企业实践角度的推荐方式

更符合企业最佳实践的路线通常是：

1. 先把 baseline RAG 做扎实：切块、元数据、权限、混合检索、rerank、引用、评测。
2. 仅在这些场景中引入图谱层：
   - 多跳关系推理
   - 全局主题总结
   - 复杂根因链路分析
   - 组织/资产/流程依赖分析
   - 审计与溯源
3. 在线检索一般不要只走图，也不要只走向量，而是混合编排：
   - 先向量召回证据
   - 再图遍历补关系
   - 最后 rerank / answer synthesis

### 2.4 为什么不能一开始就全量上图谱

GraphRAG/知识图谱的代价并不低：

- 需要实体与关系抽取质量
- 需要 schema 设计
- 需要图更新与一致性治理
- 需要更高的离线索引成本
- 权限控制会更复杂
- 错误关系会显著污染答案

因此，“向量 + 图谱”不是默认标配，而是面向复杂知识场景的升级路线。

---

## 3. 阿里云 Knowledge Studio / 百炼知识库，管理与架构上做了什么

说明：阿里云产品命名和入口近一年有较多演进，公开官方资料主要分布在百炼（Model Studio）与 PAI/LangStudio 文档中。就一手公开资料来看，其核心方向是“企业级知识库 + 应用/工作流编排 + 外部集成”，而不是公开宣称以知识图谱为中心。

### 3.1 数据与知识库管理

阿里云官方知识库文档显示：

- 知识库用于给大模型补充私有数据和最新信息，核心仍是 RAG。  
  来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>
- 知识库可与智能体应用、工作流应用、外部应用集成，并要求位于同一业务空间（workspace）。  
  来源：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>
- 可设置相似度阈值与知识库权重；当关联多个知识库时，系统会综合相关度与权重进行排序。  
  来源：同上。
- 支持知识库管理页统一查看与管理。  
  来源：同上。

这说明它在“企业级管理面”上已经做了标准化产品能力：

- workspace 级资源隔离
- 知识库可复用
- 多知识库路由与排序
- 外部应用接入

### 3.2 典型知识库处理链路

PAI/LangStudio 官方文档明确描述了知识库工作原理：

1. 从 OSS 读取源文件
2. 文档解析与分块
3. Embedding 向量化
4. 入向量库并创建索引

还提供：

- 更新索引
- 文档块启用/禁用
- 召回测试
- 在应用流中复用知识库  
  来源：<https://help.aliyun.com/zh/pai/user-guide/knowledge-base-index-management>

这意味着阿里云做得比较成熟的不是“图谱优先”，而是：

`企业级知识库生命周期管理`

即：

- 数据接入
- 解析
- 索引
- 测试
- 上线
- 在应用中复用

### 3.3 工作流 / 组件化编排

百炼工作流官方文档显示：

- 工作流可以组合大模型、API、函数计算等节点。
- 知识库节点用于 RAG，把检索结果传给下游模型。
- 支持测试、发布、复用。  
  来源：<https://help.aliyun.com/zh/model-studio/user-guide/workflow-application/>

另外，官方组件化文档说明：

- 智能体或工作流可以被发布为组件，供其他应用接入复用。  
  来源：<https://help.aliyun.com/zh/model-studio/use-agent-or-workflow-as-component>

所以从企业架构视角看，它的核心架构不是单纯“一个知识库”，而是：

`知识库服务 + 工作流编排 + 组件复用 + 应用接入`

### 3.4 公开资料中更强的地方

阿里云公开能力里比较强的点，主要体现在：

- 统一控制台与工作空间治理
- 知识库与应用/工作流解耦复用
- 多知识库权重与阈值管理
- 召回测试与索引更新流程
- 组件化发布
- 对外部业务系统接入的产品化支持

从工程角度，这类平台比很多开源 RAG 项目强的地方，通常不是“模型算法绝对领先”，而是：

- 管理面更完整
- 资源边界更清晰
- 生命周期更标准
- 应用接入更产品化

---

## 4. 对 MaxKB 的启发

### 4.1 如果只看当前版本，MaxKB 还缺什么

和更成熟的平台相比，MaxKB 当前知识库侧更像“可扩展的 RAG 引擎”，还缺少几层企业级能力深化：

1. **统一的知识库治理面板深化**
   - 召回测试
   - 检索参数可视化调优
   - 多库路由/权重配置可视化
   - chunk 级别效果分析

2. **更强的检索编排**
   - 查询改写
   - 多阶段召回
   - rerank 策略可配置
   - 失败回退策略

3. **结构化知识增强**
   - 从 `ProblemParagraphMapping` 升级到实体-关系抽取
   - 引入图谱索引或轻量子图检索
   - 面向多跳/全局问题增加 GraphRAG 模式

4. **企业管理能力**
   - workspace 级知识库治理与配额
   - 多知识库路由策略
   - 权限、审计、版本、发布

### 4.2 最推荐的升级路线

从投入产出比看，不建议直接把 MaxKB 重构成“全量图谱平台”。更稳妥的路线是：

#### 阶段 1：先把现有 RAG 做成企业级

- 强化 blend 检索配置面
- 增加 query rewrite
- 增加 rerank 可配置
- 增加召回评测与可解释性
- 增加多库权重/路由

#### 阶段 2：增加轻量 GraphRAG 能力

- 先不强依赖独立图数据库
- 先做实体、关系、文档来源、时间、标签等结构化抽取
- 在 PostgreSQL 中先落地关系表 / 邻接表 / 子图缓存
- 先支持特定问题类型进入 graph-enhanced retrieval

#### 阶段 3：按场景引入图数据库

仅当这些场景稳定存在时，再引入 Neo4j / Neptune / AGE 等：

- 多跳推理问答
- 根因分析
- 资产依赖分析
- 风险传播分析
- 审计溯源

---

## 5. 最终结论

### 对你的问题的直接回答

1. **当前 MaxKB 除了 RAG 之外，是否已有知识图谱能力？**  
   结论：**没有成体系的 Knowledge Graph / GraphRAG 能力。** 当前更像是 RAG + 混合检索 + 术语库 + 问题映射增强。

2. **市面上是否都推荐向量 + 图谱一起做？**  
   结论：**不是所有场景都推荐，但在复杂企业知识场景下，越来越多平台会走“向量为底、图谱增强”的路线。** GraphRAG 更适合多跳关系、全局总结、复杂分析，不适合一开始就全量替代 baseline RAG。

3. **阿里云 Knowledge Studio/百炼做得好的地方是什么？**  
   结论：**它强在产品化管理与企业级架构，而不只是单点检索算法。** 核心是：
   - workspace/业务空间治理
   - 知识库生命周期管理
   - 多知识库集成与排序
   - 工作流编排
   - 组件化复用
   - 外部业务系统接入

4. **对 MaxKB 最合理的方向是什么？**  
   结论：**先把现有 RAG 做深，再按场景引入 GraphRAG，而不是一上来重做成图谱平台。**

---

## 官方参考链接

- MaxKB README（仓库内）：`README_CN.md`
- 阿里云百炼知识库：<https://help.aliyun.com/zh/model-studio/rag-knowledge-base>
- 阿里云百炼工作流：<https://help.aliyun.com/zh/model-studio/user-guide/workflow-application/>
- 阿里云组件复用：<https://help.aliyun.com/zh/model-studio/use-agent-or-workflow-as-component>
- 阿里云 PAI / LangStudio 知识库管理：<https://help.aliyun.com/zh/pai/user-guide/knowledge-base-index-management>
- Microsoft GraphRAG：<https://microsoft.github.io/graphrag/>
- Microsoft Agent Framework + Neo4j GraphRAG：<https://learn.microsoft.com/en-au/agent-framework/integrations/neo4j-graphrag>
