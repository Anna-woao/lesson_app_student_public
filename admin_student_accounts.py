"""管理员后台：学生账号管理 + 通用词汇导入。"""

from __future__ import annotations

import os

import streamlit as st

import db_student as dbs
import vocab_import_service as vis
from supabase_client import has_admin_supabase_client


ROLE_LABELS = {
    "ignore": "忽略",
    "book_name": "书名/教材",
    "volume_name": "册次",
    "unit": "单元",
    "term": "单词/短语",
    "meaning": "释义",
    "ipa": "IPA",
    "pos": "词性",
    "note": "备注",
}


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
        st.error("请先配置 ADMIN_PASSWORD，再打开管理员后台。")
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


def _require_admin_data_access() -> bool:
    if has_admin_supabase_client():
        return True
    st.error("当前管理员后台缺少 SUPABASE_SERVICE_ROLE_KEY，已拒绝加载账号管理和词汇导入。")
    st.caption("请先在 Streamlit Secrets 或环境变量中配置 SUPABASE_SERVICE_ROLE_KEY。")
    return False


def _render_accounts():
    if not _require_admin_data_access():
        return
    try:
        rows = dbs.get_student_login_accounts()
    except Exception as e:
        st.error("无法读取学生账号信息。")
        st.exception(e)
        return

    if not rows:
        st.info("当前还没有学生。")
        return

    st.caption("管理员可以修改账号、重置密码，旧密码不会在这里显示。")

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
            submitted = st.form_submit_button("保存")

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


def _template_select_options():
    templates = vis.list_import_templates()
    options = ["（不使用模板）"] + [item["name"] for item in templates]
    return options, {item["name"]: item for item in templates}


def _default_mapping(headers, guessed):
    mapping = {}
    for header in headers:
        mapping[header] = guessed.get(header, "ignore")
    return mapping


def _render_mapping_editor(headers, current_mapping):
    st.markdown("### 列映射")
    updated_mapping = {}
    for header in headers:
        current_role = current_mapping.get(header, "ignore")
        role = st.selectbox(
            f"列 {header}",
            options=vis.COLUMN_ROLES,
            index=vis.COLUMN_ROLES.index(current_role) if current_role in vis.COLUMN_ROLES else 0,
            format_func=lambda item: ROLE_LABELS.get(item, item),
            key=f"mapping_{header}",
        )
        updated_mapping[header] = role
    return updated_mapping


def _render_preview_table(headers, rows, limit=15):
    st.markdown("### 预览")
    if not rows:
        st.info("没有可预览的数据。")
        return
    for idx, row in enumerate(rows[:limit], start=1):
        values = [f"{headers[col_idx]}={row[col_idx]}" for col_idx in range(min(len(headers), len(row)))]
        st.write(f"{idx}. " + " | ".join(values))


def _render_template_management(selected_template_name, mapping, active_sheet, data_start_row):
    st.markdown("### 模板")
    save_name = st.text_input("模板名称", value="" if selected_template_name == "（不使用模板）" else selected_template_name)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存模板", use_container_width=True):
            if not save_name.strip():
                st.warning("请先输入模板名称。")
            else:
                vis.save_import_template(
                    save_name.strip(),
                    {
                        "mapping": mapping,
                        "sheet_name": active_sheet,
                        "data_start_row": data_start_row,
                    },
                )
                st.success("模板已保存。")
                st.rerun()
    with col2:
        if selected_template_name != "（不使用模板）" and st.button("删除模板", use_container_width=True):
            vis.delete_import_template(selected_template_name)
            st.success("模板已删除。")
            st.rerun()


def _render_vocab_import():
    if not _require_admin_data_access():
        return
    st.subheader("通用词汇导入")
    st.caption("上传任意 Excel，确认一次列映射后就可以保存成模板，后面同类表格直接复用。")

    uploaded_file = st.file_uploader("上传 Excel（.xlsx）", type=["xlsx"], key="generic_vocab_excel")
    if not uploaded_file:
        st.info("请先上传一个 Excel 文件。")
        return

    file_bytes = uploaded_file.getvalue()
    preview = vis.preview_excel(file_bytes)

    template_options, template_lookup = _template_select_options()
    selected_template_name = st.selectbox("导入模板", options=template_options)
    guessed_mapping = vis.guess_mapping(file_bytes, sheet_name=preview["active_sheet"])
    mapping = _default_mapping(preview["headers"], guessed_mapping)
    data_start_row_default = 1

    if selected_template_name != "（不使用模板）":
        template = template_lookup[selected_template_name]
        mapping.update(template.get("mapping", {}))
        data_start_row_default = int(template.get("data_start_row", 1) or 1)

    st.write(f"工作表：{preview['active_sheet']}")
    st.write(f"总行数：{preview['row_count']}")
    st.write(f"总列数：{preview['column_count']}")

    data_start_row = st.number_input("数据起始行", min_value=1, value=data_start_row_default, step=1)
    _render_preview_table(preview["headers"], preview["preview_rows"])
    mapping = _render_mapping_editor(preview["headers"], mapping)
    _render_template_management(selected_template_name, mapping, preview["active_sheet"], int(data_start_row))

    parsed = vis.parse_generic_vocab_excel(
        file_bytes,
        mapping,
        sheet_name=preview["active_sheet"],
        data_start_row=int(data_start_row),
        source_name=uploaded_file.name,
    )

    st.markdown("### 解析结果")
    st.write(f"识别到的词汇行数：{parsed['row_count']}")
    if parsed["errors"]:
        with st.expander("提示与警告", expanded=False):
            for item in parsed["errors"][:50]:
                st.write(f"- {item}")

    for idx, row in enumerate(parsed["rows"][:20], start=1):
        st.write(
            f"{idx}. {row['book_name']} / {row['volume_name']} / {row['unit_name']} / "
            f"{row['surface_word']} / {row['meaning']} / {row['ipa']}"
        )

    if st.button("导入到词汇书", key="import_generic_vocab_excel", use_container_width=True):
        ok, message, result = vis.import_parsed_vocab_rows(parsed, source_name=uploaded_file.name)
        if ok:
            summary = result.get("summary", {})
            st.success(message)
            st.write(f"新增词汇书：{summary.get('created_books', 0)}")
            st.write(f"新增单元：{summary.get('created_units', 0)}")
            st.write(f"新增词条：{summary.get('created_vocab_items', 0)}")
            st.write(f"更新已有词条：{summary.get('updated_vocab_items', 0)}")
            st.write(f"新增词条-单元映射：{summary.get('created_links', 0)}")
        else:
            st.error(message)


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

    tab1, tab2 = st.tabs(["学生账号", "词汇导入"])
    with tab1:
        _render_accounts()
    with tab2:
        _render_vocab_import()


if __name__ == "__main__":
    main()
