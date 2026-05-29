"""
ga4_analysis.py
---------------
Fetches and analyzes 1 year of GA4 data for the Etsy shop.

What this file does:
    1. Authenticates with Google Analytics via OAuth
    2. Fetches traffic data (pages, sources, weekly trends, devices, day of week)
    3. Groups listings into card categories using AI (clustering)
    4. Generates AI-powered insights (traffic spikes, organic growth, Pinterest strategy)
    5. Saves all results to data/processed/

Usage:
    python -m analysis.ga4_analysis
"""

import os
import re
import sys
import json
import pandas as pd
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension, OrderBy
)
from openai import OpenAI
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPES            = ['https://www.googleapis.com/auth/analytics.readonly']
TOKEN_PATH        = 'token.json'               # saved after first OAuth login
CREDENTIALS_PATH  = 'ga4-credentials-oauth.json'  # OAuth client secret
PROPERTY_ID       = os.getenv('GA4_PROPERTY_ID')   # from .env

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# ---------------------------------------------------------------------------
# Authentication
# Handles OAuth flow. On first run, opens browser for Google login.
# Saves token.json so subsequent runs don't need browser login.
# ---------------------------------------------------------------------------

def get_credentials() -> Credentials:
    """
    Load saved credentials or run OAuth flow if none exist.
    Returns valid Google credentials.
    """
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials, run OAuth login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Silently refresh expired token
            creds.refresh(Request())
        else:
            # Open browser for first-time login
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_client() -> BetaAnalyticsDataClient:
    """Return an authenticated GA4 Data API client."""
    return BetaAnalyticsDataClient(credentials=get_credentials())


# ---------------------------------------------------------------------------
# Data Fetchers
# Each function makes one API call and returns a clean DataFrame.
# ---------------------------------------------------------------------------

def fetch_top_pages(days: int = 365, limit: int = 50) -> pd.DataFrame:
    """
    Fetch top pages ranked by sessions.

    Returns columns:
        page_path        — Etsy listing URL path
        sessions         — number of visits
        views            — number of page views
        bounce_rate      — % who left without any action (0.0 to 1.0)
        avg_session_sec  — average time spent on page in seconds
    """
    client = get_client()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True
        )],
        limit=limit,
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        rows.append({
            "page_path":       row.dimension_values[0].value,
            "sessions":        int(row.metric_values[0].value),
            "views":           int(row.metric_values[1].value),
            "bounce_rate":     round(float(row.metric_values[2].value), 2),
            "avg_session_sec": round(float(row.metric_values[3].value), 1),
        })

    return pd.DataFrame(rows)


def fetch_traffic_sources(days: int = 365) -> pd.DataFrame:
    """
    Fetch where visitors are coming from.

    Key sources to watch:
        google / cpc      → Etsy Offsite Ads (paid)
        (direct) / none   → Unknown origin (Etsy app, bookmarks, DMs)
        google / organic  → Free Google search traffic
        pinterest         → Pinterest traffic (free)
        instagram         → Instagram traffic

    Returns columns:
        source, medium, sessions, conversions
    """
    client = get_client()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="conversions"),
        ],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True
        )],
        limit=20,
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        rows.append({
            "source":      row.dimension_values[0].value,
            "medium":      row.dimension_values[1].value,
            "sessions":    int(row.metric_values[0].value),
            "conversions": int(row.metric_values[1].value),
        })

    return pd.DataFrame(rows)


def fetch_weekly_trend(weeks: int = 52) -> pd.DataFrame:
    """
    Fetch weekly session counts with real calendar dates.

    Converts GA4's yearWeek format (e.g. "202416") into
    human-readable dates (e.g. "Apr 14, 2025") so charts
    show actual dates instead of week numbers.

    Returns columns:
        year_week   — raw GA4 format (e.g. "202416")
        week_start  — datetime object for the Monday of that week
        week_label  — human-readable label (e.g. "Apr 14, 2025")
        sessions    — total sessions that week
        views       — total page views that week
    """
    client = get_client()
    days = weeks * 7

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="yearWeek")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
        ],
        order_bys=[OrderBy(
            dimension=OrderBy.DimensionOrderBy(dimension_name="yearWeek"),
            desc=False
        )],
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        year_week = row.dimension_values[0].value  # e.g. "202416"
        year = int(year_week[:4])
        week = int(year_week[4:])

        # Convert ISO week number to actual Monday date
        week_start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
        week_label = week_start.strftime("%b %d, %Y")

        rows.append({
            "year_week":  year_week,
            "week_start": week_start,
            "week_label": week_label,
            "sessions":   int(row.metric_values[0].value),
            "views":      int(row.metric_values[1].value),
        })

    return pd.DataFrame(rows)


