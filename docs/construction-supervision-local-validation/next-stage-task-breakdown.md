# 下一阶段任务拆分

## 推荐主线

下一阶段优先做 **前置平台单项目试点联调**。

原因：

- 前置项目文档已经明确 Node BFF / API Gateway 是浏览器侧稳定入口，MaxKB 和 OCR Worker 都是后端 provider。
- 当前 MaxKB 与 OCR Worker 本地闭环已经可用，下一步价值不在继续局部优化 OCR，而在把项目、任务、证据、知识库绑定和人工决策串成平台闭环。
- 单项目试点能最快暴露真实联调问题：对象存储引用、幂等键、correlationId、provider refs、readiness 门禁、人工复核和报告归档。
- 该方向能保持企业级边界：平台拥有事实和状态，外部 provider 只提供能力。

本轮对齐规格已新增：

- `docs/construction-supervision-local-validation/specs/preflight-platform-alignment/spec.md`

## 大方向排序

1. 前置平台单项目试点联调
   - 目标：以前置平台 API 为入口，跑通任务初始化、资料包接入、OCR Worker、MaxKB provider、命中验收、人工复核和报告归档的最小链路。
   - 投产价值：最高。
   - 当前状态：前置项目已提供架构演进、外部 provider、开工条件试点工作流和 MaxKB provider 对接文档；本项目已生成统一 alignment spec。

2. 平台事实库与 provider refs 持久化
   - 目标：建立或对齐 `Project`、`ContractPackage`、`Section`、`SubcontractTeam`、`ReviewTask`、`Evidence`、`KnowledgeBinding`、`OcrIngestionLink`、`BasisVersion`、`MasterData`、`HumanDecision`、`ReportAsset`。
   - 投产价值：高。
   - 当前状态：已明确不由 MaxKB 或 OCR Worker 承担事实库职责。

3. OCR Worker 服务端联调封装
   - 目标：前置平台服务端调用 Worker，持久化 `ingestionId`、PaddleOCR `jobId`、MaxKB `providerDocumentId`、retrieval-check 和安全诊断。
   - 投产价值：高。
   - 当前状态：Worker 已支持 Bearer 鉴权、幂等创建、correlationId、OCR、后处理、入库和命中验收。

4. MaxKB provider 支持证据展示
   - 目标：在审查页面展示 MaxKB 命中作为支持性证据，不把命中结果写成正式结论。
   - 投产价值：高。
   - 当前状态：已固化 `KNOWLEDGE_PROVIDER=maxkb`、`KnowledgeBinding` 和 safe provider refs 方向。

5. 真实证照回归与资料类型扩展
   - 目标：用真实安全生产许可证、人员证书和设备合格证/检定证书继续验证 OCR 结构化质量。
   - 投产价值：中高。
   - 建议时机：平台联调主链路跑通后持续补强。

6. 审查工作流与生产化队列
   - 目标：引入持久队列、Python agent service、Dify/RAGFlow 可选编排、报告导出和审计加强。
   - 投产价值：高，但依赖平台事实库与联调链路稳定。
   - 建议时机：单项目试点可操作后。

## 原 OCR 主线保留为支撑能力

OCR 证照结构化后处理仍是关键能力，但它现在从“下一阶段主线”降为“平台联调中的支撑任务”。

保留原因：

- 真实施工资料中 PDF 扫描件、证照照片、盖章件会高频出现。
- 结构化字段能直接支撑开工条件审查，例如企业资质、人员证书、营业执照、安全生产许可证、设备合格证。
- 该方向不要求深改 MaxKB 核心，适合在联调中持续迭代。

## 原大方向排序记录

1. OCR 证照结构化后处理
   - 目标：把扫描件 OCR 原文转换为清洗 Markdown、结构化 JSON/CSV、推荐入库 Markdown。
   - 投产价值：最高。
   - 当前状态：已形成多证照后处理框架，支持营业执照、安全生产许可证、人员证书。

2. 精确字段检索验收
   - 目标：统一社会信用代码、证书编号、身份证/岗位证号、设备编号等字段必须可命中。
   - 投产价值：高。
   - 当前状态：营业执照在 `keywords` 模式下已验证可排第 1。

3. 前置服务 API 合同适配
   - 目标：把 OCR、后处理、上传、命中验收封装成前置平台可调用接口。
   - 投产价值：高。
   - 当前状态：独立 FastAPI Worker 原型已完成，API 合同和 provider 适配边界已固化。

4. 审查工作流原型
   - 目标：围绕“某项目某分包队伍”的开工条件审查生成支持性意见、缺项提示和引用来源。
   - 投产价值：高，但依赖资料入库质量。
   - 建议时机：字段资料和审查依据召回稳定后启动。

5. MaxKB 源码级改造或 UI 上传入口
   - 目标：把脚本能力产品化到 MaxKB 插件层或前端入口。
   - 投产价值：中。
   - 建议时机：前置 API 合同稳定后。

## 本轮落地任务组

### 任务组 A：营业执照 OCR 后处理

- 输入：PaddleOCR-VL 生成的 OCR Markdown。
- 输出：
  - `cleaned.md`
  - `business-license-fields.json`
  - `business-license-fields.csv`
  - `business-license-ingest.md`
  - `postprocess-report.md`
