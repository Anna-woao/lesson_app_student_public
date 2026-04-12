"""学生前台入口（最小可用版）。

这个文件的目标不是一次做完完整产品，
而是先把“学生能看到的页面”和“管理员后台”分开。

当前提供：
1. 查看最近学案
2. 查看完整学案
3. 查看已学单词
4. 查看学习进度
5. 查看词汇检测记录

说明：
- 当前学生端读取链已切到 Supabase

注意：
- 这还是 MVP
- 现在先用“选择学生”模拟登录
- 后面再升级成学生账号 / 口令 / 邀请码
"""

import streamlit as st

import db_student as db


# ------------------------------
# 页面配置
# ------------------------------
st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")


def build_student_options(students):
    """
    把 students 查询结果转成：
    {显示标签: student_id}
    """
    return {f"{student[1]}（{student[2]}）": student[0] for student in students}


def render_recent_lessons(student_id: int):
    """
    渲染最近学案，并支持查看完整学案内容。
    """
    st.markdown("## 我的最近学案")

    recent_lessons = db.get_recent_lessons_by_student(student_id, limit=5)
    if not recent_lessons:
        st.info("你目前还没有学案记录。")
        return

    selected_lesson_id = st.session_state.get("student_selected_lesson_id")

    for lesson_id, lesson_type, difficulty, topic, created_at in recent_lessons:
        with st.container():
            st.markdown(f"### 学案 ID：{lesson_id}")
            st.write(f"题型：{lesson_type}")
            st.write(f"难度：{difficulty}")
            st.write(f"主题：{topic}")
            st.write(f"创建时间：{created_at}")

            action_col1, action_col2 = st.columns([1, 5])

            with action_col1:
                if st.button("查看完整学案", key=f"view_lesson_{lesson_id}"):
                    st.session_state["student_selected_lesson_id"] = lesson_id
                    st.rerun()

            with action_col2:
                if selected_lesson_id == lesson_id:
                    if st.button("收起当前学案", key=f"hide_lesson_{lesson_id}"):
                        st.session_state["student_selected_lesson_id"] = None
                        st.rerun()

            if selected_lesson_id == lesson_id:
                lesson_detail = db.get_lesson_detail_for_student(student_id, lesson_id)

                if not lesson_detail:
                    st.warning("没有读取到这份学案的完整内容。")
                else:
                    (
                        _lesson_id,
                        lesson_type,
                        difficulty,
                        topic,
                        content,
                        created_at,
                    ) = lesson_detail

                    with st.expander("完整学案内容", expanded=True):
                        st.write(f"题型：{lesson_type}")
                        st.write(f"难度：{difficulty}")
                        st.write(f"主题：{topic}")
                        st.write(f"创建时间：{created_at}")
                        st.text_area(
                            "学案正文",
                            value=content or "",
                            height=520,
                            key=f"student_lesson_content_{lesson_id}",
                        )

            st.markdown("---")



import random
import re


