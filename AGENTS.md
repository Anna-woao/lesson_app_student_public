# Codex 协作规则

## 核心原则

- 解决问题必须优先追根因，不允许只为单一 Bug 打补丁。
- 不允许用 fallback、静默兜底、隐藏错误来伪装问题被解决。
- 不允许保留已经报废、无人引用、与当前功能路径冲突的旧代码。
- 每次改动都要说明：改动目标、涉及文件、逻辑变化、验收方式。
- 任何跨页面、跨数据层的问题，都要先统一数据源和状态链，再谈 UI 修饰。

## 并行开发边界

- 一个对话框只负责一个功能域，不混合多个目标。
- 同一时间不要让两个对话框同时修改同一个核心入口文件。
- 遇到高冲突文件时，必须先确认 ownership，再开始改动。

### 学生端高冲突文件

- `student_app.py`
- `db_student.py`
- `student_records_data.py`
- `student_shell_view.py`

### 学生端推荐工作流

- 首页/任务池/画像：`student_app.py`、`student_home_viewmodel.py`、`student_content_*`
- 词汇训练与检测：`student_vocab_test_view.py`、`student_vocab_domain_service.py`、`student_ui_copy.py`
- 记录/画像回写：`student_records_data.py`、`student_diagnosis_service.py`、`diagnostic_vocab_service.py`

## 联调要求

- 改动完成后，至少执行语法检查和最小联调检查。
- 涉及学生端页面的改动，要确认数据读取、状态回写、页面展示三层一致。
- 如果问题实际根因在教师端/后台端，不允许在学生端继续堆补丁，必须明确指出断点并回到上游修复。

## 上线前检查要求

- 检查是否存在补丁式逻辑、重复逻辑、废弃逻辑、未引用代码。
- 检查页面入口、数据入口、写入链路是否一致。
- 检查是否存在只改显示、不改状态、不改数据结构的假修复。
