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
from datetime import date, datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from analysis.trend_analysis import get_trending_summary
from analysis.llm import complete

load_dotenv()

# ---------------------------------------------------------------------------
# Seasonal events calendar
# Fixed-date holidays use (month, day); holidays that move every year are
# computed as the nth weekday of the month (weekday: Monday=0 … Sunday=6).
# ---------------------------------------------------------------------------

SEASONAL_EVENTS = [
    {"name": "New Year",          "month": 1,  "day": 1},
    {"name": "Valentine's Day",   "month": 2,  "day": 14},
    {"name": "Mother's Day",      "month": 5,  "nth": 2, "weekday": 6},   # 2nd Sunday of May
    {"name": "Graduation Season", "month": 5,  "day": 25},
    {"name": "Father's Day",      "month": 6,  "nth": 3, "weekday": 6},   # 3rd Sunday of June
    {"name": "Fourth of July",    "month": 7,  "day": 4},
    {"name": "Back to School",    "month": 8,  "day": 15},
    {"name": "Halloween",         "month": 10, "day": 31},
    {"name": "Thanksgiving",      "month": 11, "nth": 4, "weekday": 3},   # 4th Thursday of November
    {"name": "Christmas",         "month": 12, "day": 25},
]


def nth_weekday(year: int, month: int, nth: int, weekday: int) -> date:
    """Date of the nth given weekday in a month, e.g. the 4th Thursday of November."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def event_date(event: dict, year: int) -> date:
    """Calendar date of a seasonal event in the given year."""
    if "nth" in event:
        return nth_weekday(year, event["month"], event["nth"], event["weekday"])
    return date(year, event["month"], event["day"])


def get_upcoming_events(within_days: int = 60, today: date | None = None) -> list:
    """Return events coming up within the next N days, soonest first."""
    today = today or datetime.now(timezone.utc).date()
    upcoming = []

    for event in SEASONAL_EVENTS:
        # This year's date if it hasn't passed, otherwise next year's
        for year in (today.year, today.year + 1):
            when = event_date(event, year)
            days_away = (when - today).days
            if days_away >= 0:
                if days_away <= within_days:
                    upcoming.append({
                        "name": event["name"],
                        "date": when.strftime("%B %d"),
                        "days_away": days_away,
                    })
                break

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

    return complete(prompt, max_tokens=1000, temperature=0.7)


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
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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