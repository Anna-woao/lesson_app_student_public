# supabase_client.py

import os
import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    try:
        secrets_dict = dict(st.secrets)
    except Exception:
        secrets_dict = {}

    url = (secrets_dict.get("SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").strip()
    key = (secrets_dict.get("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY") or "").strip()

    if not url:
        raise RuntimeError("缺少 SUPABASE_URL。请检查 .streamlit/secrets.toml 或 Streamlit Cloud Secrets。")

    if not key:
        raise RuntimeError("缺少 SUPABASE_PUBLISHABLE_KEY。请检查 .streamlit/secrets.toml 或 Streamlit Cloud Secrets。")

    return create_client(url, key)