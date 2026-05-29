"""
mock_data.py
------------
Generates realistic sample Etsy listing data for development.
Same schema as the real API output — swap in real data when API key is approved.

Usage:
    python -m scraper.mock_data
"""

import pandas as pd
import random
import os
from datetime import datetime, timedelta

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

TAG_POOL = [
    "birthday card", "greeting card", "funny card", "handmade card",
    "card for her", "card for him", "best friend", "personalized",
    "floral card", "cute card", "sarcastic", "watercolor",
    "minimalist", "botanical", "dog lover", "cat lover",
    "wine lover", "plant lover", "celestial", "gold foil",
    "vintage", "elegant", "colorful", "handlettered",
    "thank you card", "mom birthday", "getting old", "punny",
]

QUERIES = [
    "greeting card",
    "birthday card handmade",
    "funny greeting card",
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_listing(listing_id: int, query: str) -> dict:
    """Generate a single realistic mock listing."""

    # Assign tags — pick 8-13 random tags (Etsy max is 13)
    tags = random.sample(TAG_POOL, k=random.randint(8, 13))

    # Simulate realistic price distribution ($3 - $15)
    price = round(random.uniform(3.0, 15.0), 2)

    # Simulate favorites — power law distribution (most have few, some have many)
    favorites = int(random.paretovariate(1.5) * 50)
    favorites = min(favorites, 5000)  # cap at 5000

    # Views correlate loosely with favorites
    views = favorites * random.randint(10, 40)

    # Scraped at a random time in the past 30 days
    days_ago = random.randint(0, 30)
    scraped_at = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()

    return {
        "listing_id":   listing_id,
        "title":        random.choice(TITLES),
        "price_usd":    price,
        "currency":     "USD",
        "quantity":     random.randint(1, 999),
        "num_favorers": favorites,
        "views":        views,
        "tags":         ", ".join(tags),
        "shop_id":      random.randint(10000000, 99999999),
        "url":          f"https://www.etsy.com/listing/{listing_id}",
        "state":        "active",
        "query":        query,
        "scraped_at":   scraped_at,
    }


def generate_dataset(num_listings: int = 200) -> pd.DataFrame:
    """Generate a full mock dataset across all queries."""
    all_listings = []
    listing_id = 1000000

    per_query = num_listings // len(QUERIES)

    for query in QUERIES:
        print(f"[INFO] Generating {per_query} listings for '{query}'...")
        for _ in range(per_query):
            listing = generate_listing(listing_id, query)
            all_listings.append(listing)
            listing_id += 1

    return pd.DataFrame(all_listings)


def save_mock(df: pd.DataFrame) -> str:
    """Save mock data to data/raw/ with a clear mock label."""
    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filepath = f"data/raw/mock_data_{timestamp}.csv"
    df.to_csv(filepath, index=False)
    print(f"\n[SAVED] {filepath} ({len(df)} rows)")
    return filepath


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = generate_dataset(num_listings=300)
    filepath = save_mock(df)

    print("\n--- Preview ---")
    print(df[["title", "price_usd", "num_favorers", "tags", "query"]].head(5).to_string())
    print(f"\nTotal: {len(df)} listings across {df['query'].nunique()} queries")
    print("[DONE]")