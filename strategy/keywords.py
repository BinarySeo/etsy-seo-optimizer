"""
keywords.py
-----------
Keyword strategy for ShopSignal market data collection.

Three tiers:
    Tier 2 — Our existing categories (weekly collection)
    Tier 3 — Gap exploration / categories we don't have (weekly collection)
    Tier 1 — Broad market view (monthly collection)

To add a new keyword: add it to the appropriate tier and category.
The scraper will pick it up automatically on next run.
"""

KEYWORDS = {
    "tier2": {
        "thank_you": [
            "funny thank you card",
            "thank you card handmade",
        ],
        "housewarming": [
            "housewarming card handmade",
            "new home card",
        ],
        "birthday": [
            "funny birthday card",
            "handmade birthday card",
        ],
        "friendship": [
            "best friend card handmade",
            "funny friendship card",
        ],
        "graduation": [
            "funny graduation card",
            "graduation card handmade",
        ],
        "seasonal": [
            "mothers day card handmade",
            "fathers day card funny",
        ],
    },
    "tier3": {
        "wedding": [
            "wedding congratulations card handmade",
            "engagement card handmade",
        ],
        "sympathy": [
            "sympathy card handmade",
            "thinking of you card handmade",
        ],
        "life_events": [
            "new job congratulations card",
            "retirement card funny",
        ],
        "evergreen": [
            "just because card handmade",
            "galentines day card",
        ],
    },
    "tier1": {
        "broad": [
            "greeting card handmade",
            "funny greeting card",
        ],
    },
}


def get_keywords(tiers: list = None, flat: bool = False):
    """
    Get keywords from specified tiers.

    Args:
        tiers: list of tiers to include e.g. ["tier2", "tier3"]
               defaults to tier2 + tier3 if None
        flat:  if True, return flat list of (keyword, category, tier) tuples
               if False, return nested dict

    Examples:
        get_keywords()                    # tier2 + tier3, nested
        get_keywords(["tier2"], flat=True) # tier2 only, flat list
    """
    if tiers is None:
        tiers = ["tier2", "tier3"]

    if not flat:
        return {tier: KEYWORDS[tier] for tier in tiers if tier in KEYWORDS}

    result = []
    for tier in tiers:
        if tier not in KEYWORDS:
            continue
        for category, keywords in KEYWORDS[tier].items():
            for keyword in keywords:
                result.append({
                    "keyword": keyword,
                    "category": category,
                    "tier": tier,
                })
    return result


if __name__ == "__main__":
    # Quick check — print all active keywords
    all_keywords = get_keywords(flat=True)
    print(f"Total keywords: {len(all_keywords)}\n")
    for item in all_keywords:
        print(f"[{item['tier']}][{item['category']}] {item['keyword']}")