# 模拟施工监理审查资料包设计

## 1. 总体设计

第一阶段采用：

> 项目级逻辑知识库 + metadata 过滤

用户在 MaxKB 中看到一个项目知识库；底层每份资料必须携带项目、合同段、监理标段、分包队伍、依据版本、资料类型和审查任务 metadata。

推荐目录形态：

```text
docs/simulated-pilot-dataset/
  NJDL-JD-A1/
    00_manifest/
    01_project_basis/
    02_contract_and_supervision/
    03_team_lj01_opening_condition/
    04_team_lj01_construction_plan/
    05_review_examples/
    06_source_norms/
```

本 change 只定义规格；生成实际资料包时再创建上述目录和文件。

## 2. 模拟项目

```yaml
organization_id: org-supervision-demo
project_id: project-njdl-jd-a1
project_name: 南江至东岭高速公路改扩建工程
project_type: highway-reconstruction
contract_package_id: contract-jd-a1
contract_package_name: JD-A1 土建施工合同段
supervision_section_id: supervision-jl-01
supervision_section_name: JL-01 监理合同段
basis_version_id: basis-njdl-2026-01
effective_status: active
```

## 3. 参建单位与分包作业

```yaml
owner: 南江东岭高速建设有限公司
supervision_unit: 华东路桥工程监理咨询有限公司
general_contractor: 中交路建第二工程有限公司
subcontract_teams:
  - subcontract_team_id: team-lj-01
    team_name: LJ-01 路基土石方分包作业队
    work_scope: K12+000-K18+500 路基清表、挖方、填筑、排水临时工程
    pilot_scope: true
  - subcontract_team_id: team-ql-01
    team_name: QL-01 桥梁下部结构作业队
    work_scope: 桥梁桩基、承台、墩柱施工
    pilot_scope: false
  - subcontract_team_id: team-ja-01
    team_name: JA-01 交安设施作业队
    work_scope: 护栏、标志、标线及附属设施
    pilot_scope: false
```

第一阶段只生成和入库 `team-lj-01` 的完整审查资料；其余队伍只作为项目结构占位，避免第一批资料过大。

## 4. 第一批资料包清单

第一批建议 24 份资料，覆盖项目依据、合同监理、队伍开工条件、施工方案和历史样例。

| 编号 | 资料名称 | 类型 | 建议格式 | document_type | 主要用途 |
| --- | --- | --- | --- | --- | --- |
| 01 | 项目概况与合同段划分说明 | 项目依据 | md/docx | project_basis | 建立项目、标段、队伍上下文 |
| 02 | JD-A1 合同段主要合同条款摘编 | 合同依据 | md/docx | contract_basis | 审查合同责任和报审要求 |
| 03 | JL-01 监理规划摘编 | 监理依据 | md/docx | supervision_basis | 审查监理程序和职责 |
| 04 | 开工条件审查实施细则 | 审查依据 | md/docx | review_rule | 开工条件检查项来源 |
| 05 | 施工方案审查实施细则 | 审查依据 | md/docx | review_rule | 方案审查检查项来源 |
| 06 | 项目资料命名与归档规则 | 资料管理 | md/docx | archive_rule | 文件归档和可追溯要求 |
| 07 | LJ-01 分包合同范围说明 | 队伍资料 | md/docx | subcontract_scope | 队伍作业范围确认 |
| 08 | LJ-01 企业资质与安全生产许可证摘录 | 队伍资料 | md/docx | team_qualification | 资质审查 |
| 09 | LJ-01 项目负责人任命书 | 人员资料 | md/docx | personnel | 人员到岗审查 |
| 10 | LJ-01 安全员与质检员证书清单 | 人员资料 | xlsx/md | personnel | 关键岗位资格审查 |
| 11 | LJ-01 特种作业人员清单 | 人员资料 | xlsx/md | personnel | 特种作业资格审查 |
| 12 | LJ-01 主要机械设备进场清单 | 设备资料 | xlsx/md | equipment | 设备能力审查 |
| 13 | LJ-01 测量与试验仪器校验证明清单 | 设备资料 | xlsx/md | calibration | 仪器校验审查 |
| 14 | LJ-01 开工申请表 | 报审表 | docx/md | opening_application | 开工条件主表 |
| 15 | LJ-01 施工组织与人员进场报审表 | 报审表 | docx/md | opening_attachment | 开工附件 |
| 16 | LJ-01 安全技术交底记录 | 安全资料 | docx/md | safety_disclosure | 安全条件审查 |
| 17 | LJ-01 三级安全教育记录 | 安全资料 | xlsx/md | safety_training | 安全教育审查 |
| 18 | LJ-01 临时排水与便道准备情况说明 | 开工准备 | md/docx | site_preparation | 现场条件审查 |
| 19 | K12+000-K18+500 路基填筑施工方案 | 施工方案 | docx/md | construction_plan | 方案审查主文件 |
| 20 | 路基填料来源与试验报告摘要 | 试验资料 | md/docx | material_test | 材料适用性审查 |
| 21 | 路基填筑质量控制与检测计划 | 质量资料 | md/docx | quality_plan | 压实度、层厚、检测频率审查 |
| 22 | 路基施工安全风险辨识与控制措施 | 安全资料 | md/docx | safety_plan | 安全技术措施审查 |
| 23 | 历史样例：开工条件审查通过案例 | 历史样例 | md | review_example | 提示词和召回样例 |
| 24 | 历史样例：施工方案审查退回修改案例 | 历史样例 | md | review_example | 风险点和缺陷样例 |

