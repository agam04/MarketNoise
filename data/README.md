# Data — Ingestion & Storage

This directory contains data ingestion scripts, database schema documentation, and sample data for local development.

## Structure

```
data/
├── ingestion/      # Data ingestion scripts
│   ├── news.py     #   Fetch news articles from APIs (NewsAPI, etc.)
│   ├── social.py   #   Fetch social media discussions (Reddit, Twitter/X)
│   └── scheduler.py#   Scheduling logic for periodic data pulls
│
├── schemas/        # Database schema documentation
│   ├── models.md   #   ER diagram and model descriptions
│   └── migrations/ #   Migration notes and version tracking
│
└── samples/        # Sample data for development
    ├── news.json   #   Sample news articles
    └── social.json #   Sample social media posts
```

## Data Sources (MVP)

| Source         | Type    | Description                              |
|---------------|---------|------------------------------------------|
| News APIs     | News    | Curated financial news headlines          |
| Reddit        | Social  | Stock-related subreddit discussions       |

> Additional sources (Twitter/X, financial blogs) can be added post-MVP.

## Storage Architecture

| Store          | Purpose                                   |
|---------------|-------------------------------------------|
| PostgreSQL    | Structured data — stocks, users, metrics, sentiment scores, velocity data |
| Elasticsearch | Full-text search over news articles and social posts |
| S3 / GCS      | Raw text storage, embeddings, model artifacts |

## Sample Data

The `samples/` directory contains mock data for local development and testing. Use these when you don't have API keys or want to work offline.

## Adding a New Data Source

1. Create an ingestion script in `data/ingestion/`
2. Define the data format and add a sample to `samples/`
3. Create a Celery task in `backend/tasks/` to schedule periodic pulls
4. Update the database schema if new fields are needed
