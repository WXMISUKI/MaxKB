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
