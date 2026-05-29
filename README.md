# ShopSignal
![ShopSignal Demo](assets/demo.gif)
An agentic data pipeline that monitors Etsy market trends and shop traffic,
then uses LLM-powered analysis to surface actionable signals for a handmade greeting card business.

This project was vibe-coded: I designed the system architecture and product direction,
and used AI pair-programming to build it end-to-end. Built to solve a real problem
for a real business — not a tutorial project.

> **Status:** Core pipeline complete. Etsy API key pending approval —
> currently running on simulated weekly data with live GA4 traffic integration.
> Real market data will be swapped in once approved.

---

## The Problem

Running a small Etsy shop means constantly asking questions you don't have time to answer:

- Which keywords are trending right now?
- Why did traffic spike last week?
- Which listings are getting traffic but not converting?
- What card categories am I missing entirely?
- What should I focus on this week?

Manual research across Etsy, Google Analytics, and competitor shops takes hours.
ShopSignal automates the entire loop — from data collection to AI-generated action plan.

---

## How It Works

```
Etsy Market Data ──┐
                   ├──► SQLite (weekly runs) ──► Trend Analysis ──► LLM Agent ──► Dashboard
GA4 Traffic Data ──┘                                                    │
                                                                        ▼
                                                              Weekly Action Briefing
```

1. **Data ingestion** — Etsy API + GA4 Data API pull market and shop data weekly
2. **Storage** — SQLite accumulates runs over time, enabling week-over-week trend detection
3. **Analysis** — TF-IDF keyword extraction, tag frequency delta, traffic source breakdown
4. **LLM layer** — GPT-4o-mini synthesizes signals into plain-English recommendations
5. **Dashboard** — Streamlit surfaces everything in one place

---

## Features

### Etsy Market Intelligence
Collects listing titles, tags, prices, and favorites from Etsy search results.
Tracks keyword frequency week over week to detect rising and falling trends
before they peak or fade.

### AI Weekly Briefing
An LLM agent analyzes the latest trend data alongside a seasonal event calendar
and produces a structured weekly action report — specific tags to add, tags to drop,
and what's coming up on the seasonal calendar.

### GA4 Traffic Analytics
OAuth-authenticated connection to Google Analytics 4 pulls a full year of real shop data:
sessions by listing, traffic sources, device breakdown, day-of-week patterns,
new vs returning visitors, and time-series trend with weekly/monthly/quarterly/yearly views.

### LLM-Powered Card Clustering
GPT automatically groups all listings into card categories, scores each category's
traffic performance, identifies missing categories, and suggests specific new cards to create.

### Multi-Source Insight Generation
Combines Etsy market signals with GA4 internal traffic data to explain traffic spikes,
build an organic growth plan, and generate a Pinterest content strategy — all grounded
in actual shop data.

### Streamlit Dashboard
Five-page interactive dashboard:
- **Weekly Briefing** — AI summary, rising keywords, upcoming events
- **Trend Analysis** — keyword tracking over time, rising vs falling
- **SEO Optimizer** — opportunity scores, recommended tag lists
- **Reference Gallery** — top performing listings by favorites and conversion rate
- **GA4 Analytics** — full traffic breakdown, card clusters, AI insights

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data ingestion | Etsy Open API v3, `requests`, `BeautifulSoup4` |
| Storage | SQLite — weekly runs with `run_date` for time-series trending |
| Analysis | `pandas`, `scikit-learn` (TF-IDF), custom delta logic |
| LLM layer | OpenAI GPT-4o-mini — briefings, clustering, insight generation |
| Traffic data | Google Analytics Data API v1 (OAuth 2.0) |
| Dashboard | Streamlit, Plotly |
| Environment | Python 3.11+, `python-dotenv`, `venv` |

---

## Project Structure

