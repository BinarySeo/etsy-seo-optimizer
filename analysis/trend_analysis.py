"""
trend_analysis.py
-----------------
Weekly trend comparison using data stored in SQLite.
Compares tag frequency across runs to surface rising/falling keywords.

Usage:
    python -m analysis.trend_analysis
"""

import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from collections import Counter


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_tag_frequency(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """Count tag frequency for a given DataFrame (one week's data)."""
    all_tags = []
    for tags_str in df["tags"].dropna():
        tags = [t.strip().lower() for t in tags_str.split(",")]
        all_tags.extend(tags)

    counts = Counter(all_tags)
    freq_df = pd.DataFrame(counts.most_common(top_n), columns=["tag", "count"])
    freq_df["pct"] = (freq_df["count"] / len(df) * 100).round(1)
    return freq_df


def compare_weeks(df_this: pd.DataFrame, df_last: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """
    Compare tag frequency between two weeks.
    Returns a DataFrame with rise/fall delta for each tag.
    """
    freq_this = get_tag_frequency(df_this, top_n=50)
    freq_last = get_tag_frequency(df_last, top_n=50)

    # Merge on tag
    merged = freq_this.merge(
        freq_last[["tag", "count"]],
        on="tag",
        how="outer",
        suffixes=("_this", "_last")
    ).fillna(0)

    merged["count_this"] = merged["count_this"].astype(int)
    merged["count_last"] = merged["count_last"].astype(int)
    merged["delta"] = merged["count_this"] - merged["count_last"]
    merged["trend"] = merged["delta"].apply(
        lambda x: "🔥 rising" if x > 5 else ("📉 falling" if x < -5 else "➡️ stable")
    )

    return merged.sort_values("count_this", ascending=False).head(top_n).reset_index(drop=True)


def get_new_tags(df_this: pd.DataFrame, df_last: pd.DataFrame) -> list:
    """Tags that appear this week but not last week — brand new trends."""
    tags_this = set()
    tags_last = set()

    for tags_str in df_this["tags"].dropna():
        tags_this.update([t.strip().lower() for t in tags_str.split(",")])

    for tags_str in df_last["tags"].dropna():
        tags_last.update([t.strip().lower() for t in tags_str.split(",")])

    return sorted(tags_this - tags_last)


def get_trending_summary(db: EtsyDB) -> dict:
    """
    Full trend summary comparing latest two runs.
    Returns dict with all analysis results.
    """
    run_dates = db.get_run_dates()

    if len(run_dates) < 2:
        print("[WARN] Need at least 2 runs for trend analysis.")
        return {}

    latest = run_dates[0]
    previous = run_dates[1]

    print(f"[INFO] Comparing {latest} vs {previous}")

    df_this = db.get_listings(run_date=latest)
    df_last = db.get_listings(run_date=previous)

    comparison = compare_weeks(df_this, df_last)
    new_tags = get_new_tags(df_this, df_last)
    rising = comparison[comparison["trend"] == "🔥 rising"].head(10)
    falling = comparison[comparison["trend"] == "📉 falling"].head(10)

    return {
        "latest_run":   latest,
        "previous_run": previous,
        "comparison":   comparison,
        "new_tags":     new_tags,
        "rising":       rising,
        "falling":      falling,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = EtsyDB()
    summary = get_trending_summary(db)

    if summary:
        print(f"\n📅 Comparing: {summary['latest_run']} vs {summary['previous_run']}")

        print("\n🔥 Rising tags:")
        print(summary["rising"][["tag", "count_this", "count_last", "delta"]].to_string(index=False))

        print("\n📉 Falling tags:")
        print(summary["falling"][["tag", "count_this", "count_last", "delta"]].to_string(index=False))

        print("\n✨ Brand new tags this week:")
        print(summary["new_tags"])

    db.close()
    print("\n[DONE]")