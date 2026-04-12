"""学生前台入口（最小可用版）。

这个文件的目标不是一次做完完整产品，
而是先把“学生能看到的页面”和“管理员后台”分开。

当前提供：
1. 查看最近学案
2. 查看完整学案
3. 查看已学单词
4. 查看学习进度
5. 查看词汇检测记录

注意：
- 这还是 MVP
- 现在先用“选择学生”模拟登录
- 后面再升级成学生账号 / 口令 / 邀请码
"""

import streamlit as st

import db_student as db


# ------------------------------
# 页面配置
# ------------------------------
st.set_page_config(page_title="英语辅导系统｜学生端", layout="wide")


def build_student_options(students):
    """
    把 students 查询结果转成：
    {显示标签: student_id}
    """
    return {f"{student[1]}（{student[2]}）": student[0] for student in students}


def render_recent_lessons(student_id: int):
    """
    渲染最近学案，并支持查看完整学案内容。
    """
    st.markdown("## 我的最近学案")

    recent_lessons = db.get_recent_lessons_by_student(student_id, limit=5)
    if not recent_lessons:
        st.info("你目前还没有学案记录。")
        return

    selected_lesson_id = st.session_state.get("student_selected_lesson_id")

    for lesson_id, lesson_type, difficulty, topic, created_at in recent_lessons:
        with st.container():
            st.markdown(f"### 学案 ID：{lesson_id}")
            st.write(f"题型：{lesson_type}")
            st.write(f"难度：{difficulty}")
            st.write(f"主题：{topic}")
            st.write(f"创建时间：{created_at}")

            action_col1, action_col2 = st.columns([1, 5])

            with action_col1:
                if st.button("查看完整学案", key=f"view_lesson_{lesson_id}"):
                    st.session_state["student_selected_lesson_id"] = lesson_id
                    st.rerun()

            with action_col2:
                if selected_lesson_id == lesson_id:
                    if st.button("收起当前学案", key=f"hide_lesson_{lesson_id}"):
                        st.session_state["student_selected_lesson_id"] = None
                        st.rerun()

            if selected_lesson_id == lesson_id:
                lesson_detail = db.get_lesson_detail_for_student(student_id, lesson_id)

                if not lesson_detail:
                    st.warning("没有读取到这份学案的完整内容。")
                else:
                    (
                        _lesson_id,
                        lesson_type,
                        difficulty,
                        topic,
                        content,
                        created_at,
                    ) = lesson_detail

                    with st.expander("完整学案内容", expanded=True):
                        st.write(f"题型：{lesson_type}")
                        st.write(f"难度：{difficulty}")
                        st.write(f"主题：{topic}")
                        st.write(f"创建时间：{created_at}")
                        st.text_area(
                            "学案正文",
                            value=content or "",
                            height=520,
                            key=f"student_lesson_content_{lesson_id}",
                        )

            st.markdown("---")


def render_student_home(student_id: int, student_label: str):
    """
    学生前台首页内容。
    """
    st.subheader(f"欢迎，{student_label.split('（')[0]}")

    # ------------------------------
    # 1. 最近学案
    # ------------------------------
    render_recent_lessons(student_id)

    # ------------------------------
    # 2. 已学习单词
    # ------------------------------
    st.markdown("## 我的已学单词")

    learned_words = db.get_student_learned_vocab(student_id)
    if not learned_words:
        st.info("你目前还没有已学习单词。")
    else:
        show_count = st.selectbox(
            "显示多少个已学单词",
            [20, 50, 100],
            index=0,
            key="student_learned_word_count"
        )

        for i, row in enumerate(learned_words[:show_count], start=1):
            (
                lemma,
                meaning,
                status,
                review_count,
                error_count,
                memory_score,
                _first_learned_at,
                _last_review_time,
                _next_review_time,
            ) = row

            st.write(
                f"{i}. {lemma} - {meaning} | 状态：{status} | "
                f"复习次数：{review_count} | 错误次数：{error_count} | 记忆评分：{memory_score}"
            )

    # ------------------------------
    # 3. 词汇书学习进度
    # ------------------------------
    st.markdown("## 我的学习进度")

    book_progress = db.get_student_book_progress(student_id)
    if not book_progress:
        st.info("你目前还没有词汇学习进度。")
    else:
        for row in book_progress:
            (
                book_id,
                book_name,
                volume_name,
                learned_count,
                total_count,
                mastered_count,
                learning_count,
                review_count,
            ) = row

            label = f"{book_name}" if not volume_name else f"{book_name}（{volume_name}）"
            ratio = learned_count / total_count if total_count > 0 else 0

            st.markdown(f"### {label}")
            st.write(f"已学：{learned_count} / {total_count}")
            st.progress(ratio)
            st.write(
                f"状态分布：mastered {mastered_count} | learning {learning_count} | review {review_count}"
            )

            unit_progress = db.get_student_unit_progress(student_id, book_id)
            if unit_progress:
                with st.expander("查看单元进度", expanded=False):
                    for unit_row in unit_progress:
                        _, unit_name, _unit_order, unit_learned_count, unit_total_count = unit_row
                        unit_ratio = unit_learned_count / unit_total_count if unit_total_count > 0 else 0
                        st.write(f"{unit_name}：{unit_learned_count} / {unit_total_count}")
                        st.progress(unit_ratio)

            st.markdown("---")

    # ------------------------------
    # 4. 词汇检测记录
    # ------------------------------
    st.markdown("## 我的检测记录")

    test_records = db.get_student_vocab_test_records(student_id, limit=10)
    if not test_records:
        st.info("你目前还没有词汇检测记录。")
    else:
        for row in test_records:
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
            sync_tag = "已同步学习进度" if is_synced_to_progress else "仅记录未同步"

            with st.expander(
                f"{created_at} | {test_type} | {correct_count}/{total_count} | {accuracy:.0%}{retry_tag}",
                expanded=False,
            ):
                st.write(f"来源：{source_label}")
                st.write(f"作答方式：{test_mode}")
                st.write(f"同步状态：{sync_tag}")

                items = db.get_vocab_test_record_items(test_record_id)
                if items:
                    st.markdown("### 本轮明细")
                    for i, item in enumerate(items, start=1):
                        (
                            _vocab_item_id,
                            word,
                            meaning,
                            mode,
                            user_answer,
                            is_correct,
                        ) = item

                        result_text = "正确" if is_correct else "错误"
                        standard_answer = meaning if mode == "英译中" else word

                        st.write(
                            f"{i}. {word} | 模式：{mode} | 你的答案：{user_answer or '（未作答）'} | "
                            f"正确答案：{standard_answer} | 结果：{result_text}"
                        )


def main():
    st.title("英语辅导系统｜学生端")
    st.write("这里是学生使用的前台页面。")

    students = db.get_all_students()
    if not students:
        st.warning("当前还没有可用学生数据。")
        return

    st.info("当前版本先用“选择学生”模拟登录。后面再升级成学生账号 / 邀请码登录。")

    student_options = build_student_options(students)
    selected_student_label = st.selectbox(
        "请选择你的身份",
        list(student_options.keys()),
        key="student_front_select"
    )
    selected_student_id = student_options[selected_student_label]

    render_student_home(selected_student_id, selected_student_label)


if __name__ == "__main__":
    main()
