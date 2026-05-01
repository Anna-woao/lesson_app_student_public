"""Shared shell and page-chrome helpers for the student app."""

from __future__ import annotations

from html import escape

import streamlit as st

SECTION_LABELS = {
    "home": "学习首页",
    "task_pool": "学习任务池",
    "initial_diagnosis": "首次诊断",
    "profile_page": "成长画像",
    "recent_lessons": "最近学案",
    "learned_words": "已学单词",
    "progress": "学习进度",
    "vocab_test": "词汇检测",
    "test_history": "检测记录",
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
        "description": "这里只保留今日驾驶舱，帮助学生快速确认状态、主任务和进入今天的学习节奏。",
    },
    "task_pool": {
        "eyebrow": "Task Flow",
        "title": "学习任务池",
        "description": "这里只承接今天要做的任务和可回看的历史内容，进入后只需要决定下一步做什么。",
    },
    "initial_diagnosis": {
        "eyebrow": "Diagnosis",
        "title": "首次诊断",
        "description": "先用一轮轻量诊断确认当前起点，后续任务会自动收束到更适合的学习路径。",
    },
    "vocab_test": {
        "eyebrow": "Vocabulary",
        "title": "词汇检测",
        "description": "直接开始词汇检测或复习检测，把今天最适合先做的词汇任务一口气完成。",
    },
    "recent_lessons": {
        "eyebrow": "Lessons",
        "title": "最近学案",
        "description": "集中回看最近学案和配套词表，适合承接今日任务完成后的巩固练习。",
    },
    "learned_words": {
        "eyebrow": "Vocabulary Log",
        "title": "已学单词",
        "description": "查看已经进入学习记录的词汇积累，建立稳定的掌握感和阶段成果感。",
    },
    "progress": {
        "eyebrow": "Progress",
        "title": "学习进度",
        "description": "从词汇书和单元维度回看推进情况，判断今天更适合继续学习还是先做复习巩固。",
    },
    "test_history": {
        "eyebrow": "History",
        "title": "检测记录",
        "description": "把历史检测结果放在同一处，方便回看正确率变化和最近一次答题反馈。",
    },
    "profile_page": {
        "eyebrow": "Growth Profile",
        "title": "成长画像",
        "description": "这里展示诊断结果的浓缩视图，帮助理解当前阶段、成长重点和下一步方向。",
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
    columns = st.columns(5)
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

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">当前画像</div>
            <div class="student-home-task-title">{escape(str(diagnosis.get('title_label') or home_data.get('title_label', '成长画像')))}</div>
            <p class="student-home-subtitle">当前阶段：{escape(str(diagnosis.get('stage_label') or home_data.get('stage_label', '准备起步')))}</p>
            <p class="student-home-task-desc">{escape(str(home_data.get('growth_feedback', '')))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    grid_cols = st.columns(2)
    items = [
        ("词汇量区间", str(diagnosis.get("vocab_band") or "待生成")),
        ("阅读画像", str(diagnosis.get("reading_profile") or "待生成")),
        ("语法缺口", str(diagnosis.get("grammar_gap") or "待生成")),
        ("写作画像", str(diagnosis.get("writing_profile") or "待生成")),
        ("成长重点", str(diagnosis.get("growth_focus") or "待生成")),
        ("建议轨道", str(diagnosis.get("suggested_track") or "待生成")),
    ]
    for index, (label, value) in enumerate(items):
        with grid_cols[index % 2]:
            _render_profile_item(label, value)
