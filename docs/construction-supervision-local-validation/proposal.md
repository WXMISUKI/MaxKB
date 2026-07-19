# 本地 MaxKB 知识库闭环验收提案

## Why

当前已经完成施工监理模拟资料包规格和第一批 `docx + xlsx` 文件生成。下一阶段最能推进项目、最有价值、最快能投产的方向，不是立即深改 MaxKB 源码，而是先在 Windows + Docker Desktop 环境中跑通知识库能力，记录现有 MaxKB 对项目级知识库、Office 文档解析、召回质量和审查问答的真实表现。

只有完成本地闭环后，才知道后续应优先做：

- MaxKB 配置和部署文档
- 知识库 metadata 扩展
- 审查工作流原型
- 外部模型服务 / 昇腾 endpoint 接入

## What Changes

- 新增本地验证规格，定义启动、入库、问答、记录和归档节奏。
- 新增资料包校验脚本，避免上传缺 metadata、缺文件、格式不可读的资料。
- 新增 MaxKB 上传计划和审查问题集，方便人工在 UI 中快速验证。
- 将验证结果沉淀到资料包 `00_manifest` 目录，形成可复用验收资产。

## Recommended Direction

下一阶段推荐方向：

> 先跑通本地 MaxKB 知识库闭环，再判断是否需要源码级 metadata 扩展。

理由：

1. 这是离投产最近的路径：启动服务、上传资料、配置模型、验证召回。
2. 可以最快暴露真实问题：Office 解析、切分质量、引用质量、召回噪声、模型回答边界。
3. 能避免过早设计复杂后端模型，减少局部无限优化。
4. 后续 Linux/昇腾迁移只需要替换部署和模型 endpoint，不推翻知识库验收口径。

## Scope

### In Scope

- 本地资料包完整性校验
- 资料上传计划
- 开工条件审查问题集
- 施工方案审查问题集
- 本地 Docker Desktop 启动检查清单
- 验证报告模板

### Out of Scope

- 自动操作 MaxKB UI 上传资料
- 修改 MaxKB 后端模型
- 修改 MaxKB 前端页面
- 正式接入昇腾模型服务
- 正式生产部署脚本

## Deliverables

- `scripts/validate_pilot_dataset.py`
- `00_manifest/validation-report.json`
- `00_manifest/validation-report.md`
- `00_manifest/maxkb-upload-plan.csv`
- `00_manifest/review-question-set.md`
- `docs/construction-supervision-local-validation/runbook.md`

