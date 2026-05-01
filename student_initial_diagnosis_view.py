from __future__ import annotations

from datetime import datetime
import re

import streamlit as st
import streamlit.components.v1 as components

from db_student import (
    get_diagnostic_vocab_bank_status,
    get_diagnostic_vocab_items_for_test,
)
from student_records_data import (
    get_latest_diagnosis_record,
    get_latest_profile_snapshot,
    save_initial_diagnosis_result,
)
from student_diagnosis_service import (
    build_initial_diagnosis_definition,
    evaluate_initial_diagnosis,
)


VOCAB_DIAG_PAGE_SIZE = 8
LEVEL_SEGMENT_LABELS = {
    "L1": "L1 基础生存词",
    "L2": "L2 高频基础词",
    "L3": "L3 阅读核心词",
    "L4": "L4 进阶阅读词",
    "L5": "L5 熟词生义与易混词",
}
QUESTION_TYPE_LABELS = {
    "en_to_zh_choice": "英文识义",
    "en_to_zh": "英文识义",
    "zh_to_en": "中文找英文",
    "polysemy_context": "语境义判断",
    "confusable_choice": "易混词辨析",
}
RESULT_LEVEL_LABELS = {
    "L1": "L1 基础日常词",
    "L2": "L2 初中高频词",
    "L3": "L3 高中核心词",
    "L4": "L4 阅读高频词",
    "L5": "L5 熟词生义与易混词",
}


def clear_diagnosis_session_state() -> None:
    for key in [
        "student_diagnosis_active",
        "student_diagnosis_step",
        "student_diagnosis_answers",
        "student_diagnosis_definition",
        "student_diagnosis_started_at",
        "student_diagnosis_module_started_at",
        "student_diagnosis_module_started_at_map",
        "student_diagnosis_vocab_page",
        "student_diagnosis_missing_question_ids",
        "student_diagnosis_missing_page",
    ]:
        st.session_state.pop(key, None)


def prepare_initial_diagnosis_definition(*, force_refresh: bool = False):
    if not force_refresh:
        cached_definition = st.session_state.get("student_diagnosis_definition")
        if cached_definition:
            return cached_definition

    vocab_questions = get_diagnostic_vocab_items_for_test()
    definition = build_initial_diagnosis_definition(vocab_questions)
    st.session_state["student_diagnosis_definition"] = definition
    return definition


def activate_initial_diagnosis(*, force_refresh: bool = False) -> None:
    clear_diagnosis_session_state()
    definition = prepare_initial_diagnosis_definition(force_refresh=force_refresh)
    started_at = datetime.utcnow().isoformat()
    st.session_state["student_diagnosis_definition"] = definition
    st.session_state["student_diagnosis_active"] = True
    st.session_state["student_diagnosis_step"] = 0
    st.session_state["student_diagnosis_answers"] = {}
    st.session_state["student_diagnosis_started_at"] = started_at
    st.session_state["student_diagnosis_module_started_at"] = started_at
    st.session_state["student_diagnosis_module_started_at_map"] = {}
    st.session_state["student_diagnosis_vocab_page"] = 0
    st.session_state.pop("student_diagnosis_missing_question_ids", None)
    st.session_state.pop("student_diagnosis_missing_page", None)


def _render_diagnostic_vocab_bank_status():
    try:
        status = get_diagnostic_vocab_bank_status()
    except Exception as exc:
        st.error("首次诊断暂时还不能开始，请稍后再试。")
        return {"ready_for_diagnosis": False, "load_error": str(exc)}

    total_count = status.get("total_count", 0)
    ready_for_diagnosis = bool(status.get("ready_for_diagnosis"))
    if ready_for_diagnosis:
        st.success(f"诊断题库已就绪，本次会从 {total_count} 道正式题里为你生成个人诊断。")
    else:
        st.warning("诊断题库还在准备中，当前还不能开始首次诊断。")
    return status


