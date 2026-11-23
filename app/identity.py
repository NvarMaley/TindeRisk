"""Shared visual identity for the five-screen simulator."""

from pathlib import Path

import streamlit as st

NAMES = ["Profile", "Mandate", "Compare", "Portfolio", "Review"]
TITLES = {
    "Profile": ("Find your", "portfolio match."),
    "Mandate": ("Define your", "investment limits."),
    "Compare": ("Explore your", "portfolio matches."),
    "Portfolio": ("Follow your", "portfolio."),
    "Review": ("Review your", "next move."),
}


def hero(screen, day):
    css = (Path(__file__).parent / "identity.css").read_text()
    first, last = TITLES[screen]
    st.html(f"""<style>{css}</style>
    <header class="rm-banner">
      <div class="rm-copy"><div class="rm-wordmark">Risk<span>Match</span></div>
        <h1>{first}<br><em>{last}</em></h1>
        <p>CHF simulation <span aria-hidden="true">·</span> {day}</p>
      </div>
      <img class="rm-cherry" src="/app/static/cherry.webp" alt="">
    </header>""")
