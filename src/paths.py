"""Paths shared by the notebook, scripts, and application."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_DATA = DATA / "raw"
PROCESSED_DATA = DATA / "processed"
RESULTS = ROOT / "results"
QUESTIONS = ROOT / "questions"