def _build_saved_diagnosis_result(student_id: int):
    latest_record = get_latest_diagnosis_record(student_id) or {}
    latest_snapshot = get_latest_profile_snapshot(student_id) or {}
    profile_payload = latest_snapshot.get("profile_payload") or {}

    if not latest_record and not latest_snapshot:
        return None

    return {
        "scores": latest_record.get("module_scores") or {},
        "totals": latest_record.get("module_totals") or {},
        "vocab_profile_summary": profile_payload.get("vocab_profile_summary") or "",
        "vocab_diagnostic_result": profile_payload.get("vocab_diagnostic_result") or {},
        "vocab_training_track": profile_payload.get("vocab_training_track") or "",
        "vocab_training_track_label": profile_payload.get("vocab_training_track_label") or "",
        "vocab_training_track_reason": profile_payload.get("vocab_training_track_reason") or "",
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


def _format_question_type_label(question_type: str) -> str:
    return QUESTION_TYPE_LABELS.get(question_type or "", question_type or "词汇判断")


def _build_vocab_page_meta(questions: list[dict]) -> str:
    level_labels = []
    question_type_labels = []
    for question in questions:
        level = str(question.get("level") or "").strip()
        if level and level not in level_labels:
            level_labels.append(level)
        question_type = _format_question_type_label(str(question.get("question_type") or "").strip())
        if question_type and question_type not in question_type_labels:
            question_type_labels.append(question_type)
    parts = []
    if level_labels:
        parts.append("层级：" + " / ".join(level_labels))
    if question_type_labels:
        parts.append("题型：" + " / ".join(question_type_labels))
    return " · ".join(parts)


def _build_vocab_page_title(questions: list[dict]) -> str:
    if not questions:
        return "词汇诊断"
    first_question = questions[0]
    level = str(first_question.get("level") or "").strip()
    question_type = _format_question_type_label(str(first_question.get("question_type") or "").strip())
    level_label = LEVEL_SEGMENT_LABELS.get(level, level or "词汇诊断")
    return f"{level_label} · {question_type}"


def _build_question_anchor_id(question_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(question_id or "").strip())
    return f"diag-question-{normalized or 'unknown'}"


def _render_vocab_question_card(question: dict, question_index: int):
    question_type_label = _format_question_type_label(str(question.get("question_type") or "").strip())
    level_label = str(question.get("level") or "").strip()
    prompt = str(question.get("prompt") or "")
    sentence = str(question.get("sentence") or "")
    anchor_id = _build_question_anchor_id(str(question.get("id") or ""))
    sentence_html = f"<div class='student-diagnosis-question-sentence'>{sentence}</div>" if sentence else ""
    st.markdown(
        f"""
        <div id="{anchor_id}" class="student-diagnosis-question-shell">
            <div class="student-diagnosis-question-tag">第 {question_index} 题 · {level_label} · {question_type_label}</div>
            <div class="student-diagnosis-question-title">{prompt}</div>
            <div class="student-diagnosis-question-subtitle">
                请选择你认为最合适的答案；如果完全不会，就选“我不知道”。
            </div>
            {sentence_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_percent(value: float) -> str:
    return f"{round((value or 0.0) * 100)}%"


def _render_summary_metric(column, title: str, value: str, detail: str):
    with column:
        st.markdown(f"**{title}**")
        st.markdown(value)
        st.caption(detail)


def _render_diagnosis_result(result: dict):
    dimensions = result.get("dimensions", {}) or {}
    module_reports = result.get("module_reports", {}) or {}
    vocab_diagnostic_result = result.get("vocab_diagnostic_result") or {}

    st.markdown("### 首次诊断结果")
    st.write(result.get("overall_summary", ""))

    if vocab_diagnostic_result.get("student_explanation"):
        st.info(vocab_diagnostic_result.get("student_explanation", ""))
    elif result.get("summary_text"):
        st.info(result.get("summary_text", ""))

    if vocab_diagnostic_result:
        metric_cols = st.columns(4)
        _render_summary_metric(
            metric_cols[0],
            "优先训练",
            vocab_diagnostic_result.get("vocab_training_track_label", "待生成"),
            vocab_diagnostic_result.get("vocab_training_track_reason", ""),
        )
        _render_summary_metric(
            metric_cols[1],
            "基础词掌握",
            vocab_diagnostic_result.get("basic_vocab_status", "待判断"),
            f"基础词正确率 {_format_percent(vocab_diagnostic_result.get('high_frequency_accuracy', 0.0))}",
        )
        _render_summary_metric(
            metric_cols[2],
            "阅读词掌握",
            vocab_diagnostic_result.get("reading_vocab_status", "待判断"),
            f"阅读词正确率 {_format_percent(vocab_diagnostic_result.get('reading_vocab_accuracy', 0.0))}",
        )
        _render_summary_metric(
            metric_cols[3],
            "答题把握度",
            vocab_diagnostic_result.get("answer_confidence_label", "待判断"),
            f"“我不知道”占比 {_format_percent(vocab_diagnostic_result.get('uncertain_rate', 0.0))}",
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
            st.markdown(f"**{module.get('title', module_key)}**")
            st.write(f"{score} / {total} | {module.get('level_label', '')}")
            st.write(module.get("summary", ""))
            st.caption(module.get("recommendation", ""))
            st.progress(ratio)

    if vocab_diagnostic_result:
        st.markdown("### 词汇诊断结果解释")
        st.write(vocab_diagnostic_result.get("main_vocab_problem", ""))

        level_cols = st.columns(5)
        for column, (level_code, key) in zip(
            level_cols,
            [("L1", "l1_accuracy"), ("L2", "l2_accuracy"), ("L3", "l3_accuracy"), ("L4", "l4_accuracy"), ("L5", "l5_accuracy")],
        ):
            with column:
                st.metric(RESULT_LEVEL_LABELS[level_code], _format_percent(vocab_diagnostic_result.get(key, 0.0)))

        if vocab_diagnostic_result.get("l5_interpretation"):
            st.caption(vocab_diagnostic_result.get("l5_interpretation", ""))

        question_type_map = vocab_diagnostic_result.get("question_type_accuracy_map_display", {}) or {}
        if question_type_map:
            st.markdown("**题型表现**")
            for label, value in question_type_map.items():
                st.write(f"- {label}：{_format_percent(value)}")

        strengths = [item for item in vocab_diagnostic_result.get("strengths", []) if item]
        risk_flags = [item for item in vocab_diagnostic_result.get("risk_flags", []) if item]
        recommended_actions = [item for item in vocab_diagnostic_result.get("recommended_actions", []) if item]
        if strengths:
            st.markdown("**你已经有的优势**")
            for item in strengths:
                st.write(f"- {item}")
        if risk_flags:
            st.markdown("**接下来要注意的地方**")
            for item in risk_flags:
                st.write(f"- {item}")
        if recommended_actions:
            st.markdown("**词汇训练路径推荐**")
            for item in recommended_actions:
                st.write(f"- {item}")

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


def render_initial_diagnosis(student_id: int, *, render_section_anchor, render_section_focus_badge):
    render_section_anchor("initial_diagnosis")
    st.header("首次诊断")
    render_section_focus_badge("initial_diagnosis")

    flash_result = st.session_state.pop("student_diagnosis_flash", None)
    if flash_result:
        _render_diagnosis_result(flash_result)

    saved_result = _build_saved_diagnosis_result(student_id)
    if saved_result and not st.session_state.get("student_diagnosis_active", False):
        st.info("你已经完成过一次首次诊断，下面展示的是当前保存的诊断结果。")
        _render_diagnosis_result(saved_result)
        if st.button("重新做一次首次诊断", key="restart_initial_diagnosis"):
            try:
                activate_initial_diagnosis(force_refresh=True)
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
                overview_definition = prepare_initial_diagnosis_definition(force_refresh=True)
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

        st.info("建议一次完成，中途也可以暂停；重新进入后会从头开始这一轮诊断。")
        if st.button("开始首次诊断", key="start_initial_diagnosis", type="primary"):
            if not bank_status.get("ready_for_diagnosis"):
                st.error("正式词汇诊断题库还没有准备好，当前不能开始首次诊断。")
                return
            try:
                activate_initial_diagnosis(force_refresh=True)
            except Exception as exc:
                st.error(f"首次诊断无法启动：{exc}")
                return
            st.rerun()
        return

    definition = st.session_state.get("student_diagnosis_definition")
    if not definition:
        try:
            definition = prepare_initial_diagnosis_definition(force_refresh=True)
        except Exception as exc:
            st.error(f"首次诊断题库加载失败，无法继续：{exc}")
            clear_diagnosis_session_state()
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
        clear_diagnosis_session_state()
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
        answers_by_module[module["key"]] = {**default_answers, **current_answers}
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
            save_initial_diagnosis_result(
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
        except Exception:
            st.error("诊断结果保存失败，请联系管理员检查 Supabase 配置。")
            return

        clear_diagnosis_session_state()
        st.session_state["student_diagnosis_flash"] = result
        st.rerun()
