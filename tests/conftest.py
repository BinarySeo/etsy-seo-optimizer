import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def no_api_keys(monkeypatch):
    """Tests never call real APIs."""
    for var in ("OPENAI_API_KEY", "GA4_PROPERTY_ID", "ETSY_API_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def listings():
    """Build a small listings DataFrame from a list of tag strings."""
    def make(tag_strings, query="q", category="birthday"):
        return pd.DataFrame({
            "title": [f"Card {i}" for i in range(len(tag_strings))],
            "tags": tag_strings,
            "query": query,
            "category": category,
        })
    return make
