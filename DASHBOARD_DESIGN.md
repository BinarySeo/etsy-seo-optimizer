# ShopSignal — Dashboard Design

**Version:** 2.0  
**Last updated:** May 2026  
**Status:** In progress

---

## Design Philosophy

The dashboard exists to answer one question every Monday morning:

> "What should I do this week?"

Every page, every chart, every number must serve that question.
If it doesn't lead to a decision or an action, it doesn't belong here.

---

## Page Structure

```
🎯 This Week's Actions    ← Main. Open this first.
🔍 Market Research        ← What's working in the market
🛠️ Fix My Listings        ← What to improve in your shop
💡 New Card Ideas         ← What to create next
📖 Reference              ← Inspiration browser
```

---

## Page 1 — 🎯 This Week's Actions

**The most important page. Designed to be read in under 2 minutes.**

### Data Sources
- GA4 — bounce rate, sessions, avg time on page per listing
- Etsy API — category tag patterns (what competitors use)
- Seasonal event calendar — upcoming holidays
- OpenAI GPT-4o-mini — synthesizes all of the above into plain English

### Layout

```
┌─────────────────────────────────────────────┐
│  Good morning! Here's what needs your       │
│  attention this week.                       │
├─────────────────────────────────────────────┤
│  📅 Father's Day in 15 days                 │
│  🔴 3 listings need attention               │
│  💡 2 new card opportunities found          │
└─────────────────────────────────────────────┘
```

### Action Cards

**Action 1 — Fix a listing (GA4 + Etsy API)**
```
🔴 "Thanks for Helping Me Grow" Card

3,023 people visited but 88% left immediately.
Something's not matching what they expected.

What top competitors use that you don't:
+ funny thank you card   (49% of market)
+ appreciation card      (20% of market)
+ thank you cards        (19% of market)

[View on Etsy ↗]
```

**Action 2 — New card opportunity (Tier 3 data)**
```
💡 Sympathy Cards

200 listings in this market. You have 0.

Start with these tags:
sympathy card · thinking of you card · handmade card
```

**Action 3 — Seasonal alert (GA4 historical + calendar)**
```
📅 Father's Day — June 15 (15 days away)

Add these tags to your cards now:
fathers day card · card for dad · funny fathers day

Last year traffic spiked week of Apr 20.
You're right on time.
```

### How Actions Are Prioritized

```
Priority 1 — High bounce + high traffic listing
             (GA4: sessions > 50, bounce > 0.7)

Priority 2 — Missing category with market demand
             (Tier 3: 200 listings, shop has 0)

Priority 3 — Seasonal event within 30 days
             (Calendar: event date - today < 30)
```

---

## Page 2 — 🔍 Market Research

**Question this page answers: "What's working in the market right now?"**

### Data Sources
- Etsy API Tier 2 + Tier 3 data (weekly collection)
- SQLite DB — week-over-week trend comparison

### Layout

Left panel: Category selector
```
• Birthday
• Thank You
• Housewarming
• Graduation
• Wedding
• Sympathy
• Life Events
• Evergreen
```

Right panel: Tag patterns for selected category
```
🔴 Essential (70%+)
   Tags that almost every listing uses.
   Not having these hurts visibility.

🟡 Strong (40-70%)
   Tags used by competitive listings.
   High impact on discoverability.

🟢 Differentiating (15-40%)
   Niche tags with less competition.
   Good for long-tail search.
```

Bottom: Trending this week
```
↑ Rising tags (vs last week)
↓ Falling tags (vs last week)
✨ Brand new tags this week
```

---

## Page 3 — 🛠️ Fix My Listings

**Question this page answers: "Which of my listings needs work and what exactly should I change?"**

### Data Sources
- GA4 — bounce rate, sessions, avg session duration per listing
- Etsy API — tag patterns for the same category as the listing
- SQLite DB — listing category mapping

### Priority System

```
🔴 High urgency
   sessions > 50 AND bounce rate > 0.70
   → Lots of people are coming but leaving immediately

🟡 Medium urgency  
   sessions > 20 AND bounce rate > 0.55
   → Worth fixing when you have time

🟢 Healthy
   bounce rate < 0.50
   → Leave it alone
```

