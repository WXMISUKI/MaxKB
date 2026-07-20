# 开工条件核查单项目试点工作流

本阶段目标是跑通一个项目/合同包/参与机构/工作区内的真实试点闭环。平台先掌握业务事实和任务状态，Dify 仅作为既有核验流程参考或后续可选适配器，不进入主维护路径。

## 事实源边界

- 结构化事实源目标为 PostgreSQL 或等价关系型数据库。
- 当前实现提供本地开发文件适配器，存储在 `.local-data/opening-condition-pilot-tasks.json`。
- 对象存储保存合同、核查表、资料包、证据附件和报告产物。
- 向量库只能做语义检索辅助，不能作为依据版本、主数据、核查结论或人工决策的事实源。
- 组织/分包队伍专属知识库存储已确认资料模板、历史证据、人工修正记录和可检索资料片段，但结构化主数据和人工决策仍以平台记录为准。

## 当前 API 合同

- `POST /api/opening-condition/pilot-tasks/intake-init`
- `GET /api/opening-condition/pilot-tasks`
- `GET /api/opening-condition/pilot-tasks/:taskId`
- `PUT /api/opening-condition/pilot-tasks/:taskId`
- `GET /api/opening-condition/pilot-tasks/:taskId/readiness`
- `POST /api/opening-condition/pilot-tasks/:taskId/knowledge-base/:knowledgeBaseId/bind`
- `POST /api/opening-condition/pilot-tasks/:taskId/packet`
- `POST /api/opening-condition/pilot-tasks/:taskId/match`
- `GET /api/opening-condition/pilot-tasks/:taskId/human-review`
- `POST /api/opening-condition/pilot-tasks/:taskId/human-review/:reviewId/decision`
- `POST /api/opening-condition/pilot-tasks/:taskId/report`
- `POST /api/opening-condition/pilot-tasks/:taskId/archive`
- `POST /api/opening-condition/pilot-tasks/:taskId/transition`
- `GET /api/opening-condition/workspaces/:workspaceId/basis`
- `PUT /api/opening-condition/workspaces/:workspaceId/basis/:basisId`
- `POST /api/opening-condition/workspaces/:workspaceId/basis/:basisId/publish`
- `GET /api/opening-condition/workspaces/:workspaceId/master-data`
- `PUT /api/opening-condition/workspaces/:workspaceId/master-data/:recordId`
- `POST /api/opening-condition/workspaces/:workspaceId/master-data/:recordId/decision`
- `GET /api/opening-condition/workspaces/:workspaceId/knowledge-bases`
- `PUT /api/opening-condition/workspaces/:workspaceId/knowledge-bases/:knowledgeBaseId`

这些接口先服务试点闭环，不代表最终权限和数据库迁移方案已经完成。

## 下一阶段优先级

当前最能推进投产的方向是“单项目真实试点闭环”，不是先建设完整多租户权限平台、深度调优 RAGFlow、重写 Python 工作流编排，或把所有前端演示态一次性替换完。

推荐任务组：

1. 运营闭环可用：任务创建/读取、知识库 list/upsert/bind、readiness 检查、正式匹配前阻塞原因可见。
2. 资料包接入可用：通过领域 `intake/init` 编排入口，让对象存储中的核查表和资料包对象引用正式进入任务，不在前端保存私有 URL，也不重复建设上传通道。
3. 执行控制可用：工作区同步只沉淀依据、主数据和已有任务状态，资料包接入、正式核查、刷新状态都由操作员显式触发。
4. 人工复核可用：签名、盖章、勾选、手写日期、歧义匹配、人员设备授权缺口进入人工复核队列。
5. 报告归档可用：报告只输出内部辅助意见，必须保留证据摘要、人工决策和免责声明。
6. 后续再做生产化：PostgreSQL schema、正式 RBAC、队列/worker、RAGFlow 检索编排、ZIP 解包与 OCR 批处理。

MaxKB、RAGFlow 或其他知识库 provider 的需求规范是：服务端配置、平台保存 provider refs、前端只看安全摘要、召回结果只能作为支持证据，不能覆盖依据、主数据、人工决策或最终结论。当前前置平台联调优先按 MaxKB 项目级知识库推进。

