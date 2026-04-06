# db/supabase_client.py
# ──────────────────────────────────────────────────────────────
#  Singleton Supabase client — cached per Streamlit session.
# ──────────────────────────────────────────────────────────────

import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)