### Listing Card Layout

```
┌─────────────────────────────────────────────┐
│ 🔴 Thanks for Helping Me Grow Card          │
│                                             │
│ 3,023 visits · 88% bounce · 25s avg time   │
│                                             │
│ Category: Thank You                         │
│                                             │
│ Tags you're missing vs market:              │
│ + funny thank you card   ← 49% of market   │
│ + appreciation card      ← 20% of market   │
│ + thank you cards        ← 19% of market   │
│                                             │
│ [View on Etsy ↗]                           │
└─────────────────────────────────────────────┘
```

### How Category Matching Works

GA4 gives us the listing URL path:
```
/listing/1883979582/thanks-for-helping-me-grow-card-plant
```

We extract the listing ID, match it to a category from the Etsy DB,
then pull tag patterns for that category to compare.

---

## Page 4 — 💡 New Card Ideas

**Question this page answers: "What should I make next?"**

### Data Sources
- Etsy API Tier 3 data — categories we don't cover
- SQLite DB — our current category coverage
- OpenAI GPT-4o-mini — design concept suggestions

### Layout

**Gap Analysis section**
```
Categories the market wants that you don't have:

1. Sympathy Cards              🔴 High demand
   200 market listings · 0 in your shop
   Essential tags: sympathy card, thinking of you card
   
2. Wedding Cards               🟡 Medium demand  
   200 listings · 0 in shop
   Essential tags: wedding card, congratulations card

3. New Job / Promotion         🟢 Growing
   35.5% of life_events listings use "new job card"
```

**AI Design Ideas section**
```
Based on your shop's style (funny + handmade illustration),
here are 3 specific card concepts to create next:

1. "Congratulations on your new job — 
    sorry about your new commute"
    → Category: Life Events
    → Tags: new job card, funny card, congratulations card

2. ...
```

**Seasonal Opportunity section**
```
Coming up in the next 90 days:

Jun 15  Father's Day       → fathers day card, card for dad
Jul 4   Fourth of July     → low greeting card demand, skip
Aug 15  Back to School     → good luck card, new chapter card
Oct 31  Halloween          → low card demand, skip
```

---

## Page 5 — 📖 Reference

**Question this page answers: "What do successful listings in my category look like?"**

### Data Sources
- Etsy API — top listings by favorites and conversion
- SQLite DB — filtered by category and run date

### Layout

Filters: Category · Sort by (favorites / conversion / price)

Listing cards showing:
- Title
- Favorites count
- Estimated conversion (favorites / views)
- Tags used
- Price
- Link to Etsy

---

## GA4 Integration Map

How GA4 data feeds each page:

| Page | GA4 Metric | How It's Used |
|------|-----------|---------------|
| This Week's Actions | bounce_rate, sessions | Identify which listing to fix first |
| This Week's Actions | weekly trend (historical) | "Last year traffic spiked on Apr 20" |
| Fix My Listings | bounce_rate, sessions, avg_session_sec | Priority ranking |
| Fix My Listings | pagePath → listing_id | Match listing to category |
| New Card Ideas | off-season traffic patterns | Evergreen opportunity signals |
| Seasonal Alert | year-over-year week comparison | Timing confidence |

---

## Naming Conventions

All user-facing text should be plain English. No technical terms.

| Technical term | Plain English |
|---------------|---------------|
| bounce rate | "left immediately" or "% who left without clicking" |
| sessions | "visits" |
| avg session duration | "average time spent" |
| TF-IDF score | (never show this to the user) |
| tag frequency | "X% of listings use this tag" |
| Tier 2 / Tier 3 | (never show this to the user) |
| run_date | "week of [date]" |
| differentiating | "niche tags" |

---

## What's Not in the Dashboard

By design, the following are not shown to the user:

- Raw TF-IDF scores
- SQL query results
- API response data
- Week numbers (always use real dates)
- Tier labels (Tier 1 / 2 / 3)
- Any metric without a clear action attached to it

---

*When adding a new feature to the dashboard, ask:*
*"What decision does this help the shop owner make?"*
*If the answer isn't clear, don't add it.*
