"""学生端入口（含词汇检测作答区）"""

from datetime import datetime
from html import escape, unescape
import re

import streamlit as st
import streamlit.components.v1 as components

import db_student as dbs
from student_diagnosis_service import (
    build_initial_diagnosis_definition,
    evaluate_initial_diagnosis,
)
from lesson_html_renderer import build_downloadable_lesson_html, parse_lesson_text_to_parts
from student_home_viewmodel import build_student_home_viewmodel
from student_ui_copy import (
    build_test_result_summary,
    format_progress_status_copy,
)
from student_initial_diagnosis_view import (
    activate_initial_diagnosis as _activate_initial_diagnosis_view,
    render_initial_diagnosis as _render_initial_diagnosis_view,
)
from student_vocab_test_view import render_vocab_test as _render_vocab_test_view

st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")
st.title("英语辅导系统｜学生端")

SECTION_LABELS = {
    "home": "学习首页",
    "task_pool": "学习任务池",
    "initial_diagnosis": "首次诊断",
    "profile_page": "我的成长画像",
    "recent_lessons": "我的最近学案",
    "learned_words": "我的已学单词",
    "progress": "我的学习进度",
    "vocab_test": "我的词汇检测",
    "test_history": "我的检测记录",
}

SECTION_TO_PAGE = {
    "home": "home",
    "task_pool": "task_pool",
    "profile_page": "profile_page",
    "initial_diagnosis": "initial_diagnosis",
    "vocab_test": "vocab_test",
    "recent_lessons": "recent_lessons",
    "learned_words": "learned_words",
    "progress": "progress",
    "test_history": "test_history",
}

NAV_ITEMS = [
    ("home", "学习首页"),
    ("task_pool", "学习任务池"),
    ("initial_diagnosis", "首次诊断"),
    ("vocab_test", "词汇检测"),
    ("recent_lessons", "最近学案"),
    ("learned_words", "已学单词"),
    ("progress", "学习进度"),
    ("test_history", "检测记录"),
    ("profile_page", "成长画像"),
]

PAGE_META = {
    "home": {
        "eyebrow": "Learning Desk",
        "title": "学习首页",
        "description": "这里只保留今日驾驶舱视图，帮助学生快速确认状态、主任务和进入今天的学习节奏。",
    },
    "task_pool": {
        "eyebrow": "Task Flow",
        "title": "学习任务池",
        "description": "这里专门承接今天要做的任务和可回看的历史内容，学生进入后只需要决定下一步做什么。",
    },
    "initial_diagnosis": {
        "eyebrow": "Diagnosis",
        "title": "首次诊断",
        "description": "先用一轮轻量诊断确认当前起点，后续任务会根据结果自动收束到更合适的学习路径。",
    },
    "vocab_test": {
        "eyebrow": "Vocabulary",
        "title": "词汇检测",
        "description": "直接开始词汇书检测或复习检测，把今天最适合先做的词汇任务一口气完成。",
    },
    "recent_lessons": {
        "eyebrow": "Lessons",
        "title": "最近学案",
        "description": "这里集中回看最近学案和新词表，适合承接今天任务完成后的巩固练习。",
    },
    "learned_words": {
        "eyebrow": "Vocabulary Log",
        "title": "已学单词",
        "description": "查看已经进入学习记录的词汇积累，帮助学生建立稳定的掌握感和阶段性成果感。",
    },
    "progress": {
        "eyebrow": "Progress",
        "title": "学习进度",
        "description": "从词汇书和单元维度回看推进情况，判断今天更适合继续学习还是先做复习巩固。",
    },
    "test_history": {
        "eyebrow": "History",
        "title": "检测记录",
        "description": "把历史检测结果放在同一处，方便学生回看正确率变化和最近一次答题反馈。",
    },
    "profile_page": {
        "eyebrow": "Growth Profile",
        "title": "成长画像",
        "description": "这里展示诊断结果的浓缩视图，帮助学生理解当前阶段、成长重点和下一步方向。",
    },
}


def _render_section_anchor(section_key: str):
    st.markdown(f'<div id="section-{section_key}"></div>', unsafe_allow_html=True)


def _set_current_page(page_key: str, focus_section: str | None = None):
    st.session_state["student_current_page"] = page_key
    if focus_section:
        st.session_state["student_home_focus_section"] = focus_section
    elif page_key != "home":
        st.session_state.pop("student_home_focus_section", None)