- 验收：
  - 统一社会信用代码抽取正确。
  - 企业名称抽取正确。
  - 法定代表人抽取正确。
  - 正照编号抽取正确。
  - 结构化 Markdown 可上传 MaxKB。

### 任务组 B：证照精确字段命中验收

- 输入：结构化入库 Markdown。
- 输出：
  - `paddleocr-vl-retrieval-check.csv`
  - `paddleocr-vl-retrieval-check.md`
- 验收：
  - 企业名称 + 统一社会信用代码命中结构化文档。
  - 法定代表人 + 正照编号命中结构化文档。
  - 证照字段类查询优先采用 `keywords` 模式。

## 本轮新增任务组

### 任务组 C：多证照后处理框架

- 输入：PaddleOCR-VL 生成的 OCR Markdown。
- 支持类型：
  - `business_license`
  - `safety_production_license`
  - `personnel_certificate`
- 能力：
  - 自动识别证照类型。
  - 支持通过参数显式指定证照类型。
  - 按证照类型输出 `*-fields.json`、`*-fields.csv`、`*-ingest.md`。
  - 保留原始 OCR Markdown 和清洗后 Markdown，便于追溯。
- 验收：
  - 营业执照使用真实 OCR 产物回归通过。
  - 安全生产许可证和人员证书使用临时样本验证字段抽取通过。

## 下一批建议任务

1. 用真实扫描件回归安全生产许可证
   - 目标：用真实 PDF 验证许可证编号、企业名称、主要负责人、许可范围、有效期、发证机关抽取质量。
   - 输出：真实 OCR 归档、结构化字段、入库 Markdown、命中验收报告。

2. 用真实扫描件回归人员证书
   - 目标：用真实 PDF 验证姓名、岗位、证书编号、发证机关、有效期、单位、到岗状态抽取质量。
   - 输出：真实 OCR 归档、结构化字段、入库 Markdown、命中验收报告。

3. 支持设备合格证/检定证书结构化
   - 字段：设备名称、型号、编号、检定日期、有效期、检定机构。

4. 建立前置服务上传接口草案
   - 接口：上传原件、查询 OCR 状态、查询结构化结果、确认入库、命中验收。
   - 当前状态：已新增 `preflight-ocr-ingestion-api-contract.md` 草案。

5. 设计“项目 + 分包队伍 + 审查任务”元数据标准
   - 目标：让每份证照入库时都带上项目、队伍、审查任务和资料类型。
   - 当前状态：后处理脚本已支持写入元数据，API 草案已固化 `EvidenceMetadata`。

## 本轮完成：独立 FastAPI Worker

- 服务目录：`services/preflight-ocr-worker`
- API：健康检查、创建/查询 OCR 任务、重新后处理、确认入库、检索验收。
- 状态：单机使用原子 JSON 持久化，异步执行使用进程内 BackgroundTasks。
- 安全：本地文件限制在 allowed roots；凭据只从环境变量读取；API 不返回内部解析路径。
- 验证：Python 3.11 下 4 个公开接口回归通过，Ruff 和语法检查通过。

## 本轮完成：前置平台联调加固

- Worker 业务 API 已使用 `PREFLIGHT_API_KEY` Bearer 鉴权。
- OCR 创建接口已强制要求 `Idempotency-Key`，避免平台重试产生重复 OCR 和重复入库。
- 支持平台 `X-Correlation-ID` 透传，用于后续审计和故障定位。
- `/health` 已输出 Worker 鉴权、capabilities、PaddleOCR 和 MaxKB readiness。
- 公开 HTTP 接口回归由 4 项扩展到 11 项。

## 本轮完成：组织结构与调用合同

- 明确前置平台必须自建项目、合同段、标段、队伍、审查任务、证据和知识库绑定数据库表。
- 明确 MaxKB 只作为检索 provider，不作为公路工程资料核查事实库。
- Worker `EvidenceMetadata` 已扩展到标段、监理标段、分包队伍、依据版本、主数据引用和证据引用。
- 新增 `preflight-platform-worker-call-guide.md`，用于下一步平台真实联调。
- 新增 `preflight-organization-knowledge-design.md`，用于前置平台后端建模。

## 下一阶段推荐任务组

1. 前置平台联调
   - 使用真实平台请求字段和服务端 Bearer 凭据调用 Worker。
   - 验证幂等重试、correlationId、项目/合同段/队伍/审查任务映射和错误处理。
   - 输出一份可复现的联调请求、状态查询、provider refs 和故障记录。

2. 前置平台数据库最小实现
   - 建立 Project、ContractPackage、Section、SubcontractTeam、ReviewTask、Evidence、KnowledgeBinding、OcrIngestionLink。
   - 首版只做 CRUD、唯一键、状态流和 provider refs，不进入自动审批。

3. 两类真实证照回归
   - 分别选取安全生产许可证、人员证书真实扫描件。
   - 跑通 OCR、结构化、人工确认入库和精确字段命中验收。

4. 生产化决策门
   - 仅在单机联调稳定后，设计 PostgreSQL 状态库、Redis/Celery 队列和对象存储。
   - 保持现有 API schema 与状态语义，避免前置平台二次改造。

5. 审查工作流原型
   - 以前三项验收结果为输入，再实现“某项目某分包队伍”的开工条件审查。
   - 首版输出缺项提示、支持性意见和来源引用，不自动给出正式审批结论。