def _normalize_english_answer(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s'-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _is_english_answer_correct(user_answer: str, correct_word: str) -> bool:
    return _normalize_english_answer(user_answer) == _normalize_english_answer(correct_word)


def _build_student_question_modes(words, test_mode):
    question_modes = {}
    for row in words:
        vocab_item_id = row[0]
        if test_mode == "混合模式":
            question_modes[vocab_item_id] = random.choice(["英译中", "中译英"])
        else:
            question_modes[vocab_item_id] = test_mode
    return question_modes


def _build_student_mcq_options(words, question_modes):
    all_meanings = []
    for row in words:
        if len(row) >= 3 and row[2]:
            all_meanings.append(row[2])

    mcq_options = {}
    for row in words:
        vocab_item_id, _word, meaning = row[:3]
        if question_modes.get(vocab_item_id) != "英译中":
            continue
        wrong_pool = [m for m in all_meanings if m and m != meaning]
        random.shuffle(wrong_pool)
        options = [meaning] + wrong_pool[:2] + ["我不记得了"]
        deduped = []
        for item in options:
            if item not in deduped:
                deduped.append(item)
        random.shuffle(deduped)
        mcq_options[vocab_item_id] = deduped
    return mcq_options


def _reset_student_test_state():
    keys = [
        "student_test_words",
        "student_test_mode",
        "student_test_type",
        "student_test_source_label",
        "student_test_source_type",
        "student_test_source_book_id",
        "student_test_source_unit_id",
        "student_test_question_modes",
        "student_test_mcq_options",
        "student_test_results",
        "student_test_submitted",
        "student_test_score",
        "student_test_total",
        "student_test_save_message",
    ]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    dynamic_keys = [k for k in list(st.session_state.keys()) if k.startswith("student_test_answer_")]
    for key in dynamic_keys:
        del st.session_state[key]


def render_student_vocab_test(student_id: int, student_label: str):
    st.markdown("## 我的词汇检测")
    st.caption("当前学生端自测已经接上 Supabase 读取链。是否写入检测记录取决于当前 RLS 是否开放 insert。")

    test_tab1, test_tab2 = st.tabs(["学习进度检测", "词汇书抽词检测"])

    with test_tab1:
        progress_mode = st.selectbox(
            "作答方式",
            ["英译中", "中译英", "混合模式"],
            key="student_progress_test_mode",
        )
        progress_count = st.selectbox(
            "本次题数",
            [10, 15, 20, 30],
            index=1,
            key="student_progress_test_count",
        )
        if st.button("开始学习进度检测", key="student_start_progress_test"):
            _reset_student_test_state()
            words = db.get_progress_test_pool(student_id, count=progress_count)
            if not words:
                st.warning("你当前还没有可用于检测的已学单词。")
            else:
                st.session_state["student_test_words"] = words
                st.session_state["student_test_mode"] = progress_mode
                st.session_state["student_test_type"] = "学习进度检测"
                st.session_state["student_test_source_label"] = f"学习进度检测：{student_label}"
                st.session_state["student_test_source_type"] = "student_progress"
                st.session_state["student_test_source_book_id"] = None
                st.session_state["student_test_source_unit_id"] = None
                st.session_state["student_test_question_modes"] = _build_student_question_modes(words, progress_mode)
                st.session_state["student_test_mcq_options"] = _build_student_mcq_options(words, st.session_state["student_test_question_modes"])
                st.rerun()

    with test_tab2:
        books = db.get_all_word_books()
        if not books:
            st.info("当前还没有可用于检测的词汇书。")
        else:
            book_options = {f"{b[1]}" if not b[2] else f"{b[1]}（{b[2]}）": b[0] for b in books}
            selected_book_label = st.selectbox("选择词汇书", list(book_options.keys()), key="student_test_book_select")
            selected_book_id = book_options[selected_book_label]
            units = db.get_units_by_book(selected_book_id)
            unit_options = {"整本词汇书": None}
            for unit_id, unit_name, _unit_order in units:
                unit_options[unit_name] = unit_id
            selected_unit_label = st.selectbox("选择单元", list(unit_options.keys()), key="student_test_unit_select")
            selected_unit_id = unit_options[selected_unit_label]
            book_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_book_test_mode")
            book_count = st.selectbox("本次题数", [10, 15, 20, 30], index=1, key="student_book_test_count")
            random_mode = st.checkbox("随机抽词", value=True, key="student_book_test_random")
            if st.button("开始词汇书抽词检测", key="student_start_book_test"):
                _reset_student_test_state()
                words = db.get_book_vocab_for_test(selected_book_id, selected_unit_id, count=book_count, random_mode=random_mode)
                if not words:
                    st.warning("当前范围内没有可用于检测的单词。")
                else:
                    source_scope = selected_unit_label if selected_unit_id is not None else "整本词汇书"
                    st.session_state["student_test_words"] = words
                    st.session_state["student_test_mode"] = book_mode
                    st.session_state["student_test_type"] = "词汇书抽词检测"
                    st.session_state["student_test_source_label"] = f"{selected_book_label} / {source_scope}"
                    st.session_state["student_test_source_type"] = "word_book"
                    st.session_state["student_test_source_book_id"] = selected_book_id
                    st.session_state["student_test_source_unit_id"] = selected_unit_id
                    st.session_state["student_test_question_modes"] = _build_student_question_modes(words, book_mode)
                    st.session_state["student_test_mcq_options"] = _build_student_mcq_options(words, st.session_state["student_test_question_modes"])
                    st.rerun()

    if st.session_state.get("student_test_words"):
        words = st.session_state.get("student_test_words", [])
        question_modes = st.session_state.get("student_test_question_modes", {})
        mcq_options = st.session_state.get("student_test_mcq_options", {})

        st.markdown("---")
        st.write(f"当前检测：**{st.session_state.get('student_test_type', '')}**")
        st.write(f"来源：**{st.session_state.get('student_test_source_label', '')}**")
        st.write(f"作答方式：**{st.session_state.get('student_test_mode', '')}**")
        st.write(f"题数：**{len(words)}**")

        user_answers = {}
        for i, row in enumerate(words, start=1):
            vocab_item_id, word, meaning = row[:3]
            one_mode = question_modes.get(vocab_item_id, "英译中")
            st.markdown(f"### 第 {i} 题")
            st.caption(f"本题题型：{one_mode}")
            answer_key = f"student_test_answer_{vocab_item_id}"
            if one_mode == "英译中":
                user_answers[vocab_item_id] = st.radio(
                    f"请选择 **{word}** 的中文意思：",
                    mcq_options.get(vocab_item_id, [meaning, "我不记得了"]),
                    key=answer_key,
                )
            else:
                user_answers[vocab_item_id] = st.text_input(
                    f"请根据中文意思写出英文：**{meaning}**",
                    key=answer_key,
                )

        if st.button("提交本轮检测", key="student_submit_test"):
            results = []
            score = 0
            for row in words:
                vocab_item_id, word, meaning = row[:3]
                mode = question_modes.get(vocab_item_id, "英译中")
                user_answer = user_answers.get(vocab_item_id, "")
                if mode == "英译中":
                    is_correct = (user_answer == meaning)
                else:
                    is_correct = _is_english_answer_correct(user_answer, word)
                if is_correct:
                    score += 1
                results.append(
                    {
                        "vocab_item_id": vocab_item_id,
                        "word": word,
                        "meaning": meaning,
                        "mode": mode,
                        "user_answer": user_answer,
                        "is_correct": is_correct,
                    }
                )

            st.session_state["student_test_results"] = results
            st.session_state["student_test_score"] = score
            st.session_state["student_test_total"] = len(words)
            st.session_state["student_test_submitted"] = True
            ok, message = db.try_save_student_test_result(
                student_id=student_id,
                source_type=st.session_state.get("student_test_source_type"),
                source_book_id=st.session_state.get("student_test_source_book_id"),
                source_unit_id=st.session_state.get("student_test_source_unit_id"),
                source_label=st.session_state.get("student_test_source_label"),
                test_type=st.session_state.get("student_test_type"),
                test_mode=st.session_state.get("student_test_mode"),
                results=results,
            )
            st.session_state["student_test_save_message"] = message
            st.rerun()

    if st.session_state.get("student_test_submitted"):
        st.markdown("---")
        st.subheader("本轮检测结果")
        score = st.session_state.get("student_test_score", 0)
        total = st.session_state.get("student_test_total", 0)
        results = st.session_state.get("student_test_results", [])
        accuracy = score / total if total else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("答对题数", score)
        c2.metric("总题数", total)
        c3.metric("正确率", f"{accuracy:.0%}")
        if st.session_state.get("student_test_save_message"):
            st.info(st.session_state["student_test_save_message"])

        wrong_results = [r for r in results if not r.get("is_correct")]
        if not wrong_results:
            st.success("本轮全对，很棒。")
        else:
            st.markdown("### 错题订正")
            for i, row in enumerate(wrong_results, start=1):
                correct_answer = row["meaning"] if row["mode"] == "英译中" else row["word"]
                st.write(
                    f"{i}. {row['word']} | 模式：{row['mode']} | 你的答案：{row.get('user_answer') or '（未作答）'} | 正确答案：{correct_answer}"
                )
        if st.button("清空本轮检测", key="student_clear_test"):
            _reset_student_test_state()
            st.rerun()



def render_student_home(student_id: int, student_label: str):
    st.subheader(f"欢迎，{student_label.split('（')[0]}")

    render_recent_lessons(student_id)

    st.markdown("## 我的已学单词")
    learned_words = db.get_student_learned_vocab(student_id)
    if not learned_words:
        st.info("你目前还没有已学习单词。")
    else:
        show_count = st.selectbox("显示多少个已学单词", [20, 50, 100], index=0, key="student_learned_word_count")
        for i, row in enumerate(learned_words[:show_count], start=1):
            (lemma, meaning, status, review_count, error_count, memory_score, _first_learned_at, _last_review_time, _next_review_time) = row
            st.write(
                f"{i}. {lemma} - {meaning} | 状态：{status} | 复习次数：{review_count} | 错误次数：{error_count} | 记忆评分：{memory_score}"
            )

    st.markdown("## 我的学习进度")
    book_progress = db.get_student_book_progress(student_id)
    if not book_progress:
        st.info("你目前还没有词汇学习进度。")
    else:
        for row in book_progress:
            (book_id, book_name, volume_name, learned_count, total_count, mastered_count, learning_count, review_count) = row
            label = f"{book_name}" if not volume_name else f"{book_name}（{volume_name}）"
            ratio = learned_count / total_count if total_count > 0 else 0
            st.markdown(f"### {label}")
            st.write(f"已学：{learned_count} / {total_count}")
            st.progress(ratio)
            st.write(f"状态分布：mastered {mastered_count} | learning {learning_count} | review {review_count}")
            unit_progress = db.get_student_unit_progress(student_id, book_id)
            if unit_progress:
                with st.expander("查看单元进度", expanded=False):
                    for unit_row in unit_progress:
                        _, unit_name, _unit_order, unit_learned_count, unit_total_count = unit_row
                        unit_ratio = unit_learned_count / unit_total_count if unit_total_count > 0 else 0
                        st.write(f"{unit_name}：{unit_learned_count} / {unit_total_count}")
                        st.progress(unit_ratio)
            st.markdown("---")

    render_student_vocab_test(student_id, student_label)

    st.markdown("## 我的检测记录")
    test_records = db.get_student_vocab_test_records(student_id, limit=10)
    if not test_records:
        st.info("你目前还没有词汇检测记录。")
    else:
        for row in test_records:
            (test_record_id, _source_type, _source_book_id, _source_unit_id, source_label, test_type, test_mode, total_count, correct_count, accuracy, is_synced_to_progress, is_wrong_retry_round, created_at) = row
            retry_tag = " | 错词重测" if is_wrong_retry_round else ""
            sync_tag = "已同步学习进度" if is_synced_to_progress else "仅记录未同步"
            with st.expander(f"{created_at} | {test_type} | {correct_count}/{total_count} | {accuracy:.0%}{retry_tag}", expanded=False):
                st.write(f"来源：{source_label}")
                st.write(f"作答方式：{test_mode}")
                st.write(f"同步状态：{sync_tag}")
                items = db.get_vocab_test_record_items(test_record_id)
                if items:
                    st.markdown("### 本轮明细")
                    for i, item in enumerate(items, start=1):
                        (_vocab_item_id, word, meaning, mode, user_answer, is_correct) = item
                        result_text = "正确" if is_correct else "错误"
                        standard_answer = meaning if mode == "英译中" else word
                        st.write(f"{i}. {word} | 模式：{mode} | 你的答案：{user_answer or '（未作答）'} | 正确答案：{standard_answer} | 结果：{result_text}")