"""管理员端：学生账号管理 + 结构化词汇书导入。"""

import os

import streamlit as st

import db_student as dbs


st.set_page_config(page_title="管理员后台", layout="wide")
st.title("管理员后台")


def _get_admin_password():
    try:
        secrets_dict = dict(st.secrets)
    except Exception:
        secrets_dict = {}
    return (secrets_dict.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or "").strip()


def _render_admin_login():
    configured_password = _get_admin_password()
    if not configured_password:
        st.error("请先配置 ADMIN_PASSWORD，再打开管理员端。")
        return False

    with st.form("admin_login_form"):
        password = st.text_input("管理员密码", type="password")
        submitted = st.form_submit_button("进入")

    if not submitted:
        return False

    if password.strip() != configured_password:
        st.error("管理员密码不正确。")
        return False

    st.session_state["student_account_admin_ok"] = True
    st.rerun()


def _render_accounts():
    try:
        rows = dbs.get_student_login_accounts()
    except Exception as e:
        st.error("无法读取学生账号信息，请确认 Supabase 的 students 表已经包含登录字段。")
        st.exception(e)
        return

    if not rows:
        st.info("当前还没有学生。")
        return

    st.caption("管理员可以修改账号、重置密码；旧密码不会在这里显示。")

    for student_id, name, grade, login_account, has_password in rows:
        st.markdown(f"### {name}（{grade}）")
        st.write(f"学生 ID：{student_id}")
        st.write("密码状态：已设置" if has_password else "密码状态：未设置")

        with st.form(f"student_login_{student_id}"):
            new_account = st.text_input("账号", value=login_account, key=f"account_{student_id}")
            new_password = st.text_input(
                "新密码（留空表示不修改密码）",
                type="password",
                key=f"password_{student_id}",
            )
            submitted = st.form_submit_button("保存修改")

        if submitted:
            if not has_password and not new_password.strip():
                st.warning("这个学生还没有密码，请先设置一个新密码。")
                st.markdown("---")
                continue

            ok, message = dbs.update_student_login_account(student_id, new_account, new_password)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)

        st.markdown("---")


def _render_vocab_import():
    st.subheader("导入词汇书")
    st.caption("支持你现在这种结构化 Excel：教材版本 / 册次 / 单元 / 单词或短语 / 释义 / 音标。")

    uploaded_file = st.file_uploader(
        "上传词汇书 Excel",
        type=["xlsx"],
        key="structured_vocab_excel",
    )
    if not uploaded_file:
        st.info("请选择一个 .xlsx 文件开始导入。")
        return

    file_bytes = uploaded_file.getvalue()
    parsed = dbs.parse_structured_vocab_excel(file_bytes, source_name=uploaded_file.name)

    st.write(f"工作表：{parsed['sheet_name']}")
    st.write(f"识别到词汇行数：{parsed['row_count']}")

    if parsed["errors"]:
        with st.expander("跳过行提示", expanded=False):
            for message in parsed["errors"][:50]:
                st.write(f"- {message}")

    preview_rows = parsed["rows"][:20]
    if preview_rows:
        st.markdown("### 预览前 20 行")
        for idx, row in enumerate(preview_rows, start=1):
            st.write(
                f"{idx}. {row['book_name']} / {row['volume_name']} / {row['unit_name']} / "
                f"{row['surface_word']} / {row['meaning']} / {row['ipa']}"
            )

    if st.button("开始导入词汇书", key="import_structured_vocab_excel", use_container_width=True):
        ok, message, result = dbs.import_structured_vocab_excel(file_bytes, source_name=uploaded_file.name)
        if ok:
            st.success(message)
            summary = result.get("summary", {})
            st.write(f"新增词汇书：{summary.get('created_books', 0)}")
            st.write(f"新增单元：{summary.get('created_units', 0)}")
            st.write(f"新增词条：{summary.get('created_vocab_items', 0)}")
            st.write(f"更新已有词条：{summary.get('updated_vocab_items', 0)}")
            st.write(f"新增词条-单元映射：{summary.get('created_links', 0)}")
        else:
            st.error(message)
            if result and result.get("errors"):
                st.write("导入过程中发现的问题：")
                for item in result["errors"][:50]:
                    st.write(f"- {item}")


def main():
    if not st.session_state.get("student_account_admin_ok"):
        _render_admin_login()
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("管理功能")
    with col2:
        if st.button("退出"):
            st.session_state.pop("student_account_admin_ok", None)
            st.rerun()

    tab1, tab2 = st.tabs(["学生账号", "词汇书导入"])
    with tab1:
        _render_accounts()
    with tab2:
        _render_vocab_import()


if __name__ == "__main__":
    main()
