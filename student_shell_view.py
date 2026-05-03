"""Shared shell and page-chrome helpers for the student app."""

from __future__ import annotations

from html import escape

import streamlit as st

SECTION_LABELS = {
    "home": "学习首页",
    "task_pool": "学习任务池",
    "my_vocab": "我的词汇",
    "initial_diagnosis": "首次诊断",
    "recent_lessons": "最近学案",
    "progress": "学习进度",
    "profile_page": "成长画像",
    "learned_words": "已学单词",
    "vocab_test": "词汇检测",
    "test_history": "检测记录",
}

SECTION_TO_PAGE = {
    "home": "home",
    "task_pool": "task_pool",
    "my_vocab": "my_vocab",
    "initial_diagnosis": "initial_diagnosis",
    "recent_lessons": "recent_lessons",
    "progress": "progress",
    "profile_page": "profile_page",
    "learned_words": "my_vocab",
    "vocab_test": "my_vocab",
    "test_history": "my_vocab",
}

NAV_ITEMS = [
    ("home", "学习首页"),
    ("task_pool", "学习任务池"),
    ("initial_diagnosis", "首次诊断"),
    ("my_vocab", "我的词汇"),
    ("recent_lessons", "最近学案"),
    ("progress", "学习进度"),
    ("profile_page", "成长画像"),
]

PAGE_META = {
    "home": {
        "eyebrow": "Learning Desk",
        "title": "学习首页",
        "description": "这里先收住今天最值得做的任务，帮助你快速确认状态、进入学习节奏。",
    },
    "task_pool": {
        "eyebrow": "Task Flow",
        "title": "学习任务池",
        "description": "今天要做什么、做完后看什么，都集中放在这里，不需要来回切换页面。",
    },
    "initial_diagnosis": {
        "eyebrow": "Diagnosis",
        "title": "首次诊断",
        "description": "先用一轮轻量诊断找到当前起点，后续任务会更贴近你的真实水平。",
    },
    "my_vocab": {
        "eyebrow": "Vocabulary",
        "title": "我的词汇",
        "description": "把已学单词、词汇检测和检测记录放在同一个入口，方便连续查看和练习。",
    },
    "recent_lessons": {
        "eyebrow": "Lessons",
        "title": "最近学案",
        "description": "在这里回看最近学案、完整内容和本次学案的新词表。",
    },
    "progress": {
        "eyebrow": "Progress",
        "title": "学习进度",
        "description": "从词汇书和单元两个层面看进度，判断今天更适合继续学习还是先复习。",
    },
    "profile_page": {
        "eyebrow": "Growth Profile",
        "title": "成长画像",
        "description": "这里会展示诊断结果和阶段画像，帮助你理解自己的学习重点。",
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_logged_in_header(student: dict) -> None:
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.caption(f"当前学生：{student.get('name', '同学')} · {student.get('grade', '')}")
    with col_right:
        if st.button("退出登录", key="student_logout_btn", use_container_width=True):
            keys_to_clear = [key for key in st.session_state.keys() if key.startswith("student_") or key == "student_login"]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            st.rerun()


def render_top_navigation(current_page: str, navigate_to_page) -> None:
    st.markdown('<div class="student-top-nav">', unsafe_allow_html=True)
    columns = st.columns(4)
    for index, (page_key, label) in enumerate(NAV_ITEMS):
        button_label = f"• {label}" if current_page == page_key else label
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
        st.markdown('<span class="student-focus-badge">当前定位模块</span>', unsafe_allow_html=True)


def render_focus_hint() -> None:
    focus_section = st.session_state.pop("student_home_focus_section", None)
    if focus_section:
        st.info(f"已为你切换到：{SECTION_LABELS.get(focus_section, focus_section)}")


def render_welcome_section(home_data: dict) -> None:
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">{escape(str(home_data.get("title_label", "Learning")))}</div>
            <div class="student-home-task-title">{escape(str(home_data.get("student_name", "同学")))}，今天从这里开始</div>
            <p class="student-home-subtitle">阶段：{escape(str(home_data.get("stage_label", "准备起步")))}</p>
            <p class="student-home-task-desc">{escape(str(home_data.get("growth_feedback", "")))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_light_status_section(home_data: dict) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("本周完成度", f"{float(home_data.get('weekly_completion_ratio') or 0):.0%}")
    with col2:
        st.metric("连续学习", f"{int(home_data.get('streak_days') or 0)} 天")
    modules = home_data.get("unlocked_modules") or []
    st.caption("已解锁模块：" + (" / ".join(modules) if modules else "完成任务后会逐步开启"))


def _render_profile_item(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">{escape(label)}</div>
            <div class="student-home-task-title">{escape(value or '待生成')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_page(home_data: dict) -> None:
    diagnosis = home_data.get("diagnosis_summary") or {}
    st.header("我的成长画像")
    if not diagnosis.get("has_diagnosis"):
        st.info("完成首次诊断后，这里会展示更完整的成长画像。")
        return

    col1, col2 = st.columns(2)
    with col1:
        _render_profile_item("当前阶段", home_data.get("stage_label", "待生成"))
        _render_profile_item("重点方向", home_data.get("growth_focus", "待生成"))
    with col2:
        _render_profile_item("学习标题", home_data.get("title_label", "待生成"))
        _render_profile_item("阶段总结", diagnosis.get("summary_text", "待生成"))