def fetch_device_breakdown(days: int = 365) -> pd.DataFrame:
    """
    Fetch traffic split by device type (mobile / desktop / tablet).

    High mobile bounce rate means product photos may not look
    good on small screens — important for an Etsy shop.

    Returns columns:
        device, sessions, bounce_rate, avg_session_sec
    """
    client = get_client()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True
        )],
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        rows.append({
            "device":          row.dimension_values[0].value,
            "sessions":        int(row.metric_values[0].value),
            "bounce_rate":     round(float(row.metric_values[1].value), 2),
            "avg_session_sec": round(float(row.metric_values[2].value), 1),
        })

    return pd.DataFrame(rows)


def fetch_day_of_week(days: int = 365) -> pd.DataFrame:
    """
    Fetch traffic by day of week to find best days for posting.

    GA4 returns 0=Sunday, 1=Monday, ... 6=Saturday.
    We convert to readable day names and sort correctly.

    Returns columns:
        day_num, day, sessions, views
    """
    client = get_client()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="dayOfWeek")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
        ],
        order_bys=[OrderBy(
            dimension=OrderBy.DimensionOrderBy(dimension_name="dayOfWeek"),
            desc=False
        )],
    )
    response = client.run_report(request)

    # GA4 uses 0=Sunday through 6=Saturday
    day_names = {
        "0": "Sunday",   "1": "Monday", "2": "Tuesday",
        "3": "Wednesday","4": "Thursday","5": "Friday", "6": "Saturday"
    }

    rows = []
    for row in response.rows:
        day_num = row.dimension_values[0].value
        rows.append({
            "day_num":  int(day_num),
            "day":      day_names.get(day_num, day_num),
            "sessions": int(row.metric_values[0].value),
            "views":    int(row.metric_values[1].value),
        })

    return pd.DataFrame(rows).sort_values("day_num")


