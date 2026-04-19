# Backend — Django + Django REST Framework

The backend provides REST APIs for MarketNoise: stock tracking, narrative analysis, sentiment scores, velocity metrics, hype risk scoring, and user authentication.

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver 8000
```

Server runs at `http://localhost:8000`. Admin panel at `http://localhost:8000/admin/`.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables:
- `SECRET_KEY` — Django secret key
- `DEBUG` — `True` for development
- `DB_ENGINE` — Default SQLite, set to `django.db.backends.postgresql` for production
- `REDIS_URL` — For Celery async tasks
- `CORS_ALLOWED_ORIGINS` — Frontend URLs allowed to call the API

## API Endpoints

### Stocks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stocks/` | List all tracked stocks |
| GET | `/api/stocks/{ticker}/` | Get stock by ticker |
| GET | `/api/stocks/{ticker}/analysis/` | Full analysis (sentiment + velocity + hype + narratives) |

### Narratives & Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/narratives/?stock={ticker}` | Narratives for a stock |
| GET | `/api/sentiment/?stock={ticker}` | Sentiment scores |
| GET | `/api/velocity/?stock={ticker}` | Velocity metrics |
| GET | `/api/hype/?stock={ticker}` | Hype risk scores |

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Create account (`username`, `email`, `password`) |
| POST | `/api/auth/token/` | Get JWT tokens (`username`, `password`) |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| GET | `/api/auth/profile/` | Get current user profile (auth required) |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |

## Project Structure

```
backend/
├── config/                 # Django project config
│   ├── settings.py         #   Settings (DB, CORS, JWT, Celery)
│   ├── urls.py             #   Root URL routing
│   ├── celery.py           #   Celery app configuration
│   └── wsgi.py             #   WSGI entry point
│
├── api/                    # Core API app
│   ├── models.py           #   Stock, Narrative, SentimentScore, VelocityMetric, HypeScore
│   ├── serializers.py      #   DRF serializers for all models
│   ├── views.py            #   ViewSets + health check
│   ├── urls.py             #   API URL routes (DRF router)
│   └── admin.py            #   Admin panel registration
│
├── users/                  # Auth app
│   ├── views.py            #   Register, profile endpoints
│   └── urls.py             #   Auth URL routes (JWT tokens)
│
├── tasks/                  # Celery async tasks
│   └── celery_tasks.py     #   Placeholder tasks (ingest, analyze, score)
│
├── manage.py
├── requirements.txt
└── .env.example            #   Environment variable template
```

## Data Models

- **Stock** — Tracked ticker (ticker, name, sector, exchange)
- **Narrative** — News article or social post linked to a stock
- **SentimentScore** — Positive/negative/neutral scores for a narrative
- **VelocityMetric** — Mention count, velocity score, trend over a time window
- **HypeScore** — Composite hype risk (0-100) with explanation

## Celery Tasks (Planned)

Start a Celery worker (requires Redis):

```bash
celery -A config worker -l info
```

Task pipeline: `ingest_news → analyze_sentiment → compute_velocity → compute_hype_score`
