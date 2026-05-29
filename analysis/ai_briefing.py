"""
ai_briefing.py
--------------
Generates a weekly AI briefing using OpenAI GPT.
Analyzes trend data and produces actionable insights for shop owners.

Usage:
    python -m analysis.ai_briefing
"""

import os
import sys
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from analysis.trend_analysis import get_trending_summary

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Seasonal events calendar
# ---------------------------------------------------------------------------

SEASONAL_EVENTS = [
    {"name": "Father's Day",      "month": 6,  "day": 15},
    {"name": "Fourth of July",    "month": 7,  "day": 4},
    {"name": "Back to School",    "month": 8,  "day": 15},
    {"name": "Halloween",         "month": 10, "day": 31},
    {"name": "Thanksgiving",      "month": 11, "day": 27},
    {"name": "Christmas",         "month": 12, "day": 25},
    {"name": "New Year",          "month": 1,  "day": 1},
    {"name": "Valentine's Day",   "month": 2,  "day": 14},
    {"name": "Mother's Day",      "month": 5,  "day": 11},
    {"name": "Graduation Season", "month": 5,  "day": 25},
]


def get_upcoming_events(within_days: int = 60) -> list:
    """Return events coming up within the next N days."""
    today = datetime.utcnow()
    upcoming = []

    for event in SEASONAL_EVENTS:
        # Try this year first, then next year
        for year in [today.year, today.year + 1]:
            try:
                event_date = datetime(year, event["month"], event["day"])
                days_away = (event_date - today).days
                if 0 <= days_away <= within_days:
                    upcoming.append({
                        "name": event["name"],
                        "date": event_date.strftime("%B %d"),
                        "days_away": days_away,
                    })
                    break
            except ValueError:
                continue

    return sorted(upcoming, key=lambda x: x["days_away"])


# ---------------------------------------------------------------------------
# AI Briefing generator
# ---------------------------------------------------------------------------

def generate_briefing(summary: dict, upcoming_events: list) -> str:
    """
    Send trend data to OpenAI and get back a weekly briefing.
    Returns the briefing as a string.
    """

    rising_tags = summary["rising"][["tag", "delta"]].to_string(index=False)
    falling_tags = summary["falling"][["tag", "delta"]].to_string(index=False)
    new_tags = ", ".join(summary["new_tags"]) if summary["new_tags"] else "none"
    events_str = "\n".join(
        [f"- {e['name']} ({e['date']}, {e['days_away']} days away)" for e in upcoming_events]
    ) or "No major events in the next 60 days"

    prompt = f"""
You are an expert Etsy SEO consultant for a greeting card shop.
Analyze this week's trend data and give actionable advice.

TREND DATA ({summary['latest_run']} vs {summary['previous_run']}):

Rising tags:
{rising_tags}

Falling tags:
{falling_tags}

Brand new tags this week:
{new_tags}

Upcoming seasonal events:
{events_str}

Please provide:
1. **This Week's Summary** (2-3 sentences, plain English)
2. **Top 3 Action Items** (specific things the shop owner should do THIS week)
3. **Recommended Tags to Add** (10 tags, comma separated, ready to copy-paste)
4. **Tags to Consider Removing** (5 tags that are losing momentum)
5. **Seasonal Opportunity** (one paragraph about upcoming events and how to prepare)

Be specific, practical, and encouraging. Write for a small business owner, not a data scientist.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7,
    )

    return response.choices[0].message.content


def run_briefing(save: bool = True) -> str:
    """Full pipeline: load data → analyze → generate briefing."""
    db = EtsyDB()
    summary = get_trending_summary(db)
    db.close()

    if not summary:
        return "Not enough data for briefing. Need at least 2 weekly runs."

    upcoming = get_upcoming_events(within_days=60)
    print(f"[INFO] Upcoming events: {[e['name'] for e in upcoming]}")

    print("[INFO] Generating AI briefing...")
    briefing = generate_briefing(summary, upcoming)

    if save:
        os.makedirs("data/processed", exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = f"data/processed/briefing_{timestamp}.txt"
        with open(filepath, "w") as f:
            f.write(briefing)
        print(f"[SAVED] {filepath}")

    return briefing


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    briefing = run_briefing()
    print("\n" + "="*60)
    print("WEEKLY AI BRIEFING")
    print("="*60)
    print(briefing)
    print("="*60)
    print("\n[DONE]")