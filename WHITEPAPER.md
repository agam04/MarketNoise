# MarketNoise — Technical Whitepaper

**Version 1.0 · April 2026**
**Authors:** Agam Gupta, Aryan Shah

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [Database Design](#5-database-design)
6. [Backend — Analysis Engine](#6-backend--analysis-engine)
7. [NLP Pipeline: FinBERT + VADER](#7-nlp-pipeline-finbert--vader)
8. [Scoring: Sentiment, Velocity, Hype](#8-scoring-sentiment-velocity-hype)
9. [Pattern Classification — 6 Archetypes](#9-pattern-classification--6-archetypes)
10. [Narrative Drift & Shift Detection](#10-narrative-drift--shift-detection)
11. [LLM Narrative Summary](#11-llm-narrative-summary)
12. [ML Price-Impact Model](#12-ml-price-impact-model)
13. [Background Scraping](#13-background-scraping)
14. [Authentication & Security](#14-authentication--security)
15. [Watchlist](#15-watchlist)
16. [API Reference](#16-api-reference)
17. [Caching Strategy](#17-caching-strategy)
18. [Frontend Architecture](#18-frontend-architecture)
19. [Gamification System](#19-gamification-system)
20. [Data Flow — End to End](#20-data-flow--end-to-end)
21. [Design Decisions & Trade-offs](#21-design-decisions--trade-offs)
22. [How to Run Locally](#22-how-to-run-locally)
23. [Roadmap](#23-roadmap)

---

## 1. Product Vision

**MarketNoise** is a narrative intelligence platform for retail investors. It does not predict stock prices. Instead, it answers a more actionable question: **is the attention around this stock information-driven or just noise?**

Financial markets are as much driven by narratives as by fundamentals. A stock can surge on a Reddit post, a viral tweet, or a wave of breathless coverage — and then crash when the story fades. Most retail investors have no way to separate signal from hype.

MarketNoise surfaces four dimensions of the narrative around any US-listed stock in real time:

| Signal | Question answered |
|---|---|
| **Sentiment Score** | Is the coverage bullish, bearish, or mixed? |
| **Narrative Velocity** | Is attention growing, stable, or cooling? |
| **Hype Risk Score** | Is this information-driven or hype-driven coverage? |
| **Pattern Archetype** | Which of 6 known narrative dynamics is this stock in? |

And two deeper historical views:
- **Narrative Drift** — how has sentiment evolved over 7 / 30 / 90 days, and when did it last shift?
- **AI Summary** — a one-paragraph narrative intelligence brief, generated on demand.

The product also includes an **AI chat interface** so users can ask natural-language questions about a stock's narrative ("Why is NVDA trending?" "Is this hype or real?"), powered by their own Gemini or Groq API keys.

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│                     React 19 + TypeScript                       │
│   HomePage  ·  StockPage  ·  WatchlistPage  ·  SettingsPage     │
│                  Vite dev server (port 5173)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP /api/*  (Vite proxy in dev)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DJANGO REST API  (port 8000)                │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │  market_views.py │  │   views.py   │  │  users/views   │    │
│  │  (all analysis   │  │  (DRF CRUD   │  │  (register,    │    │
│  │   + chat + wlist)│  │   viewsets)  │  │   login, keys) │    │
│  └────────┬─────────┘  └──────────────┘  └────────────────┘    │
│           │                                                     │
│  ┌────────▼──────────────────────────────────────────────────┐  │
│  │                  ANALYSIS PIPELINE                        │  │
│  │   analysis.py → drift.py → patterns.py → llm.py          │  │
│  │   FinBERT / VADER scoring  ·  exp-decay weighting         │  │
│  └────────┬──────────────────────────────────────────────────┘  │
│           │                                                     │
│  ┌────────▼──────────────────────────────────────────────────┐  │
│  │            DJANGO ORM  /  SQLite (dev) · PostgreSQL (prod)│  │
│  │   Stock · Narrative · SentimentScore · VelocityMetric     │  │
│  │   HypeScore · PriceImpact · Watchlist · UserAPIKey        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┘  Celery tasks (async)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│               BACKGROUND SCRAPERS  (every 30 min)               │
│     RSS feeds  ·  GNews API  ·  Reddit (PRAW)                   │
│     → create Narrative records → auto-score with FinBERT        │
└─────────────────────────────────────────────────────────────────┘

           External services
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐
│ Twelve Data  │  │  GNews API   │  │ Gemini API   │  │  Groq  │
│ (price OHLCV)│  │  (news art.) │  │ (LLM chat/   │  │  API   │
└──────────────┘  └──────────────┘  │  summary)    │  └────────┘
                                    └──────────────┘
```

The architecture follows a clean separation of concerns:

- **Frontend** is purely presentation — it fetches data and renders it. It never touches raw NLP or scoring.
- **Backend API** is stateless from the client's perspective — each request either runs the analysis pipeline or returns cached results.
- **Analysis pipeline** is idempotent — re-running it for the same ticker just updates existing DB records.
- **Scrapers** run independently via Celery and pre-populate the DB so analysis requests are fast.

---

## 3. Tech Stack

### Frontend

| Tool | Role |
|---|---|
| React 19 + TypeScript | UI component tree |
| Vite | Dev server, HMR, build, `/api` proxy |
| Tailwind CSS v4 | Styling — custom dark-theme tokens (`surface`, `brand`, `danger`) |
| React Router v6 | Client-side routing |
| Recharts | AreaChart for Narrative Timeline |
| Lucide React | Icon system |
| Context API | Auth state (`AuthContext`), Gamification state (`GamificationContext`) |
| localStorage | Gamification XP persistence, game-mode preference, refresh tokens |

### Backend

| Tool | Role |
|---|---|
| Python 3.13 | Runtime |
| Django 4.2 | Web framework, ORM, admin |
| Django REST Framework | Serializers, ViewSets, response formatting |
| SimpleJWT | JWT access + refresh tokens |
| Celery 5 | Async task queue (background scrapers) |
| Redis | Celery broker + Django cache backend |
| SQLite | Dev database (zero config) |
| PostgreSQL | Production database |
| Gunicorn | Production WSGI server |

### NLP / ML

| Tool | Role |
|---|---|
| HuggingFace Transformers | FinBERT model loading + inference |
| ProsusAI/finbert | Primary NLP model (pre-trained on financial text) |
| Apple MPS (Metal) | GPU acceleration on Apple Silicon — no CUDA needed |
| NLTK VADER | Fallback sentiment when FinBERT unavailable |
| scikit-learn | Random Forest classifier for price-impact ML model |
| cryptography (Fernet) | Symmetric encryption for user API keys |

### Data Sources

| Source | What it provides | Quota |
|---|---|---|
| GNews API | News articles by ticker keyword | 100 req/day (free) |
| Twelve Data | Live price quotes, OHLCV time series | 800 req/day (free) |
| yfinance | Historical data, earnings dates (backtesting) | Unlimited |
| RSS feeds | Free news without API quota | Unlimited |
| Reddit (PRAW) | Social narrative data | Rate-limited |

---

## 4. Directory Structure

```
Market-Noise/
├── WHITEPAPER.md                    ← This document
├── info.txt                         ← Raw technical reference
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx         ← Hero + Daily Challenge + live feed
│   │   │   ├── StockPage.tsx        ← Full stock analysis (2-col layout)
│   │   │   ├── WatchlistPage.tsx    ← Saved tickers with latest signals
│   │   │   ├── LoginPage.tsx        ← JWT login
│   │   │   ├── RegisterPage.tsx     ← Account creation
│   │   │   └── SettingsPage.tsx     ← API key management
│   │   ├── components/
│   │   │   ├── Navbar.tsx           ← Nav links + auth state + XP chip
│   │   │   ├── SearchBar.tsx        ← Debounced autocomplete (Twelve Data)
│   │   │   ├── PriceChart.tsx       ← OHLCV chart with 1D/7D/1M/3M selector
│   │   │   ├── AnalysisSection.tsx  ← 4-card grid: sentiment/vel/hype/pattern
│   │   │   ├── PatternCard.tsx      ← Narrative archetype display
│   │   │   ├── NarrativeTimeline.tsx← Recharts drift chart + window stats
│   │   │   ├── NarrativeSummaryCard.tsx ← AI narrative paragraph
│   │   │   ├── NarrativeFeedCard.tsx← Homepage feed card (per ticker)
│   │   │   ├── ChatPanel.tsx        ← AI chat (right sidebar on desktop)
│   │   │   ├── NewsSection.tsx      ← Recent news articles
│   │   │   ├── WatchButton.tsx      ← Bookmark with animation + toast
│   │   │   ├── GamificationPanel.tsx← Slide-in XP/missions/badges drawer
│   │   │   ├── XPToast.tsx          ← Floating "+N XP" toast notifications
│   │   │   ├── Confetti.tsx         ← Canvas confetti on milestone events
│   │   │   └── DailyChallenge.tsx   ← Quiz card (+50 XP for correct answer)
│   │   ├── contexts/
│   │   │   ├── AuthContext.tsx      ← JWT state, getAccessToken() with refresh
│   │   │   └── GamificationContext.tsx ← XP/level/missions reducer + localStorage
│   │   ├── services/
│   │   │   ├── analysisService.ts   ← fetchAnalysis / fetchDrift / fetchTrending
│   │   │   ├── stockService.ts      ← fetchChartData / fetchQuote
│   │   │   ├── searchService.ts     ← Autocomplete
│   │   │   ├── newsService.ts       ← News articles
│   │   │   ├── chatService.ts       ← AI chat
│   │   │   ├── watchlistService.ts  ← Watchlist CRUD
│   │   │   └── authService.ts       ← Login / register
│   │   └── types/
│   │       └── stock.ts             ← Shared TypeScript interfaces
│   ├── vite.config.ts               ← /api proxy → localhost:8000
│   └── index.css                    ← Global styles, custom animations
│
└── backend/
    ├── config/
    │   ├── settings.py              ← Django settings, JWT config, cache
    │   ├── celery.py                ← Celery app + beat schedule (30 min)
    │   └── urls.py                  ← Root URL configuration
    ├── api/
    │   ├── models.py                ← All DB models (8 models)
    │   ├── analysis.py              ← Main analysis pipeline
    │   ├── drift.py                 ← Narrative drift + shift detection
    │   ├── patterns.py              ← 6-archetype pattern classifier
    │   ├── llm.py                   ← Gemini/Groq integration
    │   ├── market_views.py          ← All HTTP endpoints
    │   ├── urls.py                  ← API URL routing
    │   ├── views.py                 ← DRF CRUD viewsets
    │   ├── serializers.py           ← DRF serializers
    │   ├── price_tracker.py         ← Price impact tracking (for ML training)
    │   ├── nlp/
    │   │   └── finbert.py           ← FinBERT singleton, MPS/CUDA/CPU
    │   ├── ml/
    │   │   ├── features.py          ← Feature extraction
    │   │   ├── trainer.py           ← Model training
    │   │   └── predictor.py         ← Inference
    │   ├── scrapers/
    │   │   ├── rss_scraper.py       ← RSS feed parser
    │   │   ├── gnews_scraper.py     ← GNews API client
    │   │   └── reddit_scraper.py    ← Reddit PRAW client
    │   └── management/commands/
    │       ├── scrape_narratives.py ← Manual scrape trigger
    │       ├── train_model.py       ← Train ML model
    │       ├── backtest.py          ← Sentiment vs price correlation
    │       ├── backtest_events.py   ← Earnings-event backtester
    │       ├── backfill_prices.py   ← Historical price backfill
    │       └── dataset_stats.py     ← DB statistics report
    ├── users/
    │   ├── models.py                ← User + UserAPIKey (encrypted)
    │   ├── views.py                 ← Register / login / key CRUD
    │   ├── encryption.py            ← Fernet key encryption
    │   └── urls.py
    ├── tasks/                       ← Celery task definitions
    └── ml_models/                   ← Serialized .pkl model files
```

---

## 5. Database Design

Eight Django models capture the full data lifecycle from raw article to scored insight.

### Stock
The root entity. One record per tracked ticker.

```
Stock
├── ticker          VARCHAR(10)  [unique, indexed]
├── name            VARCHAR(200)
├── sector          VARCHAR(100)
├── exchange        VARCHAR(50)
└── is_active       BOOLEAN
```

### Narrative
A single news article or social media post. The raw input unit.

```
Narrative
├── stock           FK → Stock
├── title           VARCHAR(500)
├── content         TEXT
├── source          ENUM(news, rss, reddit, twitter, other)
├── source_name     VARCHAR(200)
├── url             URLField  [unique constraint on non-empty]
└── published_at    DATETIME
```

### SentimentScore
The FinBERT/VADER result for one Narrative. OneToOne relationship.

```
SentimentScore
├── narrative       OneToOne → Narrative
├── stock           FK → Stock          [indexed with analyzed_at]
├── label           ENUM(positive, negative, neutral, mixed)
├── positive_score  FLOAT
├── negative_score  FLOAT
├── neutral_score   FLOAT
└── compound_score  FLOAT  [-1.0 to +1.0]
```

### VelocityMetric
Mention-rate change for a stock over a time window.

```
VelocityMetric
├── stock           FK → Stock
├── mention_count   INT     (total articles in window)
├── velocity_score  FLOAT   (0–100, normalised rate of change)
├── acceleration    FLOAT   (% change vs prior window)
├── trend           ENUM(accelerating, decelerating, stable)
├── window_start    DATETIME
└── window_end      DATETIME
```

### HypeScore
Composite hype risk score — three-factor model output.

```
HypeScore
├── stock                FK → Stock
├── score                FLOAT  (0–100)
├── level                ENUM(low, moderate, high, extreme)
├── sentiment_imbalance  FLOAT  (0–40 pts contribution)
├── velocity_factor      FLOAT  (0–35 pts contribution)
├── source_concentration FLOAT  (0–25 pts contribution)
└── explanation          TEXT
```

### PriceImpact
Tracks price movement after an article — used to build ML training data.

```
PriceImpact
├── narrative            OneToOne → Narrative
├── stock                FK → Stock
├── price_at_publish     FLOAT  (null until fetched)
├── price_1h / 4h / 24h  FLOAT
├── impact_1h / 4h / 24h FLOAT  (% change)
└── direction_24h        ENUM(up, down, flat)  [ML label]
```

### Watchlist
A user's saved tickers. Auth required for all operations.

```
Watchlist
├── user      FK → auth.User
├── stock     FK → Stock
└── added_at  DATETIME
[unique_together: (user, stock)]
```

### UserAPIKey
Fernet-encrypted storage of user's LLM API keys.

```
UserAPIKey
├── user           FK → auth.User
├── service        ENUM(gemini, groq)
└── encrypted_key  TEXT
```

---

## 6. Backend — Analysis Engine

The core pipeline lives in `api/analysis.py`. It is triggered on demand by the `market_analyze` endpoint and runs sequentially:

```
GET /api/market/analyze/AAPL/?name=Apple+Inc.
         │
         ├─► 1. Stock.objects.get_or_create(ticker='AAPL')
         │
         ├─► 2. Fetch articles
         │       • Check Narrative table for last 48h
         │       • If empty → call GNews API
         │       • Dedup by URL → save new Narrative records
         │
         ├─► 3. ensure_sentiment_scores()
         │       • Find Narratives with no SentimentScore
         │       • Batch all titles through FinBERT (or VADER fallback)
         │       • Save SentimentScore records
         │
         ├─► 4. compute_velocity()
         │       • Count articles: last 24h vs 24–48h ago
         │       • % change → velocity_score 0–100
         │       • Classify trend (accelerating / stable / decelerating)
         │       • Save VelocityMetric
         │
         ├─► 5. compute_hype_score()
         │       • Factor 1: sentiment_imbalance   (0–40 pts)
         │       • Factor 2: velocity_factor       (0–35 pts)
         │       • Factor 3: source_concentration  (0–25 pts)
         │       • Save HypeScore
         │
         ├─► 6. classify_pattern(sentiment, velocity, hype)
         │       • Rule-based → one of 6 narrative archetypes
         │
         ├─► 7. Aggregate sentiment with exponential decay weighting
         │       • DECAY_LAMBDA = ln(2) / 3  (half-life: 3 days)
         │       • w_i = exp(−λ × age_in_days)
         │       • avg_compound = Σ(compound_i × w_i) / Σ(w_i)
         │       • Newer articles weighted exponentially higher
         │
         └─► 8. Return JSON + cache for 15 min
```

### Why exponential decay weighting?

A flat average treats a 10-day-old article the same as one published an hour ago. Markets react to recency. The exponential decay model (half-life 3 days) means:

- An article from **today**: weight = 1.0
- An article from **3 days ago**: weight = 0.5
- An article from **6 days ago**: weight = 0.25
- An article from **10 days ago**: weight ≈ 0.1

This makes the sentiment score react quickly to narrative shifts while not completely ignoring older context.

---

## 7. NLP Pipeline: FinBERT + VADER

### FinBERT (Primary)

FinBERT (`ProsusAI/finbert`) is a BERT-based transformer pre-trained specifically on financial text — Reuters news, Financial PhraseBank, and earnings call transcripts. It outperforms general-purpose sentiment models on financial headlines by a significant margin.

**Implementation highlights** (`api/nlp/finbert.py`):

- **Singleton pattern** — model loaded once on first call, stays in memory. Avoids 5s startup cost on every request.
- **Lazy loading** — model not downloaded until first analysis request is made.
- **Device detection** — automatically uses Apple MPS (Metal GPU) on Apple Silicon, CUDA on NVIDIA, falls back to CPU.
- **Batch inference** — `analyze_batch(texts, batch_size=32)` for processing multiple headlines together — ~10x faster than one at a time.
- **Output** — `positive_prob`, `negative_prob`, `neutral_prob` (sum to 1.0). `compound = positive_prob − negative_prob` (range −1 to +1).

```python
# Compound score classification thresholds:
compound >=  0.05  →  positive (bullish)
compound <= -0.05  →  negative (bearish)
else               →  neutral
```

### VADER (Fallback)

NLTK's VADER is a rule-based lexicon model. It's always available, instant to use, and requires no model download. However, it was not trained on financial text, so its accuracy on financial headlines is weaker. It is used only when FinBERT is unavailable (e.g., model not yet downloaded, or on resource-constrained machines).

---

## 8. Scoring: Sentiment, Velocity, Hype

### Sentiment Score (−1 to +1)

The aggregated compound score across the most recent 20 articles, with exponential decay weighting. Label bucketed as:

| Score | Label |
|---|---|
| ≥ +0.05 | Positive (Bullish) |
| ≤ −0.05 | Negative (Bearish) |
| Between | Neutral |

### Narrative Velocity (0–100)

Measures how fast the story is moving:

```
velocity_score = (count_last_24h - count_prior_24h) / max(count_prior_24h, 1) × 100
```

Capped at 100. Trend:
- **Accelerating** if `change_percent > 20%`
- **Decelerating** if `change_percent < -20%`
- **Stable** otherwise

### Hype Risk Score (0–100)

A three-factor composite. Each factor captures a different signal that separates information-driven from hype-driven coverage:

**Factor 1 — Sentiment Imbalance (0–40 pts)**

How one-sided is the narrative? If 90% of articles are positive/negative, that's a red flag. Balanced coverage is less suspicious.

```
dominant_ratio = max(pos_count, neg_count) / total_count
imbalance_score = max(0, (dominant_ratio - 0.5) × 2) × 40
```

**Factor 2 — Velocity Factor (0–35 pts)**

Fast-moving attention is itself a hype signal. Sudden spikes often precede reversals.

```
velocity_factor = min(velocity_score / 100, 1.0) × 35
```

**Factor 3 — Source Concentration (0–25 pts)**

If all articles come from the same 2 outlets, that's amplification, not independent confirmation.

```
diversity = unique_sources / total_articles
concentration_score = max(0, 1 - diversity) × 25
```

**Final score + level:**

```
hype_score = imbalance_score + velocity_factor + concentration_score

score ≥ 70  →  Extreme
score ≥ 45  →  High
score ≥ 20  →  Moderate
score <  20  →  Low
```

---

## 9. Pattern Classification — 6 Archetypes

`api/patterns.py` implements a rule-based classifier that takes the three scores and outputs one of six narrative archetypes. The classifier is ordered — first match wins.

### 1. Short Squeeze Dynamics 🔴
*Risk: Extreme*

Conditions (3 of 4 must match):
- `compound ≥ +0.30` (extreme positive sentiment)
- Velocity accelerating AND `change_percent ≥ 40%`
- `sentiment_imbalance ≥ 10 pts` (one-sided narrative)
- `hype_score ≥ 60`

Signals a coordinated, one-directional narrative that historically precedes high-volatility events. Classic retail-driven pump setup.

### 2. Macro Fear Pattern 🔴
*Risk: High*

Conditions (2 of 3 must match):
- `compound ≤ −0.15`
- Negative article ratio ≥ 35%
- Sustained coverage + `hype_score ≥ 30`

Broad negative coverage sustained over time — often macro event-driven (Fed announcement, sector regulation, etc.)

### 3. Theme / Sector Wave 🟡
*Risk: High*

Conditions (3 of 4 must match):
- `compound ≥ +0.15`
- Velocity accelerating
- Well-distributed sources (`source_conc ≤ 10`) with `hype_score ≥ 30`
- `hype_score ≥ 40`

Positive momentum with broad source coverage. Often a sector-rotation wave or a macro tailwind narrative.

### 4. Narrative Cool-Off 🔵
*Risk: Moderate*

Conditions (2 of 3 must match):
- Velocity decelerating
- Previously elevated hype (`hype ≥ 25`)
- Coverage dropped ≥ 20%

The story is fading. Can signal the end of a hype cycle — often precedes a price pullback as retail attention moves on.

### 5. Pre-Catalyst Build 🟣
*Risk: Moderate*

Conditions (1 of 2 must match):
- Volume accelerating but **neutral** tone (`|compound| < 0.2`) — anticipatory coverage
- Building anticipation: `0.05 ≤ |compound| < 0.25` with velocity ≥ 20

Quiet buildup before a known event (earnings, product launch, FDA decision). Tone is reserved because no one is willing to commit until the catalyst happens.

### 6. Balanced Coverage 🟢
*Risk: Low*

Default — no unusual signals detected. Coverage is routine, diversified, and neither accelerating nor one-sided.

---

## 10. Narrative Drift & Shift Detection

`api/drift.py` answers: **how has the narrative evolved over time?**

### Algorithm

```
1. Pull all SentimentScore records for last 91 days
2. Aggregate by calendar day → [{date, avg_compound, count, label}]
3. For each window (7d / 30d / 90d):
     a. avg_compound across window
     b. direction: positive / negative / neutral
     c. drift_direction:
          • split window in half
          • delta = avg(second_half) - avg(first_half)
          • delta > +0.05 → improving
          • delta < -0.05 → worsening
          • else          → stable
4. Shift detection:
     a. Compute 3-day rolling average across full timeline
     b. Walk backward through timeline
     c. Find last day where rolling avg crossed a sentiment boundary
     d. Return: {detected, date, from_label, to_label, description}
```

### Frontend Display

The `NarrativeTimeline` component renders this as a Recharts `AreaChart`:
- Chart color adapts to the average sentiment (green gradient for positive, red for negative, gray for neutral)
- Window selector: **7D / 30D / 90D**
- Window stat pills showing `avg_compound` + drift direction arrow
- Purple annotation box when a shift has been detected (with date and "from → to" description)

---

## 11. LLM Narrative Summary

`api/llm.py` provides an AI-generated narrative paragraph on demand.

**Endpoint:** `GET /api/market/narrative-summary/<ticker>/`

**Flow:**
1. Fetch cached analysis result (or run pipeline if not cached)
2. Fetch drift data
3. Build structured context:
   - Ticker, company name, current sentiment/velocity/hype scores
   - Pattern archetype
   - Drift direction across 7d / 30d windows
4. Call Gemini API (preferred) or Groq (fallback)
5. System prompt instructs the model to write a 3–4 sentence narrative paragraph — data-grounded, no bullet points, no speculation
6. Cache result for 15 min

**Key design choice:** The server uses its own API keys (env var `GEMINI_API_KEY` / `GROQ_API_KEY`) for the summary — no user key required. The AI chat feature requires a user key because it's open-ended and expensive.

---

## 12. ML Price-Impact Model

`api/ml/` contains an experimental Random Forest classifier that predicts whether a narrative will move the stock price UP / DOWN / FLAT over the next 24 hours.

**This is not a core product feature.** It is displayed on the StockPage as a supplementary signal with a clear confidence indicator.

### Training Data
`PriceImpact` records: narratives that have been matched with actual 24h price moves. Labels are `up` (>+0.15%), `down` (<−0.15%), `flat` (between).

### Features (12 total)
- Compound sentiment score
- Positive / negative / neutral score breakdowns
- Source type (encoded)
- Hour of day published
- Days since last major narrative
- Current hype level (encoded)
- Velocity score
- Article count

### Training
```bash
python3 manage.py train_model
# → saves ml_models/price_impact_model.pkl
```

### Backtesting
```bash
python3 manage.py backtest --model both
# → Pearson correlation: sentiment vs next-day returns
# → Directional accuracy per sentiment label
# → FinBERT vs VADER comparison
```

---

## 13. Background Scraping

Celery + Redis runs scrapers every 30 minutes in the background.

**Scraper types:**

| Scraper | Source | Quota |
|---|---|---|
| `rss_scraper.py` | RSS feeds from major finance sites | Unlimited |
| `gnews_scraper.py` | GNews API | 100 req/day (free tier) |
| `reddit_scraper.py` | Reddit via PRAW | Rate limited |

**Each scraper run:**
1. Iterates over tracked tickers (`Stock.objects.filter(is_active=True)`)
2. Fetches articles published since last scrape
3. Deduplicates by URL (DB unique constraint)
4. Creates `Narrative` records
5. Calls `ensure_sentiment_scores()` to immediately score new articles with FinBERT

**Manual trigger:**
```bash
python3 manage.py scrape_narratives --ticker AAPL
```

**Celery Beat schedule** (configured in `config/celery.py`):
```python
CELERY_BEAT_SCHEDULE = {
    'scrape-every-30min': {
        'task': 'tasks.scrape_all_active_stocks',
        'schedule': 1800,  # 30 minutes
    }
}
```

---

## 14. Authentication & Security

### JWT Authentication (SimpleJWT)

```
POST /users/login/
→ { access_token: "...", refresh_token: "..." }
```

- **Access token**: short-lived, stored in React `AuthContext` (memory only — not localStorage, not a cookie)
- **Refresh token**: stored in `localStorage`, sent to `POST /users/token/refresh/` when access token expires
- `getAccessToken()` in `AuthContext` auto-refreshes on expiry — all authenticated API calls use this instead of accessing the raw token directly

### API Key Encryption

Users can save their Gemini and Groq API keys on the Settings page. The keys are:
1. Encrypted with **Fernet symmetric encryption** (`cryptography` library)
2. Encryption key is derived from Django's `SECRET_KEY`
3. Stored as an opaque blob in `UserAPIKey.encrypted_key`
4. **Decrypted only at request time** inside the view — never logged, never returned to the frontend

### AI Chat Security

The `market_chat` endpoint requires authentication. It:
1. Fetches the user's encrypted keys from the DB
2. Decrypts at call time
3. Tries Gemini first, falls back to Groq
4. Never returns raw API keys to the client

---

## 15. Watchlist

Users can bookmark tickers and view them in a dedicated Watchlist page with their latest signals.

### Backend (`api/market_views.py`)

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/market/watchlist/` | Return watchlist with latest signals per ticker |
| POST | `/api/market/watchlist/` | Add ticker `{"ticker": "AAPL"}` |
| DELETE | `/api/market/watchlist/` | Remove ticker `{"ticker": "AAPL"}` |
| GET | `/api/market/watchlist/<ticker>/` | Check if watching `{"watching": true}` |

The GET response enriches each watchlist entry with the latest sentiment, velocity, and hype scores by querying the DB directly (no API calls triggered).

### Frontend (`WatchButton.tsx`)

The Watch button on every stock page has three states:
- **Loading** — checking if already watching
- **Watching** (bookmarked state) — green glow, bounce animation
- **Not watching** — neutral pill

On save, a spring-bounce animation plays (`cubic-bezier(0.34, 1.56, 0.64, 1)`), the button glows green, and a "✓ Saved to watchlist" micro-toast slides up from below.

**Token handling:** Uses `getAccessToken()` (not raw `tokens?.access`) to ensure the request always uses a valid, refreshed JWT.

---

## 16. API Reference

All endpoints are under `/api/`. JWT required only where noted.

### Market Endpoints (no auth required)

| Method | Endpoint | Description | Cache TTL |
|---|---|---|---|
| GET | `market/search/?q=APPL` | Ticker autocomplete | 30 min |
| GET | `market/quote/<ticker>/` | Live price quote | 10 min |
| GET | `market/chart/<ticker>/` | OHLCV time series | 10 min |
| GET | `market/news/<ticker>/` | Recent news articles | 15 min |
| GET | `market/analyze/<ticker>/` | Full analysis pipeline | 15 min |
| GET | `market/drift/<ticker>/` | Narrative drift | 30 min |
| GET | `market/trending/` | Top stocks by activity | 10 min |
| GET | `market/predict/<ticker>/` | ML price direction | None |
| GET | `market/narrative-summary/<ticker>/` | AI narrative paragraph | 15 min |

### Market Endpoints (JWT required)

| Method | Endpoint | Description |
|---|---|---|
| POST | `market/chat/<ticker>/` | AI chat (Gemini / Groq) |
| GET | `market/watchlist/` | Get watchlist with signals |
| POST | `market/watchlist/` | Add ticker to watchlist |
| DELETE | `market/watchlist/` | Remove ticker |
| GET | `market/watchlist/<ticker>/` | Check if watching |

### Auth Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `users/register/` | Create account |
| POST | `users/login/` | Get JWT pair |
| POST | `users/token/refresh/` | Refresh access token |
| GET | `users/me/` | Current user info |
| GET | `users/api-keys/` | List saved keys |
| POST | `users/api-keys/` | Save encrypted API key |
| DELETE | `users/api-keys/<id>/` | Delete key |

---

## 17. Caching Strategy

Django cache framework (in-memory in dev, Redis in production). Prevents redundant API calls and re-scoring on every page load.

| Cache Key | TTL | Endpoint |
|---|---|---|
| `quote:<TICKER>` | 10 min | market/quote/ |
| `chart:<TICKER>:<RANGE>` | 10 min | market/chart/ |
| `search:<query>` | 30 min | market/search/ |
| `news:<TICKER>` | 15 min | market/news/ |
| `analyze:<TICKER>` | 15 min | market/analyze/ |
| `drift:<TICKER>` | 30 min | market/drift/ |
| `trending:top` | 10 min | market/trending/ |
| `narrative_summary:<TICKER>` | 15 min | market/narrative-summary/ |

Cache is intentionally short (10–30 min) because narrative signals are time-sensitive — a 2-hour-old velocity reading is misleading.

---

## 18. Frontend Architecture

### Page Layout

**HomePage:**
- Full-width hero with search bar, feature pills, and value proposition headline
- Daily Challenge card (gamification)
- Live **Market Pulse** feed grid — cards for every ticker with cached analysis data, sorted by hype activity
- Skeleton loading (8 animated placeholder cards)
- Empty state with quick-start buttons for popular tickers

**StockPage (two-column layout on desktop):**
- **Left column (2fr):** back button + search bar, stock header (price, change badge), PriceChart (1D/7D/1M/3M), AI Narrative Summary, AnalysisSection (4 cards with hover tooltips), Narrative Timeline, News Section
- **Right column (1fr, sticky):** ChatPanel — pins to top of viewport as user scrolls left content
- Full-width (`w-full px-4 sm:px-8 lg:px-12`) — no max-width cap, fills the screen

**WatchlistPage:**
- Table-style rows: ticker + name, sentiment, velocity, hype
- Empty state with link to feed
- Live signals loaded from `/api/market/watchlist/`

### State Management

| State | Mechanism |
|---|---|
| Authentication | `AuthContext` (React Context) — JWT in memory + refresh in localStorage |
| Gamification | `GamificationContext` (useReducer) — persisted to localStorage |
| Page/route state | React Router v6 |
| Server data | Direct `useEffect` + `useState` per component (no global store) |

The deliberate choice to **not use Redux or React Query** keeps the codebase simple. Every component owns its data fetch. The backend's aggressive caching means duplicate requests are cheap.

### Cursor Spotlight

A fixed `div` with a green radial gradient follows the mouse via `mousemove` events at 0.12s `ease-out` transition. Implemented as a `CursorSpotlight` component in `App.tsx` — rendered once, below the `z-10` app layer, so it never blocks interaction.

---

## 19. Gamification System

The gamification layer encourages exploration and repeat engagement without being intrusive. It can be fully disabled via the navbar toggle.

### Architecture (`GamificationContext.tsx`)

- `useReducer` — all XP/badge/mission state managed in a single reducer
- **localStorage persistence** — XP, mission completion, badge unlocks, and counts survive page refresh. Stored under `mn_gamification_v1`.
- **Disabled mode** — when game mode is off, all action dispatchers become no-ops. No XP is awarded, no toasts appear, no confetti fires. The Daily Challenge is hidden from the homepage.

### XP Events

| User action | XP awarded | Notes |
|---|---|---|
| Search a stock | +10 XP | Once per search |
| Visit a stock page | +15 XP (new) / +3 XP (revisit) | First visit gives full XP |
| Change chart range | +5 XP | Skips the automatic initial load |
| Send AI chat message | +20 XP | Awarded on successful response |
| Click a news article | +10 XP | Tracked in NewsSection |
| Complete daily challenge | +50 XP | Quiz question, one-time per refresh |

### Missions (5 total)
One-time achievements that track first contact with each major feature:
- First Search, Market Explorer, Chart Analyst, Ask the AI, News Reader

### Badges (3 total)
Threshold-based, triggered by cumulative counters:
- **Stock Explorer** — visit 3 different stock pages
- **AI Whisperer** — send 5 chat messages
- **News Junkie** — read 5 news articles

### Confetti triggers
- Every 100 XP milestone (level-up)
- All 5 missions completed
- Any badge unlocked

### Navbar XP Chip
Always visible. Shows current level (Lv N), total XP, a thin progress bar toward the next level, and a missions completed counter. Clicking opens the `GamificationPanel` slide-in drawer (progress + missions + badges). A small `Gamepad2` icon next to the chip disables game mode; when disabled, it collapses to a single "Game" re-enable button.

---

## 20. Data Flow — End to End

Here is the complete journey from user interaction to rendered result:

```
1. USER types "NVDA" in search bar
   └─► SearchBar debounces 300ms → GET /api/market/search/?q=NVDA
       └─► Twelve Data autocomplete API (cached 30 min)
       └─► Dropdown shows [NVDA · NVIDIA Corp · NASDAQ]

2. USER clicks "NVDA"
   └─► onSearchStock() → +10 XP (gamification)
   └─► navigate('/stock/NVDA')

3. StockPage mounts
   ├─► onViewStock('NVDA') → +15 XP (first visit)
   ├─► GET /api/market/chart/NVDA/ → OHLCV from Twelve Data (cached 10 min)
   │     └─► PriceChart renders with 1D default
   ├─► GET /api/market/analyze/NVDA/ → analysis pipeline
   │     ├─► Check Narrative table for last 48h
   │     ├─► If empty: GNews API → save Narrative records
   │     ├─► FinBERT batch scores all new headlines
   │     ├─► Compute velocity, hype, pattern
   │     ├─► Exponential decay aggregate → compound score
   │     └─► Return {sentiment, velocity, hype, pattern} (cache 15 min)
   │           └─► AnalysisSection renders 4 cards
   ├─► GET /api/market/narrative-summary/NVDA/ → LLM paragraph (cache 15 min)
   │     └─► NarrativeSummaryCard renders
   ├─► GET /api/market/drift/NVDA/ → 91-day timeline (cache 30 min)
   │     └─► NarrativeTimeline renders AreaChart
   └─► GET /api/market/news/NVDA/ → GNews articles (cache 15 min)
         └─► NewsSection renders article list

4. USER changes chart to 1M
   └─► GET /api/market/chart/NVDA/?range=1M → new OHLCV data
   └─► onChangeChartRange() → +5 XP (after first change)

5. USER sends chat message "Is this hype?"
   └─► POST /api/market/chat/NVDA/  [JWT required]
         ├─► Decrypt user's Gemini key from DB
         ├─► Build context: ticker + company + narratives
         ├─► Call Gemini API
         └─► Return {answer: "..."}
   └─► onSendChatMessage() → +20 XP

6. USER clicks Watch button
   └─► POST /api/market/watchlist/ {ticker: "NVDA"}  [JWT required]
         └─► Watchlist.objects.get_or_create(user, stock)
   └─► Spring-bounce animation + green glow + "✓ Saved to watchlist" toast
```

---

## 21. Design Decisions & Trade-offs

### Why not train a custom NLP model?

FinBERT is pre-trained on hundreds of thousands of financial documents and consistently outperforms fine-tuned BERT on financial sentiment tasks. Training a custom model would require months of labeled data collection and GPU time. Using a pre-trained model lets the product demonstrate strong NLP capability immediately.

### Why rule-based pattern classification instead of ML?

Six archetypes was a deliberate choice: they're explainable, debuggable, and demonstrably linked to market dynamics in the literature. An ML classifier trained on pattern labels would be a black box with uncertain accuracy given our dataset size. Rule-based logic can be explained in plain English to a professor or investor.

### Why exponential decay weighting instead of a flat average?

Markets are forward-looking. A 7-day-old negative article is not equally relevant to an article published this morning. Exponential decay with a 3-day half-life weights recency appropriately and makes the sentiment score more reactive to narrative shifts.

### Why localStorage for gamification (not a backend model)?

Building a backend for XP/badges would require a new DB model, migration, API endpoint, and auth requirement. localStorage gives session-persistent progress without any of that complexity — appropriate for an MVP. Future versions could sync to the user account when logged in.

### Why no React Query / Redux?

The data model is simple: each page fetches its own data, and the backend caches aggressively. Adding a global client-side cache (React Query) or global store (Redux) would add boilerplate without clear benefit. The 15-min server cache is the source of truth.

### Why fixed seed for Daily Challenge (not dynamic)?

Integrating a daily-question backend would require a separate content management system or LLM prompt engineering for question generation. For a demo, a single hard-coded question that resets on refresh is sufficient to demonstrate the mechanic. Future: questions generated by the LLM based on current market narratives.

---

## 22. How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis (for Celery)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys

python3 manage.py migrate
python3 manage.py runserver
# → http://localhost:8000
```

**Required environment variables (`backend/.env`):**

```
SECRET_KEY=<django-secret-key>
GNEWS_API_KEY=<your-gnews-key>
TWELVEDATA_API_KEY=<your-twelvedata-key>
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=<optional-for-narrative-summary>
GROQ_API_KEY=<optional-fallback>
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_GNEWS_API_KEY if needed

npm run dev
# → http://localhost:5173
```

The Vite dev server proxies all `/api/*` requests to `localhost:8000` automatically.

### Celery (background scrapers)

```bash
redis-server                                    # start Redis (separate terminal)

cd backend && source venv/bin/activate
celery -A config worker -l info                 # worker process
celery -A config beat -l info                   # scheduler (separate terminal)
```

### Useful management commands

```bash
# Manually scrape articles for a ticker
python3 manage.py scrape_narratives --ticker AAPL

# View DB statistics
python3 manage.py dataset_stats

# Backtest: sentiment correlation with price returns
python3 manage.py backtest --model both

# Backtest: earnings event analysis
python3 manage.py backtest_events --mode future

# Train ML model (requires PriceImpact records)
python3 manage.py train_model

# Backfill historical prices for ML training data
python3 manage.py backfill_prices
```

---

## 23. Roadmap

### Short term
- [ ] Pattern-change alerts — notify user by email when archetype shifts for a watched ticker
- [ ] Sector view — aggregate narrative signals across a sector (e.g., "AI Stocks")
- [ ] Daily challenge powered by LLM — questions generated from real current narratives
- [ ] Historical pattern replay — "What was the story around NVDA 3 months ago?"

### Medium term
- [ ] Watchlist push notifications — Celery-driven email digest when a watched ticker's hype crosses a threshold
- [ ] Backtest validation — does a hype score above 70 actually predict reversals? Statistical analysis report.
- [ ] WebSocket live updates — replace polling with real-time narrative feed
- [ ] Mobile app — React Native reusing the Django backend as-is

### Long term
- [ ] Premium tier — real-time Celery scraping configured to your specific watchlist
- [ ] Institutional data sources — SEC filings, options flow as narrative signals
- [ ] Multi-language support — narrative analysis for non-English markets
- [ ] Export / API access — developers can pull raw narrative data for their own models

---

*MarketNoise — Built with React, Django, FinBERT, and a lot of caffeine.*

*For questions, open an issue or reach out to the authors.*