def _set_focus_section(section_key: str):
    page_key = SECTION_TO_PAGE.get(section_key, "home")
    _set_current_page(page_key, focus_section=section_key)


def _navigate_to_page(page_key: str, focus_section: str | None = None):
    _set_current_page(page_key, focus_section=focus_section)
    st.rerun()


def _navigate_to_section(section_key: str):
    _set_focus_section(section_key)
    st.rerun()


def _render_focus_scroll():
    return


def _start_progress_test_action(student_id: int, test_type: str, test_mode: str, test_count: int) -> bool:
    ok, payload = dbs.build_progress_test(student_id, test_type, test_mode, test_count)
    if not ok:
        st.warning(payload)
        return False

    st.session_state.pop("student_test_result", None)
    st.session_state["student_test_payload"] = payload
    st.session_state["student_test_source_label"] = f"学习进度检测：{test_type}"
    _set_focus_section("vocab_test")
    return True


def _start_book_test_action(
    student_id: int,
    book_id: int,
    book_label: str,
    unit_ids: list[int] | None,
    test_mode: str,
    test_count: int,
) -> bool:
    if not book_id:
        st.warning("当前任务还没有可用的词汇书入口，请先联系老师检查词汇书配置。")
        return False

    ok, payload = dbs.build_book_test(
        student_id,
        book_id,
        unit_ids or [],
        test_mode,
        test_count,
    )
    if not ok:
        st.warning(payload)
        return False

    st.session_state.pop("student_test_result", None)
    st.session_state["student_test_payload"] = payload
    scope = "指定单元" if unit_ids else "整本词汇书"
    st.session_state["student_test_source_label"] = f"词汇书检测：{book_label} / {scope}"
    _set_focus_section("vocab_test")
    return True


def _run_task_action(student_id: int, task_card: dict) -> bool:
    action_type = task_card.get("action_type") or "focus_section"
    action_params = task_card.get("action_params") or {}
    target_section = task_card.get("target_section") or "task_pool"

    if action_type == "start_initial_diagnosis":
        _activate_initial_diagnosis(force_refresh=True)
        _set_focus_section("initial_diagnosis")
        return True

    if action_type == "start_progress_test":
        return _start_progress_test_action(
            student_id,
            action_params.get("test_type", "复习检测"),
            action_params.get("test_mode", "混合模式"),
            action_params.get("test_count", 25),
        )

    if action_type == "start_book_test":
        return _start_book_test_action(
            student_id,
            action_params.get("book_id"),
            action_params.get("book_label", "当前词汇书"),
            action_params.get("unit_ids", []),
            action_params.get("test_mode", "混合模式"),
            action_params.get("test_count", 25),
        )

    if action_type == "open_lesson_detail":
        lesson_id = action_params.get("lesson_id")
        if lesson_id:
            st.session_state["student_auto_open_lesson_id"] = lesson_id
        _set_focus_section("recent_lessons")
        return True

    if action_type == "open_learned_words_dialog":
        st.session_state["student_auto_open_learned_words_dialog"] = True
        _set_focus_section("learned_words")
        return True

    _set_focus_section(target_section)
    return True


def _activate_initial_diagnosis(*, force_refresh: bool = False) -> None:
    _activate_initial_diagnosis_view(force_refresh=force_refresh)




def _render_vocab_test(student_id: int):
    _render_vocab_test_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )


def _render_initial_diagnosis(student_id: int):
    _render_initial_diagnosis_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )

