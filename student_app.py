"""学生端入口（含词汇检测作答区）"""

import streamlit as st
import db_student as dbs

st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")
st.title("英语辅导系统｜学生端")
st.write("这里是学生使用的前台页面。")


def _student_options(students):
    return {f"{name}（{grade}）": sid for sid, name, grade in students}


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
        if st.button("查看完整学案", key=f"view_lesson_{lesson_id}"):
            st.session_state["selected_lesson_id"] = lesson_id

    selected_lesson_id = st.session_state.get("selected_lesson_id")
    if selected_lesson_id:
        detail = dbs.get_lesson_detail_for_student(student_id, selected_lesson_id)
        if detail:
            with st.expander("完整学案内容", expanded=True):
                st.text_area(
                    "lesson_content",
                    value=detail.get("content", ""),
                    height=500,
                    key=f"lesson_content_{selected_lesson_id}",
                )


def _render_learned_words(student_id: int):
    st.header("我的已学单词")
    rows = dbs.get_student_learned_vocab(student_id, limit=200)
    if not rows:
        st.info("你目前还没有已学习单词。")
        return

    for i, row in enumerate(rows, start=1):
        lemma, meaning, status, review_count, error_count, memory_score, *_ = row
        st.write(
            f"{i}. {lemma} - {meaning} | 状态：{status} | 复习次数：{review_count} | 错误次数：{error_count} | 记忆评分：{memory_score}"
        )


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
        with st.expander("查看本次检测明细", expanded=False):
            for idx, item in enumerate(item_rows, start=1):
                _vocab_item_id, word, meaning, mode, user_answer, is_correct = item
                result_text = "正确" if is_correct else "错误"
                st.write(
                    f"{idx}. [{mode}] {word} - {meaning} | 你的答案：{user_answer if user_answer else '（未作答）'} | 结果：{result_text}"
                )


def _render_vocab_test(student_id: int):
    st.header("我的词汇检测")
    mode_tab1, mode_tab2 = st.tabs(["学习进度检测", "词汇书抽词检测"])

    with mode_tab1:
        test_type = st.selectbox("检测类型", ["新词检测", "复习检测"], key="student_progress_test_type")
        test_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_progress_test_mode")
        test_count = st.selectbox("本次检测题数", [5, 10, 15, 20, 25], index=1, key="student_progress_test_count")

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

            units = dbs.get_units_by_book(selected_book_id)
            unit_options = {"整本词汇书": None}
            for unit_id, unit_name, _unit_order in units:
                unit_options[unit_name] = unit_id

            selected_unit_label = st.selectbox("选择单元", list(unit_options.keys()), key="student_book_test_unit")
            selected_unit_id = unit_options[selected_unit_label]
            test_mode = st.selectbox("作答方式", ["英译中", "中译英", "混合模式"], key="student_book_test_mode")
            test_count = st.selectbox("本次检测题数", [5, 10, 15, 20, 25], index=1, key="student_book_test_count")

            if st.button("开始词汇书抽词检测", key="start_student_book_test"):
                ok, payload = dbs.build_book_test(student_id, selected_book_id, selected_unit_id, test_mode, test_count)
                if ok:
                    st.session_state["student_test_payload"] = payload
                    scope = selected_unit_label if selected_unit_label else "整本词汇书"
                    st.session_state["student_test_source_label"] = f"词汇书抽词检测：{selected_book_label} / {scope}"
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
        return

    st.markdown("---")
    st.subheader("开始作答")
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

    if st.button("提交检测", key="submit_student_test"):
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
    st.info("当前版本先用“选择学生”模拟登录。后面再升级成学生账号 / 邀请码登录。")
    students = dbs.get_all_students()
    if not students:
        st.warning("当前还没有学生。")
        return

    options = _student_options(students)
    selected_label = st.selectbox("请选择你的身份", list(options.keys()))
    student_id = options[selected_label]
    name = selected_label.split("（")[0]
    st.header(f"欢迎，{name}")

    _render_lessons(student_id)
    st.markdown("---")
    _render_learned_words(student_id)
    st.markdown("---")
    _render_progress(student_id)
    st.markdown("---")
    _render_vocab_test(student_id)
    st.markdown("---")
    _render_test_history(student_id)


if __name__ == "__main__":
    main()
