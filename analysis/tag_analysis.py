"""
tag_analysis.py
---------------
Category-level tag pattern analysis.

For each card category, answers:
    - What tags do top competitors use most?
    - Which tags are essential (90%+), strong (50-90%), or differentiating (20-50%)?
    - What tags are we missing for each category?

Usage:
    python -m analysis.tag_analysis
"""

import pandas as pd
import sys
import os
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_tag_patterns(df: pd.DataFrame, category: str) -> dict:
    """
    Analyze tag patterns for a single category.

    Returns:
        essential      — tags used by 70%+ of listings
        strong         — tags used by 40-70%
        differentiating — tags used by 15-40%
        all_freq       — full frequency DataFrame
    """
    df_cat = df[df["category"] == category].copy()
    total = len(df_cat)

    if total == 0:
        return {}

    # Flatten all tags
    all_tags = []
    for tags_str in df_cat["tags"].dropna():
        tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
        all_tags.extend(tags)

    counts = Counter(all_tags)
    freq_df = pd.DataFrame(counts.most_common(30), columns=["tag", "count"])
    freq_df["pct"] = (freq_df["count"] / total * 100).round(1)

    return {
        "category":         category,
        "total_listings":   total,
        "essential":        freq_df[freq_df["pct"] >= 70]["tag"].tolist(),
        "strong":           freq_df[(freq_df["pct"] >= 40) & (freq_df["pct"] < 70)]["tag"].tolist(),
        "differentiating":  freq_df[(freq_df["pct"] >= 15) & (freq_df["pct"] < 40)]["tag"].tolist(),
        "all_freq":         freq_df,
    }


def analyze_all_categories(df: pd.DataFrame) -> dict:
    """
    Run tag pattern analysis for every category in the dataset.
    Returns dict keyed by category name.
    """
    categories = df["category"].dropna().unique()
    results = {}

    for category in sorted(categories):
        results[category] = get_tag_patterns(df, category)

    return results


def gap_analysis(patterns: dict, your_tags: list) -> pd.DataFrame:
    """
    Compare your current tags against essential + strong tags
    across all categories. Shows what you're missing.

    Args:
        patterns   — output of analyze_all_categories()
        your_tags  — your current Etsy listing tags (lowercase)
    """
    your_tags_lower = [t.strip().lower() for t in your_tags]
    rows = []

    for category, data in patterns.items():
        if not data:
            continue
        for tag in data.get("essential", []) + data.get("strong", []):
            rows.append({
                "category": category,
                "tag":      tag,
                "strength": "essential" if tag in data.get("essential", []) else "strong",
                "status":   "✅ using" if tag in your_tags_lower else "❌ missing",
            })

    return pd.DataFrame(rows)


def print_category_report(patterns: dict):
    """Print a readable report for all categories."""
    for category, data in patterns.items():
        if not data:
            continue

        print(f"\n{'='*50}")
        print(f"📦 {category.upper().replace('_', ' ')} CARDS")
        print(f"   {data['total_listings']} listings analyzed")
        print(f"{'='*50}")

        if data["essential"]:
            print(f"\n🔴 Essential (70%+ listings use this):")
            for tag in data["essential"]:
                pct = data["all_freq"][data["all_freq"]["tag"] == tag]["pct"].values
                print(f"   {tag} ({pct[0]}%)" if len(pct) else f"   {tag}")

        if data["strong"]:
            print(f"\n🟡 Strong (40-70%):")
            for tag in data["strong"]:
                pct = data["all_freq"][data["all_freq"]["tag"] == tag]["pct"].values
                print(f"   {tag} ({pct[0]}%)" if len(pct) else f"   {tag}")

        if data["differentiating"]:
            print(f"\n🟢 Differentiating (15-40%):")
            for tag in data["differentiating"]:
                pct = data["all_freq"][data["all_freq"]["tag"] == tag]["pct"].values
                print(f"   {tag} ({pct[0]}%)" if len(pct) else f"   {tag}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = EtsyDB()
    df = db.get_listings(run_date=db.get_latest_run_date())
    db.close()

    print(f"[INFO] Analyzing {len(df)} listings across {df['category'].nunique()} categories")

    patterns = analyze_all_categories(df)
    print_category_report(patterns)

    print("\n[DONE]")