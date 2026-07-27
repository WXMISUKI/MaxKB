# ZHGDX 数据库结构盘点归档

盘点日期：2026-07-27

## 1. 盘点范围

已对 `zhgdx` 数据库进行只读元数据盘点：

- 基础表：135 张
- 内容：表名、表注释、字段名、字段类型、字段注释、索引概况、行数概况
- 未读取或归档身份证号、手机号、密码、文件内容等业务敏感值
- 未修改数据库

## 2. 领域分层

### 项目与组织

- `biz_project`
- `biz_project_org`
- `biz_project_org_user`
- `biz_organization`
- `sys_dept`
- `sys_tenant`
- `sys_user`
- `sys_role`

### 人员与资质

- `biz_person_profile`
- `biz_project_person_certificate`
- `biz_project_person_contract`
- `biz_project_person_entry_exit`
- `biz_project_person_health_report`
- `biz_project_position`
- `biz_project_position_duty`
- `biz_worker`
- `biz_worker_certificate`
- `biz_worker_contract`
- `biz_worker_entry_exit`
- `biz_worker_medical`

### 队伍与设备

- `biz_work_team`
- `biz_work_group`
- `biz_team`
- `biz_structure_work_team`
- `biz_equipment`
- `biz_equipment_category`
- `biz_equipment_entry_exit`
- `biz_equipment_inspection`
- `biz_device_file`

### 体系文件与项目依据

- `biz_system_document`
- `biz_system_document_structure`
- `biz_safety_plan_doc`
- `biz_emergency_plan`
- `biz_special_plan`
- `biz_monthly_risk_source_doc`
- `biz_attachment`
- `sys_file`
- `sys_file_group`

### 安全、风险与审查

- `biz_safety_briefing`
- `biz_briefing_receiver`
- `biz_safety_diary`
- `biz_safety_meeting`
- `biz_safety_inspection`
- `biz_safety_inspection_issue`
- `biz_hazard_ledger`
- `biz_training_plan`
- `biz_training_record`
- `biz_training_sign`
- `biz_startup_condition`
- `biz_major_dangerous`
- `biz_dangerous_operation`
- `biz_dangerous_process`
- `biz_work_permit`
- `biz_supervisor_side_record`

### 工程结构与风险源

- `biz_engineering_structure`
- `biz_structure_risk_source`
- `biz_structure_major_dangerous`
- `biz_structure_dangerous_operation`
- `biz_structure_work_team`
- `biz_risk_source`
- `biz_risk_control_record`

### 平台运行与设备服务

- 巡检任务、巡检日志、巡检轨迹、IoT 设备、人脸同步、OTA、Dify 任务等运行支撑表。

## 3. 关键结论

### 3.1 队伍主键

`biz_work_team.id` 是队伍知识库绑定的唯一稳定主键。

`team_code` 可为空，不可作为唯一绑定键。

### 3.2 人员归属

项目人员通过 `biz_project_org_user.team_id` 归属队伍，人员证书和人员合同通过 `project_person_id` 继续关联。

### 3.3 设备归属

设备通过 `biz_equipment.team_id` 归属队伍，设备附件通过 `biz_device_file.device_id` 继续关联。

### 3.4 文件存储

文件既可能通过 `sys_file.id` 关联，也可能只在业务表中保存 `file_url` / `attachment_url`，还可能经由 `biz_attachment` 统一关联。

平台后端必须在调用网关前统一解析为实际文件内容。

### 3.5 项目级与队伍级边界

体系文件、安全策划、应急预案、风险源等适合作为项目共享依据；安全检查、隐患、培训、开工条件和危大工程记录当前缺少稳定队伍归属，不应直接写入队伍知识库。

## 4. 当前数据观测

本次只读统计观察到：

- `biz_work_team` 约 30 条记录，其中有效队伍约 23 条。
- 部分队伍 `team_code` 为空。
- 当前队伍基础文件引用字段基本没有实际关联数据。
- `biz_project_org_user`、人员证书、人员合同已有可用于联调的数据。
- `biz_equipment` 已有数据，但只有部分设备绑定队伍。
- 培训、设备附件、开工条件等部分表当前数据量较少或为空。

这些数据现状不改变正式结构设计，但说明首轮真实联调应优先选择已有人员证书或项目人员合同资料。
