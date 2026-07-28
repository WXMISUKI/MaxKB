# 安全监管平台 - 多项目隔离规格（MaxKB Workspace 隔离）

## 1. 背景与问题

当前存在“同一个 MaxKB 实例（同一套 DB/Redis）同时服务多个项目分支”的使用场景。

如果多个项目共用同一个 MaxKB `workspace`，并且使用相同的知识库命名规则（例如 `team:{teamId}:...`），会出现以下风险：

- 误绑定：按前缀查找知识库时，可能命中另一个项目的同前缀库
- 误删：删除队伍知识库时，可能误删另一个项目的库
- 测试污染：不同项目的数据互相可见，联调与验收结论不可信

本规格目标是在不增加运维复杂度（仍共用同一 MaxKB 实例）的前提下，为“安全监管平台”提供企业级可控的隔离策略。

## 2. 目标

- 安全监管平台使用 **独立 `workspaceId`**，避免与其他项目互相污染
- 支持可选的“知识库命名前缀”作为防御性隔离（防误配置）
- 在危险操作（删除）上提供可配置的保护阀
- 本地 Docker 联调与线上部署保持同一套配置口径，避免环境漂移

## 3. 非目标

- 不引入新的 MaxKB 实例（不做“多套 DB/Redis”硬隔离）
- 不把 MaxKB 的 `workspace` 当作业务租户模型（平台仍以自身 DB 为事实源）
- 不在网关内落库维护 `teamId -> knowledgeBaseId` 映射（由平台后端落库）

## 4. 方案

### 4.1 Workspace 隔离（主策略）

安全监管平台网关通过环境变量指定其工作空间：

- `MAXKB_WORKSPACE_ID=safety_platform`

该 workspace 内的知识库、文档、检索均与其他 workspace 完全隔离，满足首版联调与试点投产的安全边界需求。

### 4.2 知识库命名前缀（防御性策略，可选）

在独立 workspace 的基础上，网关仍支持对队伍知识库命名加“项目级前缀”，用于：

- 降低运维误配置（把 `MAXKB_WORKSPACE_ID` 配回 `default`）时的数据污染概率
- 未来如需同一 workspace 承载多个“子域”，仍有额外隔离手段

推荐配置：

- `MAXKB_TEAM_KB_PREFIX=safety-team`

队伍知识库命名规则：

`{prefix}:{teamId}:{displayName} 资质知识库`

示例：

`safety-team:team-lj-01:LJ-01 路基土石方分包作业队 资质知识库`

### 4.3 删除保护阀（安全控制）

提供一个可配置开关，用于限制“未显式指定 `knowledgeBaseId` 的删除”：

- `REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE=true`

当开启后：

- 删除队伍知识库接口必须传 `knowledgeBaseId`
- 仅基于 `teamId` 的删除将返回 400，提示调用方先查询并确认 `knowledgeBaseId`

该策略用于线上环境规避误删，联调环境可保持关闭以降低门槛。

## 5. 配置清单（网关）

必填：

- `GATEWAY_API_KEY`
- `MAXKB_BASE_URL`
- `MAXKB_USERNAME`
- `MAXKB_PASSWORD`
- `MAXKB_WORKSPACE_ID=safety_platform`

推荐：

- `MAXKB_TEAM_KB_PREFIX=safety-team`
- `REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE=true`（线上）

## 6. 验收清单

- 安管网关在 `safety_platform` workspace 下创建知识库，其他项目在 `default` workspace 下不可见
- 同 teamId 在两个 workspace 各自创建知识库时，互不影响
- 开启删除保护阀后，不传 `knowledgeBaseId` 的删除返回 400；传入正确 `knowledgeBaseId` 可成功删除

## 7. Open-source 版本的 Workspace 初始化说明

开源版没有 workspace CRUD 接口，`workspaceId` 在数据层表现为多张业务表上的字符串字段（例如 `knowledge.workspace_id`）。

同时，知识库创建依赖 “根文件夹” 存在：`knowledge.folder_id` 默认等于 `workspaceId`，因此需要先为该 workspace 写入根文件夹记录。

本仓库已提供管理命令 `bootstrap_workspace` 用于初始化根文件夹（知识库/工具/应用三类 folder）。

在 MaxKB 容器内执行：

```bash
docker exec -w /opt/maxkb-app maxkb python apps/manage.py bootstrap_workspace --workspace-id safety_platform
```

如需同时初始化建议的队伍知识库命名前缀，请在网关侧配置：

- `MAXKB_WORKSPACE_ID=safety_platform`
- `MAXKB_TEAM_KB_PREFIX=safety-team`
