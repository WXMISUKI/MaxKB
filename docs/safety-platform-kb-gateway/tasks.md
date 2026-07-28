# 安全监管平台知识网关服务任务拆分

## Task Group A - 规格

- [x] A1 明确服务定位：平台后端与 MaxKB 之间的稳定代理层
- [x] A2 明确首版主线：单项目试点联调的知识网关原型
- [x] A3 明确首版边界：不做 OCR 编排、不做业务事实存储、不做自动结论
- [x] A4 明确知识库粒度：一个队伍一个知识库
- [x] A5 明确上传方式：`multipart/form-data`
- [x] A6 明确返回方式：结构化 hits
- [x] A7 明确支持文件类型：office / pdf / image
- [x] A8 形成设计文档

## Task Group B - 服务骨架

- [x] B1 新建 `services/safety-platform-kb-gateway/`
- [x] B2 新建 `pyproject.toml`
- [x] B3 实现 `config.py`
- [x] B4 实现 `schemas.py`
- [x] B5 实现 `security.py`

## Task Group C - 核心实现

- [x] C1 实现 `MaxKBClient`
- [x] C2 实现 `GatewayAdapter`
- [x] C3 实现 `/health`
- [x] C4 实现 `/api/teams/{teamId}/documents`
- [x] C5 实现 `/api/teams/{teamId}/knowledge-base`
- [x] C6 实现 `/api/teams/{teamId}/knowledge-base` 删除
- [x] C7 实现 `/api/teams/{teamId}/documents/{documentId}` 删除
- [x] C8 实现 `/api/teams/{teamId}/search`
- [x] C9 实现 `/api/teams/{teamId}/search/field`
- [x] C10 实现 `/api/teams/{teamId}/knowledge-base/sync-basis`

## Task Group D - 验证

- [x] D1 为公开接口补测试
- [x] D2 验证鉴权失败场景
- [x] D3 验证自动创建知识库场景
- [x] D4 验证普通检索和字段检索 DTO
- [x] D5 完成 pytest 回归

## Task Group E - 归档

- [x] E1 补运行说明
- [x] E2 补平台后端接入说明
- [ ] E3 清理测试缓存与临时产物

## 本轮归档记录（2026-07-27）

- 规格归档：`specs/zhgdx-team-knowledge-mapping/spec.md`
- 数据库盘点：`zhgdx-schema-inventory.md`
- 设计同步：已补充 ZHGDX 映射和项目/队伍归属边界
- 实现基线：现有网关接口保持不变，避免未经验证的 provider 元数据改造
- 验证结果：`pytest` 13 项通过，Ruff 通过，`git diff --check` 通过
- 清理状态：测试缓存已定位在服务目录内，但当前本地安全策略禁止递归删除，缓存未进入 Git
- 后续入口：G8 平台后端事件驱动同步；G9 MaxKB provider 元数据兼容性验证
- 本轮实现：H1-H6 已完成，网关上传契约已具备真实平台联调所需的归属字段和内容哈希
- 本轮验证：`pytest` 15 项通过，Ruff 通过，`git diff --check` 通过

## 本轮归档记录（2026-07-28）

- 规格归档：`specs/multi-project-isolation/spec.md`
- 文档同步：runbook/design 补充 workspace 隔离、命名前缀与删除保护阀口径
- 运维补充：runbook 补充开源版 workspace 根文件夹初始化命令与 embedding 模型 id 查询方式
- 实现变更：新增 `MAXKB_TEAM_KB_PREFIX` 与 `REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE` 配置；队伍知识库命名统一走可配置前缀
- 验证结果：`pytest` 16 项通过

## 本轮归档记录（2026-07-28-2）

- 联调现状：`8092` 网关已在宿主机以 `python -m uvicorn` 方式跑通，不属于 Docker 容器
- 本地口径：当前 MaxKB 运行态仅开放 `default` workspace，因此本地联调采用 `default + safety-team` 前缀隔离
- 交付补充：新增后端可直接复制的 `.env` 示例与后端联调清单
- quickstart：补充 `8092` 启动说明、宿主机运行说明和后端交付文档入口

## Task Group F - Phase 2 合同增强

- [x] F1 支持显式 `knowledgeBaseId` 绑定上传
- [x] F2 支持显式 `knowledgeBaseId` 绑定检索
- [x] F3 支持显式 `knowledgeBaseId` 绑定队伍知识库查询与删除
- [ ] F4 让平台后端可在 `teamId` 和 `knowledgeBaseId` 之间逐步切换

## Task Group I - 多项目隔离（Workspace）

- [x] I1 规格：明确同一 MaxKB 实例多项目共存的隔离策略（workspace + 可选前缀）
- [x] I2 文档：补本地联调与线上部署的 workspace 配置口径
- [x] I3 实现：支持队伍知识库命名前缀配置，避免误绑定
- [x] I4 实现：提供删除保护阀，线上可要求必须显式传 `knowledgeBaseId`
- [x] I5 验证：补充前缀与删除保护阀的测试覆盖

## Task Group G - ZHGDX 数据映射与同步边界

- [x] G1 只读盘点 `zhgdx` 全量表结构
- [x] G2 明确 `biz_work_team.id` 为队伍知识库绑定主键
- [x] G3 明确人员、证书、合同和设备的队伍归属链路
- [x] G4 明确 `sys_file`、业务 URL、`biz_attachment` 三种文件来源
- [x] G5 明确队伍专属资料和项目共享依据边界
- [x] G6 明确暂不投影到队伍库的项目级审查数据
- [x] G7 新增 ZHGDX 映射规格和数据库盘点归档
- [ ] G8 平台后端按映射规格实现事件驱动同步调用
- [ ] G9 对 MaxKB 文档 provider 元数据能力做兼容性验证

## Task Group H - 真实资料同步契约

- [x] H1 上传接口接收 `scope`、`projectId`、`documentType` 等归属字段
- [x] H2 支持 `sourceTable`、`sourceObjectId`、`basisVersionId`
- [x] H3 自动计算并返回文件内容 SHA-256
- [x] H4 上传响应返回 `knowledgeBaseId` 和 `providerDocumentId`
- [x] H5 增加项目共享资料的归属校验
- [x] H6 增加归属校验失败时的临时文件清理
- [ ] H7 由安全监管平台持久化幂等键、版本状态和 provider refs
- [ ] H8 对真实 `biz_project_person_certificate` 资料执行端到端联调

## Task Group I - 平台后端 AI 对接说明

- [x] I1 编写后端 AI 可直接执行的网关对接说明
- [x] I2 固化 ZHGDX 表到 `teamId`、`sourceTable`、`sourceObjectId` 的映射
- [x] I3 固化新增、更新、删除和项目共享资料流程
- [x] I4 固化错误码、重试和幂等建议
- [x] I5 固化平台后端与网关的职责边界
- [ ] I6 由安全监管平台后端 AI 按说明实现调用方
- [ ] I7 使用真实人员证书或队伍合同完成端到端联调
