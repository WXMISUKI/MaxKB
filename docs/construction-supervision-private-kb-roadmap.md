# 监理与施工队伍审查知识库项目路线

本文沉淀当前项目定位、知识库粒度、部署形态和近期启动前置条件，作为后续开发 MaxKB 私有知识库能力时的总纲。

## 1. 项目定位

本项目以 MaxKB 作为企业级私人知识库与智能体平台主体，优先服务以下场景：

- 某项目下某施工队伍或分包队伍的开工条件审查
- 某项目下某施工队伍或分包队伍的施工方案审查
- 后续扩展到监理资料核查、报审资料辅助审查、整改闭环和项目知识问答

MaxKB 负责：

- 知识库管理
- 用户、权限和项目空间
- 工作流和智能体编排
- 审查应用入口
- 审计记录、人工结论和报告资产

外部模型服务负责：

- LLM 推理
- Embedding
- Rerank
- OCR / 多模态识别

后续迁移到昇腾服务器时，只替换模型服务后端与模型服务 endpoint，不推翻 MaxKB 的知识库、审查流程和 provider contract。

## 2. 部署原则

### 2.1 当前 Windows 本地阶段

当前阶段目标不是一次性完成生产架构，而是先在 Windows + Docker Desktop 上跑通知识库闭环：

1. 启动 MaxKB
2. 配置可用的大模型、Embedding 和可选 Rerank
3. 建立项目级知识库
4. 上传一批代表性资料
5. 验证检索、引用、问答和审查提示词链路

优先使用 Docker Desktop 跑 MaxKB 或依赖服务。不要一开始就在 Windows 裸机上追求完整生产环境。

### 2.2 Linux 生产阶段

MaxKB 本体部署在普通 Linux 服务器上，推荐优先使用容器化部署：

- MaxKB Web / Celery / local_model 服务
- PostgreSQL + pgvector
- Redis
- 对象存储，如 MinIO / OSS
- 日志、备份、监控和反向代理

Linux 服务器不应直接绑定昇腾专用 Python 环境。业务服务和模型服务需要解耦。

### 2.3 昇腾模型服务阶段

昇腾服务器承载模型推理服务，向 MaxKB 暴露稳定接口：

- OpenAI-compatible chat/completions
- Embedding API
- Rerank API
- OCR / 多模态 API

昇腾侧可以使用 Miniconda 或官方容器管理 CANN、torch_npu、模型推理框架和模型权重。MaxKB 侧只保存模型 provider 配置和 endpoint。

## 3. 知识库粒度

第一阶段采用：

> 项目级逻辑知识库 + metadata 过滤

用户看到的是一个项目知识库空间，但底层资料必须保留标段、合同段、队伍、依据版本、资料类型和审查任务等 metadata。

推荐逻辑结构：

```text
组织 / 监理单位
  项目
    项目依据库
    标段 / 合同段资料域
    施工队伍 / 分包队伍资料域
    审查任务临时资料域
```

第一阶段不建议把每个队伍都拆成独立物理知识库，原因是联调成本高、资料复用弱、后续项目级审查不方便。但数据模型必须预留队伍级和审查任务级过滤能力。

## 4. 核心 metadata

项目资料入库时至少保留：

- `organization_id`
- `project_id`
- `contract_package_id`
- `section_id`
- `supervision_section_id`
- `subcontract_team_id`
- `review_task_id`
- `basis_version_id`
- `document_type`
- `source_object_id`
- `content_hash`
- `effective_status`
- `effective_date`
- `indexed_at`

这些字段用于：

- 权限隔离
- 检索过滤
- stale 判定
- 审查引用追溯
- 后续从项目级 dataset 演进到标段 / 队伍 dataset

## 5. 第一阶段资料范围

优先准备某一个真实或模拟项目的最小资料包：

- 合同依据、招标文件关键条款、项目管理制度
- 开工条件审查依据和审查表
- 施工方案审查依据和审查表
- 一个施工队伍或分包队伍的人员、资质、设备、证照、报审材料
- 1 到 3 个历史通过 / 驳回样例

第一批资料控制在 10 到 30 份，目标是验证检索质量和审查链路，不追求一次性全量导入。

模拟资料包规格见 `construction-supervision-pilot-dataset/`。该规格当前定义了“南江至东岭高速公路改扩建工程 JD-A1 标段监理审查试点”、LJ-01 路基土石方分包作业队、24 份第一批资料、官方规范来源登记和本地 MaxKB 验收任务。

## 6. Source of Truth

MaxKB / 平台侧是正式事实 owner：

- 项目与合同依据版本
- 项目主数据
- 队伍资料状态
- 审查任务状态
- 人工审核结论
- 检查项结果
- 报告资产

向量库、RAGFlow 或其他外部 provider 只能保存：

- dataset / document / chunk refs
- embedding
- retrieval score
- safe snippet
- provider-side metadata

检索结果只能作为支持性召回，不能直接成为正式审查结论。

## 7. 本地启动前置条件

当前 Windows 阶段建议先确认：

1. Docker Desktop 已启动，并能正常运行 Linux containers
2. 本地 8080 端口未被占用，或准备换端口
3. 预留足够磁盘空间给镜像、PostgreSQL 数据、向量索引和模型缓存
4. 准备一个可用 LLM provider，可先用外部 OpenAI-compatible 服务
5. 准备 embedding 模型；如果使用官方 MaxKB 镜像，基础本地 embedding 模型通常随镜像/模型层提供
6. 准备第一批项目资料包，不超过 30 份

如果只是先跑通知识库能力，优先级是：

1. 先跑通 MaxKB 官方容器
2. 再配置模型 provider
3. 再上传资料验证知识库问答
4. 最后再进入源码级二开

## 8. 近期开发任务方向

### 阶段 A：本地知识库闭环

- 启动 MaxKB
- 建立一个试点项目知识库
- 配置 LLM、Embedding、可选 Rerank
- 上传第一批资料
- 验证召回片段、引用来源和问答质量

### 阶段 B：项目/队伍审查建模

- 固化项目、标段、合同段、施工队伍、审查任务的 metadata
- 设计开工条件审查检查项
- 设计施工方案审查检查项
- 明确哪些结论必须人工确认

### 阶段 C：审查应用原型

- 基于 MaxKB 工作流搭建开工条件审查应用
- 基于 MaxKB 工作流搭建施工方案审查应用
- 输出结构化审查建议、缺失项、风险点和引用依据

### 阶段 D：Linux/昇腾迁移

- Linux 上容器化部署 MaxKB 本体
- 昇腾服务器部署模型服务
- MaxKB 切换到昇腾模型 endpoint
- 验证 provider health、知识库召回和审查工作流不变

## 9. 当前已确认决策

- MaxKB 是平台主体，不是单纯前端壳
- 昇腾服务器提供模型服务接口，不承载 MaxKB 业务状态
- 第一阶段优先做“某项目下某施工 / 分包队伍的开工条件审查 + 施工方案审查”
- 知识库采用“项目级逻辑知识库 + metadata 过滤”
- 外部 RAG provider 不能成为事实源或流程 owner

## 10. 待确认问题

按照 grill-me 的方式，下一步需要优先确认：

> 第一批试点资料是使用真实项目脱敏资料，还是先用模拟项目资料？

推荐答案：先用一个模拟项目资料包跑通链路；如果有真实资料，先脱敏后作为第二批验证数据。
