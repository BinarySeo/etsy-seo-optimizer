"""
app.py
------
ShopSignal Dashboard v2.0

Pages:
    1. This Week's Actions  — prioritized action list (GA4 + Etsy + AI)
    2. Market Research      — tag patterns + trends by category
    3. Fix My Listings      — GA4 diagnostics + tag gap per listing
    4. New Card Ideas       — market gap analysis + AI suggestions
    5. Reference            — top performing listings browser

Usage:
    python -m streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import json
import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from analysis.trend_analysis import get_trending_summary, get_tag_frequency
from analysis.ai_briefing import run_briefing, get_upcoming_events
from analysis.tag_analysis import analyze_all_categories
from analysis.ga4_analysis import (
    fetch_top_pages, fetch_weekly_trend,
    aggregate_by_period, get_listing_performance,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ShopSignal",
    page_icon="🌿",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def get_db():
    return EtsyDB()

@st.cache_data(ttl=300)
def load_all_listings():
    return get_db().get_listings()

@st.cache_data(ttl=300)
def load_runs():
    return get_db().get_runs()

@st.cache_data(ttl=300)
def load_trend_summary():
    return get_trending_summary(get_db())

@st.cache_data(ttl=300)
def load_latest_briefing():
    files = glob.glob("data/processed/briefing_*.txt")
    if not files:
        return None
    with open(max(files, key=os.path.getctime)) as f:
        return f.read()

@st.cache_data(ttl=3600)
def load_ga4_pages():
    return fetch_top_pages(days=365, limit=50)

@st.cache_data(ttl=3600)
def load_ga4_weekly():
    return fetch_weekly_trend(weeks=52)

@st.cache_data(ttl=300)
def load_tag_patterns():
    df = load_all_listings()
    if df.empty:
        return {}
    latest = df["run_date"].max()
    return analyze_all_categories(df[df["run_date"] == latest])

@st.cache_data(ttl=3600)
def load_latest_clusters():
    files = glob.glob("data/processed/card_clusters_*.json")
    if not files:
        return None
    with open(max(files, key=os.path.getctime)) as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_listing_id(path: str) -> str:
    match = re.search(r'/listing/(\d+)', path)
    return match.group(1) if match else None

def bounce_label(rate: float) -> str:
    if rate < 0.5:
        return "🟢 Healthy"
    elif rate < 0.7:
        return "🟡 OK"
    else:
        return "🔴 Needs attention"

def format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"

def listing_name_from_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 4:
        return parts[-1].replace("-", " ").title()[:50]
    return path

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

upcoming = get_upcoming_events(within_days=90)

with st.sidebar:
    st.title("🌿 ShopSignal")
    st.caption("Handmade Card Intelligence")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🎯 This Week's Actions",
            "🔍 Market Research",
            "🛠️ Fix My Listings",
            "💡 New Card Ideas",
            "📖 Reference",
        ],
        label_visibility="collapsed"
    )

    st.divider()

    # Run history
    runs = load_runs()
    if not runs.empty:
        st.markdown("**Last updated**")
        latest_run = runs.iloc[0]
        st.caption(f"📅 {latest_run['run_date']} — {latest_run['total_rows']} listings")

    st.divider()

    # Upcoming events
    if upcoming:
        st.markdown("**Upcoming events**")
        for event in upcoming[:3]:
            days = event['days_away']
            emoji = "🔴" if days < 14 else ("🟡" if days < 30 else "🟢")
            st.caption(f"{emoji} {event['name']} — {days}d away")

# ---------------------------------------------------------------------------
# Page 1: This Week's Actions
# ---------------------------------------------------------------------------

if page == "🎯 This Week's Actions":
    st.title("🎯 This Week's Actions")
    st.caption("Everything you need to focus on this week — in one place.")

    df_all   = load_all_listings()
    patterns = load_tag_patterns()

    if df_all.empty:
        st.warning("No market data found. Run `python -m scraper.etsy_scraper` first.")
        st.stop()

    # Load GA4
    with st.spinner("Loading your shop data..."):
        try:
            df_ga4 = load_ga4_pages()
            ga4_available = not df_ga4.empty
        except Exception:
            ga4_available = False
            df_ga4 = pd.DataFrame()

    # ── Summary bar ─────────────────────────────────────────────────────────
    next_event = upcoming[0] if upcoming else None
    urgent_listings = 0

    if ga4_available:
        df_listings = get_listing_performance(df_ga4)
        urgent_listings = len(df_listings[
            (df_listings["sessions"] > 50) & (df_listings["bounce_rate"] > 0.70)
        ])

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Next event",
        next_event["name"] if next_event else "—",
        delta=f"{next_event['days_away']} days away" if next_event else None
    )
    col2.metric("Listings needing attention", urgent_listings)
    col3.metric(
        "New opportunities",
        len([c for c in patterns if patterns[c].get("total_listings", 0) > 0])
    )

    st.divider()

    # ── Action 1: Fix a listing ──────────────────────────────────────────────
    if ga4_available:
        df_listings = get_listing_performance(df_ga4)
        urgent = df_listings[
            (df_listings["sessions"] > 50) & (df_listings["bounce_rate"] > 0.70)
        ].head(3)

        if not urgent.empty:
            st.subheader("🔴 Listings to fix this week")
            st.caption("High traffic but most visitors leave immediately.")

            for _, row in urgent.iterrows():
                name = listing_name_from_path(row["page_path"])
                avg_time = format_time(row["avg_session_sec"])

                with st.expander(f"**{name}**  —  {int(row['bounce_rate']*100)}% left immediately"):
                    col_l, col_r = st.columns(2)

                    with col_l:
                        st.markdown("**Traffic**")
                        st.metric("Visits", f"{row['sessions']:,}")
                        st.metric("Left immediately", f"{int(row['bounce_rate']*100)}%")
                        st.metric("Avg time spent", avg_time)
                        st.markdown(f"[View on Etsy ↗](https://www.etsy.com{row['page_path']})")

                    with col_r:
                        st.markdown("**What top competitors use that you might be missing**")

                        # Try to match to a category by keyword in URL
                        path_lower = row["page_path"].lower()
                        matched_category = None
                        for cat in patterns:
                            if cat.replace("_", " ") in path_lower or cat in path_lower:
                                matched_category = cat
                                break

                        # Fallback — show thank_you if plant/thank in URL
                        if not matched_category:
                            if any(k in path_lower for k in ["thank", "plant", "grow"]):
                                matched_category = "thank_you"
                            elif any(k in path_lower for k in ["birthday"]):
                                matched_category = "birthday"
                            elif any(k in path_lower for k in ["home", "housewarming"]):
                                matched_category = "housewarming"

                        if matched_category and matched_category in patterns:
                            cat_data = patterns[matched_category]
                            top_tags = (
                                cat_data.get("essential", []) +
                                cat_data.get("strong", [])
                            )[:6]
                            for tag in top_tags:
                                pct_row = cat_data["all_freq"][
                                    cat_data["all_freq"]["tag"] == tag
                                ]
                                pct = pct_row["pct"].values[0] if not pct_row.empty else 0
                                st.markdown(f"`{tag}` — {pct}% of listings use this")
                        else:
                            st.caption("Category not matched — run tag analysis first.")

    st.divider()

    # ── Action 2: Seasonal alert ─────────────────────────────────────────────
    if upcoming:
        st.subheader("📅 Seasonal alerts")
        st.caption("Add these tags now so your listings are ready in time.")

        for event in upcoming[:2]:
            days = event["days_away"]
            urgency = "🔴" if days < 14 else ("🟡" if days < 30 else "🟢")

            with st.expander(f"{urgency} **{event['name']}** — {days} days away ({event['date']})"):
                # Pull relevant tags from patterns
                event_name_lower = event["name"].lower()
                relevant_tags = []

                if "father" in event_name_lower and "seasonal" in patterns:
                    cat = patterns["seasonal"]
                    relevant_tags = cat.get("essential", []) + cat.get("strong", []) + cat.get("differentiating", [])
                    relevant_tags = [t for t in relevant_tags if "father" in t or "dad" in t]

                elif "mother" in event_name_lower and "seasonal" in patterns:
                    cat = patterns["seasonal"]
                    relevant_tags = cat.get("essential", []) + cat.get("strong", []) + cat.get("differentiating", [])
                    relevant_tags = [t for t in relevant_tags if "mother" in t or "mom" in t or "mum" in t]

                elif "graduation" in event_name_lower and "graduation" in patterns:
                    cat = patterns["graduation"]
                    relevant_tags = cat.get("essential", []) + cat.get("strong", [])

                if relevant_tags:
                    st.markdown("**Recommended tags to add now:**")
                    st.code(" · ".join(relevant_tags[:8]), language=None)
                else:
                    st.caption("Add seasonal tags relevant to this event to your listings.")

    st.divider()

    # ── Action 3: AI briefing ────────────────────────────────────────────────
    st.subheader("🤖 AI weekly briefing")
    briefing = load_latest_briefing()
    if briefing:
        st.markdown(briefing)
    else:
        st.info("No briefing yet.")
        if st.button("Generate briefing"):
            with st.spinner("Analyzing with GPT..."):
                run_briefing()
                st.cache_data.clear()
                st.rerun()

# ---------------------------------------------------------------------------
# Page 2: Market Research
# ---------------------------------------------------------------------------

elif page == "🔍 Market Research":
    st.title("🔍 Market Research")
    st.caption("What's working in the market right now — by card category.")

    df_all   = load_all_listings()
    patterns = load_tag_patterns()
    summary  = load_trend_summary()

    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.markdown("**Select category**")
        categories = sorted(patterns.keys())
        selected = st.radio(
            "Category",
            categories,
            format_func=lambda x: x.replace("_", " ").title(),
            label_visibility="collapsed"
        )

    with col_right:
        data = patterns.get(selected, {})

        if not data:
            st.warning("No data for this category.")
        else:
            st.markdown(f"### {selected.replace('_', ' ').title()} Cards")
            st.caption(f"{data['total_listings']} listings analyzed")

            # Chart
            df_freq = data["all_freq"].head(20).copy()
            df_freq["strength"] = df_freq["tag"].apply(
                lambda t: "Essential (70%+)" if t in data["essential"]
                else ("Strong (40-70%)" if t in data["strong"]
                else ("Niche (15-40%)" if t in data["differentiating"]
                else "Other"))
            )
            color_map = {
                "Essential (70%+)": "#D4543A",
                "Strong (40-70%)":  "#E8A838",
                "Niche (15-40%)":   "#4C9BE8",
                "Other":            "#CCCCCC",
            }
            fig = px.bar(
                df_freq,
                x="pct", y="tag",
                orientation="h",
                color="strength",
                color_discrete_map=color_map,
                labels={"pct": "% of listings using this tag", "tag": ""},
            )
            fig.update_layout(
                height=450, legend_title="Tag strength",
                margin=dict(l=0, r=0, t=0, b=0),
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)

            # Tag lists
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🔴 Essential**")
                st.caption("Almost everyone uses these")
                if data["essential"]:
                    for tag in data["essential"]:
                        st.code(tag, language=None)
                else:
                    st.caption("Market is fragmented — opportunity to stand out")

            with col2:
                st.markdown("**🟡 Strong**")
                st.caption("Competitive listings use these")
                for tag in data["strong"]:
                    st.code(tag, language=None)

            with col3:
                st.markdown("**🟢 Niche**")
                st.caption("Less competition, specific searches")
                for tag in data["differentiating"][:6]:
                    st.code(tag, language=None)

    st.divider()

    # Trends
    if summary:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("↑ Rising this week")
            rising = summary["rising"].rename(columns={"tag": "Keyword", "delta": "Listings gained"})
            fig_r = px.bar(
                rising[["Keyword", "Listings gained"]],
                x="Listings gained", y="Keyword",
                orientation="h", color="Listings gained",
                color_continuous_scale="reds",
            )
            fig_r.update_layout(height=300, showlegend=False, coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0))
            fig_r.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_r, use_container_width=True)

        with col_r:
            st.subheader("↓ Losing momentum")
            falling = summary["falling"].rename(columns={"tag": "Keyword", "delta": "Change"})
            fig_f = px.bar(
                falling[["Keyword", "Change"]],
                x="Change", y="Keyword",
                orientation="h", color="Change",
                color_continuous_scale="blues",
            )
            fig_f.update_layout(height=300, showlegend=False, coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0))
            fig_f.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_f, use_container_width=True)

# ---------------------------------------------------------------------------
# Page 3: Fix My Listings
# ---------------------------------------------------------------------------

elif page == "🛠️ Fix My Listings":
    st.title("🛠️ Fix My Listings")
    st.caption("Your listings ranked by urgency — with specific tags to add.")

    patterns = load_tag_patterns()

    with st.spinner("Loading your shop data from GA4..."):
        try:
            df_ga4 = load_ga4_pages()
            ga4_ok = not df_ga4.empty
        except Exception as e:
            st.error(f"Could not load GA4 data: {e}")
            st.stop()

    df_listings = get_listing_performance(df_ga4)

    if df_listings.empty:
        st.warning("No listing data found in GA4.")
        st.stop()

    # Add urgency label
    df_listings = df_listings.copy()
    df_listings["urgency"] = df_listings.apply(
        lambda r: "🔴 Fix this week" if r["sessions"] > 50 and r["bounce_rate"] > 0.70
        else ("🟡 Worth improving" if r["sessions"] > 20 and r["bounce_rate"] > 0.55
        else "🟢 Healthy"),
        axis=1
    )
    df_listings["name"] = df_listings["page_path"].apply(listing_name_from_path)
    df_listings["avg_time"] = df_listings["avg_session_sec"].apply(format_time)

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Listings tracked", len(df_listings))
    col2.metric("Need attention", len(df_listings[df_listings["urgency"].str.startswith("🔴")]))
    col3.metric("Healthy", len(df_listings[df_listings["urgency"].str.startswith("🟢")]))

    st.divider()

    # Filter
    urgency_filter = st.radio(
        "Show",
        ["All", "🔴 Fix this week", "🟡 Worth improving", "🟢 Healthy"],
        horizontal=True
    )

    df_show = df_listings if urgency_filter == "All" else df_listings[df_listings["urgency"] == urgency_filter]

    for _, row in df_show.iterrows():
        with st.expander(f"{row['urgency']}  —  **{row['name']}**"):
            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown("**Performance**")
                st.metric("Visits (1 year)", f"{row['sessions']:,}")
                st.metric("Left immediately", f"{int(row['bounce_rate']*100)}%")
                st.metric("Avg time spent", row["avg_time"])
                st.markdown(f"[View on Etsy ↗](https://www.etsy.com{row['page_path']})")

            with col_r:
                st.markdown("**Suggested tags to add**")
                path_lower = row["page_path"].lower()
                matched = None

                for cat in patterns:
                    if cat.replace("_", "") in path_lower.replace("-", ""):
                        matched = cat
                        break

                if not matched:
                    if any(k in path_lower for k in ["thank", "plant", "grow", "bagel", "matcha"]):
                        matched = "thank_you"
                    elif any(k in path_lower for k in ["birthday", "espresso", "oyster"]):
                        matched = "birthday"
                    elif any(k in path_lower for k in ["home", "housewarming"]):
                        matched = "housewarming"
                    elif any(k in path_lower for k in ["friend", "best"]):
                        matched = "friendship"
                    elif any(k in path_lower for k in ["grad", "graduation", "smarty", "bread"]):
                        matched = "graduation"
                    elif any(k in path_lower for k in ["mother", "mom", "floral"]):
                        matched = "seasonal"

                if matched and matched in patterns:
                    cat_data = patterns[matched]
                    top_tags = (
                        cat_data.get("essential", []) +
                        cat_data.get("strong", [])
                    )[:8]
                    st.caption(f"Based on **{matched.replace('_', ' ').title()}** category:")
                    for tag in top_tags:
                        pct_row = cat_data["all_freq"][cat_data["all_freq"]["tag"] == tag]
                        pct = pct_row["pct"].values[0] if not pct_row.empty else 0
                        st.markdown(f"`{tag}` — {pct}% of listings use this")
                else:
                    st.caption("Could not match to a category automatically.")

# ---------------------------------------------------------------------------
# Page 4: New Card Ideas
# ---------------------------------------------------------------------------

elif page == "💡 New Card Ideas":
    st.title("💡 New Card Ideas")
    st.caption("Card categories the market wants that you don't have yet.")

    patterns  = load_tag_patterns()
    clusters  = load_latest_clusters()
    df_all    = load_all_listings()

    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    # ── Market gaps from Tier 3 ──────────────────────────────────────────────
    st.subheader("Categories you're missing")

    tier3_categories = ["wedding", "sympathy", "life_events", "evergreen"]
    latest = df_all["run_date"].max()
    df_latest = df_all[df_all["run_date"] == latest]

    gap_rows = []
    for cat in tier3_categories:
        df_cat = df_latest[df_latest["category"] == cat]
        if df_cat.empty:
            continue
        gap_rows.append({
            "Category":     cat.replace("_", " ").title(),
            "Market listings": len(df_cat),
            "Your listings": 0,
            "Top tag": (patterns.get(cat, {}).get("strong") or ["—"])[0] if patterns.get(cat) else "—",
        })

    if gap_rows:
        df_gaps = pd.DataFrame(gap_rows)
        fig = px.bar(
            df_gaps,
            x="Market listings", y="Category",
            orientation="h",
            color="Market listings",
            color_continuous_scale="oranges",
            labels={"Market listings": "Listings in market", "Category": ""},
        )
        fig.update_layout(height=250, coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        for row in gap_rows:
            cat_key = row["Category"].lower().replace(" ", "_")
            cat_data = patterns.get(cat_key, {})
            essential = cat_data.get("essential", [])
            strong    = cat_data.get("strong", [])
            top_tags  = (essential + strong)[:6]

            with st.expander(f"**{row['Category']}** — {row['Market listings']} listings in market, 0 in your shop"):
                st.markdown("**Start with these tags:**")
                if top_tags:
                    st.code(" · ".join(top_tags), language=None)
                else:
                    st.caption("Run tag analysis to see tag recommendations.")

    st.divider()

    # ── AI suggestions ───────────────────────────────────────────────────────
    st.subheader("💡 AI design suggestions")

    if clusters and "new_card_ideas" in clusters:
        for idea in clusters["new_card_ideas"]:
            with st.expander(f"✨ {idea['title']}"):
                st.write(idea["reason"])
    else:
        st.info("No AI suggestions yet. Run `python -m analysis.ga4_analysis` to generate.")

    st.divider()

    # ── Seasonal opportunities ───────────────────────────────────────────────
    st.subheader("📅 Upcoming seasonal opportunities")
    st.caption("Plan ahead — start creating 6-8 weeks before each event.")

    if upcoming:
        for event in upcoming[:5]:
            days  = event["days_away"]
            emoji = "🔴" if days < 21 else ("🟡" if days < 45 else "🟢")
            st.markdown(f"{emoji} **{event['name']}** — {event['date']} ({days} days away)")
    else:
        st.caption("No upcoming events in the next 90 days.")

# ---------------------------------------------------------------------------
# Page 5: Reference
# ---------------------------------------------------------------------------

elif page == "📖 Reference":
    st.title("📖 Reference")
    st.caption("Browse top performing listings for design inspiration.")

    df_all = load_all_listings()
    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    latest   = df_all["run_date"].max()
    df_latest = df_all[df_all["run_date"] == latest].copy()
    df_latest["saves_per_view"] = (
        df_latest["num_favorers"] / df_latest["views"].replace(0, 1)
    ).round(4)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        categories = ["All"] + sorted(df_latest["category"].dropna().unique().tolist())
        cat_filter = st.selectbox("Category", categories, format_func=lambda x: x.replace("_", " ").title() if x != "All" else "All")
    with col2:
        sort_options = {
            "num_favorers":  "Most favorited",
            "saves_per_view": "Best conversion",
            "views":          "Most viewed",
            "price_usd":      "Price",
        }
        sort_by = st.selectbox("Sort by", list(sort_options.keys()), format_func=lambda x: sort_options[x])
    with col3:
        top_n = st.slider("Show top", 10, 50, 20)

    df_show = df_latest.copy()
    if cat_filter != "All":
        df_show = df_show[df_show["category"] == cat_filter]
    df_show = df_show.sort_values(sort_by, ascending=False).head(top_n)

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg favorites", f"{df_show['num_favorers'].mean():.0f}")
    col2.metric("Avg conversion", f"{df_show['saves_per_view'].mean():.3f}")
    col3.metric("Avg price", f"${df_show['price_usd'].mean():.2f}")

    st.divider()

    st.dataframe(
        df_show.rename(columns={
            "title":          "Title",
            "price_usd":      "Price ($)",
            "num_favorers":   "Favorites",
            "views":          "Views",
            "saves_per_view": "Saves per view",
            "tags":           "Tags",
            "url":            "Link",
            "category":       "Category",
        })[["Title", "Category", "Price ($)", "Favorites", "Views", "Saves per view", "Tags", "Link"]],
        use_container_width=True,
        hide_index=True,
    )