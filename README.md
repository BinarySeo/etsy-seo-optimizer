# Etsy SEO Optimizer

A data pipeline and analytics dashboard that scrapes Etsy greeting card listings,
extracts trending keywords, and surfaces actionable SEO recommendations.

## Tech Stack
- Scraping: requests, BeautifulSoup4
- Data: pandas, SQLite
- Analysis: scikit-learn (TF-IDF)
- Dashboard: Streamlit, Plotly

## Getting Started

1. Clone the repo
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install: `pip install -r requirements.txt`
5. Run dashboard: `streamlit run dashboard/app.py`
