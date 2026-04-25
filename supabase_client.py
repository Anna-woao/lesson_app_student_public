# supabase_client.py

import os
import streamlit as st
from supabase import create_client, Client


def _read_secret_value(name: str) -> str:
    try:
        secrets_dict = dict(st.secrets)
    except Exception:
        secrets_dict = {}
    return (secrets_dict.get(name) or os.getenv(name) or "").strip()


def has_admin_supabase_client() -> bool:
    return bool(_read_secret_value("SUPABASE_URL") and _read_secret_value("SUPABASE_SERVICE_ROLE_KEY"))


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    url = _read_secret_value("SUPABASE_URL")
    key = _read_secret_value("SUPABASE_PUBLISHABLE_KEY")

    if not url:
        raise RuntimeError("缺少 SUPABASE_URL。请检查 .streamlit/secrets.toml 或 Streamlit Cloud Secrets。")

    if not key:
        raise RuntimeError("缺少 SUPABASE_PUBLISHABLE_KEY。请检查 .streamlit/secrets.toml 或 Streamlit Cloud Secrets。")

    return create_client(url, key)


@st.cache_resource(show_spinner=False)
def get_admin_supabase_client() -> Client | None:
    url = _read_secret_value("SUPABASE_URL")
    key = _read_secret_value("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)
