# 词汇训练与检测：本次对话产品定义与约束

## 1. 本文档用途

本文档用于约束本次对话只处理“学生端-词汇训练与检测”功能域。

后续排查、改动、验收都必须先对齐这里的定义：先确认数据源、状态链、页面入口和回写链路，再处理 UI 或交互细节。

## 2. 产品定位

“词汇训练与检测”不是单一页面按钮，而是学生端围绕词汇学习形成的闭环：

1. 从“学习进度”或“词汇书”抽取一轮词汇检测。
2. 学生按指定作答方式完成检测。
3. 系统即时判分并展示错词、正确词和不确定项。
4. 检测结果写入历史记录。
5. 检测结果同步回学生词汇学习进度。
6. 已学单词、学习进度、首页任务和检测记录读取同一套状态结果。

因此，本功能的核心不是“显示一套题”，而是“用检测驱动学生词汇状态变化”。

## 3. 功能范围

本对话负责以下内容：

- 词汇检测入口与答题页。
- 学习进度检测。
- 词汇书抽词检测。
- 检测结果页与逐题反馈。
- 检测历史记录展示所依赖的检测记录数据。
- 已学单词、学习进度中由词汇检测引起的状态变化。
- 词汇题目生成、释义清洗、作答判分等领域规则。

本对话不负责以下内容，除非确认根因就在上游：

- 教师端学生总览、建议页、后台审核流。
- 词汇导入后台的产品体验。
- 初始诊断词汇题库与画像诊断算法。
- 学案生成链路本身。

如果问题断点在教师端、后台端或词汇导入端，不允许在学生端继续堆补丁，必须指出上游断点。

## 4. 当前页面与入口

### 4.1 我的词汇

“我的词汇”是聚合入口，包含三个可展开模块：

- 已学单词
- 词汇检测
- 检测记录

该页的职责是把学生词汇相关信息集中起来，但不能制造第二套数据口径。

### 4.2 词汇检测

词汇检测页提供两种检测入口：

- 学习进度检测：从 `student_vocab_progress` 中抽取学生当前学习或复习中的词。
- 词汇书抽词检测：从 `word_books`、`word_units`、`book_unit_vocab` 指定范围抽词。

检测开始后，题目保存在 `st.session_state["student_test_payload"]`。提交后清除当前检测 payload，并把结果保存到 `st.session_state["student_test_result"]`，页面切换为结果反馈。

### 4.3 已学单词

已学单词读取 `student_vocab_progress`，再关联 `vocab_items` 和学案词汇快照进行展示。

只要一个词进入 `student_vocab_progress`，它就属于学生词汇学习记录的一部分。页面不能单独伪造“已学”状态。

### 4.4 学习进度

学习进度读取 `student_vocab_progress`，并按词汇书、单元统计：

- 已学数量
- 总词量
- `learning` 数量
- `review` 数量
- `mastered` 数量

学习进度页面只展示状态，不应成为独立写入入口。

## 5. 核心数据表

### 5.1 词条与词汇书

- `vocab_items`：标准词条本体，包含 `lemma`、`normalized_lemma`、`default_meaning` 等。
- `word_books`：词汇书。
- `word_units`：词汇书单元。
- `book_unit_vocab`：词汇书、单元、词条之间的映射。

### 5.2 学生词汇状态

- `student_vocab_progress`：学生-词条维度的学习状态，是已学单词和学习进度的核心数据源。

关键字段：

- `status`：`learning`、`review`、`mastered`。
- `review_count`：复习次数。
- `error_count`：错误次数。
- `memory_score`：记忆稳定度。
- `first_source_book_id` / `first_source_unit_id`：首次进入学习进度的来源。
- `last_review_time` / `next_review_time`：复习时间链路。

### 5.3 检测记录

- `vocab_test_records`：一轮检测的总记录。
- `vocab_test_record_items`：一轮检测的逐题明细。

检测记录必须真实反映提交结果，不能只写总分不写明细，也不能只写明细不回写进度。

## 6. 检测类型

### 6.1 学习进度检测

入口参数：

- 检测类型：`新词检测`、`复习检测`
- 作答方式：`英译中`、`中译英`、`混合模式`
- 本次检测题数：15、25、35、45、60

抽题规则：

- `新词检测`：从当前学生 `student_vocab_progress.status == "learning"` 的词中抽取。
- `复习检测`：从当前学生 `student_vocab_progress` 中按较早复习时间优先抽取，再随机打乱并截取题数。

### 6.2 词汇书抽词检测

入口参数：

- 词汇书
- 单元范围：可多选；不选则代表整本词汇书。
- 作答方式：`英译中`、`中译英`、`混合模式`
- 本次检测题数：15、25、35、45、60

