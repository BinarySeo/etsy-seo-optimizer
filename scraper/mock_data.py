"""
mock_data.py
------------
Generates realistic mock Etsy listing data and saves to SQLite DB.
Simulates multiple weekly runs for trend tracking.

Usage:
    python -m scraper.mock_data
"""

import pandas as pd
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB


# ---------------------------------------------------------------------------
# Sample data pools
# ---------------------------------------------------------------------------

TITLES = [
    "Funny Birthday Card for Best Friend",
    "Handmade Floral Birthday Card",
    "Cute Cat Happy Birthday Card",
    "Sarcastic Birthday Card for Him",
    "Watercolor Flower Greeting Card",
    "Minimalist Birthday Card Set of 5",
    "Dog Lover Birthday Card Funny",
    "Personalized Birthday Card Mom",
    "Botanical Illustration Thank You Card",
    "Funny Getting Old Birthday Card",
    "Happy Birthday Card with Envelope",
    "Custom Name Birthday Card",
    "Vintage Floral Greeting Card",
    "Punny Birthday Card Plant Lover",
    "Handlettered Birthday Card",
    "Celestial Birthday Card Stars Moon",
    "Funny Wine Birthday Card for Her",
    "Cute Sloth Birthday Card",
    "Rainbow Birthday Card Colorful",
    "Elegant Gold Foil Birthday Card",
]

# Week 1 tags — baseline
TAGS_WEEK1 = [
    "birthday card", "greeting card", "funny card", "handmade card",
    "card for her", "card for him", "best friend", "personalized",
    "floral card", "cute card", "sarcastic", "watercolor",
    "minimalist", "botanical", "dog lover", "cat lover",
    "wine lover", "plant lover", "celestial", "gold foil",
]

# Week 2 tags — some new trending tags appear
TAGS_WEEK2 = TAGS_WEEK1 + [
    "graduation card", "mental health", "self care card",
    "aesthetic card", "retro card",
]

# Week 3 tags — graduation season peaks
TAGS_WEEK3 = TAGS_WEEK2 + [
    "class of 2026", "senior year", "congrats grad",
    "college graduation", "high school grad",
]

WEEKLY_TAGS = {
    0: TAGS_WEEK1,
    1: TAGS_WEEK2,
    2: TAGS_WEEK3,
}

QUERIES = [
    "greeting card",
    "birthday card handmade",
    "funny greeting card",
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_listing(listing_id: int, query: str, tag_pool: list) -> dict:
    tags = random.sample(tag_pool, k=min(random.randint(8, 13), len(tag_pool)))
    price = round(random.uniform(3.0, 15.0), 2)
    favorites = int(random.paretovariate(1.5) * 50)
    favorites = min(favorites, 5000)
    views = favorites * random.randint(10, 40)

    return {
        "listing_id":   str(listing_id),
        "title":        random.choice(TITLES),
        "price_usd":    price,
        "currency":     "USD",
        "quantity":     random.randint(1, 999),
        "num_favorers": favorites,
        "views":        views,
        "tags":         ", ".join(tags),
        "shop_id":      str(random.randint(10000000, 99999999)),
        "url":          f"https://www.etsy.com/listing/{listing_id}",
        "state":        "active",
        "query":        query,
        "scraped_at":   datetime.utcnow().isoformat(),
    }


def generate_weekly_data(week_offset: int = 0, num_listings: int = 300) -> pd.DataFrame:
    """Generate one week's worth of mock data."""
    tag_pool = WEEKLY_TAGS.get(week_offset, TAGS_WEEK3)
    all_listings = []
    listing_id = 1000000 + (week_offset * 10000)
    per_query = num_listings // len(QUERIES)

    for query in QUERIES:
        for _ in range(per_query):
            listing = generate_listing(listing_id, query, tag_pool)
            all_listings.append(listing)
            listing_id += 1

    return pd.DataFrame(all_listings)


# ---------------------------------------------------------------------------
# Entry point — simulate 3 weeks of data
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = EtsyDB()

    # Simulate 3 weekly runs going back from today
    for week_offset in range(3):
        run_date = (datetime.utcnow() - timedelta(weeks=2 - week_offset)).strftime("%Y-%m-%d")
        print(f"\n[INFO] Generating week {week_offset + 1} data — run_date: {run_date}")

        df = generate_weekly_data(week_offset=week_offset, num_listings=300)
        db.insert_listings(df, run_date=run_date)

    print("\n--- Run History ---")
    print(db.get_runs().to_string(index=False))

    print("\n--- Sample listings ---")
    df_all = db.get_listings()
    print(f"Total rows in DB: {len(df_all)}")
    print(df_all[["title", "tags", "query", "run_date"]].head(5).to_string())

    db.close()
    print("\n[DONE]")