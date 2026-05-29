"""
keyword_analysis.py
-------------------
Analyzes tag and title frequency from scraped Etsy listings.
Extracts high-signal keywords using TF-IDF and frequency counts.

Usage:
    python -m analysis.keyword_analysis
"""

import pandas as pd
import numpy as np
import os
import glob
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_latest_data(data_dir: str = "data/raw") -> pd.DataFrame:
    """Load the most recently saved CSV from data/raw/."""
    files = glob.glob(f"{data_dir}/*.csv")
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    latest = max(files, key=os.path.getctime)
    print(f"[INFO] Loading: {latest}")
    df = pd.read_csv(latest)
    print(f"[INFO] {len(df)} listings loaded")
    return df


# ---------------------------------------------------------------------------
# Tag analysis
# ---------------------------------------------------------------------------

def extract_all_tags(df: pd.DataFrame) -> list:
    """Flatten all tags from every listing into a single list."""
    all_tags = []
    for tags_str in df["tags"].dropna():
        tags = [t.strip().lower() for t in tags_str.split(",")]
        all_tags.extend(tags)
    return all_tags


def tag_frequency(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """Count how often each tag appears across all listings."""
    all_tags = extract_all_tags(df)
    counts = Counter(all_tags)
    freq_df = pd.DataFrame(counts.most_common(top_n), columns=["tag", "count"])
    freq_df["pct"] = (freq_df["count"] / len(df) * 100).round(1)
    return freq_df


def tag_frequency_by_query(df: pd.DataFrame, top_n: int = 15) -> dict:
    """Tag frequency broken down by search query."""
    results = {}
    for query in df["query"].unique():
        subset = df[df["query"] == query]
        results[query] = tag_frequency(subset, top_n=top_n)
    return results


# ---------------------------------------------------------------------------
# TF-IDF on titles
# ---------------------------------------------------------------------------

def tfidf_keywords(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Run TF-IDF on listing titles to find the most distinctive keywords.
    High TF-IDF score = appears often in this dataset but not generically.
    """
    titles = df["title"].dropna().tolist()
    if len(titles) < 2:
        print("[WARN] Not enough titles for TF-IDF")
        return pd.DataFrame()

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),   # single words + two-word phrases
        max_features=500,
        min_df=2,             # must appear in at least 2 listings
    )

    tfidf_matrix = vectorizer.fit_transform(titles)
    feature_names = vectorizer.get_feature_names_out()

    # Mean TF-IDF score across all listings
    mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

    tfidf_df = pd.DataFrame({
        "keyword": feature_names,
        "tfidf_score": mean_scores,
    }).sort_values("tfidf_score", ascending=False).head(top_n)

    return tfidf_df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# SEO gap analysis
# ---------------------------------------------------------------------------

def seo_gap_analysis(df: pd.DataFrame, your_tags: list) -> pd.DataFrame:
    """
    Compare your current tags against top trending tags.
    Shows which high-value tags you're missing.
    """
    top_tags = tag_frequency(df, top_n=50)
    your_tags_lower = [t.strip().lower() for t in your_tags]

    top_tags["in_your_shop"] = top_tags["tag"].isin(your_tags_lower)
    top_tags["status"] = top_tags["in_your_shop"].map(
        {True: "already using", False: "missing — consider adding"}
    )

    return top_tags[["tag", "count", "pct", "status"]]


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_analysis(results: dict, output_dir: str = "data/processed"):
    """Save analysis DataFrames to processed/ folder."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    for name, df in results.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            filepath = f"{output_dir}/{name}_{timestamp}.csv"
            df.to_csv(filepath, index=False)
            print(f"[SAVED] {filepath}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = load_latest_data()

    # 1. Tag frequency
    print("\n--- Top 20 Tags ---")
    freq = tag_frequency(df, top_n=20)
    print(freq.to_string(index=False))

    # 2. TF-IDF keywords from titles
    print("\n--- Top TF-IDF Keywords (titles) ---")
    tfidf = tfidf_keywords(df, top_n=20)
    print(tfidf.to_string(index=False))

    # 3. SEO gap analysis — replace with your actual tags
    YOUR_TAGS = [
        "birthday card", "greeting card", "handmade card", "funny card"
    ]
    print("\n--- SEO Gap Analysis ---")
    gap = seo_gap_analysis(df, YOUR_TAGS)
    print(gap.head(20).to_string(index=False))

    # Save all results
    save_analysis({
        "tag_frequency": freq,
        "tfidf_keywords": tfidf,
        "seo_gap": gap,
    })

    print("\n[DONE] Analysis complete.")