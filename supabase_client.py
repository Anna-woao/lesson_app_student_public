# supabase_client.py

import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    创建并返回 Supabase 客户端

    学生端当前使用：
    - SUPABASE_URL
    - SUPABASE_PUBLISHABLE_KEY

    注意：
    1. 这里不要写死 key
    2. 一律从 Streamlit secrets 读取
    """
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]

    return create_client(url, key)