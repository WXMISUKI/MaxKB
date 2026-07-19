# 本地 MaxKB 知识库闭环验收提案

## Why

当前已经完成：

- 施工监理模拟资料包规格与第一批 `docx + xlsx` 文件生成
- 本地 MaxKB 启动、模型配置、项目级知识库上传
- 开工条件审查与施工方案审查召回验收
- PaddleOCR-VL 扫描件接入
- 营业执照真实 OCR 后处理与结构化入库
- 多证照后处理框架骨架

下一阶段最能推进项目、最有价值、最快能投产的方向，不是立即深改 MaxKB 源码，也不是先做前端页面，而是把扫描件资料稳定地转为“带业务元数据的结构化证据”，并固化成前置服务可调用接口。

只有完成本地闭环后，才知道后续应优先做：

- MaxKB 配置和部署文档
- 知识库 metadata 扩展
- 审查工作流原型
- 外部模型服务 / 昇腾 endpoint 接入

## What Changes

- 新增本地验证规格，定义启动、入库、问答、OCR、结构化、命中验收和归档节奏。
- 新增资料包校验脚本，避免上传缺 metadata、缺文件、格式不可读的资料。
- 新增 MaxKB API 配置与上传能力，减少手工前端操作依赖。
- 新增 PaddleOCR-VL 异步接入、OCR 归档和命中验收脚本。
- 新增营业执照、安全生产许可证、人员证书结构化后处理骨架。
- 新增前置服务 OCR 入库 API 合同草案。
- 将验证结果沉淀到资料包 `00_manifest` 目录，形成可复用验收资产。

## Recommended Direction

下一阶段推荐方向：

> 先完成“多证照结构化后处理 + 业务元数据固化 + 前置 API 合同”，再进入真实证照回归和工作流原型。

理由：

1. 这是离投产最近的路径：把真实扫描件转成可用证据，比继续优化单个问答更直接。
2. 可以最快暴露真实问题：OCR 噪声、结构化字段缺失、业务元数据不全、证照字段检索偏差。
3. 能避免过早设计复杂工作流或 UI，减少局部无限优化。
4. 后续 Linux/昇腾迁移只需要替换模型或 OCR endpoint，不推翻外部集成合同。
5. 前置平台最先需要的是稳定上传和证据组织，而不是花哨交互。

## Scope

### In Scope

- 本地资料包完整性校验
- 资料上传计划
- 开工条件审查问题集
- 施工方案审查问题集
- 本地 Docker Desktop 启动检查清单
- 验证报告模板
- OCR 证照接入
- 多证照结构化后处理
- 业务元数据标准
- 前置服务 OCR 入库 API 合同草案

### Out of Scope

- 自动操作 MaxKB UI 上传资料
- 修改 MaxKB 后端模型
- 修改 MaxKB 前端页面
- 正式接入昇腾模型服务
- 正式生产部署脚本
- 正式对象存储和审计数据库实现

## Deliverables

- `scripts/validate_pilot_dataset.py`
- `scripts/configure_and_upload_maxkb.py`
- `scripts/paddleocr_vl_ingest.py`
- `scripts/postprocess_ocr_document.py`
- `scripts/validate_ocr_ingest_hit.py`
- `00_manifest/validation-report.json`
- `00_manifest/validation-report.md`
- `00_manifest/maxkb-upload-plan.csv`
- `00_manifest/review-question-set.md`
- `docs/construction-supervision-local-validation/runbook.md`
- `docs/construction-supervision-local-validation/preflight-ocr-ingestion-api-contract.md`
