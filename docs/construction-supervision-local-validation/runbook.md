# 本地 MaxKB 知识库闭环验收 Runbook

## 1. 目标

在 Windows + Docker Desktop 环境中跑通：

1. MaxKB 启动
2. 模型 provider 配置
3. 项目级知识库创建
4. 模拟资料包上传
5. 开工条件审查和施工方案审查问答验证

本轮只验证现有能力，不立即做源码级深改。

## 2. 前置条件

- Docker Desktop 已启动，且使用 Linux containers
- 本机 `8080` 端口可用，或准备映射到其他端口
- 已准备可用 LLM provider，推荐先用 OpenAI-compatible 服务
- 已生成并校验模拟资料包

## 3. 资料包校验

运行：

```powershell
python docs\construction-supervision-local-validation\scripts\validate_pilot_dataset.py
```

脚本会生成：

- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/validation-report.json`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/validation-report.md`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/maxkb-upload-plan.csv`
- `docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/review-question-set.md`

只有 `validation-report.md` 中阻塞错误为 0 时，才进入 MaxKB 上传验证。

## 4. MaxKB 启动建议

优先使用官方容器启动 MaxKB。若本机 8080 未占用，可使用：

```powershell
docker run -d --name=maxkb --restart=always -p 8080:8080 -v C:/maxkb:/opt/maxkb registry.fit2cloud.com/maxkb/maxkb
```

默认登录信息以当前 MaxKB 镜像说明为准。首次启动需要等待数据库初始化、模型文件和服务进程就绪。

## 5. 知识库创建

建议创建知识库：

```text
南江至东岭高速公路改扩建工程 JD-A1 监理审查知识库
```

建议描述：

```text
用于验证 LJ-01 路基土石方分包作业队开工条件审查和 K12+000-K18+500 路基填筑施工方案审查。
```

上传顺序参考：

```text
00_manifest/maxkb-upload-plan.csv
```

## 6. 模型配置

第一阶段推荐：

- LLM：外部 OpenAI-compatible 服务
- Embedding：MaxKB 内置本地 embedding 或可用外部 embedding
- Rerank：可先关闭；如果召回噪声明显，再配置

不要第一轮就在 Windows 本机部署大模型。后续迁移到昇腾时，只替换模型服务 endpoint。

## 7. 验收问题

使用：

```text
00_manifest/review-question-set.md
```

每个问题记录：

- 是否召回正确资料
- 是否遗漏关键资料
- 是否召回其他队伍或其他审查任务资料
- 是否能标注来源
- 是否把支持性召回误写成正式结论

## 8. 进入源码改造的判断

只有出现以下问题，才进入源码级改造：

- MaxKB 无法稳定解析 `docx` / `xlsx`
- 无法实现项目 / 队伍 / 审查任务过滤
- 引用来源不足以支撑人工复核
- 工作流无法表达“支持性召回 + 人工确认”

否则下一阶段优先做工作流应用原型，而不是后端模型大改。