## 5. 官方规范来源策略

规范资料分两类沉淀：

1. `source-register`: 保存官方标题、标准号、发布单位、实施日期、官方 URL、适用范围和建议入库片段。
2. `06_source_norms`: 后续若确认允许下载和使用，再保存官方 PDF 或摘编版；不得保存来源不明的转载版本。

第一阶段建议入库“规范来源登记 + 少量自写摘要”，避免一开始导入大量规范全文导致检索噪声过高。

## 6. Metadata 规则

每份资料至少携带：

```yaml
organization_id: org-supervision-demo
project_id: project-njdl-jd-a1
contract_package_id: contract-jd-a1
section_id: section-k12-k18
supervision_section_id: supervision-jl-01
subcontract_team_id: team-lj-01
review_task_id: opening-condition-lj01 或 construction-plan-lj01
basis_version_id: basis-njdl-2026-01
document_type: 按资料清单填写
source_object_id: 模拟对象 ID
content_hash: 生成实际文件后计算
effective_status: active / sample / draft
effective_date: 2026-07-18
indexed_at: 入库时间
```

## 7. 审查任务设计

### 7.1 开工条件审查

核心检查项：

- 分包作业范围是否与合同段和报审范围一致
- 企业资质和安全生产许可证是否齐备
- 项目负责人、安全员、质检员是否到岗并具备资格
- 特种作业人员是否满足作业内容要求
- 主要机械设备和试验检测仪器是否进场并可用
- 安全教育、技术交底、临时设施、便道、排水是否完成
- 资料命名、签章、日期、版本是否满足归档要求

### 7.2 施工方案审查

核心检查项：

- 方案适用范围是否与 K12+000-K18+500 路基作业一致
- 施工工艺、填料来源、压实控制、检测计划是否完整
- 质量控制点是否能对应检验评定要求
- 安全风险辨识和控制措施是否覆盖临边、机械、运输、雨季施工等风险
- 方案引用的依据版本是否为当前有效版本
- 缺陷项是否需要退回修改或人工复核

## 8. 验收标准

本资料包规格完成后，实际生成和入库应满足：

1. MaxKB 中存在一个项目级逻辑知识库。
2. 第一批资料数量控制在 10-30 份。
3. 每份资料能映射到项目、合同段、监理标段、队伍、审查任务和资料类型。
4. 开工条件问题能召回队伍资质、人员、设备、安全教育和开工申请资料。
5. 施工方案问题能召回项目依据、方案、质量计划、安全计划和相关规范摘要。
6. 输出必须标注引用来源，不把召回内容直接写成正式审查结论。

