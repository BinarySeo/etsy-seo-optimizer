"""Smoke test: every dashboard page renders with mock data and no API keys."""
import os

import pytest
from streamlit.testing.v1 import AppTest

from database.db import EtsyDB
from scraper.mock_data import generate_weekly_data

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "app.py")


@pytest.fixture
def mock_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the app reads data/ relative to the working directory
    with EtsyDB("data/etsy.db") as db:
        for week, run_date in enumerate(["2026-01-01", "2026-01-08", "2026-01-15"]):
            db.insert_listings(generate_weekly_data(week, num_listings=90, seed=3), run_date=run_date)
    return tmp_path


def test_every_page_renders_without_keys(mock_workspace):
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception

    pages = at.sidebar.radio[0].options
    assert len(pages) == 5
    for page in pages:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, f"{page}: {at.exception[0].message}"
        assert not at.error, f"{page}: {at.error[0].value}"
