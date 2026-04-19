"""管理员端：学生账号和密码重置。"""

import os

import streamlit as st

import db_student as dbs


st.set_page_config(page_title="学生账号管理", layout="wide")
st.title("学生账号管理")


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


def main():
    if not st.session_state.get("student_account_admin_ok"):
        _render_admin_login()
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("学生登录信息")
    with col2:
        if st.button("退出"):
            st.session_state.pop("student_account_admin_ok", None)
            st.rerun()

    _render_accounts()


if __name__ == "__main__":
    main()
