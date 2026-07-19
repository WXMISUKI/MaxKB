# 模拟施工监理审查资料包任务

## Task Group A — Spec

- [x] A1 确认试点场景：某项目下某施工 / 分包队伍的开工条件审查 + 施工方案审查。
- [x] A2 确认知识库粒度：项目级逻辑知识库 + metadata 过滤。
- [x] A3 定义模拟项目、合同段、监理标段、施工总包和分包作业队伍。
- [x] A4 定义第一批资料包清单和 metadata。
- [x] A5 登记官方规范候选来源。

## Task Group B — Data Pack Generation

- [ ] B1 创建 `docs/simulated-pilot-dataset/NJDL-JD-A1/` 资料包目录。
- [x] B2 生成 `00_manifest/dataset-manifest.yaml`、`.json`、`.csv`、`.xlsx`。
- [x] B3 生成项目依据、合同监理、队伍开工条件、施工方案、历史样例等 24 份业务模拟资料。
- [x] B4 生成 5 份官方规范来源摘要文件，不导入来源不明全文。
- [x] B5 为每份资料写入 manifest 条目和核心 metadata。
- [ ] B6 对资料包做一次命名、来源、审查任务覆盖检查。

## Task Group C — Local MaxKB Validation

- [ ] C1 使用 Docker Desktop 启动 MaxKB。
- [ ] C2 建立 `南江至东岭高速公路改扩建工程 JD-A1` 项目知识库。
- [ ] C3 上传第一批模拟资料。
- [ ] C4 配置可用 LLM provider、embedding 模型和可选 reranker。
- [ ] C5 验证开工条件审查召回。
- [ ] C6 验证路基填筑施工方案审查召回。
- [ ] C7 记录召回质量、缺失字段、误召回和需要进入源码定制的点。

## Task Group D — Implementation Decision

- [ ] D1 判断 MaxKB 现有知识库 metadata 能否满足项目 / 标段 / 队伍 / 审查任务过滤。
- [ ] D2 如不能满足，创建正式 OpenSpec 后端变更，设计 metadata 扩展。
- [ ] D3 设计开工条件审查工作流原型。
- [ ] D4 设计施工方案审查工作流原型。
- [ ] D5 确认 Linux/昇腾迁移时模型服务 endpoint 与 provider health 契约。
