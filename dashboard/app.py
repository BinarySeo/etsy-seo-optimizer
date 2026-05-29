"""
app.py
------
Streamlit dashboard for Etsy SEO Optimizer.
Pages:
    1. Weekly Briefing  — AI summary + rising tags + new keywords
    2. Trend Analysis   — tag frequency over time
    3. SEO Optimizer    — keyword opportunity scores + recommended tags
    4. Reference Gallery — top performing listings
    5. GA4 Analytics    — traffic data, card clusters, AI insights

Usage:
    python -m streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from analysis.trend_analysis import get_trending_summary, get_tag_frequency
from analysis.ai_briefing import run_briefing, get_upcoming_events
from analysis.ga4_analysis import (
    fetch_top_pages, fetch_traffic_sources, fetch_weekly_trend,
    fetch_device_breakdown, fetch_day_of_week, fetch_new_vs_returning,
    aggregate_by_period, get_listing_performance, generate_traffic_insights,
    cluster_listings
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Etsy SEO Optimizer",
    page_icon="🌿",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loaders — cached so they don't re-fetch on every interaction
# ---------------------------------------------------------------------------

@st.cache_resource
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
def load_ga4_sources():
    return fetch_traffic_sources(days=365)

@st.cache_data(ttl=3600)
def load_ga4_weekly():
    return fetch_weekly_trend(weeks=52)

@st.cache_data(ttl=3600)
def load_ga4_devices():
    return fetch_device_breakdown(days=365)

@st.cache_data(ttl=3600)
def load_ga4_dow():
    return fetch_day_of_week(days=365)

@st.cache_data(ttl=3600)
def load_ga4_new_returning():
    return fetch_new_vs_returning(days=365)

@st.cache_data(ttl=3600)
def load_latest_clusters():
    """Load most recent card clusters JSON from disk."""
    files = glob.glob("data/processed/card_clusters_*.json")
    if not files:
        return None
    with open(max(files, key=os.path.getctime)) as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def load_latest_ga4_insights():
    """Load most recent GA4 AI insights from disk."""
    files = glob.glob("data/processed/ga4_insights_*.txt")
    if not files:
        return None
    with open(max(files, key=os.path.getctime)) as f:
        return f.read()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

upcoming = get_upcoming_events(within_days=90)

with st.sidebar:
    st.title("🌿 Etsy SEO Optimizer")
    st.caption("Handmade Card Analytics")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠 Weekly Briefing",
            "📈 Trend Analysis",
            "🎯 SEO Optimizer",
            "🖼️ Reference Gallery",
            "📊 GA4 Analytics",
        ],
        label_visibility="collapsed"
    )

    st.divider()

    runs = load_runs()
    if not runs.empty:
        st.markdown("**Run History**")
        for _, run in runs.iterrows():
            st.caption(f"📅 {run['run_date']} — {run['total_rows']} listings")

    st.divider()

    if upcoming:
        st.markdown("**Upcoming Events**")
        for event in upcoming[:3]:
            st.info(f"🗓️ {event['name']} — in {event['days_away']} days")

# ---------------------------------------------------------------------------
# Page: Weekly Briefing
# ---------------------------------------------------------------------------

if page == "🏠 Weekly Briefing":
    st.title("🏠 Weekly Briefing")

    df_all = load_all_listings()
    summary = load_trend_summary()

    if df_all.empty:
        st.warning("No data found. Run `python -m scraper.mock_data` first.")
        st.stop()

    latest_run   = df_all["run_date"].max()
    df_latest    = df_all[df_all["run_date"] == latest_run]
    new_tags_count = len(summary.get("new_tags", [])) if summary else 0
    next_event   = upcoming[0] if upcoming else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Listings Analyzed", f"{len(df_latest):,}")
    col2.metric("Avg Favorites", f"{df_latest['num_favorers'].mean():.0f}")
    col3.metric("New Keywords This Week", new_tags_count)
    col4.metric(
        "Next Big Event",
        next_event["name"] if next_event else "—",
        delta=f"in {next_event['days_away']} days" if next_event else None
    )

    st.divider()
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🤖 AI Weekly Briefing")
        briefing = load_latest_briefing()
        if briefing:
            st.markdown(briefing)
        else:
            st.info("No briefing generated yet.")
            if st.button("Generate This Week's Briefing"):
                with st.spinner("Analyzing trends with GPT..."):
                    run_briefing()
                    st.cache_data.clear()
                    st.rerun()

    with col_right:
        st.subheader("🔥 Trending Up This Week")
        if summary and not summary["rising"].empty:
            rising = summary["rising"].head(8).copy()
            rising = rising.rename(columns={"tag": "Keyword", "delta": "Gained listings"})
            fig = px.bar(
                rising, x="Gained listings", y="Keyword",
                orientation="h", color="Gained listings",
                color_continuous_scale="reds",
            )
            fig.update_layout(
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=0, b=0), height=280,
            )
            fig.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("✨ Brand New Keywords")
        if summary and summary["new_tags"]:
            st.write(" · ".join([f"`{tag}`" for tag in summary["new_tags"]]))
        else:
            st.caption("No brand new keywords this week.")

# ---------------------------------------------------------------------------
# Page: Trend Analysis
# ---------------------------------------------------------------------------

elif page == "📈 Trend Analysis":
    st.title("📈 Trend Analysis")
    st.caption("See how keywords are rising or falling week over week")

    df_all   = load_all_listings()
    summary  = load_trend_summary()

    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    run_dates = sorted(df_all["run_date"].unique())
    records   = []
    for run_date in run_dates:
        freq = get_tag_frequency(df_all[df_all["run_date"] == run_date], top_n=20)
        for _, row in freq.iterrows():
            records.append({"run_date": run_date, "tag": row["tag"], "count": row["count"]})

    df_trend  = pd.DataFrame(records)
    all_tags  = df_trend["tag"].unique().tolist()
    default_tags = [t for t in summary["rising"]["tag"].head(5).tolist() if t in all_tags] if summary else all_tags[:5]

    selected_tags = st.multiselect(
        "Select keywords to track", options=all_tags, default=default_tags
    )

    if selected_tags:
        fig = px.line(
            df_trend[df_trend["tag"].isin(selected_tags)],
            x="run_date", y="count", color="tag", markers=True,
            labels={"run_date": "Week", "count": "Listings using keyword", "tag": "Keyword"},
            title="Keyword usage over time",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if summary:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("🔥 Rising This Week")
            st.caption("Used more than last week")
            rising = summary["rising"].rename(columns={"tag": "Keyword", "delta": "Change"})
            fig_r = px.bar(
                rising[["Keyword", "Change"]], x="Change", y="Keyword",
                orientation="h", color="Change", color_continuous_scale="reds",
                labels={"Change": "Listings gained"},
            )
            fig_r.update_layout(height=320, showlegend=False, coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0))
            fig_r.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_r, use_container_width=True)

        with col_r:
            st.subheader("📉 Losing Steam")
            st.caption("Used less than last week")
            falling = summary["falling"].rename(columns={"tag": "Keyword", "delta": "Change"})
            fig_f = px.bar(
                falling[["Keyword", "Change"]], x="Change", y="Keyword",
                orientation="h", color="Change", color_continuous_scale="blues",
                labels={"Change": "Listings lost"},
            )
            fig_f.update_layout(height=320, showlegend=False, coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0))
            fig_f.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_f, use_container_width=True)

# ---------------------------------------------------------------------------
# Page: SEO Optimizer
# ---------------------------------------------------------------------------

elif page == "🎯 SEO Optimizer":
    st.title("🎯 SEO Optimizer")
    st.caption("Find the best keywords to add to your listings right now")

    df_all = load_all_listings()
    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    df_latest = df_all[df_all["run_date"] == df_all["run_date"].max()]
    freq = get_tag_frequency(df_latest, top_n=50)
    freq["recommendation_score"] = (freq["count"] / freq["count"].max() * 100).round(1)
    freq["how_competitive"] = freq["count"].apply(
        lambda x: "🔴 Very competitive" if x > 100 else ("🟡 Moderate" if x > 60 else "🟢 Less competitive")
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📊 Keyword Recommendation Map")
        st.caption("Bigger bubble = used by more listings. Higher = stronger recommendation.")
        fig = px.scatter(
            freq.head(30).rename(columns={"tag": "Keyword", "count": "Used by listings", "recommendation_score": "Score"}),
            x="Used by listings", y="Score", text="Keyword",
            size="Used by listings", color="Score", color_continuous_scale="oranges",
        )
        fig.update_traces(textposition="top center", textfont_size=9)
        fig.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏷️ Top 13 Tags to Use Now")
        st.caption("Etsy allows 13 tags per listing. Copy and paste:")
        st.code(", ".join(freq.head(13)["tag"].tolist()), language=None)

    st.divider()
    st.subheader("📋 Full Keyword Table")
    st.dataframe(
        freq.rename(columns={
            "tag": "Keyword", "count": "Used by # listings",
            "pct": "% of listings", "how_competitive": "Competition",
            "recommendation_score": "Recommendation Score"
        })[["Keyword", "Used by # listings", "% of listings", "Competition", "Recommendation Score"]],
        use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------------------
# Page: Reference Gallery
# ---------------------------------------------------------------------------

elif page == "🖼️ Reference Gallery":
    st.title("🖼️ Reference Gallery")
    st.caption("Browse top performing listings for design inspiration")

    df_all = load_all_listings()
    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    df_latest = df_all[df_all["run_date"] == df_all["run_date"].max()].copy()
    df_latest["saves_per_view"] = (
        df_latest["num_favorers"] / df_latest["views"].replace(0, 1)
    ).round(4)

    col1, col2, col3 = st.columns(3)
    with col1:
        query_filter = st.selectbox("Filter by search term", ["All"] + list(df_latest["query"].unique()))
    with col2:
        sort_options = {
            "num_favorers": "Most Favorited",
            "saves_per_view": "Best Conversion",
            "views": "Most Viewed",
            "price_usd": "Price",
        }
        sort_by = st.selectbox("Sort by", list(sort_options.keys()), format_func=lambda x: sort_options[x])
    with col3:
        top_n = st.slider("How many to show", 10, 50, 20)

    df_gallery = df_latest.copy()
    if query_filter != "All":
        df_gallery = df_gallery[df_gallery["query"] == query_filter]
    df_gallery = df_gallery.sort_values(sort_by, ascending=False).head(top_n)

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Favorites", f"{df_gallery['num_favorers'].mean():.0f}")
    col2.metric("Avg Saves per View", f"{df_gallery['saves_per_view'].mean():.3f}")
    col3.metric("Avg Price", f"${df_gallery['price_usd'].mean():.2f}")

    st.divider()
    st.dataframe(
        df_gallery.rename(columns={
            "title": "Title", "price_usd": "Price ($)",
            "num_favorers": "Favorites", "views": "Views",
            "saves_per_view": "Saves per View", "tags": "Tags", "url": "Link",
        })[["Title", "Price ($)", "Favorites", "Views", "Saves per View", "Tags", "Link"]],
        use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------------------
# Page: GA4 Analytics
# ---------------------------------------------------------------------------

elif page == "📊 GA4 Analytics":
    st.title("📊 GA4 Analytics")
    st.caption("Real traffic data from your Etsy shop — last 12 months")

    # Load all GA4 data
    with st.spinner("Loading GA4 data..."):
        df_pages      = load_ga4_pages()
        df_sources    = load_ga4_sources()
        df_weekly     = load_ga4_weekly()
        df_devices    = load_ga4_devices()
        df_dow        = load_ga4_dow()
        df_new_ret    = load_ga4_new_returning()
        clusters      = load_latest_clusters()
        ga4_insights  = load_latest_ga4_insights()

    # ── KPI row ──────────────────────────────────────────────────────────────
    total_sessions  = df_pages["sessions"].sum()
    top_page        = df_pages.iloc[0]["page_path"].split("/")[-1].replace("-", " ").title() if not df_pages.empty else "—"
    mobile_pct      = int(df_devices[df_devices["device"] == "mobile"]["sessions"].sum() / df_devices["sessions"].sum() * 100) if not df_devices.empty else 0
    returning_pct   = int(df_new_ret[df_new_ret["visitor_type"] == "returning"]["sessions"].sum() / df_new_ret["sessions"].sum() * 100) if not df_new_ret.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sessions (1yr)", f"{total_sessions:,}")
    col2.metric("Top Listing", top_page[:30] + "..." if len(top_page) > 30 else top_page)
    col3.metric("Mobile Traffic", f"{mobile_pct}%")
    col4.metric("Returning Visitors", f"{returning_pct}%")

    st.divider()

    # ── Traffic Over Time ─────────────────────────────────────────────────────
    st.subheader("📅 Traffic Over Time")

    period = st.radio(
        "Group by",
        ["Weekly", "Monthly", "Quarterly", "Yearly"],
        horizontal=True,
    )

    df_period = aggregate_by_period(df_weekly, period.lower())

    fig_trend = px.bar(
        df_period, x="period", y="sessions",
        labels={"period": "", "sessions": "Sessions"},
        color="sessions",
        color_continuous_scale="teal",
    )
    fig_trend.update_layout(
        height=350, coloraxis_showscale=False,
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()

    # ── Traffic Sources + Device breakdown ───────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("🌐 Where Visitors Come From")
        st.caption("`(direct)` = Etsy app, bookmarks, or DMs — source unknown")

        # Clean up source labels
        df_src = df_sources.copy()
        df_src["source_label"] = df_src["source"] + " / " + df_src["medium"]
        df_src = df_src[~df_src["source"].isin(["(data not available)", "(not set)"])]

        fig_src = px.bar(
            df_src.head(8),
            x="sessions", y="source_label",
            orientation="h",
            color="sessions",
            color_continuous_scale="blues",
            labels={"sessions": "Sessions", "source_label": ""},
        )
        fig_src.update_layout(
            height=320, coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        fig_src.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_src, use_container_width=True)

    with col_r:
        st.subheader("📱 Device Breakdown")
        st.caption("High mobile bounce rate = check how photos look on phone")

        fig_dev = px.pie(
            df_devices, values="sessions", names="device",
            color_discrete_sequence=["#4C9BE8", "#F4A261", "#6B8F71"],
            hole=0.4,
        )
        fig_dev.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_dev, use_container_width=True)

        # Device table
        df_dev_display = df_devices.rename(columns={
            "device": "Device",
            "sessions": "Sessions",
            "bounce_rate": "Bounce Rate",
            "avg_session_sec": "Avg Time (sec)",
        })
        st.dataframe(df_dev_display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Day of Week + New vs Returning ───────────────────────────────────────
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.subheader("📆 Best Days to Post")
        st.caption("Post on your highest-traffic days for maximum visibility")

        fig_dow = px.bar(
            df_dow, x="day", y="sessions",
            color="sessions",
            color_continuous_scale="oranges",
            labels={"day": "", "sessions": "Sessions"},
        )
        fig_dow.update_layout(
            height=280, coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig_dow, use_container_width=True)

    with col_r2:
        st.subheader("👥 New vs Returning Visitors")
        st.caption("Low returning % = people aren't coming back after first visit")

        df_nr = df_new_ret[df_new_ret["visitor_type"] != "(not set)"].copy()
        fig_nr = px.pie(
            df_nr, values="sessions", names="visitor_type",
            color_discrete_sequence=["#4C9BE8", "#F4A261"],
            hole=0.4,
        )
        fig_nr.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_nr, use_container_width=True)

        df_nr_display = df_nr.rename(columns={
            "visitor_type": "Visitor Type",
            "sessions": "Sessions",
            "bounce_rate": "Bounce Rate",
        })
        st.dataframe(df_nr_display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Top Listings Performance ──────────────────────────────────────────────
    st.subheader("🏆 Top Listing Performance")
    st.caption("How your individual listings are performing")

    df_listings = get_listing_performance(df_pages).copy()

    # Extract readable name from URL
    df_listings["listing_name"] = df_listings["page_path"].apply(
        lambda x: x.split("/")[-1].replace("-", " ").title()[:50]
    )

    # Color-code bounce rate
    def bounce_label(rate):
        if rate < 0.4:
            return "🟢 Good"
        elif rate < 0.6:
            return "🟡 OK"
        else:
            return "🔴 High"

    df_listings["bounce_label"] = df_listings["bounce_rate"].apply(bounce_label)
    df_listings["avg_time"] = df_listings["avg_session_sec"].apply(
        lambda x: f"{int(x//60)}m {int(x%60)}s"
    )

    st.dataframe(
        df_listings[[
            "listing_name", "sessions", "views",
            "bounce_label", "avg_time"
        ]].rename(columns={
            "listing_name": "Listing",
            "sessions": "Sessions",
            "views": "Views",
            "bounce_label": "Bounce Rate",
            "avg_time": "Avg Time on Page",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Card Clusters ─────────────────────────────────────────────────────────
    st.subheader("🗂️ Card Category Analysis")
    st.caption("AI-grouped card categories — what's strong, what's missing")

    if clusters:
        cluster_list = clusters.get("clusters", [])

        if cluster_list:
            # Build summary DataFrame for chart
            df_clusters = pd.DataFrame([{
                "Category":        c["category"],
                "Sessions":        c["total_sessions"],
                "Avg Bounce Rate": c["avg_bounce_rate"],
                "Performance":     c["performance"],
            } for c in cluster_list])

            col_cl, col_cr = st.columns([2, 1])

            with col_cl:
                fig_cl = px.bar(
                    df_clusters.sort_values("Sessions", ascending=True),
                    x="Sessions", y="Category",
                    orientation="h",
                    color="Avg Bounce Rate",
                    color_continuous_scale="RdYlGn_r",
                    labels={"Sessions": "Total Sessions", "Category": ""},
                    title="Sessions per category (color = bounce rate, green = good)",
                )
                fig_cl.update_layout(height=350, coloraxis_showscale=True)
                st.plotly_chart(fig_cl, use_container_width=True)

            with col_cr:
                st.markdown("**Performance by category**")
                for c in cluster_list:
                    emoji = "🟢" if c["performance"] == "strong" else "🟡"
                    st.markdown(f"{emoji} **{c['category']}**")
                    st.caption(f"{c['total_sessions']} sessions · bounce {c['avg_bounce_rate']}")

        # Missing categories
        missing = clusters.get("missing_categories", [])
        if missing:
            st.markdown("---")
            st.markdown("**❌ Missing Categories — Big Opportunities**")
            cols = st.columns(len(missing))
            for i, cat in enumerate(missing):
                cols[i].error(f"🚫 {cat}")

        # New card ideas
        ideas = clusters.get("new_card_ideas", [])
        if ideas:
            st.markdown("---")
            st.markdown("**💡 New Card Ideas from AI**")
            for idea in ideas:
                with st.expander(f"✨ {idea['title']}"):
                    st.write(idea["reason"])

    else:
        st.info("No cluster data yet. Run `python -m analysis.ga4_analysis` first.")
        if st.button("Run Cluster Analysis Now"):
            with st.spinner("Analyzing listings with AI..."):
                df_pages_fresh = fetch_top_pages(days=365, limit=50)
                result = cluster_listings(df_pages_fresh)
                os.makedirs("data/processed", exist_ok=True)
                from datetime import datetime
                with open(f"data/processed/card_clusters_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(result, f, indent=2)
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # ── AI Insights ───────────────────────────────────────────────────────────
    st.subheader("🤖 AI Traffic Insights")
    st.caption("Why traffic spiked, how to grow organic traffic, Pinterest strategy")

    if ga4_insights:
        st.markdown(ga4_insights)
    else:
        st.info("No insights yet.")
        if st.button("Generate AI Insights"):
            with st.spinner("Analyzing 1 year of traffic data..."):
                insights = generate_traffic_insights(
                    df_weekly, df_sources, df_pages,
                    df_devices, df_dow, df_new_ret
                )
                os.makedirs("data/processed", exist_ok=True)
                from datetime import datetime
                with open(f"data/processed/ga4_insights_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
                    f.write(insights)
                st.cache_data.clear()
                st.rerun()