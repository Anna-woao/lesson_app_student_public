"""Content page views for lessons, learned words, progress, and test history."""

from __future__ import annotations

import re

import streamlit as st
import streamlit.components.v1 as components

import db_student as dbs
from lesson_html_renderer import build_downloadable_lesson_html, build_lesson_plain_text
from student_content_service import (
    build_learned_words_page_data,
    build_lessons_page_data,
    build_progress_page_data,
    build_test_feedback_results,
    build_test_history_page_data,
)
from student_ui_copy import format_progress_status_copy
from student_vocab_test_view import _render_test_feedback_blocks


def _sanitize_filename_part(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text.strip("_")


def _build_lesson_html_filename(student: dict, lesson: dict) -> str:
    student_name = _sanitize_filename_part(student.get("name", "学生"))
    lesson_id = _sanitize_filename_part(lesson.get("id") or lesson.get("lesson_id") or "")
    lesson_type = _sanitize_filename_part(lesson.get("lesson_type") or "学案")
    topic = _sanitize_filename_part(lesson.get("topic") or "")
    parts = [student_name, lesson_type, topic, f"lesson_{lesson_id}" if lesson_id else ""]
    file_stem = "_".join([part for part in parts if part]) or "英语学案"
    return f"{file_stem}.html"


def _build_lesson_download_html(lesson: dict) -> str:
    parts = lesson.get("parts") or {}
    title_bits = [str(lesson.get("lesson_type") or "英语学案"), str(lesson.get("topic") or "")]
    title = " - ".join([bit for bit in title_bits if bit])
    student = st.session_state.get("student_login", {}) or {}
    lesson_meta = {
        "student_name": student.get("name", "学生"),
        "grade": student.get("grade", ""),
        "lesson_type": lesson.get("lesson_type", ""),
        "difficulty": lesson.get("difficulty", ""),
        "topic": lesson.get("topic", ""),
    }
    return build_downloadable_lesson_html(parts, title=title or "英语学案", lesson_meta=lesson_meta)


def _render_lesson_content(detail: dict) -> None:
    raw_content = detail.get("content", "") or ""
    parts = detail.get("parts") or {}
    plain_text = detail.get("normalized_content") or build_lesson_plain_text(parts, raw_content)
    if not raw_content and not plain_text:
        st.info("这份学案暂时没有内容。")
        return

    html_doc = _build_lesson_download_html(detail)
    st.download_button(
        "下载网页 HTML（可用浏览器打印 PDF）",
        data=html_doc,
        file_name=_build_lesson_html_filename(st.session_state.get("student_login", {}), detail),
        mime="text/html",
        key=f"download_lesson_html_{detail.get('id')}",
    )

    preview_tab, text_tab = st.tabs(["网页预览", "纯文本内容"])
    with preview_tab:
        components.html(html_doc, height=650, scrolling=True)
    with text_tab:
        st.text_area(
            "完整学案内容",
            value=plain_text,
            height=650,
            key=f"lesson_content_{detail.get('id')}",
        )


def _render_lesson_vocab_rows(rows) -> None:
    if not rows:
        st.info("这份学案暂时没有可展示的词汇记录。")
        return

    for idx, item in enumerate(rows, start=1):
        lemma = item.get("lemma", "")
        pos = item.get("pos", "")
        ipa_br = item.get("ipa_br", "")
        ipa_am = item.get("ipa_am", "")
        meaning = item.get("meaning", "")
        example_en = item.get("example_en", "")
        example_zh = item.get("example_zh", "")

        st.markdown(f"### {idx}. {lemma}")
        if pos:
            st.write(f"词性：{pos}")
        if ipa_br or ipa_am:
            st.write(f"音标：英 {ipa_br or '-'} / 美 {ipa_am or '-'}")
        if meaning:
            st.write(f"释义：{meaning}")
        if example_en:
            st.write(f"例句：{example_en}")
        if example_zh:
            st.write(f"译文：{example_zh}")
        st.markdown("---")


@st.dialog("完整学案")
def _show_lesson_detail_dialog(student_id: int, lesson_snapshot: dict) -> None:
    detail = lesson_snapshot or {}
    if not detail:
        st.warning("没有找到这份学案，或这份学案不属于当前学生。")
        return

    st.write(f"类型：{detail.get('lesson_type')}")
    st.write(f"主题：{detail.get('topic')}")
    st.write(f"创建时间：{detail.get('created_at')}")
    _render_lesson_content(detail)


@st.dialog("本次学案新词表")
def _show_lesson_vocab_dialog(student_id: int, lesson_snapshot: dict) -> None:
    bundle = (lesson_snapshot or {}).get("vocab_bundle")
    if not bundle:
        st.warning("没有找到这份学案，或这份学案不属于当前学生。")
        return

    new_rows = bundle.get("new_words", [])
    review_rows = bundle.get("review_words", [])
    st.write(f"新词数量：{len(new_rows)}")
    st.write(f"复习词数量：{len(review_rows)}")

    new_tab, review_tab = st.tabs(["本次新词", "本次复习词"])
    with new_tab:
        _render_lesson_vocab_rows(new_rows)
    with review_tab:
        _render_lesson_vocab_rows(review_rows)


def _render_learned_word_groups(groups) -> None:
    if not groups:
        st.info("你目前还没有可展示的已学单词。")
        return

    for group in groups:
        created_at = group.get("created_at", "")
        lesson_type = group.get("lesson_type", "") or "未标注类型"
        topic = group.get("topic", "") or "未标注主题"
        lesson_id = group.get("lesson_id")
        word_count = group.get("word_count", 0)
        lesson_label = "未关联学案" if lesson_id is None else f"学案 {lesson_id}"
        title = f"{created_at or '暂无记录'}｜{lesson_label}｜{lesson_type}｜{topic}（{word_count}词）"

        with st.expander(title, expanded=False):
            for idx, word in enumerate(group.get("words", []), start=1):
                lemma = word.get("lemma", "")
                meaning = word.get("meaning", "")
                if meaning:
                    st.write(f"{idx}. {lemma} - {meaning}")
                else:
                    st.write(f"{idx}. {lemma}")


@st.dialog("我的已学单词")
def _show_learned_words_dialog(student_id: int) -> None:
    page_data = build_learned_words_page_data(student_id)
    st.subheader(f"已学单词总数：{page_data['total_unique_words']}")
    st.caption("按学案分类查看：哪天、哪份学案里学了哪些词。")
    _render_learned_word_groups(page_data["lesson_groups"])


def render_lessons(student_id: int, *, render_section_anchor, render_section_focus_badge) -> None:
    render_section_anchor("recent_lessons")
    st.header("我的最近学案")
    render_section_focus_badge("recent_lessons")

    page_data = build_lessons_page_data(student_id, limit=10)
    lessons = page_data["lessons"]
    if not lessons:
        st.info("这里会慢慢收集你的学案练习。完成今天的第一步后，再回来看看。")
        return

    auto_open_lesson_id = st.session_state.pop("student_auto_open_lesson_id", None)
    if auto_open_lesson_id:
        auto_open_snapshot = next(
            (lesson for lesson in lessons if lesson.get("id") == auto_open_lesson_id),
            None,
        ) or dbs.get_student_lesson_snapshot(student_id, auto_open_lesson_id)
        if auto_open_snapshot:
            _show_lesson_detail_dialog(student_id, auto_open_snapshot)

    latest_lesson = page_data["latest_lesson"]
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">学案模块说明</div>
            <div class="student-home-task-title">最近 {page_data["lesson_count"]} 份学案都集中放在这里</div>
            <p class="student-home-task-desc">
                最近一次主题：{latest_lesson.get("topic") or latest_lesson.get("lesson_type") or '继续练习'}。<br/>
                在这个页面里只做两件事：查看完整学案，或查看对应新词表。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 学案列表")
    for lesson in lessons:
        lesson_id = lesson.get("id")
        lesson_type = lesson.get("lesson_type")
        difficulty = lesson.get("difficulty")
        topic = lesson.get("topic")
        created_at = lesson.get("created_at")
        bundle = lesson.get("vocab_bundle") or {}
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">最近学案</div>
                <div class="student-home-task-title">{topic or lesson_type or '本次学案'}</div>
                <p class="student-home-subtitle">题型：{lesson_type or '未标注'} ｜ 难度：{difficulty or '未标注'}</p>
                <p class="student-home-task-desc">
                    创建时间：{created_at or '暂无记录'}<br/>
                    词汇结构：新词 {len(bundle.get("new_words", []))} ｜ 复习词 {len(bundle.get("review_words", []))}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("查看完整学案", key=f"view_lesson_{lesson_id}", use_container_width=True):
                _show_lesson_detail_dialog(student_id, lesson)
        with col2:
            if st.button("查看本次学案新词表", key=f"view_lesson_vocab_{lesson_id}", use_container_width=True):
                _show_lesson_vocab_dialog(student_id, lesson)


def render_learned_words(student_id: int, *, render_section_anchor, render_section_focus_badge) -> None:
    render_section_anchor("learned_words")
    st.header("我的已学单词")
    render_section_focus_badge("learned_words")

    page_data = build_learned_words_page_data(student_id)
    total_unique_words = page_data["total_unique_words"]
    if total_unique_words == 0:
        st.info("这里会记录你已经接触过的词汇内容。")
        return

    if st.session_state.pop("student_auto_open_learned_words_dialog", False):
        _show_learned_words_dialog(student_id)

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">已学单词模块说明</div>
            <div class="student-home-task-title">这里只回看已经进入学习记录的词汇积累</div>
            <p class="student-home-task-desc">
                当前共记录 {total_unique_words} 个已学单词，关联 {page_data["lesson_group_count"]} 份学案。<br/>
                这个页面只负责查看积累，不承接检测或学案练习。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("已学单词总数", total_unique_words)
    with col2:
        st.metric("关联学案数", page_data["lesson_group_count"])
    with col3:
        if st.button("查看完整单词清单", key="view_learned_words_dialog", use_container_width=True):
            _show_learned_words_dialog(student_id)

    st.markdown("## 学习积累摘要")
    for group in page_data["preview_groups"]:
        lesson_label = group.get("topic", "") or group.get("lesson_type", "") or "未命名学案"
        mix_label = f"新词 {group.get('new_word_count', 0)} ｜ 复习词 {group.get('review_word_count', 0)}"
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">关联学案</div>
                <div class="student-home-task-title">{lesson_label}</div>
                <p class="student-home-subtitle">词汇数量：{group.get("word_count", 0)} ｜ {mix_label}</p>
                <p class="student-home-task-desc">创建时间：{group.get("created_at", "") or '暂无记录'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_progress(student_id: int, *, render_section_anchor, render_section_focus_badge) -> None:
    render_section_anchor("progress")
    st.header("我的学习进度")
    render_section_focus_badge("progress")

    page_data = build_progress_page_data(student_id)
    books = page_data["books"]
    if not books:
        st.info("完成学习任务后，这里会逐步展示你的进度变化。")
        return

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">进度模块说明</div>
            <div class="student-home-task-title">这里只看词汇书进度，不承接其他学习动作</div>
            <p class="student-home-task-desc">
                当前共有 {page_data["active_book_count"]} 本词汇书已启动，
                已学 {page_data["total_learned"]} / {page_data["total_vocab"] or 0}，
                待复习词汇 {page_data["total_review"]} 个。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_col1, overview_col2, overview_col3 = st.columns(3)
    with overview_col1:
        st.metric("已启动词汇书", page_data["active_book_count"])
    with overview_col2:
        st.metric("累计已学词汇", page_data["total_learned"])
    with overview_col3:
        st.metric("待复习词汇", page_data["total_review"])

    status_columns = st.columns(3)
    for column, status_key in zip(status_columns, ["learning", "review", "mastered"]):
        status_title, status_desc = format_progress_status_copy(status_key)
        with column:
            st.markdown(
                f"""
                <div class="student-home-card">
                    <div class="student-home-kicker">状态说明</div>
                    <div class="student-home-task-title">{status_title}</div>
                    <p class="student-home-task-desc">{status_desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("## 词汇书进度")
    for book in books:
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">词汇书</div>
                <div class="student-home-task-title">{book["label"]}</div>
                <p class="student-home-subtitle">已学：{book["learned_count"]} / {book["total_count"]}</p>
                <p class="student-home-task-desc">
                    状态分布：mastered {book["mastered_count"]} ｜ learning {book["learning_count"]} ｜ review {book["review_count"]}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(book["ratio"])

        with st.expander(f"查看 {book['label']} 的单元进度", expanded=False):
            for unit in book["units"]:
                st.write(f"{unit['unit_name']}：{unit['learned_count']} / {unit['total_count']}")
                st.progress(unit["ratio"])


def render_test_history(student_id: int, *, render_section_anchor, render_section_focus_badge) -> None:
    render_section_anchor("test_history")
    st.header("我的检测记录")
    render_section_focus_badge("test_history")

    page_data = build_test_history_page_data(student_id, limit=20)
    records = page_data["records"]
    if not records:
        st.info("完成第一轮检测后，这里会留下你每一次练习的成长轨迹。")
        return

    latest_record = page_data["latest_record"]
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">检测记录模块说明</div>
            <div class="student-home-task-title">这里只回看历史检测结果和答题反馈</div>
            <p class="student-home-task-desc">
                当前共记录 {page_data["record_count"]} 次检测；
                最近一次成绩 {latest_record["correct_count"]} / {latest_record["total_count"]}，
                正确率 {latest_record["accuracy"]:.0%}。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_col1, overview_col2, overview_col3 = st.columns(3)
    with overview_col1:
        st.metric("累计检测次数", page_data["record_count"])
    with overview_col2:
        st.metric("最近一次得分", f"{latest_record['correct_count']} / {latest_record['total_count']}")
    with overview_col3:
        st.metric("最近一次正确率", f"{latest_record['accuracy']:.0%}")

    st.markdown("## 检测记录列表")
    for record in records:
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">检测记录{record["retry_tag"]}</div>
                <div class="student-home-task-title">{record["source_label"] or '词汇检测记录'}</div>
                <p class="student-home-subtitle">检测类型：{record["test_type"]} ｜ 作答方式：{record["test_mode"]}</p>
                <p class="student-home-task-desc">
                    得分：{record["correct_count"]} / {record["total_count"]}（正确率：{record["accuracy"]:.0%}）<br/>
                    记录时间：{record["created_at"]}<br/>
                    同步状态：{record["sync_tag"]}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"查看记录 {record['test_record_id']} 的答题反馈", expanded=False):
            _render_test_feedback_blocks(build_test_feedback_results(record["test_record_id"]))