```
shop-signal/
├── scraper/
│   ├── etsy_scraper.py       # Etsy API v3 data collection
│   └── mock_data.py          # Simulated weekly data for development
├── analysis/
│   ├── keyword_analysis.py   # TF-IDF, tag frequency, SEO gap detection
│   ├── trend_analysis.py     # Week-over-week keyword delta
│   ├── ai_briefing.py        # LLM-powered weekly action report
│   └── ga4_analysis.py       # GA4 fetchers, clustering, AI insights
├── database/
│   └── db.py                 # SQLite manager — listings + run history
├── dashboard/
│   └── app.py                # Streamlit app — 5 pages
├── data/
│   ├── raw/                  # Scraped CSVs (git-ignored)
│   └── processed/            # Analysis outputs (git-ignored)
├── .env.example              # Environment variable template
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- OpenAI API key
- Google Cloud project with GA4 Data API enabled
- Etsy developer account *(API key pending — mock data works without it)*

### Installation

```bash
git clone https://github.com/BinarySeo/etsy-seo-optimizer.git
cd etsy-seo-optimizer

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add: OPENAI_API_KEY, GA4_PROPERTY_ID
# Add when approved: ETSY_API_KEY
```

### Run with mock data *(current state — no Etsy API key needed)*

```bash
# Simulate 3 weeks of market data
python -m scraper.mock_data

# Keyword + trend analysis
python -m analysis.keyword_analysis
python -m analysis.trend_analysis

# AI weekly briefing
python -m analysis.ai_briefing

# Launch dashboard
python -m streamlit run dashboard/app.py
```

### Run with live GA4 data *(OAuth login required on first run)*

```bash
# Pull 1 year of shop traffic + generate AI insights
python -m analysis.ga4_analysis

# Launch dashboard
python -m streamlit run dashboard/app.py
```

### Run with real Etsy data *(once API key is approved)*

```bash
python -m scraper.etsy_scraper
python -m analysis.keyword_analysis
python -m analysis.trend_analysis
python -m analysis.ai_briefing
python -m streamlit run dashboard/app.py
```

---

## Key Design Decisions

**Why SQLite instead of flat files?**
Each scraping run is stored with a `run_date` column. Week-over-week trend comparison
becomes a simple grouped query — no manual file management, no fragile CSV joins.
The schema is also designed to accommodate a wholesale order management layer later
without structural changes.

**Why not RAG?**
At 300 listings per weekly run, the full dataset fits comfortably within GPT's context window.
RAG adds retrieval complexity without meaningful benefit at this data volume.
The architecture is designed to introduce a ChromaDB vector store in Phase 3 once
52+ weeks of data accumulates and semantic search over historical trends becomes valuable.

**Why GPT-4o-mini?**
Summarizing trend data, classifying listings, and writing action plans don't require
frontier-level reasoning. GPT-4o-mini handles them reliably at a fraction of the cost —
the right tool for the job.

**Why OAuth for GA4 instead of a Service Account?**
GA4's UI blocks Service Account emails from being added as property users — a known platform
bug. OAuth with the shop owner's Google account is the correct pattern for personal shop
analytics and requires no workarounds.

---

## Current Status

| Component | Status |
|-----------|--------|
| Mock data pipeline | ✅ Complete |
| SQLite storage | ✅ Complete |
| Keyword + trend analysis | ✅ Complete |
| AI weekly briefing | ✅ Complete |
| GA4 OAuth integration | ✅ Complete |
| GA4 traffic analysis | ✅ Complete |
| Card clustering (LLM) | ✅ Complete |
| Streamlit dashboard | ✅ Complete |
| Etsy API (real data) | ⏳ API key pending approval |
| GA4 + Etsy combined scoring | 🔜 Next |
| Automated weekly pipeline | 🔜 Planned |

---

## Roadmap

**Phase 2 — Real Data**
- Swap mock data for live Etsy API v3 data once key is approved
- Combine GA4 traffic quality signals with Etsy keyword demand scores
- Build a unified opportunity score per keyword

**Phase 3 — Agentic Pipeline**
- APScheduler to run the full pipeline every Monday automatically
- Email or Slack digest with the weekly briefing
- LLM agent that monitors trend shifts and alerts on anomalies

**Phase 4 — Wholesale Integration**
- Faire / wholesale marketplace API connection
- Order management layer in the existing SQLite schema
- Wholesale performance tab in the dashboard

**Phase 5 — RAG Layer**
- ChromaDB vector store over accumulated listing and trend data
- Natural-language queries: *"What worked last Valentine's Day?"*
- Semantic similarity search across historical keyword patterns

---

*Built to solve a real problem for a real business.*
*Architecture designed to scale — from a weekend side project to a full business intelligence layer.*
