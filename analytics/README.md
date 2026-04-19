# Analytics — NLP & Narrative Analysis Pipeline

The analytics layer handles all NLP processing, sentiment extraction, narrative velocity computation, and hype-risk scoring. This is the core intelligence of MarketNoise.

## Structure

```
analytics/
├── sentiment/          # Sentiment extraction
│   ├── analyzer.py     #   Main sentiment analysis module
│   ├── models.py       #   Sentiment model wrappers (HuggingFace, custom)
│   └── utils.py        #   Text preprocessing, cleaning utilities
│
├── velocity/           # Narrative velocity & anomaly detection
│   ├── tracker.py      #   Compute narrative velocity over time windows
│   ├── anomaly.py      #   Detect abnormal attention spikes
│   └── metrics.py      #   Velocity metrics (acceleration, deceleration)
│
├── hype/               # Hype-risk scoring
│   ├── scorer.py       #   Compute hype-risk scores for a stock
│   ├── signals.py      #   Identify hype signals (social surge, sentiment imbalance)
│   └── thresholds.py   #   Configurable thresholds for hype classification
│
├── extraction/         # Topic & entity extraction
│   ├── topics.py       #   Extract key topics/themes from text
│   ├── entities.py     #   Named entity recognition (stocks, people, orgs)
│   └── keywords.py     #   Keyword extraction and frequency analysis
│
└── requirements.txt    # Analytics-specific Python dependencies
```

## Key Concepts

### Narrative Velocity
Measures how quickly the volume of mentions/attention around a stock is changing. A sudden acceleration in mentions within a short window signals an abnormal attention spike.

### Hype-Risk Scoring
Combines multiple signals — sentiment imbalance (overwhelmingly positive with no substance), social-to-news ratio, mention acceleration — into a single hype-risk score that indicates whether attention is information-driven or hype-driven.

### Sentiment Analysis
Goes beyond simple positive/negative classification. We track sentiment distribution, sentiment shifts over time, and sentiment-volume correlation.

## Setup

```bash
cd analytics
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Integration with Backend

The analytics modules are called by Celery tasks defined in `backend/tasks/`. The flow is:

1. **Data ingestion** brings in new articles/posts → stored in DB
2. **Celery task** triggers analytics pipeline on new data
3. **Sentiment module** extracts sentiment scores
4. **Velocity module** computes narrative velocity metrics
5. **Hype module** calculates hype-risk scores
6. Results are written back to PostgreSQL and served via the API

## Adding a New Analysis Module

1. Create a new directory under `analytics/`
2. Implement the core logic with a clear entry-point function
3. Add a corresponding Celery task in `backend/tasks/`
4. Expose results through a new API endpoint in `backend/api/`
