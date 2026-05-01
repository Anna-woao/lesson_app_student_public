"""Shared shell and page-chrome helpers for the student app."""

from __future__ import annotations

from html import escape

import streamlit as st

SECTION_LABELS = {
    "home": "????",
    "task_pool": "?????",
    "initial_diagnosis": "????",
    "profile_page": "????",
    "recent_lessons": "????",
    "learned_words": "????",
    "progress": "????",
    "vocab_test": "????",
    "test_history": "????",
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
    ("home", "????"),
    ("task_pool", "?????"),
    ("initial_diagnosis", "????"),
    ("vocab_test", "????"),
    ("recent_lessons", "????"),
    ("learned_words", "????"),
    ("progress", "????"),
    ("test_history", "????"),
    ("profile_page", "????"),
]

PAGE_META = {
    "home": {
        "eyebrow": "Learning Desk",
        "title": "????",
        "description": "????????????????????????????????????",
    },
    "task_pool": {
        "eyebrow": "Task Flow",
        "title": "?????",
        "description": "?????????????????????????????????????",
    },
    "initial_diagnosis": {
        "eyebrow": "Diagnosis",
        "title": "????",
        "description": "??????????????????????????????????",
    },
    "vocab_test": {
        "eyebrow": "Vocabulary",
        "title": "????",
        "description": "?????????????????????????????????",
    },
    "recent_lessons": {
        "eyebrow": "Lessons",
        "title": "????",
        "description": "???????????????????????????????",
    },
    "learned_words": {
        "eyebrow": "Vocabulary Log",
        "title": "????",
        "description": "???????????????????????????????",
    },
    "progress": {
        "eyebrow": "Progress",
        "title": "????",
        "description": "????????????????????????????????????",
    },
    "test_history": {
        "eyebrow": "History",
        "title": "????",
        "description": "????????????????????????????????",
    },
    "profile_page": {
        "eyebrow": "Growth Profile",
        "title": "????",
        "description": "??????????????????????????????????",
    },
}


def render_section_anchor(section_key: str) -> None:
    st.markdown(f'<div id="section-{section_key}"></div>', unsafe_allow_html=True)


def render_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        .student-page-shell {max-width: 1180px; margin: 0 auto; padding: 8px 0 48px;}
        .student-home-card {
            border: 1px solid #dbeafe; border-radius: 22px; padding: 20px 22px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06); margin: 12px 0;
        }
        .student-home-kicker {
            font-size: 12px; letter-spacing: .11em; text-transform: uppercase;
            color: #0369a1; font-weight: 800; margin-bottom: 8px;
        }
        .student-home-task-title {font-size: 22px; font-weight: 850; color: #0f172a; margin-bottom: 8px;}
        .student-home-subtitle {color: #334155; font-weight: 650; margin: 6px 0;}
        .student-home-task-desc {color: #475569; line-height: 1.75; margin: 6px 0 0;}
        .student-home-history-tip {
            border-radius: 18px; padding: 14px 18px; color: #0f172a;
            background: #fef3c7; border: 1px solid #fde68a; margin: 12px 0 20px;
        }
        .student-top-nav {display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 18px;}
        .student-focus-badge {
            display: inline-flex; align-items: center; border-radius: 999px;
            padding: 5px 11px; color: #075985; background: #e0f2fe;
            font-size: 12px; font-weight: 750; margin-bottom: 8px;
        }
        .student-profile-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px; margin-top: 12px;
        }
        .student-profile-pill {
            display: inline-flex; align-items: center; padding: 7px 12px; border-radius: 999px;
            background: #eff6ff; color: #1d4ed8; font-size: 13px; font-weight: 700; margin: 4px 8px 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_logged_in_header(student: dict) -> None:
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.caption(f"?????{student.get('name', '??')} ? {student.get('grade', '')}")
    with col_right:
        if st.button("????", key="student_logout_btn", use_container_width=True):
            keys_to_clear = [
                key for key in st.session_state.keys()
                if key.startswith("student_") or key == "student_login"
            ]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            st.rerun()


def render_top_navigation(current_page: str, navigate_to_page) -> None:
    st.markdown('<div class="student-top-nav">', unsafe_allow_html=True)
    columns = st.columns(5)
    for index, (page_key, label) in enumerate(NAV_ITEMS):
        button_label = label
        if current_page == page_key:
            button_label = f"? {label}"
        with columns[index % len(columns)]:
            if st.button(button_label, key=f"student_nav_{page_key}", use_container_width=True):
                navigate_to_page(page_key)
    st.markdown("</div>", unsafe_allow_html=True)


def render_page_hero(current_page: str) -> None:
    meta = PAGE_META.get(current_page, PAGE_META["home"])
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">{escape(meta.get("eyebrow", ""))}</div>
            <div class="student-home-task-title">{escape(meta.get("title", ""))}</div>
            <p class="student-home-task-desc">{escape(meta.get("description", ""))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_focus_badge(section_key: str) -> None:
    if st.session_state.get("student_home_focus_section") == section_key:
        st.markdown('<span class="student-focus-badge">??????</span>', unsafe_allow_html=True)


def render_focus_hint() -> None:
    focus_section = st.session_state.pop("student_home_focus_section", None)
    if focus_section:
        st.info(f"???????{SECTION_LABELS.get(focus_section, focus_section)}")


def render_welcome_section(home_data: dict) -> None:
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">{escape(str(home_data.get("title_label", "Learning")))}</div>
            <div class="student-home-task-title">{escape(str(home_data.get("student_name", "??")))}????????</div>
            <p class="student-home-subtitle">???{escape(str(home_data.get("stage_label", "????")))}</p>
            <p class="student-home-task-desc">{escape(str(home_data.get("growth_feedback", "")))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_light_status_section(home_data: dict) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("?????", f"{float(home_data.get('weekly_completion_ratio') or 0):.0%}")
    with col2:
        st.metric("????", f"{int(home_data.get('streak_days') or 0)} ?")
    modules = home_data.get("unlocked_modules") or []
    st.caption("??????" + (" / ".join(modules) if modules else "??????????"))


def _render_profile_item(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">{escape(label)}</div>
            <div class="student-home-task-title">{escape(value or '???')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_page(home_data: dict) -> None:
    diagnosis = home_data.get("diagnosis_summary") or {}
    st.header("??????")
    if not diagnosis.get("has_diagnosis"):
        st.info("??????????????????????")
        return

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">????</div>
            <div class="student-home-task-title">{escape(str(diagnosis.get('title_label') or home_data.get('title_label', '????')))}</div>
            <p class="student-home-subtitle">?????{escape(str(diagnosis.get('stage_label') or home_data.get('stage_label', '????')))}</p>
            <p class="student-home-task-desc">{escape(str(home_data.get('growth_feedback', '')))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    grid_cols = st.columns(2)
    items = [
        ("?????", str(diagnosis.get("vocab_band") or "???")),
        ("????", str(diagnosis.get("reading_profile") or "???")),
        ("????", str(diagnosis.get("grammar_gap") or "???")),
        ("????", str(diagnosis.get("writing_profile") or "???")),
        ("????", str(diagnosis.get("growth_focus") or "???")),
        ("????", str(diagnosis.get("suggested_track") or "???")),
    ]
    for index, (label, value) in enumerate(items):
        with grid_cols[index % 2]:
            _render_profile_item(label, value)
