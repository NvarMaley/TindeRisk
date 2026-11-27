"""Streamlit entry point that displays the original RiskMatch web application."""
import os
from urllib.parse import urlsplit

import streamlit as st

st.set_page_config(page_title="RiskMatch", page_icon="🍒", layout="wide")

url = os.environ.get("RISKMATCH_APP_URL", "http://127.0.0.1:3000/").strip()
parsed = urlsplit(url)
local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
valid_origin = (parsed.hostname and parsed.username is None and parsed.password is None
                and (local_http or parsed.scheme == "https"))
if url != "/riskmatch/" and not valid_origin:
    st.error("L’adresse RiskMatch doit être une URL HTTPS, une adresse HTTP locale ou le chemin /riskmatch/.")
    st.stop()

st.html("""
<style>
[data-testid="stMainBlockContainer"] { padding: 0; max-width: none; }
[data-testid="stHeader"] { display: none; }
[data-testid="stMainBlockContainer"] iframe { height: 100dvh !important; display: block; }
</style>
""")
st.iframe(url, height=850, alt="Interface originale de RiskMatch")
