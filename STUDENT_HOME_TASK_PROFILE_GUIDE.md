# 学生端-P0-首页/任务池/画像 对话约束文档

## 文档目的

本文件用于约束当前对话框的功能域、产品目标、数据链路和验收标准。

当前对话框只负责学生端主闭环中的三个页面：

- 学习首页
- 学习任务池
- 成长画像

本对话不负责词汇检测内部答题体验、记录写入、画像生成算法、教师端页面、后台生成链路。若问题根因位于这些上游或相邻模块，必须明确指出断点，不允许在首页或任务池里用显示层补丁掩盖。

## 已查依据

本说明基于当前仓库内已有协作文档和真实代码反推，不引入外部未落地产品假设。

- `AGENTS.md`：协作规则、根因原则、高冲突文件边界。
- `WORKSTREAMS.md`：学生端 P0 首页/任务池/画像的职责范围。
- `CONTROL_TOWER.md`：总控对话框中对该功能域的文件边界。
- `student_app.py`：学生端登录后页面入口、任务动作执行、页面路由。
- `student_home_viewmodel.py`：首页聚合数据、任务卡片决策、画像摘要聚合。
- `student_shell_view.py`：顶部导航、页面说明、轻状态、成长画像展示。
- `student_content_service.py` / `student_content_views.py`：任务池动作跳转后承接的学案、词汇、进度、检测记录内容页。

## 产品定位

### 学习首页

学习首页是学生登录后的默认起点，不是内容堆叠页。

它负责回答三个问题：

- 今天从哪里开始。
- 当前学习状态是什么。
- 下一步应该进入哪个明确任务。

首页应展示：

- 学生称呼、阶段标签、成长反馈。
- 今日主任务，包括标题、预计耗时、说明和开始按钮。
- 轻状态，包括本周完成度、连续学习天数、已解锁模块。
- 今日学习提醒，用来确认首页和任务池的关系。

首页不应该承接完整训练内容，也不应该直接混入学案列表、词汇长列表、检测历史长列表。它只做聚合、判断、引导。

### 学习任务池

学习任务池是当天可执行任务和可回看内容的集中入口。

它负责回答两个问题：

- 当前待完成任务有哪些。
- 已经产生的历史内容可以从哪里回看。

任务池应展示：

- 当前待完成任务卡片，最多保留少量高优先级任务。
- 历史内容池，包括最近学案、已学单词、历史检测记录或学习进度回看。
- 成长记录回看摘要，包括学案数、已学单词数、检测记录数。

任务池的按钮可以触发动作，但动作必须使用真实业务入口：

- 首次诊断：进入 `initial_diagnosis`。
- 词汇复习检测：调用 `db_student.build_progress_test` 后进入 `vocab_test`。
- 词汇书检测：调用 `db_student.build_book_test` 后进入 `vocab_test`。
- 学案回看：设置目标学案 id 后进入 `recent_lessons`。
- 已学单词：打开已学单词弹窗并进入 `my_vocab`。

任务池不应该自己复制词汇检测、学案详情或记录页逻辑。它只编排任务入口，不重写承接模块。

### 成长画像

成长画像页是学生理解当前阶段、重点方向和诊断结论的页面。

它负责回答三个问题：

- 当前处于什么学习阶段。
- 当前最需要关注什么方向。
- 诊断和画像快照给出的阶段总结是什么。

画像页应展示：

- 未完成首次诊断时，明确提示完成首次诊断后生成画像。
- 已有诊断时，展示当前阶段、重点方向、学习标题、阶段总结。
- 后续如果扩展画像维度，应优先来自 `diagnosis_summary` 和 `profile_payload`，不能在 UI 层临时拼接假数据。

画像页不负责生成画像，也不负责写回画像。画像生成和快照写入属于记录/画像回写功能域。

## 当前数据链路

### 首页聚合入口

`student_app.py` 在当前页为 `home`、`task_pool`、`profile_page` 时调用：

```python
build_student_home_viewmodel(student)
```

该函数位于 `student_home_viewmodel.py`，是本功能域的数据和任务决策中心。

