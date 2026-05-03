# 项目总控-任务分配与验收

这个文件对应建议保留的总控对话框：`项目总控-任务分配与验收`。

它不负责直接改代码，只负责三件事：

- 记录当前有哪些活跃对话框
- 记录每个对话框负责什么
- 记录哪些高冲突文件已被占用

---

## 当前建议保留的活跃对话框

| 对话框 | 仓库 | 职责 | 当前允许文件 |
|---|---|---|---|
| 学生端-P0-首页/任务池/画像 | `lesson_app_student_public` | 学生主闭环首页、任务池、画像页 | `student_app.py` `student_home_viewmodel.py` `student_shell_view.py` `student_content_service.py` `student_content_views.py` |
| 学生端-词汇训练与检测 | `lesson_app_student_public` | 词汇检测、结果页、已学单词、学习进度交互 | `student_vocab_test_view.py` `student_vocab_domain_service.py` `student_ui_copy.py` `db_student.py` |
| 学生端-记录/画像回写 | `lesson_app_student_public` | 训练结果回写、画像快照、lesson/vocab 一致性 | `student_records_data.py` `student_diagnosis_service.py` `diagnostic_vocab_service.py` `supabase_client.py` |
| 教师端-P1-学生总览/详情/建议 | `lesson_app` | 教师协同页、学生总览、学生详情、建议 | `admin_app.py` `app_tab_views.py` `app_ui_helpers.py` `db.py` |
| 后台-P2-生成链路/状态机/监督池 | `lesson_app` | 生成链路、状态流转、待审核池、异常池 | `generator.py` `lesson_export_service.py` `lesson_docx_exporter.py` `db_admin_supabase.py` `db_common.py` |
| 部署与联调自动化 | `lesson_app` / `lesson_app_student_public` | 双端脚本、端口、日志、健康检查、联调 | `D:/lesson_app/scripts/devops/*` `D:/lesson_app_student_public/scripts/*.ps1` |

---

## 高冲突文件占用表

| 文件 | 当前 owner 对话框 | 是否允许并行修改 |
|---|---|---|
| `student_app.py` |  | 否 |
| `db_student.py` |  | 否 |
| `student_records_data.py` |  | 否 |
| `student_shell_view.py` |  | 否 |
| `D:/lesson_app/app.py` |  | 否 |
| `D:/lesson_app/admin_app.py` |  | 否 |
| `D:/lesson_app/app_tab_views.py` |  | 否 |
| `D:/lesson_app/db.py` |  | 否 |
| `D:/lesson_app/generator.py` |  | 否 |
| `D:/lesson_app/lesson_html_renderer.py` / `D:/lesson_app_student_public/lesson_html_renderer.py` |  | 否 |

---

## 开工登记模板

复制这一段到每个新对话框的第一条任务说明里：

```text
本次目标：

允许修改文件：

禁止碰触文件：

验收标准：
1.
2.
3.
```

---

## 关闭规则

- 已完成的对话框不再继续塞新需求。
- 做完后回到总控对话框登记“已完成/暂停/废弃”。
- 同一个需求如果跨了两个高冲突文件，先暂停其他相关对话框，再继续。