## 任务状态

```text
draft
  -> blocked_missing_basis
  -> blocked_missing_master_data
  -> ready_for_packet
  -> packet_uploaded
  -> extracting
  -> matching
  -> awaiting_human_review
  -> report_ready
  -> archived
  -> failed
  -> canceled
```

已归档、失败或取消的任务不能再回到执行中状态。状态事件只保存安全摘要，不保存密钥、私有 URL、原始 provider trace、完整 prompt 或未截断全文。

## 当前门禁

- 没有已发布依据版本时，任务会进入 `blocked_missing_basis`。
- 需要主数据但没有可用主数据引用时，任务会进入 `blocked_missing_master_data`。
- 判定依据确认和项目主数据初始化是正式资料核查前的强制前置阶段；平台不得在每次资料包上传时绕过前置阶段，让智能体临时重新理解合同边界、人员设备清单或依据适用性。
- 正式核查前，工作区应绑定组织/分包队伍知识库，用于召回历史资料模板、已确认字段、人工修正记录和可复用证据摘要。
- 领域正式入口为 `POST /api/opening-condition/pilot-tasks/intake-init`；该入口只接收已上传对象的安全引用，并在一次编排中完成任务初始化、资料包绑定、依据/主数据/知识库解析和 readiness 返回。
- `intake/init` 优先使用后端受控 checklist adapter：若请求未显式提供 checklist definition，后端会先根据 `checklistObject` 的已知模板派生任务内 checklist definition；若模板未识别且任务也没有既有定义，则返回“需人工补定义”的安全诊断，而不是伪造正式核查输入。
- packet 在任务内不仅保存 `sourceObjects`，还保存一份 `inventoryEntries` 清单事实：若前端显式提供资料条目清单，平台优先持久化该清单；否则若资料对象是可读取 ZIP，后端会优先提取真实 ZIP manifest 条目；再不满足时才由 `sourceObjects` 默认派生一份 bounded inventory，供 formal match、人工复核说明和后续 OCR 能力统一复用。
- 工作区页面加载和上下文切换只允许同步业务事实与已有任务状态，不得隐式触发正式核查；正式资料包接入和正式匹配必须由操作员显式发起。
- 任务在 intake/init 阶段应持有一份规范化 checklist definition；正式核查优先复用任务内 checklist definition，而不是依赖前端每次重新临时拼装并传入全部核查项。
- 资料包 intake 会保存核查表对象引用和资料对象清单，并写入 `packet_uploaded` 安全事件。
- 核查匹配优先使用确定性规则：核查表条目先匹配资料包文件名/摘要和已发布主数据，再为缺失、歧义、主数据缺口或视觉断言不确定创建人工复核项。
- 正式核查优先匹配 `packet.inventoryEntries` 的条目名、相对路径和摘要；若 inventory entry 绑定了上传对象，证据继续安全回指该对象，但操作员看到的是更贴近真实资料内容的条目级名称。
- 当 ZIP manifest 提取不可用时，intake/init 和 packet 事件会返回安全的 fallback reason，帮助操作员区分“已读到真实清单”与“当前仍是对象级兜底清单”。
- 合同、补充协议等依据记录用于确认参与机构和合同工作范围；人员、设备核查项必须通过该工作区内已发布或人工批准的项目主数据确认，不能仅凭上传文件名或证书文本自动通过。
- 当前试点只核查资料核查范围；现场核查、应急响应、现场观测等无资料证据的条目应标记为 `out_of_scope` 或 `not_applicable`，不计为资料缺失失败。
- 签名、盖章、勾选、手写日期等视觉要素记录为 `visualAssertions`，只能说明检测或人工确认的存在性、清晰度和证据位置，不证明实体签章或签名真实有效。
- 人工复核项支持确认、修正、驳回和延期；阻塞项全部处理后，任务可进入 `report_ready`。
- 内部辅助报告摘要只能在阻塞人工复核项清零后生成，报告归档会保留任务、报告资产、证据摘要和事件链。
- 已发布依据版本会使同一工作区内先前发布的依据版本进入 `superseded`。
- 主数据可以通过人工决策发布、人工批准或驳回。
