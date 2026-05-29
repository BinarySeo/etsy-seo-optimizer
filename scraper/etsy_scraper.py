"""
etsy_scraper.py
---------------
Fetches Etsy listing data via the official Etsy Open API v3.
No scraping — clean, stable, and TOS-compliant.

Usage:
    python -m scraper.etsy_scraper
"""

import requests
import pandas as pd
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.getenv("ETSY_API_KEY")
BASE_URL = "https://api.etsy.com/v3/application"
HEADERS = {"x-api-key": API_KEY}

# Etsy API limit: 25 results per page, max 100 per request
LIMIT = 100
DELAY = 1.0  # seconds between requests


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def fetch_active_listings(keywords: str, limit: int = 100, offset: int = 0) -> dict:
    """
    Call findAllListingsActive endpoint.
    Returns raw JSON response as a dict.
    """
    url = f"{BASE_URL}/listings/active"
    params = {
        "keywords": keywords,
        "limit": limit,
        "offset": offset,
        "sort_on": "score",       # relevance ranking
        "sort_order": "desc",
    }

    response = requests.get(url, headers=HEADERS, params=params, timeout=10)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")
        return {}


def parse_listings(data: dict, query: str) -> list:
    """
    Parse API response into a flat list of dicts.
    """
    listings = []
    results = data.get("results", [])

    for item in results:
        listing = {
            "listing_id":   item.get("listing_id", ""),
            "title":        item.get("title", ""),
            "price_usd":    item.get("price", {}).get("amount", "") / 100 if item.get("price") else "",
            "currency":     item.get("price", {}).get("currency_code", ""),
            "quantity":     item.get("quantity", ""),
            "num_favorers": item.get("num_favorers", 0),
            "views":        item.get("views", 0),
            "tags":         ", ".join(item.get("tags", [])),
            "shop_id":      item.get("shop_id", ""),
            "url":          item.get("url", ""),
            "state":        item.get("state", ""),
            "query":        query,
            "scraped_at":   datetime.utcnow().isoformat(),
        }
        listings.append(listing)

    return listings


def fetch_query(query: str, total: int = 200) -> pd.DataFrame:
    """
    Fetch multiple pages of results for a query.
    total = how many listings to fetch (max 200 recommended)
    """
    all_listings = []
    offset = 0
    print(f"\n[INFO] Fetching: '{query}' (target: {total} listings)")

    while offset < total:
        batch_size = min(LIMIT, total - offset)
        print(f"  Offset {offset} — fetching {batch_size} listings...")

        data = fetch_active_listings(query, limit=batch_size, offset=offset)
        if not data:
            break

        listings = parse_listings(data, query)
        if not listings:
            print("  No more results.")
            break

        all_listings.extend(listings)
        print(f"  Got {len(listings)} listings (total so far: {len(all_listings)})")

        offset += batch_size
        time.sleep(DELAY)

    df = pd.DataFrame(all_listings)
    return df


def save_raw(df: pd.DataFrame, query: str) -> str:
    """Save raw DataFrame to data/raw/ with timestamp."""
    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_")
    filepath = f"data/raw/{safe_query}_{timestamp}.csv"
    df.to_csv(filepath, index=False)
    print(f"\n[SAVED] {filepath} ({len(df)} rows)")
    return filepath


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not API_KEY:
        print("[ERROR] ETSY_API_KEY not found. Check your .env file.")
        exit(1)

    queries = [
        "greeting card",
        "birthday card handmade",
        "funny greeting card",
    ]

    for query in queries:
        df = fetch_query(query, total=200)
        if not df.empty:
            save_raw(df, query)
        else:
            print(f"[WARN] No results for '{query}'")

    print("\n[DONE] All queries complete.")