# 安管后端联调清单

本文给安全监管平台后端同学使用，按顺序逐项勾选即可。

## 1. 联调前准备

- [ ] 已拿到网关基地址，例如：`http://192.168.0.219:8092`
- [ ] 已拿到网关 Bearer Token
- [ ] 已确认调用目标是网关 `8092`，不是 MaxKB `8080`
- [ ] 已准备 1 份最小测试文件（建议 `.txt` 或 `.docx`）
- [ ] 已准备最小业务字段：
  - [ ] `teamId`
  - [ ] `projectId`
  - [ ] `teamName`
  - [ ] `projectName`
  - [ ] `documentType`
  - [ ] `sourceTable`
  - [ ] `sourceObjectId`

## 2. 基础连通性

- [ ] 调用 `GET /health` 成功
- [ ] 返回中 `ready=true`
- [ ] 返回中 `providers.maxkb.ready=true`

## 3. 队伍知识库状态

- [ ] 调用 `GET /api/teams/{teamId}/knowledge-base` 成功
- [ ] 若首次联调，返回 `exists=false` 也正常

## 4. 上传联调

- [ ] 调用 `POST /api/teams/{teamId}/documents` 成功
- [ ] 返回 `knowledgeBaseId`
- [ ] 返回 `providerDocumentId`
- [ ] 返回 `metadata.contentHash`
- [ ] 后端已把以下字段写入本地库：
  - [ ] `teamId`
  - [ ] `knowledgeBaseId`
  - [ ] `providerDocumentId`
  - [ ] `sourceTable`
  - [ ] `sourceObjectId`
  - [ ] `contentHash`

## 5. 检索联调

- [ ] 上传后等待数秒再检索
- [ ] 调用 `POST /api/teams/{teamId}/search` 成功
- [ ] 能返回 `hits`
- [ ] `diagnostics.workspaceId` 与当前联调环境一致

建议优先验证两类 query：

- [ ] 唯一标识型关键词，如统一社会信用代码
- [ ] 业务问句型 query，如“该队伍安全生产许可证是否有效”

## 6. 字段检索联调

- [ ] 调用 `POST /api/teams/{teamId}/search/field` 成功
- [ ] 用 `fieldName + fieldValue` 能召回刚上传资料

## 7. 项目共享依据补数

- [ ] 调用 `POST /api/teams/{teamId}/knowledge-base/sync-basis` 成功
- [ ] `scope=project_shared` 的资料边界已由后端控制
- [ ] 不可稳定归属到队伍的项目级资料，未误投到队伍知识库

## 8. 删除与回收

- [ ] 删除文档时，已保存 `knowledgeBaseId + providerDocumentId`
- [ ] 删除知识库时，线上按约定显式传 `knowledgeBaseId`

## 9. 常见问题

### 9.1 为什么 `docker ps` 里看不到 8092 网关？

因为当前联调阶段的 `8092` 网关是本机直接用 `python -m uvicorn` 启动的，不是 Docker 容器。

### 9.2 为什么本地联调先用 `default` workspace？

因为当前这台机器上的 MaxKB 运行态，`admin` 用户仅对 `default` workspace 可见；所以本地联调先采用：

- `MAXKB_WORKSPACE_ID=default`
- `MAXKB_TEAM_KB_PREFIX=safety-team`

### 9.3 上传成功但检索一开始没结果？

MaxKB 文档切分/索引存在短暂异步过程，建议上传成功后等待几秒再检索。

## 10. 验收标准

- [ ] 后端可稳定完成上传
- [ ] 后端可稳定完成普通检索
- [ ] 后端可稳定完成字段检索
- [ ] 上传结果已完成本地持久化
- [ ] 未把 MaxKB 管理员账号密码暴露给业务前端

