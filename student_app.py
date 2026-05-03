"""学生端入口（学习首页、任务流、诊断与检测）"""

from __future__ import annotations

from html import escape

import streamlit as st

import db_student as dbs
from student_content_views import (
    render_lessons as _render_lessons_view,
    render_my_vocab as _render_my_vocab_view,
    render_progress as _render_progress_view,
)
from student_home_viewmodel import build_student_home_viewmodel
from student_initial_diagnosis_view import (
    activate_initial_diagnosis as _activate_initial_diagnosis_view,
    render_initial_diagnosis as _render_initial_diagnosis_view,
)
from student_shell_view import (
    SECTION_TO_PAGE,
    render_dashboard_styles as _render_dashboard_styles,
    render_focus_hint as _render_focus_hint,
    render_light_status_section as _render_light_status_section,
    render_logged_in_header as _render_logged_in_header,
    render_page_hero as _render_page_hero,
    render_profile_page as _render_profile_page_view,
    render_section_anchor as _render_section_anchor,
    render_section_focus_badge as _render_section_focus_badge,
    render_top_navigation as _render_top_navigation_shell,
    render_welcome_section as _render_welcome_section,
)
st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")
st.title("英语辅导系统｜学生端")


def _render_login():
    st.markdown("## 学生登录")
    st.caption("请输入老师为你设置的学生端账号和密码。")

    with st.form("student_login_form", clear_on_submit=False):
        login_account = st.text_input("账号", key="student_login_account_input")
        login_password = st.text_input("密码", type="password", key="student_login_password_input")
        submitted = st.form_submit_button("登录")

    if not submitted:
        return

    student = dbs.authenticate_student(login_account, login_password)
    if not student:
        st.error("账号或密码不正确，请检查后再试。")
        return

    st.session_state["student_login"] = student
    st.session_state["student_current_page"] = "home"
    st.session_state.pop("student_test_payload", None)
    st.session_state.pop("student_test_result", None)
    st.success(f"欢迎回来，{student.get('name') or '同学'}。")
    st.rerun()


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


def _render_top_navigation():
    current_page = st.session_state.get("student_current_page", "home")
    _render_top_navigation_shell(current_page, navigate_to_page=_navigate_to_page)


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

    ok, payload = dbs.build_book_test(student_id, book_id, unit_ids or [], test_mode, test_count)
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


def _render_initial_diagnosis(student_id: int):
    _render_initial_diagnosis_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )


def _render_primary_task_section(home_data: dict):
    task_cards = home_data.get("current_task_cards") or []
    primary = next((card for card in task_cards if card.get("is_primary")), None)
    primary = primary or (task_cards[0] if task_cards else {})
    title = primary.get("title") or home_data.get("primary_task") or "开始今天的学习任务"
    desc = primary.get("description") or "先完成一小步，系统会继续帮你安排后面的节奏。"
    eta = primary.get("eta") or home_data.get("primary_task_eta") or "10 分钟"
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">今日主任务 ｜ {escape(str(eta))}</div>
            <div class="student-home-task-title">{escape(str(title))}</div>
            <p class="student-home-task-desc">{escape(str(desc))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("开始今天的成长之旅", key="start_primary_task", use_container_width=True):
        if primary and _run_task_action(st.session_state["student_login"]["id"], primary):
            st.rerun()
        _navigate_to_page("task_pool", focus_section="task_pool")


def _render_task_pool_section(home_data: dict):
    _render_section_anchor("task_pool")
    _render_section_focus_badge("task_pool")
    st.markdown("## 学习任务池")
    current_cards = home_data.get("current_task_cards") or []
    history_cards = home_data.get("history_task_cards") or []

    if current_cards:
        st.markdown("### 当前待完成任务")
        for index, card in enumerate(current_cards, start=1):
            st.markdown(
                f"""
                <div class="student-home-card">
                    <div class="student-home-kicker">任务 {index} ｜ {escape(str(card.get('eta', '灵活安排')))}</div>
                    <div class="student-home-task-title">{escape(str(card.get('title', '学习任务')))}</div>
                    <p class="student-home-task-desc">{escape(str(card.get('description', '')))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("开始这一项", key=f"student_current_task_{index}", use_container_width=True):
                if _run_task_action(st.session_state["student_login"]["id"], card):
                    st.rerun()
    if history_cards:
        st.markdown("### 历史内容池")
        for index, card in enumerate(history_cards, start=1):
            st.markdown(
                f"""
                <div class="student-home-card">
                    <div class="student-home-kicker">回看入口 ｜ {escape(str(card.get('eta', '灵活安排')))}</div>
                    <div class="student-home-task-title">{escape(str(card.get('title', '历史内容')))}</div>
                    <p class="student-home-task-desc">{escape(str(card.get('description', '')))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("查看这一项", key=f"student_history_task_{index}", use_container_width=True):
                if _run_task_action(st.session_state["student_login"]["id"], card):
                    st.rerun()

    if not current_cards and not history_cards:
        st.info("暂时没有新的任务。可以先进入词汇检测或查看最近学案。")


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
            <div class="student-home-task-title">{escape(str(home_data.get('primary_task', '开始今天的学习任务')))}</div>
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
            已收集 {history_summary.get('recent_lessons_count', 0)} 份学案、
            {history_summary.get('learned_vocab_count', 0)} 个已学单词、
            {history_summary.get('test_record_count', 0)} 条检测记录。
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_focus_hint()


def _render_lessons(student_id: int):
    _render_lessons_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )


def _render_progress(student_id: int):
    _render_progress_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )


def _render_my_vocab(student_id: int):
    _render_my_vocab_view(
        student_id,
        render_section_anchor=_render_section_anchor,
        render_section_focus_badge=_render_section_focus_badge,
    )


def _render_profile_page(home_data: dict):
    _set_current_page("profile_page", focus_section="profile_page")
    _render_section_anchor("profile_page")
    _render_section_focus_badge("profile_page")
    _render_profile_page_view(home_data)


def main():
    student = st.session_state.get("student_login")
    if not student:
        _render_login()
        return

    student_id = student["id"]
    st.markdown('<div class="student-page-shell">', unsafe_allow_html=True)
    _render_logged_in_header(student)
    _render_dashboard_styles()

    current_page = st.session_state.get("student_current_page", "home")
    needs_home_data = current_page in {"home", "task_pool", "profile_page"}
    home_data = build_student_home_viewmodel(student) if needs_home_data else {}
    _render_top_navigation()
    _render_page_hero(current_page)

    if current_page == "task_pool":
        _render_task_pool_page(home_data)
    elif current_page == "profile_page":
        _render_profile_page(home_data)
    elif current_page == "initial_diagnosis":
        _render_initial_diagnosis(student_id)
    elif current_page in {"my_vocab", "vocab_test", "learned_words", "test_history"}:
        _render_my_vocab(student_id)
    elif current_page == "recent_lessons":
        _render_lessons(student_id)
    elif current_page == "progress":
        _render_progress(student_id)
    else:
        _render_home_page(home_data)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
