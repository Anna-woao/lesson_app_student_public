# Codex 对话框与文件边界

## 建议保留的活跃对话框

### `学生端-P0-首页/任务池/画像`

- 负责：学生首页、任务池、画像页、轻状态区
- 主文件：`student_app.py`、`student_home_viewmodel.py`、`student_shell_view.py`、`student_content_*`

### `学生端-词汇训练与检测`

- 负责：词汇检测、结果页、已学单词、学习进度的词汇训练交互
- 主文件：`student_vocab_test_view.py`、`student_vocab_domain_service.py`、`student_ui_copy.py`、`db_student.py`

### `学生端-记录/画像回写`

- 负责：训练结果回写、画像快照、lesson/vocab 数据一致性
- 主文件：`student_records_data.py`、`student_diagnosis_service.py`、`diagnostic_vocab_service.py`

### `教师端-P1-学生总览/详情/建议`

- 负责：教师协同端页面
- 主文件：`D:/lesson_app/admin_app.py`、`D:/lesson_app/app_tab_views.py`、`D:/lesson_app/app_ui_helpers.py`

### `后台-P2-生成链路/状态机/监督池`

- 负责：生成、发布、状态流转、异常池、待审核池
- 主文件：`D:/lesson_app/generator.py`、`D:/lesson_app/lesson_export_service.py`、`D:/lesson_app/db_admin_supabase.py`

### `部署与联调自动化`

- 负责：端口、脚本、日志、健康检查、启动/重启
- 主文件：`D:/lesson_app/scripts/devops/*`

## 禁止并行修改的高冲突文件

- `student_app.py`
- `db_student.py`
- `student_records_data.py`
- `student_shell_view.py`
- `D:/lesson_app/admin_app.py`
- `D:/lesson_app/app.py`
- `D:/lesson_app/app_tab_views.py`
- `D:/lesson_app/db.py`
- `D:/lesson_app/generator.py`

## 使用方式

- 一个对话框只接一个目标。
- 开工前先确认自己只改哪几个文件。
- 如果要碰高冲突文件，先暂停其它对话框。
