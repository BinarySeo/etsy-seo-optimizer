import pytest

from analysis.keyword_analysis import load_latest_data, seo_gap_analysis, tag_frequency, tfidf_keywords
from database.db import EtsyDB
from scraper.mock_data import generate_weekly_data


def test_tag_frequency_top_n(listings):
    freq = tag_frequency(listings(["a, b", "a", "c"]), top_n=1)
    assert freq["tag"].tolist() == ["a"]


def test_tfidf_needs_two_titles(listings):
    assert tfidf_keywords(listings(["a"])).empty


def test_tfidf_returns_ranked_keywords(listings):
    df = listings(["a"] * 4)
    df["title"] = ["funny birthday card", "funny birthday card", "floral card", "floral card"]
    result = tfidf_keywords(df, top_n=20)
    assert {"funny birthday", "floral card"} <= set(result["keyword"])
    assert result["tfidf_score"].is_monotonic_decreasing


def test_seo_gap_marks_missing_tags(listings):
    gap = seo_gap_analysis(listings(["a, b", "a"]), your_tags=["A"]).set_index("tag")
    assert gap.loc["a", "status"] == "already using"
    assert gap.loc["b", "status"].startswith("missing")


def test_load_latest_data_reads_newest_run_from_sqlite(tmp_path):
    db_path = str(tmp_path / "etsy.db")
    with EtsyDB(db_path) as db:
        db.insert_listings(generate_weekly_data(0, num_listings=30, seed=1), run_date="2026-01-01")
        db.insert_listings(generate_weekly_data(1, num_listings=60, seed=1), run_date="2026-01-08")
    df = load_latest_data(data_dir=str(tmp_path / "raw"), db_path=db_path)
    assert len(df) == 60
    assert set(df["run_date"]) == {"2026-01-08"}


def test_load_latest_data_explains_missing_data(tmp_path):
    with pytest.raises(FileNotFoundError, match="mock_data"):
        load_latest_data(data_dir=str(tmp_path / "raw"), db_path=str(tmp_path / "none.db"))