def _render_home_page(home_data: dict):
    _set_current_page("home")
    _render_welcome_section(home_data)

    top_left, top_right = st.columns([1.2, 1])
    with top_left:
        _render_primary_task_section(home_data)
    with top_right:
        st.markdown("## 轻状态")
        _render_light_status_section(home_data)

    st.markdown("## 今日学习提醒")
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">今天先做什么</div>
            <div class="student-home-task-title">{home_data["primary_task"]}</div>
            <p class="student-home-task-desc">
                点击上方“开始今天的成长之旅”会直接进入学习任务池；
                任务池页面只负责承接今天的任务，不再和其他模块混在一起。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_task_pool_page(home_data: dict):
    _set_current_page("task_pool", focus_section="task_pool")
    _render_task_pool_section(home_data)

    history_summary = home_data.get("history_summary", {})
    st.markdown("## 成长记录回看")
    st.markdown(
        f"""
        <div class="student-home-history-tip">
            已收集 {history_summary.get("recent_lessons_count", 0)} 份学案、
            {history_summary.get("learned_vocab_count", 0)} 个已学单词、
            {history_summary.get("test_record_count", 0)} 条检测记录。
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_focus_hint()


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
    parts = parse_lesson_text_to_parts(lesson.get("content", ""))
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


def _looks_like_html(content: str) -> bool:
    lowered = (content or "").lower()
    return "<html" in lowered or "<body" in lowered or "<!doctype" in lowered


def _render_lesson_content(detail: dict):
    content = detail.get("content", "") or ""
    if not content:
        st.info("这份学案暂时没有内容。")
        return

    html_doc = content if _looks_like_html(content) else _build_lesson_download_html(detail)
    st.download_button(
        "下载网页 HTML（可用浏览器打印 PDF）",
        data=html_doc,
        file_name=_build_lesson_html_filename(st.session_state.get("student_login", {}), detail),
        mime="text/html",
        key=f"download_lesson_html_{detail.get('id')}",
    )

    preview_tab, text_tab = st.tabs(["网页预览", "纯文本内容"])
    with preview_tab:
        if _looks_like_html(content):
            components.html(content, height=650, scrolling=True)
        else:
            components.html(html_doc, height=650, scrolling=True)
    with text_tab:
        st.text_area(
            "完整学案内容",
            value=content,
            height=650,
            key=f"lesson_content_{detail.get('id')}",
        )


def _render_lesson_vocab_rows(rows):
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
def _show_lesson_detail_dialog(student_id: int, lesson_snapshot: dict):
    detail = lesson_snapshot or {}
    if not detail:
        st.warning("没有找到这份学案，或这份学案不属于当前学生。")
        return

    st.write(f"类型：{detail.get('lesson_type')}")
    st.write(f"主题：{detail.get('topic')}")
    st.write(f"创建时间：{detail.get('created_at')}")
    _render_lesson_content(detail)


@st.dialog("本次学案新词表")
def _show_lesson_vocab_dialog(student_id: int, lesson_snapshot: dict):
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


def _render_learned_word_groups(groups):
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
def _show_learned_words_dialog(student_id: int):
    summary = dbs.get_student_learned_vocab_summary(student_id)
    total_unique_words = summary.get("total_unique_words", 0)
    lesson_groups = summary.get("lesson_groups", [])

    st.subheader(f"已学单词总数：{total_unique_words}")
    st.caption("按学案分类查看：哪天、哪份学案里学了哪些词。")
    _render_learned_word_groups(lesson_groups)


def _render_lessons(student_id: int):
    _render_section_anchor("recent_lessons")
    st.header("我的最近学案")
    _render_section_focus_badge("recent_lessons")
    lessons = dbs.get_student_recent_lesson_snapshots(student_id, limit=10)
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

    latest_lesson = lessons[0]
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">学案模块说明</div>
            <div class="student-home-task-title">最近 {len(lessons)} 份学案都集中放在这里</div>
            <p class="student-home-task-desc">
                最近一次主题：{latest_lesson.get("topic") or latest_lesson.get("lesson_type") or '继续练习'}；
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


def _render_learned_words(student_id: int):
    _render_section_anchor("learned_words")
    st.header("我的已学单词")
    _render_section_focus_badge("learned_words")
    summary = dbs.get_student_learned_vocab_summary(student_id)
    total_unique_words = summary.get("total_unique_words", 0)
    lesson_groups = summary.get("lesson_groups", [])

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
                当前共记录 {total_unique_words} 个已学单词，关联 {len(lesson_groups)} 份学案。
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
        st.metric("关联学案数", len(lesson_groups))
    with col3:
        if st.button("查看完整单词清单", key="view_learned_words_dialog", use_container_width=True):
            _show_learned_words_dialog(student_id)

    st.markdown("## 学习积累摘要")
    preview_groups = lesson_groups[:3]
    for group in preview_groups:
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


def _render_progress(student_id: int):
    _render_section_anchor("progress")
    st.header("我的学习进度")
    _render_section_focus_badge("progress")
    progress_rows = dbs.get_student_book_progress(student_id)
    if not progress_rows:
        st.info("完成学习任务后，这里会逐步展示你的进度变化。")
        return

    active_books = [row for row in progress_rows if row[4] > 0]
    total_learned = sum(row[3] for row in progress_rows)
    total_vocab = sum(row[4] for row in progress_rows)
    total_review = sum(row[7] for row in progress_rows)

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">进度模块说明</div>
            <div class="student-home-task-title">这里只看词汇书进度，不承接其他学习动作</div>
            <p class="student-home-task-desc">
                当前共有 {len(active_books)} 本词汇书已启动，
                已学 {total_learned} / {total_vocab or 0}，
                待复习词汇 {total_review} 个。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_col1, overview_col2, overview_col3 = st.columns(3)
    with overview_col1:
        st.metric("已启动词汇书", len(active_books))
    with overview_col2:
        st.metric("累计已学词汇", total_learned)
    with overview_col3:
        st.metric("待复习词汇", total_review)

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
    for row in progress_rows:
        book_id, book_name, volume_name, learned_count, total_count, mastered_count, learning_count, review_count = row
        label = book_name if not volume_name else f"{book_name}（{volume_name}）"
        ratio = (learned_count / total_count) if total_count else 0
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">词汇书</div>
                <div class="student-home-task-title">{label}</div>
                <p class="student-home-subtitle">已学：{learned_count} / {total_count}</p>
                <p class="student-home-task-desc">
                    状态分布：mastered {mastered_count} ｜ learning {learning_count} ｜ review {review_count}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(ratio)

        with st.expander(f"查看 {label} 的单元进度", expanded=False):
            unit_rows = dbs.get_student_unit_progress(student_id, book_id)
            for _, unit_name, _unit_order, unit_learned, unit_total in unit_rows:
                st.write(f"{unit_name}：{unit_learned} / {unit_total}")
                st.progress((unit_learned / unit_total) if unit_total else 0)


def _render_test_history(student_id: int):
    _render_section_anchor("test_history")
    st.header("我的检测记录")
    _render_section_focus_badge("test_history")
    rows = dbs.get_student_vocab_test_records(student_id, limit=20)
    if not rows:
        st.info("完成第一次检测后，这里会留下你每一次练习的成长轨迹。")
        return

    latest_row = rows[0]
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">检测记录模块说明</div>
            <div class="student-home-task-title">这里只回看历史检测结果和答题反馈</div>
            <p class="student-home-task-desc">
                当前共记录 {len(rows)} 次检测；
                最近一次成绩 {latest_row[8]} / {latest_row[7]}，正确率 {latest_row[9]:.0%}。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_col1, overview_col2, overview_col3 = st.columns(3)
    with overview_col1:
        st.metric("累计检测次数", len(rows))
    with overview_col2:
        st.metric("最近一次得分", f"{latest_row[8]} / {latest_row[7]}")
    with overview_col3:
        st.metric("最近一次正确率", f"{latest_row[9]:.0%}")

    st.markdown("## 检测记录列表")
    for row in rows:
        (
            test_record_id,
            _source_type,
            _source_book_id,
            _source_unit_id,
            source_label,
            test_type,
            test_mode,
            total_count,
            correct_count,
            accuracy,
            is_synced_to_progress,
            is_wrong_retry_round,
            created_at,
        ) = row
        retry_tag = " | 错词重测" if is_wrong_retry_round else ""
        sync_tag = "已同步到学习进度" if is_synced_to_progress else "仅记录未同步"
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">检测记录{retry_tag}</div>
                <div class="student-home-task-title">{source_label or '词汇检测记录'}</div>
                <p class="student-home-subtitle">检测类型：{test_type} ｜ 作答方式：{test_mode}</p>
                <p class="student-home-task-desc">
                    得分：{correct_count} / {total_count}（正确率：{accuracy:.0%}）<br/>
                    记录时间：{created_at}<br/>
                    同步状态：{sync_tag}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        item_rows = dbs.get_vocab_test_record_items(test_record_id)
        with st.expander(f"查看记录 {test_record_id} 的答题反馈", expanded=False):
            results = []
            for item in item_rows:
                vocab_item_id, word, meaning, mode, user_answer, is_correct = item
                results.append({
                    "vocab_item_id": vocab_item_id,
                    "word": word,
                    "meaning": meaning,
                    "mode": mode,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                })
            _render_test_feedback_blocks(results)


def main():
    student = st.session_state.get("student_login")
    if not student:
        _render_login()
        return

    student_id = student["id"]
    st.markdown('<div class="student-page-shell">', unsafe_allow_html=True)
    _render_logged_in_header(student)
    _render_dashboard_styles()

    home_data = build_student_home_viewmodel(student)
    current_page = st.session_state.get("student_current_page", "home")
    _render_top_navigation()
    _render_page_hero(current_page, home_data)
    _render_page_quick_actions(current_page)

    if current_page == "home":
        _render_home_page(home_data)
    elif current_page == "task_pool":
        _render_task_pool_page(home_data)
    elif current_page == "profile_page":
        _render_profile_page(home_data)
    elif current_page == "initial_diagnosis":
        _render_initial_diagnosis(student_id)
    elif current_page == "vocab_test":
        _render_vocab_test(student_id)
    elif current_page == "recent_lessons":
        _render_lessons(student_id)
    elif current_page == "learned_words":
        _render_learned_words(student_id)
    elif current_page == "progress":
        _render_progress(student_id)
    elif current_page == "test_history":
        _render_test_history(student_id)
    else:
        _render_home_page(home_data)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_initial_diagnosis(student_id: int):
    _render_section_anchor("initial_diagnosis")
    st.header("首次诊断")
    _render_section_focus_badge("initial_diagnosis")

    flash_result = st.session_state.pop("student_diagnosis_flash", None)
    if flash_result:
        _render_diagnosis_result(flash_result)

    saved_result = _build_saved_diagnosis_result(student_id)
    if saved_result and not st.session_state.get("student_diagnosis_active", False):
        st.info("你已经完成过一次首次诊断，下面展示的是当前保存的诊断结果。")
        _render_diagnosis_result(saved_result)
        if st.button("重新做一次首次诊断", key="restart_initial_diagnosis"):
            try:
                _activate_initial_diagnosis(force_refresh=True)
            except Exception as exc:
                st.error(f"正式诊断题库重新加载失败：{exc}")
                return
            st.rerun()
        return

    if not st.session_state.get("student_diagnosis_active", False):
        bank_status = _render_diagnostic_vocab_bank_status()
        overview_definition = None
        if bank_status.get("ready_for_diagnosis"):
            try:
                overview_definition = _prepare_initial_diagnosis_definition(force_refresh=True)
            except Exception as exc:
                st.error(f"正式诊断定义加载失败：{exc}")

        st.markdown(
            """
            <div class="student-home-card">
                <div class="student-home-kicker">诊断说明</div>
                <div class="student-home-task-title">先用一轮 10-15 分钟的轻量诊断，帮你找到更合适的学习起点</div>
                <p class="student-home-subtitle">
                    这次会看四个模块：词汇、阅读、语法基础、写作基础。
                    诊断结束后，系统会生成你的初始画像，并把首页任务切到更适合你的学习轨道。
                </p>
                <p class="student-home-task-desc">
                    当前阶段先重视“看清起点”，不追求一次测得很全；后面会随着训练继续更新。
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if overview_definition:
            _render_diagnosis_module_overview(overview_definition)
        intro_col1, intro_col2, intro_col3 = st.columns(3)
        with intro_col1:
            st.metric("诊断模块", len(overview_definition or []))
        with intro_col2:
            st.metric("总题数", sum(len(module.get("questions", [])) for module in (overview_definition or [])))
        with intro_col3:
            st.metric("预计时长", f"{sum(module.get('estimated_minutes', 3) for module in (overview_definition or []))} 分钟")

        _render_diagnostic_vocab_preview_box()

        st.info("建议一次完成，中途也可以暂停；重新进入后会从头开始这一轮诊断。")
        if st.button("开始首次诊断", key="start_initial_diagnosis", type="primary"):
            if not bank_status.get("ready_for_diagnosis"):
                st.error("正式词汇诊断题库还没有准备好，当前不能开始首次诊断。请先确认 Supabase 中已有 diagnostic_vocab_items 数据。")
                return
            try:
                _activate_initial_diagnosis(force_refresh=True)
            except Exception as exc:
                st.error(f"首次诊断无法启动：{exc}")
                return
            st.rerun()
        return

    definition = st.session_state.get("student_diagnosis_definition")
    if not definition:
        try:
            definition = _prepare_initial_diagnosis_definition(force_refresh=True)
        except Exception as exc:
            st.error(f"首次诊断题库加载失败，无法继续：{exc}")
            _clear_diagnosis_session_state()
            return

    step = st.session_state.get("student_diagnosis_step", 0)
    answers_by_module = st.session_state.setdefault("student_diagnosis_answers", {})
    module = definition[step]
    module_started_at_map = st.session_state.setdefault("student_diagnosis_module_started_at_map", {})
    if module["key"] not in module_started_at_map:
        module_started_at_map[module["key"]] = datetime.utcnow().isoformat()
    st.session_state["student_diagnosis_module_started_at"] = module_started_at_map[module["key"]]

    _render_diagnosis_module_overview(definition, active_step=step)
    st.progress((step + 1) / len(definition))
    st.subheader(f"{step + 1}. {module['title']}")
    st.write(module["intro"])
    focus_points = module.get("focus_points") or []
    if focus_points:
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">本模块关注点</div>
                <div class="student-home-task-title">{module.get("short_title", module["title"])}</div>
                <p class="student-home-task-desc">{' / '.join(focus_points)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if module.get("question_count_summary"):
        st.caption(module.get("question_count_summary"))
    if module.get("passage"):
        st.markdown(
            f"""
            <div style="padding: 14px 16px; border-radius: 10px; background: #f6fbff; border: 1px solid #d9e6f2; margin-bottom: 12px;">
                {module["passage"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    default_answers = answers_by_module.get(module["key"], {})
    is_vocab_module = module["key"] == "vocab"
    module_questions = module["questions"]
    vocab_page = 0
    total_vocab_pages = 1
    page_questions = module_questions
    page_start_index = 0
    if is_vocab_module:
        total_vocab_pages = max(1, (len(module_questions) + VOCAB_DIAG_PAGE_SIZE - 1) // VOCAB_DIAG_PAGE_SIZE)
        vocab_page = int(st.session_state.get("student_diagnosis_vocab_page", 0) or 0)
        vocab_page = max(0, min(vocab_page, total_vocab_pages - 1))
        st.session_state["student_diagnosis_vocab_page"] = vocab_page
        page_start_index = vocab_page * VOCAB_DIAG_PAGE_SIZE
        page_questions = module_questions[page_start_index: page_start_index + VOCAB_DIAG_PAGE_SIZE]
        st.markdown(
            f"""
            <div class="student-diagnosis-page-summary">
                <div class="student-diagnosis-page-title">{_build_vocab_page_title(page_questions)}</div>
                <div class="student-diagnosis-page-meta">
                    第 {vocab_page + 1} / {total_vocab_pages} 页 · 本页 {len(page_questions)} 题 · {_build_vocab_page_meta(page_questions)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        missing_ids = st.session_state.get("student_diagnosis_missing_question_ids", []) or []
        missing_page = st.session_state.get("student_diagnosis_missing_page")
        if missing_ids and missing_page == vocab_page:
            question_number_map = {
                question["id"]: page_start_index + index + 1
                for index, question in enumerate(page_questions)
            }
            missing_links = "".join(
                f'<a href="#{_build_question_anchor_id(question_id)}">定位到第 {question_number_map.get(question_id, "?")} 题</a>'
                for question_id in missing_ids
            )
            st.markdown(
                f"""
                <div class="student-diagnosis-missing-box">
                    <div class="student-diagnosis-missing-title">这一页还有题没做完</div>
                    <div class="student-home-task-desc">请先完成下面这些题，再继续下一页。</div>
                    <div class="student-diagnosis-missing-links">{missing_links}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            first_missing_id = _build_question_anchor_id(missing_ids[0])
            components.html(
                f"""
                <script>
                const target = parent.document.getElementById("{first_missing_id}");
                if (target) {{
                    target.scrollIntoView({{behavior: "smooth", block: "center"}});
                }}
                </script>
                """,
                height=0,
            )

    with st.form(f"initial_diagnosis_form_{module['key']}"):
        current_answers = {}
        for question_index, question in enumerate(page_questions, start=page_start_index + 1):
            default_value = default_answers.get(question["id"])
            if is_vocab_module:
                _render_vocab_question_card(question, question_index)
            current_answers[question["id"]] = st.radio(
                "请选择答案",
                question["options"],
                index=question["options"].index(default_value) if default_value in question["options"] else None,
                key=f"diagnosis_{module['key']}_{question['id']}",
                label_visibility="collapsed" if is_vocab_module else "visible",
            )

        button_cols = st.columns(4 if is_vocab_module else 3)
        with button_cols[0]:
            previous_label = "上一页" if is_vocab_module and vocab_page > 0 else "上一部分"
            previous_disabled = (is_vocab_module and vocab_page == 0 and step == 0) or (not is_vocab_module and step == 0)
            go_previous = st.form_submit_button(previous_label, disabled=previous_disabled, use_container_width=True)
        with button_cols[1]:
            if is_vocab_module and vocab_page < total_vocab_pages - 1:
                button_label = "下一页"
            else:
                button_label = "完成诊断" if step == len(definition) - 1 else "进入下一部分"
            submitted = st.form_submit_button(button_label, type="primary", use_container_width=True)
        if is_vocab_module:
            with button_cols[2]:
                st.markdown(
                    f"""
                    <div style="padding-top: 10px; color: #486581; font-size: 14px;">
                        已完成 {vocab_page + 1} / {total_vocab_pages} 页
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with button_cols[3 if is_vocab_module else 2]:
            pause = st.form_submit_button("暂停本轮诊断", use_container_width=True)

    if go_previous:
        st.session_state.pop("student_diagnosis_missing_question_ids", None)
        st.session_state.pop("student_diagnosis_missing_page", None)
        answers_by_module[module["key"]] = {
            question_id: answer
            for question_id, answer in {**default_answers, **current_answers}.items()
            if answer
        }
        st.session_state["student_diagnosis_answers"] = answers_by_module
        if is_vocab_module and vocab_page > 0:
            st.session_state["student_diagnosis_vocab_page"] = vocab_page - 1
        else:
            st.session_state["student_diagnosis_step"] = max(step - 1, 0)
            if is_vocab_module:
                st.session_state["student_diagnosis_vocab_page"] = 0
            elif step > 0 and definition[step - 1]["key"] == "vocab":
                previous_vocab_pages = max(1, (len(definition[step - 1]["questions"]) + VOCAB_DIAG_PAGE_SIZE - 1) // VOCAB_DIAG_PAGE_SIZE)
                st.session_state["student_diagnosis_vocab_page"] = previous_vocab_pages - 1
        st.rerun()

    if pause:
        _clear_diagnosis_session_state()
        st.rerun()

    if submitted:
        unanswered = [question["prompt"] for question in page_questions if not current_answers.get(question["id"])]
        if unanswered:
            st.session_state["student_diagnosis_missing_question_ids"] = [
                question["id"] for question in page_questions if not current_answers.get(question["id"])
            ]
            st.session_state["student_diagnosis_missing_page"] = vocab_page if is_vocab_module else None
            st.rerun()

        st.session_state.pop("student_diagnosis_missing_question_ids", None)
        st.session_state.pop("student_diagnosis_missing_page", None)
        answers_by_module[module["key"]] = {
            **default_answers,
            **current_answers,
        }
        st.session_state["student_diagnosis_answers"] = answers_by_module

        if is_vocab_module and vocab_page < total_vocab_pages - 1:
            st.session_state["student_diagnosis_vocab_page"] = vocab_page + 1
            st.rerun()

        if step < len(definition) - 1:
            st.session_state["student_diagnosis_step"] = step + 1
            if is_vocab_module:
                st.session_state["student_diagnosis_vocab_page"] = 0
            next_module = definition[step + 1]
            module_started_at_map = st.session_state.setdefault("student_diagnosis_module_started_at_map", {})
            module_started_at_map.setdefault(next_module["key"], datetime.utcnow().isoformat())
            st.rerun()

        result = evaluate_initial_diagnosis(answers_by_module, definition=definition)
        try:
            dbs.save_initial_diagnosis_result(
                student_id,
                result,
                module_answers=answers_by_module,
                definition=definition,
                diagnostic_meta={
                    "started_at": st.session_state.get("student_diagnosis_started_at"),
                    "submitted_at": datetime.utcnow().isoformat(),
                    "module_started_at_map": st.session_state.get("student_diagnosis_module_started_at_map", {}),
                },
            )
        except Exception as exc:
            st.error("诊断结果保存失败，请联系管理员检查 Supabase 配置。")
            return

        _clear_diagnosis_session_state()
        st.session_state["student_diagnosis_flash"] = result
        st.rerun()

if __name__ == "__main__":
    main()
