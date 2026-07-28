# 安全监管平台知识网关隔离（Workspace）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让安全监管平台网关在同一套 MaxKB 实例下实现多项目隔离，避免误绑定/误删/数据污染，并保留本地联调的低门槛。

**Architecture:** 使用独立 `workspaceId` 作为主隔离边界；提供可选的队伍知识库命名前缀作为防御性隔离；对“删除知识库”提供可配置的保护阀。

**Tech Stack:** FastAPI + pytest（网关）；MaxKB Admin API（/admin/api）；环境变量配置。

---

## File Map

**Docs**
- Create: [spec.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/specs/multi-project-isolation/spec.md)
- Modify: [design.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/design.md)
- Modify: [runbook.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/runbook.md)
- Modify: [tasks.md](file:///c:/project/tool/MaxKB/docs/safety-platform-kb-gateway/tasks.md)

**Gateway Service**
- Modify: [config.py](file:///c:/project/tool/MaxKB/services/safety-platform-kb-gateway/safety_platform_kb_gateway/config.py)
- Modify: [adapters.py](file:///c:/project/tool/MaxKB/services/safety-platform-kb-gateway/safety_platform_kb_gateway/adapters.py)
- Modify: [main.py](file:///c:/project/tool/MaxKB/services/safety-platform-kb-gateway/safety_platform_kb_gateway/main.py)
- Modify: [test_api.py](file:///c:/project/tool/MaxKB/services/safety-platform-kb-gateway/tests/test_api.py)

---

## Task 1: 规格与文档对齐

**Files:**
- Create: `docs/safety-platform-kb-gateway/specs/multi-project-isolation/spec.md`
- Modify: `docs/safety-platform-kb-gateway/design.md`
- Modify: `docs/safety-platform-kb-gateway/runbook.md`
- Modify: `docs/safety-platform-kb-gateway/tasks.md`

- [ ] **Step 1: 明确隔离策略与风险边界**

输出要点：
- 主策略：`MAXKB_WORKSPACE_ID=safety_platform`
- 推荐：`MAXKB_TEAM_KB_PREFIX=safety-team`
- 线上可开：`REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE=true`

- [ ] **Step 2: 更新 runbook 的环境变量样例与说明**

确保 runbook 的配置样例可直接复制用于本地联调。

- [ ] **Step 3: 更新 design 文档补充多项目隔离策略**

在“关键决策”中补齐多项目共存时的隔离口径。

- [ ] **Step 4: 更新任务清单**

将与 `knowledgeBaseId` 显式绑定有关的 Phase 2 项勾选，对齐现实状态，并新增 “Workspace 隔离”任务组。

---

## Task 2: 配置与命名规则实现

**Files:**
- Modify: `services/safety-platform-kb-gateway/safety_platform_kb_gateway/config.py`
- Modify: `services/safety-platform-kb-gateway/safety_platform_kb_gateway/adapters.py`

- [ ] **Step 1: 增加环境变量配置项**

新增：
- `MAXKB_TEAM_KB_PREFIX`（默认 `team`，兼容既有命名）
- `REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE`（默认 false）

- [ ] **Step 2: 统一队伍知识库前缀生成逻辑**

改造适配器，使 `find/create/delete` 共享同一规则：

`{prefix}:{teamId}:...`

---

## Task 3: 删除保护阀实现

**Files:**
- Modify: `services/safety-platform-kb-gateway/safety_platform_kb_gateway/main.py`

- [ ] **Step 1: 在删除知识库接口增加保护阀检查**

当 `REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE=true` 时：
- 不传 `knowledgeBaseId` 直接返回 400

---

## Task 4: 测试与验证

**Files:**
- Modify: `services/safety-platform-kb-gateway/tests/test_api.py`

- [ ] **Step 1: 增加删除保护阀测试**

覆盖：
- 开启保护阀 + 不传 `knowledgeBaseId` → 400

- [ ] **Step 2: 运行 pytest**

Run:

```bash
pytest services/safety-platform-kb-gateway/tests -q
```

Expected:
- 全部通过

