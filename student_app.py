"""学生端入口（含词汇检测作答区）"""

from html import escape
import re

import streamlit as st
import streamlit.components.v1 as components

import db_student as dbs
from student_diagnosis_service import (
    evaluate_initial_diagnosis,
    get_initial_diagnosis_definition,
)
from lesson_html_renderer import build_downloadable_lesson_html, parse_lesson_text_to_parts
from student_home_viewmodel import build_student_home_viewmodel

st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")
st.title("英语辅导系统｜学生端")
st.write("这里是学生使用的前台页面。")

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
        st.session_state["student_diagnosis_active"] = True
        st.session_state["student_diagnosis_step"] = 0
        st.session_state["student_diagnosis_answers"] = {}
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


def _render_test_feedback_blocks(results):
    """
    用更清楚的两个区块展示本次检测反馈。
    """
    if not results:
        st.info("当前没有可展示的检测反馈。")
        return

    st.markdown("### 本次考察单词清单")
    for idx, item in enumerate(results, start=1):
        st.write(f"{idx}. {item.get('word', '')}")

    st.markdown("---")
    st.markdown("### 错词订正")

    wrong_results = [item for item in results if not item.get("is_correct")]
    if not wrong_results:
        st.success("本轮没有错词，很棒。")
        return

    for idx, item in enumerate(wrong_results, start=1):
        word = escape(str(item.get("word", "")))
        meaning = escape(str(item.get("meaning", "") or ""))
        mode = item.get("mode", "")
        user_answer = escape(str(item.get("user_answer") or "（未作答）"))
        correct_answer = meaning if mode == "英译中" else word

        st.markdown(
            f"""
            <div style="
                margin-bottom: 14px;
                padding: 10px 12px;
                border: 1px solid #f3d6d6;
                border-radius: 8px;
                background: #fff8f8;
            ">
                <div style="
                    color: #c62828;
                    font-weight: 700;
                    font-size: 18px;
                ">
                    {idx}. {word}
                </div>

                <div style="margin-top: 6px;">
                    你的答案：{user_answer}
                </div>

                <div style="margin-top: 4px;">
                    正确答案：{correct_answer}
                </div>

                <div style="margin-top: 4px; color: #666;">
                    标准词义：{meaning}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_vocab_test_intro(payload_exists: bool, result_exists: bool):
    if payload_exists:
        st.info("当前有一轮正在进行中的词汇检测。先完成这一轮，再开始新的检测。")
        return
    if result_exists:
        st.info("这里保留你刚完成的检测结果，也可以直接开始下一轮。")
        return
    st.info("词汇检测页只负责一件事：开始检测并完成答题。先选择一种检测方式，然后进入本轮任务。")


def _render_vocab_test_result_panel(result: dict):
    if not result.get("persistence_ok", True):
        st.warning("本次检测分数已算出，但历史记录暂未成功保存。请稍后重试，或联系老师检查数据库配置。")
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
    unit_name_to_id = {}
    for unit_id, unit_name, _unit_order in units:
        unit_name_to_id[unit_name] = unit_id

    selected_unit_labels = st.multiselect(
        "选择单元（可多选；如果一个都不选，默认检测整本词汇书）",
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
            st.session_state["student_test_source_label"] = (
                f"词汇书抽词检测：{selected_book_label} / {scope}"
            )

            st.success("已进入词汇书检测。")
            st.rerun()
        else:
            st.warning(payload)


def _render_login():
    st.info("请输入老师分配给你的账号和密码。")

    with st.form("student_login_form"):
        login_account = st.text_input("账号")
        login_password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")

    if not submitted:
        return None

    try:
        student = dbs.authenticate_student(login_account, login_password)
    except Exception as e:
        st.error("登录功能暂时不可用，请联系老师检查学生账号字段是否已经配置。")
        st.exception(e)
        return None

    if not student:
        st.error("账号或密码不正确。")
        return None

    st.session_state["student_login"] = student
    st.session_state["student_current_page"] = "home"
    st.session_state["student_home_focus_section"] = "task_pool"
    st.session_state.pop("student_test_payload", None)
    st.session_state.pop("student_test_result", None)
    st.rerun()


def _render_logged_in_header(student):
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header(f"欢迎，{student['name']}")
        if student.get("grade"):
            st.caption(f"年级：{student['grade']}")
    with col2:
        if st.button("退出登录", key="student_logout"):
            for key in [
                "student_login",
                "student_test_payload",
                "student_test_result",
                "student_current_page",
                "student_home_focus_section",
                "student_auto_open_lesson_id",
                "student_auto_open_learned_words_dialog",
            ]:
                st.session_state.pop(key, None)
            st.rerun()


def _render_dashboard_styles():
    st.markdown(
        """
        <style>
        .student-page-shell {
            padding-top: 4px;
        }
        .student-nav-shell {
            margin: 6px 0 14px 0;
            padding: 12px 14px 10px 14px;
            border: 1px solid #d9e6f2;
            border-radius: 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(247,251,255,0.96) 100%);
            box-shadow: 0 10px 28px rgba(33, 76, 110, 0.08);
        }
        .student-nav-title {
            color: #486581;
            font-size: 13px;
            margin-bottom: 4px;
        }
        .student-nav-subtitle {
            color: #7b8794;
            font-size: 13px;
        }
        .student-page-hero {
            border: 1px solid #d9e6f2;
            border-radius: 22px;
            padding: 18px 20px;
            background:
                radial-gradient(circle at top right, rgba(227, 242, 253, 0.95), rgba(255,255,255,0) 30%),
                linear-gradient(180deg, #ffffff 0%, #f6fbff 100%);
            box-shadow: 0 10px 30px rgba(33, 76, 110, 0.08);
            margin-bottom: 16px;
        }
        .student-page-eyebrow {
            color: #5a7184;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }
        .student-page-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 8px;
        }
        .student-page-title {
            color: #102a43;
            font-size: 28px;
            font-weight: 700;
            margin: 0;
        }
        .student-page-description {
            color: #486581;
            font-size: 14px;
            line-height: 1.7;
            margin-bottom: 0;
        }
        .student-page-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: #e8f4ff;
            color: #1f5f8b;
            font-size: 13px;
            white-space: nowrap;
        }
        .student-home-card {
            border: 1px solid #d9e6f2;
            border-radius: 18px;
            padding: 18px 20px;
            background: linear-gradient(180deg, #ffffff 0%, #f6fbff 100%);
            box-shadow: 0 8px 22px rgba(33, 76, 110, 0.06);
            margin-bottom: 12px;
        }
        .student-home-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #e8f4ff;
            color: #23527c;
            font-size: 13px;
            margin-right: 8px;
            margin-bottom: 8px;
        }
        .student-home-kicker {
            color: #5a7184;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .student-home-title {
            font-size: 26px;
            font-weight: 700;
            color: #183b56;
            margin: 0 0 8px 0;
        }
        .student-home-subtitle {
            color: #486581;
            font-size: 15px;
            margin-bottom: 0;
        }
        .student-home-task-title {
            font-size: 20px;
            font-weight: 700;
            color: #102a43;
            margin: 0 0 8px 0;
        }
        .student-home-task-desc {
            color: #486581;
            font-size: 14px;
            margin-bottom: 0;
        }
        .student-home-history-tip {
            color: #52606d;
            font-size: 14px;
            margin-top: 2px;
        }
        .student-diagnosis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }
        .student-diagnosis-mini-card {
            border: 1px solid #d9e6f2;
            border-radius: 16px;
            padding: 14px 16px;
            background: #ffffff;
        }
        .student-diagnosis-mini-title {
            color: #486581;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .student-diagnosis-mini-body {
            color: #102a43;
            font-size: 15px;
            line-height: 1.5;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
            min-height: 42px;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="secondary"] {
            border-radius: 999px;
            border: 1px solid #d7e7f6;
            background: #f7fbff;
            color: #335c81;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="primary"] {
            border-radius: 999px;
            background: linear-gradient(135deg, #165d8c 0%, #0f7a9f 100%);
            border: none;
            box-shadow: 0 8px 18px rgba(18, 103, 145, 0.24);
        }
        @media (max-width: 900px) {
            .student-page-title-row {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_top_navigation():
    current_page = st.session_state.get("student_current_page", "home")
    st.markdown(
        """
        <div class="student-nav-shell">
            <div class="student-nav-title">学习导航</div>
            <div class="student-nav-subtitle">把今天要做的事情收成几个清晰页面，减少上下翻找。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    columns = st.columns(len(NAV_ITEMS))
    for column, (page_key, label) in zip(columns, NAV_ITEMS):
        with column:
            button_type = "primary" if current_page == page_key else "secondary"
            if st.button(label, key=f"student_nav_{page_key}", type=button_type, use_container_width=True):
                _navigate_to_page(page_key, focus_section="task_pool" if page_key == "home" else None)


def _render_page_hero(current_page: str, home_data: dict):
    meta = PAGE_META.get(current_page, PAGE_META["home"])
    badge = ""

    if current_page == "home":
        badge = f"今日主任务：{home_data.get('primary_task', '开始今天的成长之旅')}"
    elif current_page == "vocab_test":
        if st.session_state.get("student_test_payload"):
            badge = "当前状态：正在进行中的检测"
        else:
            badge = "当前状态：可直接开始新一轮检测"
    elif current_page == "task_pool":
        badge = f"今日主任务：{home_data.get('primary_task', '开始今天的成长之旅')}"
    elif current_page == "initial_diagnosis":
        badge = "当前状态：诊断完成后会自动更新首页任务"
    elif current_page == "profile_page":
        badge = f"当前阶段：{home_data.get('stage_label', '准备起步')}"
    else:
        badge = f"当前称号：{home_data.get('title_label', '启程学员')}"

    st.markdown(
        f"""
        <div class="student-page-hero">
            <div class="student-page-eyebrow">{meta["eyebrow"]}</div>
            <div class="student-page-title-row">
                <div class="student-page-title">{meta["title"]}</div>
                <div class="student-page-badge">{badge}</div>
            </div>
            <p class="student-page-description">{meta["description"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_page_quick_actions(current_page: str):
    if current_page == "home":
        return

    left, right = st.columns([1, 1])
    with left:
        if st.button("返回学习首页", key=f"back_home_{current_page}", use_container_width=True):
            _navigate_to_page("home", focus_section="task_pool")
    with right:
        if current_page != "profile_page":
            if st.button("查看成长画像", key=f"jump_profile_{current_page}", use_container_width=True):
                _navigate_to_page("profile_page")


def _render_welcome_section(home_data: dict):
    unlocked_modules = home_data.get("unlocked_modules", [])
    module_html = "".join(
        f'<span class="student-home-chip">{module}</span>' for module in unlocked_modules
    ) or '<span class="student-home-chip">新的学习旅程</span>'

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">欢迎回来</div>
            <div class="student-home-title">{home_data["student_name"]}，今天继续向前走一点点</div>
            <p class="student-home-subtitle">
                当前称号：<strong>{home_data["title_label"]}</strong>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                当前阶段：<strong>{home_data["stage_label"]}</strong>
            </p>
            <p class="student-home-subtitle">{home_data["growth_feedback"]}</p>
            <div style="margin-top: 10px;">{module_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_diagnosis_summary_card(home_data: dict):
    diagnosis = home_data.get("diagnosis_summary", {})
    if not diagnosis.get("has_diagnosis"):
        return

    st.markdown("## 当前诊断结果")
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">你的当前起点</div>
            <div class="student-home-task-title">{diagnosis.get("title_label", "")} ｜ {diagnosis.get("stage_label", "")}</div>
            <p class="student-home-subtitle">{diagnosis.get("growth_focus", "")}</p>
            <div class="student-diagnosis-grid">
                <div class="student-diagnosis-mini-card">
                    <div class="student-diagnosis-mini-title">词汇量区间</div>
                    <div class="student-diagnosis-mini-body">{diagnosis.get("vocab_band", "待生成")}</div>
                </div>
                <div class="student-diagnosis-mini-card">
                    <div class="student-diagnosis-mini-title">阅读画像</div>
                    <div class="student-diagnosis-mini-body">{diagnosis.get("reading_profile", "待生成")}</div>
                </div>
                <div class="student-diagnosis-mini-card">
                    <div class="student-diagnosis-mini-title">语法重点</div>
                    <div class="student-diagnosis-mini-body">{diagnosis.get("grammar_gap", "待生成")}</div>
                </div>
                <div class="student-diagnosis-mini-card">
                    <div class="student-diagnosis-mini-title">建议轨道</div>
                    <div class="student-diagnosis-mini-body">{diagnosis.get("suggested_track", "待生成")}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("查看我的成长画像", key="jump_to_profile_page", use_container_width=True):
        _navigate_to_page("profile_page")

def _render_primary_task_section(home_data: dict):
    button_key = f"student_home_start_today_{home_data['student_name']}"

    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">今日成长之旅</div>
            <div class="student-home-task-title">{home_data["primary_task"]}</div>
            <p class="student-home-subtitle">预计用时：{home_data["primary_task_eta"]}</p>
            <p class="student-home-task-desc">{home_data["current_task_cards"][0]["description"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("开始今天的成长之旅", key=button_key, type="primary", use_container_width=True):
        _navigate_to_page("task_pool", focus_section="task_pool")


def _render_light_status_section(home_data: dict):
    unlocked_modules = home_data.get("unlocked_modules", [])
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本周完成度", f"{home_data['weekly_completion_ratio']:.0%}")
        st.progress(home_data["weekly_completion_ratio"])
    with col2:
        st.metric("连续学习天数", f"{home_data['streak_days']} 天")
        st.caption("按近 30 天的学案创建与检测完成日期计算")
    with col3:
        st.metric("已解锁模块", len(unlocked_modules))
        st.caption(" / ".join(unlocked_modules) if unlocked_modules else "完成首个任务后会逐步解锁")


def _render_task_pool_section(home_data: dict):
    _render_section_anchor("task_pool")
    st.markdown("## 学习任务池")
    _render_section_focus_badge("task_pool")
    current_cards = home_data.get("current_task_cards", [])
    history_cards = home_data.get("history_task_cards", [])

    st.markdown("### 当前待完成任务池")
    if not current_cards:
        st.info("今天先从一小步开始，我们会在这里给你准备接下来的任务。")
    else:
        columns = st.columns(len(current_cards))
        for index, (column, card) in enumerate(zip(columns, current_cards)):
            badge = "今日主任务" if card.get("is_primary") else "接下来可以做"
            with column:
                st.markdown(
                    f"""
                    <div class="student-home-card">
                        <div class="student-home-kicker">{badge}</div>
                        <div class="student-home-task-title">{card["title"]}</div>
                        <p class="student-home-subtitle">预计用时：{card["eta"]}</p>
                        <p class="student-home-task-desc">{card["description"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                button_label = "开始这一项" if card.get("action_type") != "focus_section" else "查看这一项"
                if st.button(button_label, key=f"student_current_task_{index}", use_container_width=True):
                    if _run_task_action(st.session_state["student_login"]["id"], card):
                        st.rerun()

    st.markdown("### 历史内容池")
    if not history_cards:
        st.info("完成第一轮学习后，这里会帮你收集可回看的旧内容。")
        return

    columns = st.columns(len(history_cards))
    for index, (column, card) in enumerate(zip(columns, history_cards)):
        with column:
            st.markdown(
                f"""
                <div class="student-home-card">
                    <div class="student-home-kicker">已完成内容</div>
                    <div class="student-home-task-title">{card["title"]}</div>
                    <p class="student-home-subtitle">{card["eta"]}</p>
                    <p class="student-home-task-desc">{card["description"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("前往回看", key=f"student_history_task_{index}", use_container_width=True):
                if _run_task_action(st.session_state["student_login"]["id"], card):
                    st.rerun()


def _render_focus_hint():
    if st.session_state.get("student_current_page", "home") != "home":
        return

    target_section = st.session_state.get("student_home_focus_section")
    if not target_section:
        return

    target_label = SECTION_LABELS.get(target_section, "对应学习区域")
    st.info(f"今天先从下方的“{target_label}”开始吧，我已经帮你把重点放在那里了。")


def _render_section_focus_badge(section_key: str):
    current_page = st.session_state.get("student_current_page", "home")
    target_section = st.session_state.get("student_home_focus_section")
    if current_page == SECTION_TO_PAGE.get(section_key, section_key) and (
        target_section == section_key or current_page == section_key
    ):
        st.success(f"今天建议先完成这一部分：{SECTION_LABELS.get(section_key, '当前区域')}")


def _clear_diagnosis_session_state():
    for key in [
        "student_diagnosis_active",
        "student_diagnosis_step",
        "student_diagnosis_answers",
    ]:
        st.session_state.pop(key, None)


def _build_saved_diagnosis_result(student_id: int):
    latest_record = dbs.get_latest_diagnosis_record(student_id) or {}
    latest_snapshot = dbs.get_latest_profile_snapshot(student_id) or {}
    profile_payload = latest_snapshot.get("profile_payload") or {}

    if not latest_record and not latest_snapshot:
        return None

    return {
        "scores": latest_record.get("module_scores") or {},
        "totals": latest_record.get("module_totals") or {},
        "module_reports": profile_payload.get("module_reports") or {},
        "priority_module": profile_payload.get("priority_module"),
        "strongest_module": profile_payload.get("strongest_module"),
        "overall_accuracy": profile_payload.get("overall_accuracy"),
        "overall_summary": profile_payload.get("overall_summary") or latest_snapshot.get("summary_text") or "",
        "title_label": latest_snapshot.get("title_label") or "",
        "stage_label": latest_snapshot.get("stage_label") or "",
        "growth_focus": latest_snapshot.get("growth_focus") or "",
        "summary_text": latest_snapshot.get("summary_text") or "",
        "next_actions": profile_payload.get("next_actions") or [],
        "dimensions": profile_payload.get("dimensions") or {},
        "suggested_track": profile_payload.get("suggested_track") or latest_record.get("suggested_track") or "",
        "vocab_band": profile_payload.get("vocab_band") or latest_record.get("vocab_band") or "",
        "reading_profile": profile_payload.get("reading_profile") or latest_record.get("reading_profile") or "",
        "grammar_gap": profile_payload.get("grammar_gap") or latest_record.get("grammar_gap") or "",
        "writing_profile": profile_payload.get("writing_profile") or latest_record.get("writing_profile") or "",
    }


def _render_diagnosis_module_overview(definition, active_step: int | None = None):
    columns = st.columns(len(definition))
    for index, (column, module) in enumerate(zip(columns, definition)):
        if active_step is None:
            status_label = "待完成"
        elif index < active_step:
            status_label = "已完成"
        elif index == active_step:
            status_label = "当前进行中"
        else:
            status_label = "待完成"

        with column:
            st.markdown(
                f"""
                <div class="student-diagnosis-mini-card" style="min-height: 150px;">
                    <div class="student-diagnosis-mini-title">{index + 1}. {module.get("short_title", module["title"])}</div>
                    <div class="student-diagnosis-mini-body">
                        {status_label}<br/>
                        预计 {module.get("estimated_minutes", 3)} 分钟<br/>
                        {len(module.get("questions", []))} 道题
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_diagnosis_result(result: dict):
    dimensions = result.get("dimensions", {})
    module_reports = result.get("module_reports", {})
    card_items = [
        ("词汇量区间", result.get("vocab_band", "")),
        ("阅读能力画像", result.get("reading_profile", "")),
        ("语法基础缺口", result.get("grammar_gap", "")),
        ("写作基础判断", result.get("writing_profile", "")),
        ("建议学习轨道", result.get("suggested_track", "")),
        ("当前成长重点", result.get("growth_focus", "")),
    ]
    cards_html = "".join(
        f"""
        <div class="student-diagnosis-mini-card">
            <div class="student-diagnosis-mini-title">{title}</div>
            <div class="student-diagnosis-mini-body">{body or '待生成'}</div>
        </div>
        """
        for title, body in card_items
    )
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">首次诊断结果</div>
            <div class="student-home-task-title">{result.get("title_label", "")}｜{result.get("stage_label", "")}</div>
            <p class="student-home-subtitle">{result.get("overall_summary", "")}</p>
            <p class="student-home-subtitle">{result.get("summary_text", "")}</p>
            <div class="student-diagnosis-grid">
                {cards_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if module_reports:
        st.markdown("### 模块诊断拆解")
        for module_key in ["vocab", "reading", "grammar", "writing"]:
            module = module_reports.get(module_key) or {}
            if not module:
                continue
            score = module.get("score", 0)
            total = module.get("total", 0)
            ratio = module.get("ratio", 0.0) or 0.0
            st.markdown(
                f"""
                <div class="student-home-card">
                    <div class="student-home-kicker">{module.get("title", module_key)}</div>
                    <div class="student-home-task-title">{score} / {total} ｜ {module.get("level_label", "")}</div>
                    <p class="student-home-subtitle">{module.get("summary", "")}</p>
                    <p class="student-home-task-desc">{module.get("recommendation", "")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(ratio)

    next_actions = [item for item in result.get("next_actions", []) if item]
    if next_actions:
        st.markdown("### 下一步建议")
        for item in next_actions:
            st.write(f"- {item}")

    if dimensions:
        with st.expander("查看六维画像说明", expanded=False):
            for title, body in dimensions.items():
                st.markdown(f"### {title}")
                st.write(body)
    return
    card_items = [
        ("词汇量区间", result.get("vocab_band", "")),
        ("阅读能力画像", result.get("reading_profile", "")),
        ("语法基础缺口", result.get("grammar_gap", "")),
        ("写作基础判断", result.get("writing_profile", "")),
        ("建议学习轨道", result.get("suggested_track", "")),
        ("当前成长重点", result.get("growth_focus", "")),
    ]
    cards_html = "".join(
        f"""
        <div class="student-diagnosis-mini-card">
            <div class="student-diagnosis-mini-title">{title}</div>
            <div class="student-diagnosis-mini-body">{body or '待生成'}</div>
        </div>
        """
        for title, body in card_items
    )
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">首次诊断结果</div>
            <div class="student-home-task-title">{result.get("title_label", "")}｜{result.get("stage_label", "")}</div>
            <p class="student-home-subtitle">{result.get("summary_text", "")}</p>
            <div class="student-diagnosis-grid">
                {cards_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if dimensions:
        with st.expander("查看六维画像说明", expanded=False):
            for title, body in dimensions.items():
                st.markdown(f"### {title}")
                st.write(body)


def _render_profile_page(home_data: dict):
    _render_section_anchor("profile_page")
    st.header("我的成长画像")
    _render_section_focus_badge("profile_page")

    diagnosis = home_data.get("diagnosis_summary", {})
    if not diagnosis.get("has_diagnosis"):
        st.info("完成首次诊断后，这里会展示更完整的成长画像。")
        return

    dimensions = diagnosis.get("dimensions", {}) or {}
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">当前画像总览</div>
            <div class="student-home-task-title">{diagnosis.get("title_label", "")} ｜ {diagnosis.get("stage_label", "")}</div>
            <p class="student-home-subtitle">{diagnosis.get("growth_focus", "")}</p>
            <p class="student-home-task-desc">{diagnosis.get("suggested_track", "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not dimensions:
        st.info("当前画像数据还在整理中，稍后会在这里补齐。")
        return

    st.markdown("### 六维画像")
    dimension_items = list(dimensions.items())
    for start in range(0, len(dimension_items), 2):
        columns = st.columns(2)
        for column, (title, body) in zip(columns, dimension_items[start:start + 2]):
            with column:
                st.markdown(
                    f"""
                    <div class="student-diagnosis-mini-card" style="min-height: 180px;">
                        <div class="student-diagnosis-mini-title">{title}</div>
                        <div class="student-diagnosis-mini-body">{body}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### 下一步建议")
    next_steps = [
        diagnosis.get("growth_focus", ""),
        diagnosis.get("suggested_track", ""),
        "先把今天的主任务完成，再回来看看有没有新的变化。",
    ]
    for item in [text for text in next_steps if text]:
        st.write(f"- {item}")

def _render_initial_diagnosis(student_id: int):
    _render_section_anchor("initial_diagnosis")
    st.header("首次诊断")
    _render_section_focus_badge("initial_diagnosis")

    flash_result = st.session_state.pop("student_diagnosis_flash", None)
    if flash_result:
        _render_diagnosis_result(flash_result)

    latest_record = dbs.get_latest_diagnosis_record(student_id)
    if latest_record and not st.session_state.get("student_diagnosis_active", False):
        st.info("你已经完成过首次诊断，下面是当前保存的诊断结果。")
        _render_diagnosis_result(latest_record)
        if st.button("重新做一次首次诊断", key="restart_initial_diagnosis"):
            st.session_state["student_diagnosis_active"] = True
            st.session_state["student_diagnosis_step"] = 0
            st.session_state["student_diagnosis_answers"] = {}
            st.rerun()
        return

    if not st.session_state.get("student_diagnosis_active", False):
        st.info("这是一轮轻量诊断，会帮助系统判断你当前更适合从哪里开始。")
        if st.button("开始首次诊断", key="start_initial_diagnosis", type="primary"):
            st.session_state["student_diagnosis_active"] = True
            st.session_state["student_diagnosis_step"] = 0
            st.session_state["student_diagnosis_answers"] = {}
            st.rerun()
        return

    definition = get_initial_diagnosis_definition()
    step = st.session_state.get("student_diagnosis_step", 0)
    answers_by_module = st.session_state.setdefault("student_diagnosis_answers", {})
    module = definition[step]

    st.progress((step + 1) / len(definition))
    st.subheader(f"{step + 1}. {module['title']}")
    st.write(module["intro"])
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
    with st.form(f"initial_diagnosis_form_{module['key']}"):
        current_answers = {}
        for question in module["questions"]:
            current_answers[question["id"]] = st.radio(
                question["prompt"],
                question["options"],
                index=question["options"].index(default_answers[question["id"]])
                if question["id"] in default_answers and default_answers[question["id"]] in question["options"]
                else 0,
                key=f"diagnosis_{module['key']}_{question['id']}",
            )

        button_label = "完成诊断" if step == len(definition) - 1 else "进入下一部分"
        submitted = st.form_submit_button(button_label)

    if submitted:
        answers_by_module[module["key"]] = current_answers
        st.session_state["student_diagnosis_answers"] = answers_by_module

        if step < len(definition) - 1:
            st.session_state["student_diagnosis_step"] = step + 1
            st.rerun()

        result = evaluate_initial_diagnosis(answers_by_module)
        try:
            dbs.save_initial_diagnosis_result(student_id, result)
        except Exception as e:
            st.error("诊断结果保存失败，请联系管理员检查 Supabase 配置。")
            st.exception(e)
            return

        _clear_diagnosis_session_state()
        st.session_state["student_diagnosis_flash"] = result
        st.rerun()

    if st.button("先暂停这轮诊断", key="pause_initial_diagnosis"):
        _clear_diagnosis_session_state()
        st.rerun()

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
    return build_downloadable_lesson_html(parts, title=title or "英语学案")


def _looks_like_html(content: str) -> bool:
    lowered = (content or "").lower()
    return "<html" in lowered or "<body" in lowered or "<!doctype" in lowered


def _render_lesson_content(detail):
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
        st.info("这份学案暂时没有记录新词。")
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
def _show_lesson_detail_dialog(student_id: int, lesson_id: int):
    detail = dbs.get_lesson_detail_for_student(student_id, lesson_id)
    if not detail:
        st.warning("没有找到这份学案，或这份学案不属于当前学生。")
        return

    st.write(f"学案 ID：{detail.get('id')}")
    st.write(f"类型：{detail.get('lesson_type')}")
    st.write(f"主题：{detail.get('topic')}")
    st.write(f"创建时间：{detail.get('created_at')}")
    _render_lesson_content(detail)


@st.dialog("本次学案新词表")
def _show_lesson_vocab_dialog(student_id: int, lesson_id: int):
    rows = dbs.get_lesson_new_vocab_for_student(student_id, lesson_id)
    st.write(f"学案 ID：{lesson_id}")
    st.write(f"新词数量：{len(rows)}")
    _render_lesson_vocab_rows(rows)


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
        title = f"{created_at}｜学案 {lesson_id}｜{lesson_type}｜{topic}（{word_count}词）"

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
    lessons = dbs.get_student_recent_lessons(student_id, limit=10)
    if not lessons:
        st.info("这里会慢慢收集你的学案练习。完成今天的第一步后，再回来看看。")
        return

    auto_open_lesson_id = st.session_state.pop("student_auto_open_lesson_id", None)
    if auto_open_lesson_id:
        _show_lesson_detail_dialog(student_id, auto_open_lesson_id)

    latest_lesson = lessons[0]
    st.markdown(
        f"""
        <div class="student-home-card">
            <div class="student-home-kicker">学案模块说明</div>
            <div class="student-home-task-title">最近 {len(lessons)} 份学案都集中放在这里</div>
            <p class="student-home-task-desc">
                最近一次主题：{latest_lesson[3] or latest_lesson[1] or '继续练习'}；
                在这个页面里只做两件事：查看完整学案，或查看对应新词表。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 学案列表")
    for lesson_id, lesson_type, difficulty, topic, created_at in lessons:
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">学案 ID：{lesson_id}</div>
                <div class="student-home-task-title">{topic or lesson_type or '本次学案'}</div>
                <p class="student-home-subtitle">题型：{lesson_type or '未标注'} ｜ 难度：{difficulty or '未标注'}</p>
                <p class="student-home-task-desc">创建时间：{created_at or '暂无记录'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("查看完整学案", key=f"view_lesson_{lesson_id}", use_container_width=True):
                _show_lesson_detail_dialog(student_id, lesson_id)
        with col2:
            if st.button("查看本次学案新词表", key=f"view_lesson_vocab_{lesson_id}", use_container_width=True):
                _show_lesson_vocab_dialog(student_id, lesson_id)


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
        st.markdown(
            f"""
            <div class="student-home-card">
                <div class="student-home-kicker">关联学案</div>
                <div class="student-home-task-title">{lesson_label}</div>
                <p class="student-home-subtitle">词汇数量：{group.get("word_count", 0)}</p>
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
                <div class="student-home-kicker">检测记录 ID：{test_record_id}{retry_tag}</div>
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


def _render_vocab_test(student_id: int):
    _render_section_anchor("vocab_test")
    st.header("我的词汇检测")
    _render_section_focus_badge("vocab_test")
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
    st.subheader("正在答题")
    st.caption("请先完成这一轮检测。提交后，本页只保留结果和重新开始入口。")

    with st.form("student_vocab_test_form", clear_on_submit=False):
        user_answers = {}

        for idx, q in enumerate(payload["questions"], start=1):
            st.markdown(f"### 第 {idx} 题")
            st.caption(f"本题题型：{q['mode']}")
            if q["mode"] == "英译中":
                user_answers[q["vocab_item_id"]] = st.radio(
                    f"请选择 **{q['word']}** 的中文意思：",
                    q["options"],
                    key=f"student_mcq_{q['vocab_item_id']}",
                )
            else:
                user_answers[q["vocab_item_id"]] = st.text_input(
                    f"请根据中文意思写出英文：**{q['meaning']}**",
                    key=f"student_text_{q['vocab_item_id']}",
                )

        submitted = st.form_submit_button("提交检测")

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


def _show_debug_info():
    with st.expander("调试信息", expanded=True):
        try:
            secret_keys = set(dict(st.secrets).keys())
        except Exception:
            secret_keys = set()

        st.write("SUPABASE_URL：", "已配置" if "SUPABASE_URL" in secret_keys else "未配置")
        st.write("SUPABASE_PUBLISHABLE_KEY：", "已配置" if "SUPABASE_PUBLISHABLE_KEY" in secret_keys else "未配置")


def _safe_render(section_name: str, render_func, student_id: int):
    try:
        render_func(student_id)
    except Exception as e:
        st.error(f"{section_name} 加载失败")
        st.exception(e)


if __name__ == "__main__":
    main()
