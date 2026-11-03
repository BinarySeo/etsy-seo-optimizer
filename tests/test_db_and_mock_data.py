from analysis.tag_analysis import analyze_all_categories
from database.db import EtsyDB
from scraper.mock_data import QUERIES, generate_weekly_data


def test_rerunning_a_run_date_replaces_rather_than_duplicates(tmp_path):
    df = generate_weekly_data(0, num_listings=30, seed=1)
    with EtsyDB(str(tmp_path / "sub" / "etsy.db")) as db:   # folder is created
        db.insert_listings(df, run_date="2026-01-01")
        db.insert_listings(df, run_date="2026-01-01")
        assert len(db.get_listings("2026-01-01")) == 30
        assert db.get_run_dates() == ["2026-01-01"]


def test_mock_data_is_reproducible_with_seed():
    a = generate_weekly_data(1, num_listings=30, seed=7)
    b = generate_weekly_data(1, num_listings=30, seed=7)
    cols = ["title", "tags", "price_usd", "num_favorers"]
    assert a[cols].equals(b[cols])


def test_mock_data_has_categories_for_tag_analysis():
    df = generate_weekly_data(2, num_listings=90, seed=1)
    expected = {category for _, category in QUERIES}
    assert set(df["category"]) == expected
    patterns = analyze_all_categories(df)
    assert set(patterns) == expected
    assert all(p["total_listings"] == 30 for p in patterns.values())
