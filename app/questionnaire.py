"""Streamlit entry for the client studio and the archived section 13 research walkthrough."""

import logging
import runpy
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import declare_component

from riskmatch_v2.studio import WEB, dispatch

if st.query_params.get("view") == "research":
    runpy.run_path(
        str(Path(__file__).with_name("research_journey.py")), run_name="__main__"
    )
else:
    st.set_page_config(
        page_title="RiskMatch",
        page_icon="🍒",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.html("""<style>header[data-testid="stHeader"],[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],footer {display:none!important}
    .stApp,[data-testid="stMain"]{background:#120e23;padding:0!important}
    [data-testid="stMainBlockContainer"]{max-width:none;padding:0!important;margin:0!important}
    [data-testid="stVerticalBlock"]{gap:0!important}
    [data-testid="stElementContainer"]:has(style):not(:has(iframe)){height:0;overflow:hidden}
    iframe[title*="client_studio"]{border:0;width:100%;height:100dvh!important;display:block}</style>""")
    studio = declare_component("client_studio", path=str(WEB))
    reply = st.session_state.get("studio_reply")
    event = studio(reply=reply, key="studio_client", default=None)
    if (
        isinstance(event, dict)
        and event.get("id")
        and (not reply or reply["id"] != event["id"])
    ):
        try:
            result = {
                "ok": True,
                "result": dispatch(event["action"], event.get("data", {})),
            }
        except (ValueError, TypeError, KeyError) as exc:
            result = {"ok": False, "error": str(exc)}
        except Exception:
            logging.getLogger(__name__).exception("Studio operation failed")
            result = {
                "ok": False,
                "error": "The simulation could not complete this request.",
            }
        st.session_state.studio_reply = result | {"id": event["id"]}
        st.rerun()
