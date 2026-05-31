# ShopSignal — Project Structure

**Version:** 1.1  
**Last updated:** May 2026

---

## Directory Overview

```
shop-signal/
├── strategy/                  # Business logic — keyword strategy, shop profile
│   ├── __init__.py
│   └── keywords.py            # Tier 1/2/3 keyword definitions
│
├── scraper/                   # Data collection from Etsy API
│   ├── __init__.py
│   ├── etsy_scraper.py        # Etsy Open API v3 — market data collection
│   └── mock_data.py           # Simulated weekly data for development
│
├── analysis/                  # Data analysis modules
│   ├── __init__.py
│   ├── keyword_analysis.py    # TF-IDF + tag frequency analysis
│   ├── trend_analysis.py      # Week-over-week keyword delta
│   ├── tag_analysis.py        # Category-level tag pattern analysis (in progress)
│   ├── ai_briefing.py         # GPT-powered weekly action report
│   └── ga4_analysis.py        # GA4 traffic fetchers + AI insights
│
├── database/                  # Data persistence
│   ├── __init__.py
│   └── db.py                  # SQLite manager — listings + run history
│
├── dashboard/                 # Streamlit UI
│   └── app.py                 # 5-page interactive dashboard
│
├── docs/                      # Project documentation
│   ├── PROJECT_DEFINITION.md  # What ShopSignal is, core jobs, AI strategy
│   ├── STRUCTURE.md           # This file
│   └── CHANGELOG.md           # Change log (coming soon)
│
├── data/
│   ├── raw/                   # Scraped CSVs — git-ignored
│   ├── processed/             # Analysis outputs — git-ignored
│   └── etsy.db                # SQLite DB — git-ignored
│
├── ga4-credentials-oauth.json # OAuth credentials — git-ignored
├── token.json                 # OAuth token — git-ignored
├── .env                       # API keys — git-ignored
├── .env.example               # Environment variable template
├── requirements.txt
└── README.md
```

---

## Module Responsibilities

### `strategy/`
Business logic layer. Defines *what* to collect and *why*.
Nothing here should know about API calls or data processing.

| File | Responsibility |
|------|---------------|
| `keywords.py` | Tier 1/2/3 keyword definitions with category grouping. Single source of truth for all keyword decisions. Add new keywords here — scraper picks them up automatically. |

**Keyword Tiers:**
- **Tier 1** — Broad market view (monthly refresh)
- **Tier 2** — Our existing categories (weekly collection)
- **Tier 3** — Gap exploration / categories we don't have yet (weekly collection)

---

### `scraper/`
Data collection layer. Talks to external APIs. Returns raw DataFrames.
Should not contain business logic or analysis.

| File | Responsibility |
|------|---------------|
| `etsy_scraper.py` | Calls Etsy Open API v3. Reads keywords from `strategy/keywords.py`. Saves raw CSVs to `data/raw/` with category + run timestamp. |
| `mock_data.py` | Generates realistic simulated data for development and testing. Mirrors real API output schema exactly. |

---

### `analysis/`
Analysis layer. Reads from DB or raw CSVs. Returns insights.
Each file is independent — runs without knowing about the others.

| File | Responsibility |
|------|---------------|
| `keyword_analysis.py` | TF-IDF on titles + tag frequency. Runs across all data or filtered by category. |
| `trend_analysis.py` | Week-over-week delta. Which tags are rising, falling, or brand new. Requires 2+ weekly runs in DB. |
| `tag_analysis.py` | **In progress.** Category-level tag pattern analysis. "For birthday cards, top competitors use these tags in this frequency." |
| `ai_briefing.py` | Sends trend data + seasonal events to GPT. Returns plain-English weekly action report. |
| `ga4_analysis.py` | OAuth-authenticated GA4 data fetcher. Traffic by listing, source, device, day-of-week. Includes AI insight generation and card clustering. |

---

### `database/`
Persistence layer. All DB operations go through here.
No other module should write SQL directly.

| File | Responsibility |
|------|---------------|
| `db.py` | SQLite manager. Two tables: `listings` (all scraped data with `run_date`) and `runs` (run history). `run_date` enables time-series trend tracking. |

**Why SQLite and not flat files?**
Each scraping run is stored with a `run_date` column. Week-over-week comparison
is a simple grouped query. Flat files would require manual file management.

---

### `dashboard/`
Presentation layer. Reads from DB and processed files. No business logic.

| File | Responsibility |
|------|---------------|
| `app.py` | 5-page Streamlit app. Weekly Briefing · Trend Analysis · SEO Optimizer · Reference Gallery · GA4 Analytics |

---

## Data Flow

```
strategy/keywords.py
        │
        ▼
scraper/etsy_scraper.py  ──────────────────────┐
        │                                       │
        ▼                                       ▼
database/db.py (SQLite)              data/raw/*.csv
        │
        ├──► analysis/trend_analysis.py
        ├──► analysis/keyword_analysis.py
        ├──► analysis/tag_analysis.py (in progress)
        │
analysis/ga4_analysis.py ◄── Google Analytics 4
        │
        ▼
analysis/ai_briefing.py ◄── OpenAI GPT-4o-mini
        │
        ▼
dashboard/app.py ◄── data/processed/*.txt, *.json
```

---

## Design Principles

**Modular** — Each module has one job. Swap out any piece without breaking others.

**Strategy-driven** — `strategy/keywords.py` is the single source of truth for
what gets collected. Change keywords there; nothing else needs to change.

**Human-in-the-loop** — AI surfaces recommendations. Humans decide what to act on.
No automated changes to listings without explicit approval.

**Time-series first** — Every data collection run is stamped with `run_date`.
This enables trend tracking from day one.

**Minimal** — No features beyond what serves the two core jobs defined in
`PROJECT_DEFINITION.md`. When in doubt, don't add it.

---

## Current Status

| Module | Status | Notes |
|--------|--------|-------|
| `strategy/keywords.py` | ✅ Complete | Tier 1/2/3 structure with category grouping |
| `scraper/etsy_scraper.py` | ✅ Complete | Live Etsy API, reads from keywords.py |
| `scraper/mock_data.py` | ✅ Complete | Development use |
| `database/db.py` | ✅ Complete | SQLite with run history |
| `analysis/keyword_analysis.py` | ✅ Complete | TF-IDF + frequency |
| `analysis/trend_analysis.py` | ✅ Complete | Week-over-week delta |
| `analysis/ai_briefing.py` | ✅ Complete | GPT-4o-mini briefing |
| `analysis/ga4_analysis.py` | ✅ Complete | GA4 OAuth + clustering |
| `analysis/tag_analysis.py` | 🔧 In progress | Category-level tag patterns |
| `dashboard/app.py` | ✅ Complete | 5 pages |

---

## Adding a New Keyword

```python
# strategy/keywords.py

KEYWORDS = {
    "tier2": {
        "birthday": [
            "funny birthday card",
            "handmade birthday card",
            "birthday card for her",  # ← just add here
        ],
    }
}
```

That's it. Next scraper run picks it up automatically.

---

## Adding a New Analysis Module

1. Create `analysis/your_module.py`
2. Read from `database/db.py` or `data/processed/`
3. Return a DataFrame or dict
4. Add to `dashboard/app.py` if it needs a UI

No other files need to change.
