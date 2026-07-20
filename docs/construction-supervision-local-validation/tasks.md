# 本地 MaxKB 知识库闭环验收任务

## Task Group A — Spec

- [x] A1 确认下一阶段方向：本地 MaxKB 知识库闭环验收。
- [x] A2 确认第一批资料包格式：`docx + xlsx`。
- [x] A3 确认验证方式：先人工 UI 上传和问答验证，不自动操作 MaxKB UI。
- [x] A4 确认源码改造门槛：只有现有能力无法满足验收才进入后端/前端改造。
- [x] A5 确认扫描件资料必须经过 OCR 后处理和结构化入库。
- [x] A6 确认平台是事实 owner，MaxKB 只承载支持性检索副本。

## Task Group B — Implementation

- [x] B1 新增资料包校验脚本。
- [x] B2 校验 manifest 和实际文件一致。
- [x] B3 生成 MaxKB 上传计划。
- [x] B4 生成开工条件审查问题集。
- [x] B5 生成施工方案审查问题集。
- [x] B6 输出本地验证报告。
- [x] B7 支持 MaxKB API 配置、知识库创建与资料上传。
- [x] B8 支持 PaddleOCR-VL 异步 OCR 归档。
- [x] B9 支持营业执照 OCR 后处理与结构化入库。
- [x] B10 支持安全生产许可证和人员证书结构化骨架。
- [x] B11 支持结构化证照命中验收。
- [x] B12 支持项目 / 队伍 / 审查任务元数据写入结构化产物。

## Task Group C — Archive

- [x] C1 编写本地 MaxKB 验收 runbook。
- [x] C2 归档 Docker Desktop 启动检查。
- [x] C3 归档模型配置建议。
- [x] C4 归档验收结果记录模板。
- [x] C5 归档多证照后处理设计和任务拆分。
- [x] C6 归档前置服务 OCR 入库 API 合同草案。

## Task Group D — Next Decision

- [x] D1 根据本地验证结果判断需要 metadata 扩展，并已固化元数据字段。
- [ ] D2 用真实扫描件回归安全生产许可证。
- [ ] D3 用真实扫描件回归人员证书。
- [ ] D4 设计设备合格证 / 检定证书结构化规则。
- [x] D5 将现有脚本封装为独立 FastAPI 前置服务 API 原型。
- [ ] D6 根据真实证照回归结果判断是否进入工作流原型。
- [ ] D7 根据 OCR / 检索链路稳定性判断 Linux/昇腾迁移前置条件。

## Task Group E — Preflight OCR Worker

- [x] E1 新增独立 FastAPI Worker 规格，不侵入 MaxKB Django 核心。
- [x] E2 实现健康检查、OCR 创建/查询、后处理、MaxKB 入库和检索验收接口。
- [x] E3 实现本地文件 allowed roots 校验和原子 JSON 状态存储。
- [x] E4 实现 PaddleOCR、证照后处理、MaxKB 和命中验收适配器。
- [x] E5 API 输出统一为 camelCase，隐藏内部解析路径和 provider 凭据。
- [x] E6 未配置 provider 凭据时健康检查降级，不提供默认管理员密码。
- [x] E7 使用公开 HTTP 接口完成成功链路、越权路径、健康降级和失败持久化回归。
- [x] E8 在 Python 3.11 下完成测试、语法和 Ruff 验证。
- [x] E9 归档 Worker 启动方式、环境变量、API 合同和原型边界。

## Task Group F — Platform Integration Hardening

- [x] F1 新增平台联调加固 Spec。
- [x] F2 使用 `PREFLIGHT_API_KEY` 保护全部业务 API，保留匿名健康检查。
- [x] F3 未配置 Worker 鉴权时返回 `503`，无效 Bearer 凭据返回 `401`。
- [x] F4 创建 OCR 任务强制使用 `Idempotency-Key`。
- [x] F5 同 key、同请求返回已有任务且不重复执行 OCR。
- [x] F6 同 key、不同请求返回 `409`，原任务保持不变。
- [x] F7 支持 `X-Correlation-ID` 透传，缺失时由 Worker 生成。
- [x] F8 健康检查输出鉴权配置、Worker capabilities 和 provider readiness。
- [x] F9 归档平台调用请求头、错误语义和幂等规则。
- [x] F10 使用公开 HTTP 接口完成 11 项 Worker 回归。

## Task Group G — Organization and Calling Contract

- [x] G1 新增前置平台组织结构与知识库绑定 Spec。
- [x] G2 明确项目、合同段、标段、施工/分包队伍、审查任务和证据必须由前置平台数据库管理。
- [x] G3 明确 MaxKB 只创建知识库、文件夹、文档和检索副本，不创建公路工程业务事实。
- [x] G4 扩展 Worker `EvidenceMetadata`，支持标段、监理标段、分包队伍、依据版本、主数据和证据引用。
- [x] G5 将扩展 metadata 透传到 OCR 后处理产物。
- [x] G6 新增前置平台调用 OCR Worker 详细说明文档。
- [x] G7 新增前置平台组织结构与知识库绑定设计文档。
- [x] G8 新增面向前置平台团队的当前进度与待解决问题交接文档。

## Task Group H — Platform Alignment Spec

- [x] H1 阅读前置项目对接文档：架构演进、外部 provider、单项目试点工作流、MaxKB provider、交接说明。
- [x] H2 固化平台事实源边界：前置平台拥有业务事实，MaxKB / OCR Worker / Dify / RAGFlow 只提供能力。
- [x] H3 固化 Node BFF 边界：浏览器只调用前置平台 API，不直连外部 provider 或 Worker。
- [x] H4 固化 MaxKB provider 边界：只保存 provider refs、安全摘要和支持性召回。
- [x] H5 固化 OCR Worker 联调边界：服务端调用、Bearer 鉴权、幂等键、correlationId 和安全 provider refs。
- [x] H6 固化开工条件单项目试点门禁：依据、主数据、资料包、清单、正式匹配、人工复核和报告归档。
- [x] H7 新增 `preflight-platform-alignment` 规格，作为前置平台联调与后续开发的统一约束。

## Task Group I — LAN MaxKB Provider Proxy

- [x] I1 新增 `preflight-maxkb-provider-proxy` 规格，明确前置平台通过 OCR Worker proxy 调用 MaxKB。
- [x] I2 新增 `/api/health` 兼容入口。
- [x] I3 新增 `/api/knowledge-base/provider/status`，返回 MaxKB provider readiness 安全摘要。
- [x] I4 新增 `/api/knowledge/{knowledgeId}/search`，由 Worker 使用服务端 MaxKB 管理员账号登录并执行 hit-test。
- [x] I5 明确局域网联调配置：前置平台电脑使用 `MAXKB_BASE_URL=http://192.168.0.235:8091`，`MAXKB_API_KEY=<PREFLIGHT_API_KEY>`。
- [x] I6 为 provider status 和 search proxy 增加回归测试。

## Task Group J — Local LAN Startup Quickstart

- [x] J1 新增 `local-lan-worker-startup` 规格，明确本地联调启动和密钥不落盘要求。
- [x] J2 生成本次联调建议使用的 Worker bearer token。
- [x] J3 更新仓库根目录 `quickstart.md`，补充 MaxKB、OCR Worker、前置平台 provider 配置、健康检查和检索代理测试命令。
- [x] J4 明确 Worker 需要使用 `--host 0.0.0.0 --port 8091` 暴露给 `192.168.0.219`。
