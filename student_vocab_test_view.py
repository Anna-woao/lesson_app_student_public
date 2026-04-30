from __future__ import annotations

from html import escape, unescape
import re

import streamlit as st

import db_student as dbs
from student_ui_copy import build_test_result_summary


def _clean_feedback_text(value, fallback: str = "（未作答）") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    text = unescape(text.replace("&nbsp;", " "))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _get_correct_answer_text(item: dict) -> str:
    mode = str(item.get("mode") or "").strip()
    if mode == "英译中":
        return _clean_feedback_text(item.get("meaning"), fallback="（暂无答案）")
    return _clean_feedback_text(item.get("word"), fallback="（暂无答案）")


def _render_vocab_feedback_grid(results, empty_message: str, card_tone: str):
    if not results:
        st.info(empty_message)
        return

    cards_html = []
    for idx, item in enumerate(results, start=1):
        word = escape(_clean_feedback_text(item.get("word"), fallback="未命名单词"))
        mode = escape(str(item.get("mode") or ""))
        user_answer = escape(_clean_feedback_text(item.get("user_answer")))
        correct_answer = escape(_get_correct_answer_text(item))
        tone_label = "暂不确定" if item.get("is_uncertain") else ("需要订正" if card_tone == "wrong" else "回答正确")
        cards_html.append(
            (
                f'<div class="vocab-feedback-card vocab-feedback-card--{card_tone}">'
                '<div class="vocab-feedback-card-top">'
                '<div>'
                f'<div class="vocab-feedback-card-title">{idx}. {word}</div>'
                f'<div class="vocab-feedback-card-mode">{mode}</div>'
                "</div>"
                f'<span class="vocab-feedback-card-pill vocab-feedback-card-pill--{card_tone}">{tone_label}</span>'
                "</div>"
                '<div class="vocab-feedback-answer-row">'
                '<span class="vocab-feedback-answer-label">学生答案</span>'
                f'<span class="vocab-feedback-answer-value">{user_answer}</span>'
                "</div>"
                '<div class="vocab-feedback-answer-row">'
                '<span class="vocab-feedback-answer-label">正确答案</span>'
                f'<span class="vocab-feedback-answer-value">{correct_answer}</span>'
                "</div>"
                "</div>"
            )
        )

    st.markdown(f'<div class="vocab-feedback-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def _render_test_feedback_blocks(results):
    if not results:
        st.info("当前没有可展示的检测反馈。")
        return

    total_count = len(results)
    correct_results = [item for item in results if item.get("is_correct")]
    wrong_results = [item for item in results if not item.get("is_correct")]
    uncertain_results = [item for item in results if item.get("is_uncertain")]
    st.markdown(
        (
            '<div class="vocab-feedback-overview">'
            f'<div class="vocab-feedback-overview-item"><span class="label">本次题数</span><span class="value">{total_count}</span></div>'
            f'<div class="vocab-feedback-overview-item"><span class="label">答对</span><span class="value correct">{len(correct_results)}</span></div>'
            f'<div class="vocab-feedback-overview-item"><span class="label">答错</span><span class="value wrong">{len(wrong_results)}</span></div>'
            f'<div class="vocab-feedback-overview-item"><span class="label">不确定</span><span class="value pending">{len(uncertain_results)}</span></div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    word_chips = "".join(
        f'<span class="vocab-feedback-chip">{idx}. {escape(str(item.get("word", "") or "未命名单词"))}</span>'
        for idx, item in enumerate(results, start=1)
    )
    with st.expander(f"查看本次考查单词（{total_count}）", expanded=False):
        st.markdown(f'<div class="vocab-feedback-chip-wrap">{word_chips}</div>', unsafe_allow_html=True)

    wrong_tab, correct_tab = st.tabs(["需要订正", "回答正确"])
    with wrong_tab:
        _render_vocab_feedback_grid(
            wrong_results,
            empty_message="这一轮没有错词，表现很稳。",
            card_tone="wrong",
        )
    with correct_tab:
        _render_vocab_feedback_grid(
            correct_results,
            empty_message="这一轮暂时还没有答对的词，先把错词订正完就好。",
            card_tone="correct",
        )


def _build_vocab_test_prompt(question: dict) -> str:
    if question.get("mode") == "英译中":
        word = escape(_clean_feedback_text(question.get("word"), fallback="未命名单词"))
        return f"请选择 <strong>{word}</strong> 的中文意思"
    meaning = escape(_clean_feedback_text(question.get("meaning"), fallback="暂无提示"))
    return f"请根据中文意思写出英文：<strong>{meaning}</strong>"


def _count_answered_vocab_questions(questions) -> int:
    answered = 0
    for question in questions:
        key_prefix = "student_mcq_" if question.get("mode") == "英译中" else "student_text_"
        state_value = st.session_state.get(f"{key_prefix}{question['vocab_item_id']}")
        if str(state_value or "").strip():
            answered += 1
    return answered


def _render_vocab_test_intro(payload_exists: bool, result_exists: bool):
    if payload_exists:
        st.markdown(
            """
            <div class="student-home-card">
                <div class="student-home-kicker">进行中</div>
                <div class="student-home-task-title">这一轮词汇检测还没完成</div>
                <p class="student-home-task-desc">先把当前题目做完，再开始下一轮，会更容易看清今天真正需要巩固的词。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    if result_exists:
        st.markdown(
            """
            <div class="student-home-card">
                <div class="student-home-kicker">结果已保留</div>
                <div class="student-home-task-title">你刚完成的这轮检测还在这里</div>
                <p class="student-home-task-desc">先回看结果也可以，准备好了再开始下一轮。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        """
        <div class="student-home-card">
            <div class="student-home-kicker">Vocabulary Check</div>
            <div class="student-home-task-title">先选一种检测方式，再直接完成这一轮</div>
            <p class="student-home-task-desc">这里只负责开始检测、完成答题、回看结果。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_vocab_test_result_panel(result: dict):
    title, desc = build_test_result_summary(result)
    if not result.get("persistence_ok", True):
        st.warning("本次检测分数已算出，但历史记录暂未成功保存。请稍后重试，或联系老师检查数据库配置。")
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">检测总结</div>
            <div class="student-home-task-title">{title}</div>
            <p class="student-home-task-desc">{desc}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## 本次检测结果")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("得分", f"{result['score']} / {result['total']}")
    with col2:
        st.metric("正确率", f"{result['accuracy']:.0%}")
    with col3:
        if st.button("开始新一轮检测", key="restart_vocab_test_from_result", use_container_width=True):
            st.session_state.pop("student_test_result", None)
            st.rerun()
    _render_test_feedback_blocks(result.get("results", []))


def _render_progress_test_launcher(student_id: int):
    st.markdown("### 学习进度检测")
    st.caption("适合处理当前学习中或待复习的词汇，直接进入一轮轻量检测。")

    test_type = st.selectbox("检测类型", ["新词检测", "复习检测"], key="student_progress_test_type")
    test_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_progress_test_mode")
    test_count = st.selectbox("本次检测题数", [15, 25, 35, 45, 60], index=1, key="student_progress_test_count")

    if st.button("开始学习进度检测", key="start_student_progress_test", use_container_width=True):
        ok, payload = dbs.build_progress_test(student_id, test_type, test_mode, test_count)
        if ok:
            st.session_state["student_test_payload"] = payload
            st.session_state["student_test_source_label"] = f"学习进度检测：{test_type}"
            st.success("已进入学习进度检测。")
            st.rerun()
        else:
            st.warning(payload)


def _render_book_test_launcher(student_id: int):
    st.markdown("### 词汇书抽词检测")
    st.caption("适合从指定词汇书或单元直接开始，快速完成今天的词汇任务。")

    books = dbs.get_all_word_books()
    if not books:
        st.info("当前还没有词汇书。")
        return

    book_options = {label: book_id for book_id, label in books}
    selected_book_label = st.selectbox("选择词汇书", list(book_options.keys()), key="student_book_test_book")
    selected_book_id = book_options[selected_book_label]

    units = dbs.get_units_by_book(selected_book_id)
    unit_name_to_id = {unit_name: unit_id for unit_id, unit_name, _unit_order in units}
    selected_unit_labels = st.multiselect(
        "选择单元（可多选）；如果一个都不选，默认检测整本词汇书",
        options=list(unit_name_to_id.keys()),
        default=[],
        key="student_book_test_units",
    )
    selected_unit_ids = [unit_name_to_id[label] for label in selected_unit_labels]

    if selected_unit_labels:
        st.caption("当前已选择单元：" + " / ".join(selected_unit_labels))
    else:
        st.caption("当前范围：整本词汇书")

    test_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_book_test_mode")
    test_count = st.selectbox("本次检测题数", [15, 25, 35, 45, 60], index=1, key="student_book_test_count")

    if st.button("开始词汇书检测", key="start_student_book_test", use_container_width=True):
        ok, payload = dbs.build_book_test(
            student_id,
            selected_book_id,
            selected_unit_ids,
            test_mode,
            test_count,
        )

        if ok:
            st.session_state.pop("student_test_result", None)
            st.session_state["student_test_payload"] = payload
            scope = " / ".join(selected_unit_labels) if selected_unit_labels else "整本词汇书"
            st.session_state["student_test_source_label"] = f"词汇书抽词检测：{selected_book_label} / {scope}"
            st.success("已进入词汇书检测。")
            st.rerun()
        else:
            st.warning(payload)


def render_vocab_test(student_id: int, *, render_section_anchor, render_section_focus_badge):
    render_section_anchor("vocab_test")
    st.header("我的词汇检测")
    render_section_focus_badge("vocab_test")
    payload = st.session_state.get("student_test_payload")
    result = st.session_state.get("student_test_result")
    _render_vocab_test_intro(payload_exists=bool(payload), result_exists=bool(result))

    if not payload:
        launcher_left, launcher_right = st.columns(2)
        with launcher_left:
            _render_progress_test_launcher(student_id)
        with launcher_right:
            _render_book_test_launcher(student_id)

        if result:
            st.markdown("---")
            _render_vocab_test_result_panel(result)
        return

    st.markdown("---")
    questions = payload.get("questions", [])
    source_label = st.session_state.get("student_test_source_label", "学生检测")
    answered_count = _count_answered_vocab_questions(questions)
    pending_count = max(len(questions) - answered_count, 0)
    mode_summary = " / ".join(sorted({str(q.get("mode") or "") for q in questions if q.get("mode")})) or "未标注"

    st.markdown(
        f"""
        <div class="vocab-test-shell">
            <div class="vocab-test-shell-header">
                <div>
                    <div class="vocab-test-shell-title">正在答题</div>
                    <p class="vocab-test-shell-desc">
                        这一页只做一件事：把这一轮检测顺着做完。提交后，页面会自动切换到结果反馈。
                    </p>
                </div>
                <span class="vocab-test-shell-badge">当前范围：{escape(source_label)}</span>
            </div>
            <div class="vocab-test-overview">
                <div class="vocab-test-overview-item">
                    <span class="label">本轮题数</span>
                    <span class="value">{len(questions)}</span>
                </div>
                <div class="vocab-test-overview-item">
                    <span class="label">作答方式</span>
                    <span class="value">{escape(mode_summary)}</span>
                </div>
                <div class="vocab-test-overview-item">
                    <span class="label">已填写</span>
                    <span class="value">{answered_count}</span>
                </div>
                <div class="vocab-test-overview-item">
                    <span class="label">待完成</span>
                    <span class="value pending">{pending_count}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("student_vocab_test_form", clear_on_submit=False):
        user_answers = {}
        st.markdown('<div class="vocab-test-questions">', unsafe_allow_html=True)

        for idx, question in enumerate(questions, start=1):
            st.markdown(
                f"""
                <div class="vocab-test-question-card">
                <div class="vocab-test-question-head">
                    <div>
                        <div class="vocab-test-question-index">Question {idx}</div>
                        <div class="vocab-test-question-prompt">{_build_vocab_test_prompt(question)}</div>
                    </div>
                    <span class="vocab-test-question-mode">{escape(str(question.get("mode") or "未标注"))}</span>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if question["mode"] == "英译中":
                user_answers[question["vocab_item_id"]] = st.radio(
                    "选择正确答案",
                    question["options"],
                    index=None,
                    key=f"student_mcq_{question['vocab_item_id']}",
                    label_visibility="collapsed",
                )
            else:
                user_answers[question["vocab_item_id"]] = st.text_input(
                    "输入你的答案",
                    key=f"student_text_{question['vocab_item_id']}",
                    placeholder="在这里输入英文单词",
                    label_visibility="collapsed",
                )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="vocab-test-submit-box">
                <div class="vocab-test-submit-title">完成后统一提交</div>
                <p class="vocab-test-submit-desc">
                    提交后会立即显示正确词和错词反馈；如果还有没写的题，也会按未作答一并进入结果页。
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button("提交检测", type="primary", use_container_width=True)

    if submitted:
        result = dbs.submit_student_test(
            student_id=student_id,
            payload=payload,
            user_answers=user_answers,
            source_label=st.session_state.get("student_test_source_label", "学生检测"),
        )
        st.session_state["student_test_result"] = result
        st.session_state.pop("student_test_payload", None)
        st.success(f"提交完成：{result['score']} / {result['total']}")
        st.rerun()