def fetch_new_vs_returning(days: int = 365) -> pd.DataFrame:
    """
    Fetch new vs returning visitor breakdown.

    Low returning % = people don't come back after first visit.
    High returning % = building a loyal customer base.

    Returns columns:
        visitor_type, sessions, bounce_rate
    """
    client = get_client()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="newVsReturning")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="bounceRate"),
        ],
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        rows.append({
            "visitor_type": row.dimension_values[0].value,
            "sessions":     int(row.metric_values[0].value),
            "bounce_rate":  round(float(row.metric_values[1].value), 2),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_listing_id(path: str) -> str:
    """
    Extract the numeric listing ID from an Etsy URL path.
    Example: /listing/1883979582/thanks-for-... → "1883979582"
    Returns None if no listing ID found (e.g. homepage, non-listing pages).
    """
    match = re.search(r'/listing/(\d+)', path)
    return match.group(1) if match else None


def get_listing_performance(df_pages: pd.DataFrame) -> pd.DataFrame:
    """
    Filter pages to only Etsy listing pages and add listing_id column.
    Removes non-listing pages (homepage, about, etc.)
    """
    df = df_pages.copy()
    df["listing_id"] = df["page_path"].apply(extract_listing_id)
    df = df[df["listing_id"].notna()].copy()
    return df.sort_values("sessions", ascending=False)


def aggregate_by_period(df_weekly: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Aggregate weekly data into monthly, quarterly, or yearly totals.

    Args:
        df_weekly: Weekly trend DataFrame from fetch_weekly_trend()
        period: "weekly" | "monthly" | "quarterly" | "yearly"

    Returns:
        DataFrame with period label, sessions, views columns
    """
    df = df_weekly.copy()
    df["week_start"] = pd.to_datetime(df["week_start"])

    if period == "weekly":
        # Already weekly — just return with readable labels
        return df[["week_label", "sessions", "views"]].rename(
            columns={"week_label": "period"}
        )

    elif period == "monthly":
        df["period"] = df["week_start"].dt.strftime("%b %Y")  # e.g. "Apr 2026"
        df["period_sort"] = df["week_start"].dt.to_period("M")

    elif period == "quarterly":
        # Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec
        df["quarter"] = df["week_start"].dt.quarter
        df["year"] = df["week_start"].dt.year
        df["period"] = "Q" + df["quarter"].astype(str) + " " + df["year"].astype(str)
        df["period_sort"] = df["year"] * 10 + df["quarter"]

    elif period == "yearly":
        df["period"] = df["week_start"].dt.strftime("%Y")
        df["period_sort"] = df["week_start"].dt.year

    # Sum sessions and views within each period
    result = (
        df.groupby(["period", "period_sort"], as_index=False)
        .agg(sessions=("sessions", "sum"), views=("views", "sum"))
        .sort_values("period_sort")
        .drop(columns=["period_sort"])
    )

    return result


# ---------------------------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------------------------

def generate_traffic_insights(
    df_weekly: pd.DataFrame,
    df_sources: pd.DataFrame,
    df_pages: pd.DataFrame,
    df_devices: pd.DataFrame,
    df_dow: pd.DataFrame,
    df_new_returning: pd.DataFrame,
) -> str:
    """
    Send all GA4 data to GPT and generate actionable insights.

    Covers:
        - Why traffic spiked on specific dates
        - How to grow organic traffic (currently very low)
        - Pinterest strategy based on day-of-week data
        - 3 quick wins for this week
    """
    # Find weeks with 2x above average traffic (spikes)
    avg_sessions = df_weekly["sessions"].mean()
    spikes = df_weekly[
        df_weekly["sessions"] > avg_sessions * 2
    ][["week_label", "sessions"]].to_string(index=False)

    top_pages  = df_pages.head(10)[["page_path", "sessions", "bounce_rate", "avg_session_sec"]].to_string(index=False)
    sources    = df_sources.to_string(index=False)
    devices    = df_devices.to_string(index=False)
    dow        = df_dow[["day", "sessions"]].to_string(index=False)
    new_ret    = df_new_returning.to_string(index=False)

    prompt = f"""
You are a digital marketing expert specializing in Etsy shops and handmade goods.
Analyze this 1-year GA4 data for a handmade greeting card shop and provide actionable insights.

TRAFFIC SPIKES (weeks with 2x above average of {avg_sessions:.0f} sessions/week):
{spikes}

TOP 10 PAGES:
{top_pages}

TRAFFIC SOURCES:
{sources}

DEVICE BREAKDOWN:
{devices}

DAY OF WEEK:
{dow}

NEW VS RETURNING:
{new_ret}

Please provide:

## Why Did Traffic Spike?
Explain each spike with likely seasonal/holiday reasons. Match dates to known events.

## Organic Traffic Growth Plan
5 specific actionable steps to grow organic traffic for a handmade greeting card shop.

## Pinterest Strategy
Step-by-step Pinterest strategy based on this shop's data.
Include posting frequency, board structure, pin types, and best days to post.

## Quick Wins This Week
3 things the shop owner can do THIS WEEK to improve traffic and sales.

Write in plain English. Be specific and practical. No jargon.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7,
    )

    return response.choices[0].message.content


def cluster_listings(df_pages: pd.DataFrame) -> dict:
    """
    Use GPT to group listings into card categories and identify gaps.

    Why: Helps the shop owner see which card types are strong,
    which are weak, and what new cards to create next.

    Returns a dict with:
        clusters         — list of card categories with performance data
        missing_categories — card types the shop is missing
        new_card_ideas   — specific new card ideas with reasoning
    """
    df_listings = get_listing_performance(df_pages)

    listing_data = df_listings[
        ["page_path", "sessions", "bounce_rate", "avg_session_sec"]
    ].to_string(index=False)

    prompt = f"""
You are an Etsy product strategist for a handmade greeting card shop.

Here are the shop's listings with their traffic data:
{listing_data}

Please:
1. Group these listings into card categories (Birthday, Housewarming, Funny, Thank You, Seasonal, etc.)
2. For each category show: listings count, total sessions, avg bounce rate, performance rating
3. Identify which categories are MISSING or UNDERREPRESENTED
4. Suggest 3 specific new card ideas the shop should create next

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
    "clusters": [
        {{
            "category": "Housewarming Cards",
            "listings": ["listing title 1", "listing title 2"],
            "total_sessions": 526,
            "avg_bounce_rate": 0.49,
            "performance": "strong"
        }}
    ],
    "missing_categories": ["Wedding Cards", "Sympathy Cards"],
    "new_card_ideas": [
        {{
            "title": "Funny New Job Card",
            "reason": "High search volume on Etsy, not represented in shop"
        }}
    ]
}}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,  # lower temp = more consistent JSON output
    )

    raw = response.choices[0].message.content

    # Strip markdown code fences if present
    clean = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # If parsing fails, return raw text wrapped in dict
        return {"raw": raw}


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_ga4_data(df_pages: pd.DataFrame, df_sources: pd.DataFrame):
    """Save raw GA4 page and source data to data/processed/."""
    os.makedirs("data/processed", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    pages_path   = f"data/processed/ga4_pages_{timestamp}.csv"
    sources_path = f"data/processed/ga4_sources_{timestamp}.csv"

    df_pages.to_csv(pages_path, index=False)
    df_sources.to_csv(sources_path, index=False)

    print(f"[SAVED] {pages_path}")
    print(f"[SAVED] {sources_path}")


def save_insights(insights: str, clusters: dict):
    """Save AI insights and clusters to data/processed/."""
    os.makedirs("data/processed", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Save traffic insights as text
    insights_path = f"data/processed/ga4_insights_{timestamp}.txt"
    with open(insights_path, "w") as f:
        f.write(insights)
    print(f"[SAVED] {insights_path}")

    # Save clusters as JSON
    clusters_path = f"data/processed/card_clusters_{timestamp}.json"
    with open(clusters_path, "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"[SAVED] {clusters_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[INFO] Fetching 1 year of GA4 data...")

    # Fetch all data
    df_pages   = fetch_top_pages(days=365, limit=50)
    df_sources = fetch_traffic_sources(days=365)
    df_weekly  = fetch_weekly_trend(weeks=52)
    df_devices = fetch_device_breakdown(days=365)
    df_dow     = fetch_day_of_week(days=365)
    df_new_ret = fetch_new_vs_returning(days=365)

    # Print summaries
    print("\n--- Top 10 Pages ---")
    print(df_pages.head(10).to_string(index=False))

    print("\n--- Weekly Trend ---")
    print(df_weekly[["week_label", "sessions", "views"]].to_string(index=False))

    print("\n--- Monthly Trend ---")
    print(aggregate_by_period(df_weekly, "monthly").to_string(index=False))

    print("\n--- Quarterly Trend ---")
    print(aggregate_by_period(df_weekly, "quarterly").to_string(index=False))

    print("\n--- Traffic Sources ---")
    print(df_sources.to_string(index=False))

    print("\n--- Device Breakdown ---")
    print(df_devices.to_string(index=False))

    print("\n--- Day of Week ---")
    print(df_dow[["day", "sessions", "views"]].to_string(index=False))

    print("\n--- New vs Returning ---")
    print(df_new_ret.to_string(index=False))

    # AI analysis
    print("\n[INFO] Generating AI traffic insights...")
    insights = generate_traffic_insights(
        df_weekly, df_sources, df_pages,
        df_devices, df_dow, df_new_ret
    )
    print("\n" + "="*60)
    print("AI TRAFFIC INSIGHTS")
    print("="*60)
    print(insights)

    print("\n[INFO] Clustering listings by card type...")
    clusters = cluster_listings(df_pages)
    print("\n--- Card Clusters ---")
    print(json.dumps(clusters, indent=2))

    # Save everything
    save_ga4_data(df_pages, df_sources)
    save_insights(insights, clusters)

    print("\n[DONE]")