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

## Task Group F - Phase 2 合同增强

- [ ] F1 支持显式 `knowledgeBaseId` 绑定上传
- [ ] F2 支持显式 `knowledgeBaseId` 绑定检索
- [ ] F3 支持显式 `knowledgeBaseId` 绑定队伍知识库查询与删除
- [ ] F4 让平台后端可在 `teamId` 和 `knowledgeBaseId` 之间逐步切换