抽题规则：

- 从 `book_unit_vocab` 按词汇书和可选单元范围抽取。
- 同一个 `vocab_item_id` 在多单元范围内只出现一次。
- 随机打乱后截取指定题数。

## 7. 作答方式与判分规则

### 7.1 英译中

题目展示英文词，学生选择中文释义。

选项来源：

- 正确释义来自当前词条清洗后的 `default_meaning`。
- 干扰项来自同一批候选词的清洗释义。
- 固定追加 `我不确定` 选项。

判分：

- 学生选择的文本与清洗后正确释义一致，才算正确。
- 选择 `我不确定` 记为不确定，且不算正确。

### 7.2 中译英

题目展示中文释义，学生输入英文词。

判分：

- 输入内容经过 NFKC 归一化、大小写折叠、空白压缩、首尾标点清理。
- 归一化后必须与 `word` 一致才算正确。
- 不允许用宽松 fallback 把近似答案静默判对。

### 7.3 混合模式

每道题在 `英译中` 和 `中译英` 之间随机选择一种。

## 8. 提交后的状态回写

提交检测时必须完成三件事：

1. 计算本轮逐题结果、总分、正确率和不确定数量。
2. 写入 `vocab_test_records` 和 `vocab_test_record_items`。
3. 同步更新 `student_vocab_progress`。

### 8.1 词汇书抽词检测回写

- 答对：状态设为 `mastered`，`review_count` 至少为 3，`memory_score` 至少为 4.5，清空下次复习时间。
- 答错或未作答：状态设为 `learning`，`review_count` 归 0，`error_count + 1`，`memory_score` 下降，次日复习。

### 8.2 学习进度检测回写

新词检测：

- 答对：状态设为 `mastered`，`review_count` 至少为 3，清空下次复习时间。
- 答错或未作答：状态设为 `learning`，`review_count` 归 0，`error_count + 1`，次日复习。

复习检测：

- 答对：`review_count + 1`，按记忆分和复习次数计算下次复习；复习次数达到阈值后进入 `mastered`。
- 答错或未作答：状态回到 `learning`，`review_count` 归 0，`error_count + 1`，次日复习。

## 9. 一致性要求

任何改动都必须维护以下一致性：

- 题目来源与页面显示一致。
- 页面提交结果与 `vocab_test_records` 一致。
- 逐题反馈与 `vocab_test_record_items` 一致。
- 已学单词与 `student_vocab_progress` 一致。
- 学习进度统计与 `student_vocab_progress`、`book_unit_vocab`、`vocab_items.normalized_lemma` 一致。
- 首页任务、我的词汇、学习进度读取同一条状态链。

不允许出现以下假修复：

- 只改页面文案，不修正数据状态。
- 只在页面上过滤异常，不修正抽题或回写根因。
- 写入失败后用静默兜底伪装成功。
- 为了某个单词或某次检测写特殊 case。
- 在已有领域规则之外复制一套判分或状态计算逻辑。

## 10. 本对话允许修改的文件

优先文件：

- `student_vocab_test_view.py`
- `student_vocab_domain_service.py`
- `student_ui_copy.py`

需要触达数据链时允许修改：

- `db_student.py`
- `student_content_service.py`
- `student_content_views.py`
- `student_records_data.py`

触达高冲突文件前必须说明原因：

- `student_app.py`
- `db_student.py`
- `student_records_data.py`
- `student_shell_view.py`

## 11. 验收方式

每次改动至少执行：

- Python 语法检查。
- 相关函数最小联调或可替代的静态链路检查。

涉及页面行为时，必须核对：

- 数据读取入口是否正确。
- 状态回写是否发生且字段含义正确。
- 页面展示是否来自同一数据源。
- 检测记录与学习进度是否同步。

若无法执行真实数据库联调，必须明确说明未验证项，并给出阻塞原因。

## 12. 当前查证来源

本定义基于以下本地资料和实现梳理：

- `AGENTS.md`：功能域和协作规则。
- `WORKSTREAMS.md`：词汇训练与检测职责边界。
- `CONTROL_TOWER.md`：允许文件和总控职责。
- `student_vocab_test_view.py`：检测入口、答题页、结果反馈。
- `student_vocab_domain_service.py`：释义清洗、题目构造、判分规则。
- `student_ui_copy.py`：检测结果文案。
- `db_student.py`：抽题、提交、检测记录写入、进度同步。
- `student_records_data.py`：已学单词、检测记录读取。
- `student_content_views.py`：我的词汇、已学单词、学习进度页面。
- `system_check_student.py`：本地表结构说明。