### 读取数据源

首页聚合层当前读取：

- 最近学案：`get_student_recent_lessons`
- 已学词汇摘要：`get_student_learned_vocab_summary`
- 词汇书进度：`db_student.get_student_book_progress`
- 词汇检测记录：`get_student_vocab_test_records`
- 活跃日期：`get_student_activity_dates`
- 最新诊断记录：`get_latest_diagnosis_record`
- 最新画像快照：`get_latest_profile_snapshot`

这些读取共同决定首页状态、任务池卡片和成长画像内容。

### 任务决策规则

当前主任务优先级大致为：

1. 没有首次诊断：引导完成首次诊断。
2. 有诊断但没有检测记录：优先引导词汇书检测或词汇检测。
3. 有待复习词：优先引导复习检测。
4. 有未完成词汇书：引导当前词汇书检测。
5. 有最近学案：引导回看最近学案并完成练习。
6. 有画像快照中的 `priority_module`：按画像优先模块重排当前任务。

如果 `priority_module` 指向阅读、语法、写作，但当前没有对应专门训练入口，允许临时承接到最近学案或现有词汇检测入口，但必须在文案中说明“现阶段可直接承接的入口”是什么，不能伪装成已有完整专项训练。

## 状态与路由约定

学生端当前使用 `st.session_state["student_current_page"]` 保存当前页面。

功能域内核心页面：

- `home`：学习首页。
- `task_pool`：学习任务池。
- `profile_page`：成长画像。

任务池可定位到的承接区：

- `initial_diagnosis`
- `recent_lessons`
- `my_vocab`
- `learned_words`
- `vocab_test`
- `test_history`
- `progress`

`student_shell_view.SECTION_TO_PAGE` 负责 section 到页面的映射。改动任务入口时，必须同步检查这里的映射是否仍然成立。

## 修改边界

### 允许优先修改

- `student_app.py`
- `student_home_viewmodel.py`
- `student_shell_view.py`
- `student_content_service.py`
- `student_content_views.py`
- 本文档

### 谨慎触碰

以下文件是高冲突或相邻功能域文件。除非根因明确在这里，否则本对话不主动修改：

- `db_student.py`
- `student_records_data.py`
- `student_diagnosis_service.py`
- `diagnostic_vocab_service.py`
- `student_vocab_test_view.py`
- `student_vocab_domain_service.py`
- `student_ui_copy.py`

### 禁止用法

- 不允许只改显示文案来掩盖数据源缺失。
- 不允许在首页或任务池里复制检测、学案、画像生成逻辑。
- 不允许新增 fallback 静默吞错，让任务看起来存在但实际无法执行。
- 不允许保留与当前页面路径冲突的旧入口。
- 不允许让多个页面各算一套“今日任务”。

## 后续改动原则

任何涉及首页、任务池、画像的改动，必须先回答：

- 数据从哪里来。
- 状态由谁写入。
- 页面由谁展示。
- 点击动作最终进入哪个真实业务入口。

如果跨页面出现不一致，优先统一 `student_home_viewmodel.py` 的聚合结果和任务卡片结构，再调整 UI。

如果跨数据层出现不一致，先追到 `student_records_data.py`、`db_student.py` 或上游教师端/后台端，不允许在 `student_app.py` 里堆条件分支遮住问题。

## 验收方式

每次改动完成后至少执行：

```powershell
python -m py_compile student_app.py student_home_viewmodel.py student_shell_view.py student_content_service.py student_content_views.py
```

如果改动影响任务动作，还要最小联调检查：

- 首页是否能生成唯一明确的今日主任务。
- 点击主任务是否进入正确页面或承接区。
- 任务池当前任务和首页主任务是否来自同一份 viewmodel。
- 成长画像是否只展示诊断记录或画像快照中的真实字段。
- 空数据状态是否明确暴露真实缺口，而不是伪造任务或静默兜底。

## 本对话交付格式

每次完成改动后，需要说明：

- 改动目标。
- 涉及文件。
- 逻辑变化。
- 验收方式和结果。
- 若发现根因不在本功能域，明确指出上游断点。
