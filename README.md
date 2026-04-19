# MarketNoise

**A narrative analysis platform that helps retail investors distinguish meaningful market signals from hype-driven noise.**

MarketNoise scrapes news from multiple sources, analyzes sentiment with NLP, tracks narrative velocity, and scores hype risk — giving investors transparent explanations of *why* attention is shifting, not price predictions.

---

## Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Scraping & Analysis](#scraping--analysis)
- [Team](#team)

---

## Problem

Retail investors are exposed to massive amounts of market news and social media content, but lack tools to distinguish meaningful information from hype-driven narratives. Existing platforms focus on price or basic sentiment — they don't explain *why* attention is shifting or whether it's abnormal.

## Solution

MarketNoise measures **narrative velocity**, **attention acceleration**, and **sentiment imbalance** to identify hype-driven market behavior. Instead of telling users what to buy or sell, we provide transparent explanations and visualizations so they can make more informed decisions.

### Core Features

1. **Multi-Source News Scraping** — Aggregates articles from Yahoo Finance RSS, Google Finance News, MarketWatch, Reddit (r/wallstreetbets, r/stocks, r/investing), and GNews API
2. **VADER Sentiment Analysis** — Automated NLP sentiment scoring on every scraped narrative, with human-readable explanations
3. **Narrative Velocity Detection** — Measures how quickly attention around a stock is increasing or decreasing, comparing 24h windows
4. **Hype Risk Scoring** — Combines sentiment imbalance (0-40pts), velocity factor (0-35pts), and source concentration (0-25pts) into a 0-100 hype risk score
5. **Visual Dashboard** — Dark-themed fintech UI with interactive price charts, sentiment/velocity/hype cards, news feed, and AI chat interface
6. **Background Collection** — Celery Beat scheduled tasks scrape all active stocks every 30 minutes

---

## Current Status

### What's Working
- **Django REST backend** with JWT auth, REST APIs, Celery task infrastructure
- **Frontend-to-backend proxy** — all external API calls routed through Django (no API keys exposed in browser)
- **Multi-source scraping pipeline**:
  - RSS feeds (Yahoo Finance, Google Finance News, MarketWatch) — free, unlimited
  - Reddit (PRAW) — free, requires app registration
  - GNews API — 100 req/day free tier
  - URL deduplication at DB level (unique constraint)
- **Sentiment analysis** — VADER-based NLP on all scraped narratives with auto-scoring
- **Narrative velocity** — 24h vs prior-24h comparison with trend detection
- **Hype risk scoring** — 3-factor model with level classification (low/moderate/high/extreme)
- **Stock price & charts** — Twelve Data API with 1D/7D/1M/3M ranges, dynamic price change per range
- **Polished UI** — Glassmorphism, gradient accents, animated score bars, SVG chart glow effects
- **Management commands** for manual scraping and backfill

- **Price impact tracking** — records stock price at news publish time + 1h/4h/24h, computes % change, labels direction (up/down/flat) for ML training data
- **ML prediction pipeline** — Random Forest & XGBoost classifiers trained on sentiment + temporal + source features to predict price direction from news
- **Management commands** for scraping, price backfill, dataset stats, and model training

### Planned
- LLM reasoning layer (Claude/GPT for narrative summarization, theme classification, AI Chat)

---

## Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│    Frontend      │    │      Backend         │    │   Analytics Layer   │    │  Data & Storage   │
│  React + TS      │◄──►│  Django + DRF        │◄──►│  VADER Sentiment    │◄──►│  SQLite (dev)     │
│  Dashboard UI    │    │  REST APIs           │    │  Velocity Detection │    │  PostgreSQL (prod)│
│  Recharts        │    │  Celery + Redis      │    │  Hype Scoring       │    │                   │
│  Tailwind CSS    │    │  News Scrapers       │    │  ML Pipeline (WIP)  │    │                   │
└─────────────────┘    └─────────────────────┘    └─────────────────────┘    └──────────────────┘
```

**Data flow:**
1. Celery Beat triggers `scrape_all_stocks` every 30 minutes
2. Scrapers (RSS, Reddit, GNews) fetch articles → deduplicate → store as Narratives
3. VADER sentiment analysis auto-scores new narratives
4. Frontend calls `/api/market/analyze/<ticker>/` → runs sentiment aggregation + velocity + hype scoring
5. Results displayed in dashboard with explanations

---

## Project Structure

```
Market-Noise/
│
├── backend/                    # Django backend
│   ├── config/                 #   Settings, URLs, WSGI, Celery config
│   ├── api/                    #   Core API app
│   │   ├── models.py           #     Stock, Narrative, SentimentScore, VelocityMetric, HypeScore, PriceImpact
│   │   ├── analysis.py         #     Sentiment, velocity, hype analysis pipeline
│   │   ├── market_views.py     #     Proxy endpoints (quote, chart, search, news, analyze, predict)
│   │   ├── scrapers/           #     Multi-source scraping engine
│   │   │   ├── base.py         #       Abstract BaseScraper with dedup logic
│   │   │   ├── rss_scraper.py  #       Yahoo Finance, Google Finance, MarketWatch RSS
│   │   │   ├── reddit_scraper.py #     r/wallstreetbets, r/stocks, r/investing
│   │   │   └── gnews_scraper.py  #     GNews API scraper
│   │   ├── ml/                  #     ML prediction pipeline
│   │   │   ├── features.py      #       Feature extraction (12 features)
│   │   │   ├── trainer.py       #       RandomForest / XGBoost training
│   │   │   └── predictor.py     #       Model loading & prediction serving
│   │   ├── price_tracker.py     #     Twelve Data price tracking + rate limiting
│   │   └── management/commands/ #    Management commands
│   │       ├── scrape_narratives.py # Manual scrape + backfill
│   │       ├── backfill_prices.py   # Historical price impact labeling
│   │       ├── dataset_stats.py     # ML training data readiness
│   │       └── train_model.py       # Train ML classifiers
│   ├── users/                  #   Authentication & user management
│   ├── tasks/                  #   Celery task definitions
│   │   └── celery_tasks.py     #     scrape_all_sources, scrape_all_stocks, run_full_pipeline
│   ├── requirements.txt        #   Python dependencies
│   └── .env                    #   API keys & config (not in git)
│
├── frontend/                   # React + TypeScript dashboard (Vite)
│   └── src/
│       ├── components/         #   Navbar, SearchBar, PriceChart, AnalysisSection, ChatPanel, NewsSection
│       ├── pages/              #   HomePage (search), StockPage (detail view)
│       ├── services/           #   stockService, newsService, searchService, analysisService
│       ├── types/              #   TypeScript interfaces
│       └── utils/              #   Constants (32 stock tickers, time ranges)
│
└── README.md
```

---

## Tech Stack

| Layer           | Technology                                       | Status       |
|----------------|--------------------------------------------------|--------------|
| Frontend       | React 19, TypeScript, Vite, Tailwind CSS v4      | Implemented  |
| Charts         | Recharts (AreaChart with SVG glow effects)        | Implemented  |
| Stock Prices   | Twelve Data API (via Django proxy)                | Implemented  |
| News Scraping  | feedparser (RSS), PRAW (Reddit), GNews API        | Implemented  |
| Sentiment      | NLTK VADER                                        | Implemented  |
| Backend        | Django 4.2, Django REST Framework, JWT auth       | Implemented  |
| Async Tasks    | Celery + Redis                                    | Implemented  |
| Database       | SQLite (dev), PostgreSQL-ready                    | Implemented  |
| Price Tracking | Twelve Data API (price impact labeling)            | Implemented  |
| ML Pipeline    | scikit-learn, XGBoost (price impact prediction)   | Implemented  |
| LLM Layer      | Claude/OpenAI API (reasoning enhancement)         | Planned      |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for Celery background tasks)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` from the example:

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   TWELVEDATA_API_KEY  — from https://twelvedata.com (800 req/day free)
#   GNEWS_API_KEY       — from https://gnews.io (100 req/day free)
#   REDDIT_CLIENT_ID    — from https://www.reddit.com/prefs/apps
#   REDDIT_CLIENT_SECRET
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for admin panel
python manage.py runserver          # http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173 (proxies /api/* to Django)
```

### Background Scraping (optional)

Start Redis, then run Celery worker + beat:

```bash
redis-server                                    # Terminal 1
celery -A config worker -l info                 # Terminal 2
celery -A config beat -l info                   # Terminal 3 (auto-scrapes every 30 min)
```

---

## Scraping & Analysis

### Manual Scraping

```bash
cd backend
source venv/bin/activate

# Scrape one ticker from RSS feeds (last 7 days) + run sentiment analysis
python manage.py scrape_narratives --ticker AAPL --sources rss --backfill-days 7 --analyze

# Scrape from all sources
python manage.py scrape_narratives --ticker AAPL --sources rss,reddit,gnews --backfill-days 30 --analyze

# Scrape all active stocks in the database
python manage.py scrape_narratives --all-stocks --sources rss --analyze
```

### Price Impact Tracking

```bash
# Backfill historical prices for narratives (creates ML training labels)
python manage.py backfill_prices --ticker AAPL --limit 50

# Backfill all stocks
python manage.py backfill_prices --all-stocks --limit 100

# Check dataset readiness for ML training
python manage.py dataset_stats
```

### ML Model Training

```bash
# Train a Random Forest classifier (default)
python manage.py train_model

# Train an XGBoost classifier
python manage.py train_model --algorithm xgboost
```

Requires 50+ labeled samples. Use `dataset_stats` to check progress.

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/market/quote/<ticker>/` | Current stock price + daily change |
| `GET /api/market/chart/<ticker>/?range=1D` | Price history (1D, 7D, 1M, 3M) |
| `GET /api/market/search/?q=apple` | Symbol search (US stocks + ETFs) |
| `GET /api/market/news/<ticker>/` | Recent news articles |
| `GET /api/market/analyze/<ticker>/` | Full analysis (sentiment + velocity + hype) |
| `GET /api/market/predict/<ticker>/` | ML price impact predictions for latest narratives |
| `GET /admin/` | Django admin panel |

---

## Team

| Name                  | Role               |
|----------------------|---------------------|
| Agam Gupta           | Product Owner       |
| Piyusha Taware       | Scrum Master        |
| Shaunak Mahajan      | Development Lead    |
| Karna Mehta          | Backend Developer   |
| Paarth Soni          | Backend Developer   |
| Chaitanya Gandhi     | Backend Developer   |
| Mihika Dakappagari   | Frontend Developer  |
| Aryan Shah           | Frontend Developer  |
| Khushi Mehta         | UI/UX Designer      |
| Harsh Mangukiya      | Tester              |

---

## Development Methodology

We follow **Agile Scrum** with iterative sprints, regular standups, sprint reviews, and retrospectives.

---

*MarketNoise does not predict prices or provide trading advice. It helps users understand market narratives.*
