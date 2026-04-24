"""学生端入口（含词汇检测作答区）"""

from html import escape
import re
import streamlit as st
import streamlit.components.v1 as components
import db_student as dbs
from lesson_html_renderer import build_downloadable_lesson_html, parse_lesson_text_to_parts

st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")
st.title("英语辅导系统｜学生端")
st.write("这里是学生使用的前台页面。")

def _render_test_feedback_blocks(results):
    """
    用更清楚的两个区块展示本次检测反馈。

    展示结构：
    1. 本次考察单词清单
       - 只显示：序号 + 单词
       - 不在这里堆太多判题信息，保证一眼能看清本轮考了什么

    2. 错词订正区
       - 只显示答错的词
       - 错词本身用红色加粗突出
       - 同时给出：你的答案 / 正确答案 / 标准词义
    """
    if not results:
        st.info("当前没有可展示的检测反馈。")
        return

    # ------------------------------
    # 区块 1：本次考察单词清单
    # ------------------------------
    st.markdown("### 本次考察单词清单")
    for idx, item in enumerate(results, start=1):
        st.write(f"{idx}. {item.get('word', '')}")

    st.markdown("---")

    # ------------------------------
    # 区块 2：错词订正区
    # ------------------------------
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

        # 根据题型决定“正确答案”展示什么
        # 英译中：正确答案应是中文释义
        # 中译英：正确答案应是英文单词
        if mode == "英译中":
            correct_answer = meaning
        else:
            correct_answer = word

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
            ]:
                st.session_state.pop(key, None)
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
    st.header("我的最近学案")
    lessons = dbs.get_student_recent_lessons(student_id, limit=10)
    if not lessons:
        st.info("你目前还没有学案记录。")
        return

    for lesson_id, lesson_type, difficulty, topic, created_at in lessons:
        st.markdown(f"### 学案 ID：{lesson_id}")
        st.write(f"题型：{lesson_type}")
        st.write(f"难度：{difficulty}")
        st.write(f"主题：{topic}")
        st.write(f"创建时间：{created_at}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("查看完整学案", key=f"view_lesson_{lesson_id}"):
                _show_lesson_detail_dialog(student_id, lesson_id)
        with col2:
            if st.button("查看本次学案新词表", key=f"view_lesson_vocab_{lesson_id}"):
                _show_lesson_vocab_dialog(student_id, lesson_id)


def _render_learned_words(student_id: int):
    st.header("我的已学单词")
    summary = dbs.get_student_learned_vocab_summary(student_id)
    total_unique_words = summary.get("total_unique_words", 0)
    lesson_groups = summary.get("lesson_groups", [])

    if total_unique_words == 0:
        st.info("你目前还没有已学习单词。")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("已学单词总数", total_unique_words)
    with col2:
        st.caption(f"共关联 {len(lesson_groups)} 份学案。")
        st.write("主页面先只显示摘要，详细单词列表放到弹窗里查看。")

    if st.button("查看按学案分类的已学单词", key="view_learned_words_dialog"):
        _show_learned_words_dialog(student_id)


def _render_progress(student_id: int):
    st.header("我的学习进度")
    progress_rows = dbs.get_student_book_progress(student_id)
    if not progress_rows:
        st.info("你目前还没有学习进度。")
        return

    for row in progress_rows:
        book_id, book_name, volume_name, learned_count, total_count, mastered_count, learning_count, review_count = row
        label = book_name if not volume_name else f"{book_name}（{volume_name}）"
        st.subheader(label)
        st.write(f"已学：{learned_count} / {total_count}")
        ratio = (learned_count / total_count) if total_count else 0
        st.progress(ratio)
        st.write(f"状态分布：mastered {mastered_count} | learning {learning_count} | review {review_count}")

        with st.expander("查看单元进度", expanded=False):
            unit_rows = dbs.get_student_unit_progress(student_id, book_id)
            for _, unit_name, _unit_order, unit_learned, unit_total in unit_rows:
                st.write(f"{unit_name}：{unit_learned} / {unit_total}")
                st.progress((unit_learned / unit_total) if unit_total else 0)


def _render_test_history(student_id: int):
    st.header("我的检测记录")
    rows = dbs.get_student_vocab_test_records(student_id, limit=20)
    if not rows:
        st.info("你目前还没有词汇检测记录。")
        return

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
        st.markdown(f"### 检测记录 ID：{test_record_id}{retry_tag}")
        st.write(f"来源：{source_label}")
        st.write(f"检测类型：{test_type}")
        st.write(f"作答方式：{test_mode}")
        st.write(f"得分：{correct_count} / {total_count}（正确率：{accuracy:.0%}）")
        st.write(f"记录时间：{created_at}")
        st.write(f"同步状态：{sync_tag}")

        item_rows = dbs.get_vocab_test_record_items(test_record_id)

        with st.expander("查看本次检测反馈", expanded=False):
            # 把数据库返回的元组列表，转成和即时反馈区一致的字典格式
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
    st.header("我的词汇检测")
    mode_tab1, mode_tab2 = st.tabs(["学习进度检测", "词汇书抽词检测"])

    with mode_tab1:
        test_type = st.selectbox("检测类型", ["新词检测", "复习检测"], key="student_progress_test_type")
        test_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_progress_test_mode")
        test_count = st.selectbox("本次检测题数", [15, 25, 35, 45, 60], index=1, key="student_progress_test_count")

        if st.button("开始学习进度检测", key="start_student_progress_test"):
            ok, payload = dbs.build_progress_test(student_id, test_type, test_mode, test_count)
            if ok:
                st.session_state["student_test_payload"] = payload
                st.session_state["student_test_source_label"] = f"学习进度检测：{test_type}"
                st.success("已开始学习进度检测。")
                st.rerun()
            else:
                st.warning(payload)

    with mode_tab2:
        books = dbs.get_all_word_books()
        if not books:
            st.info("当前还没有词汇书。")
        else:
            book_options = {label: book_id for book_id, label in books}
            selected_book_label = st.selectbox("选择词汇书", list(book_options.keys()), key="student_book_test_book")
            selected_book_id = book_options[selected_book_label]

            # ------------------------------
            # 单元多选区
            # 说明：
            # 1. 这里改成 multiselect，实现“可一次选择多个单元检测”
            # 2. 如果一个单元都不选，默认表示“整本词汇书”
            # 3. Streamlit 原生没有“下拉项前带 checkbox”的真正控件，
            #    multiselect 是当前最稳、最原生的多选方案
            # ------------------------------
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

            if st.button("开始词汇书抽词检测", key="start_student_book_test"):
                ok, payload = dbs.build_book_test(
                    student_id,
                    selected_book_id,
                    selected_unit_ids,
                    test_mode,
                    test_count,
                )

                if ok:
                    # 开始新一轮检测前，清掉上一轮结果，避免旧结果残留
                    st.session_state.pop("student_test_result", None)

                    st.session_state["student_test_payload"] = payload

                    scope = " / ".join(selected_unit_labels) if selected_unit_labels else "整本词汇书"
                    st.session_state["student_test_source_label"] = (
                        f"词汇书抽词检测：{selected_book_label} / {scope}"
                    )

                    st.success("已开始词汇书抽词检测。")
                    st.rerun()
                else:
                    st.warning(payload)

    payload = st.session_state.get("student_test_payload")
    if not payload:
        result = st.session_state.get("student_test_result")
        if result:
            st.markdown("---")
            st.subheader("本次检测结果")
            st.write(f"得分：{result['score']} / {result['total']}")
            st.write(f"正确率：{result['accuracy']:.0%}")

            # ------------------------------
            # 用新的清晰版反馈区替代旧的逐题流水账
            # ------------------------------
            _render_test_feedback_blocks(result.get("results", []))
        return

    st.markdown("---")
    st.subheader("开始作答")
    st.caption("请认真完成本次检测，填写完成后统一提交。")

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


def main():
    student = st.session_state.get("student_login")
    if not student:
        _render_login()
        return

    student_id = student["id"]
    _render_logged_in_header(student)

    _render_lessons(student_id)
    st.markdown("---")
    _render_learned_words(student_id)
    st.markdown("---")
    _render_progress(student_id)
    st.markdown("---")
    _render_vocab_test(student_id)
    st.markdown("---")
    _render_test_history(student_id)

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
