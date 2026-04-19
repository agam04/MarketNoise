import logging
import math
import os
from datetime import datetime, timedelta

import nltk
import requests as http
from django.utils import timezone
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from .models import Stock, Narrative, SentimentScore, VelocityMetric, HypeScore
from .nlp import finbert as _finbert

logger = logging.getLogger(__name__)

# Download VADER lexicon on first import (no-op if already downloaded)
nltk.download('vader_lexicon', quiet=True)

GNEWS_KEY = os.getenv('GNEWS_API_KEY', '')
GNEWS_BASE = 'https://gnews.io/api/v4'

# VADER kept as a fast fallback if FinBERT is unavailable
_vader = SentimentIntensityAnalyzer()


def _score_text(text: str) -> dict:
    """
    Score a single text snippet.  Tries FinBERT first; falls back to VADER.
    Returns {'compound', 'pos', 'neg', 'neu'} with the same sign convention.
    """
    if _finbert.is_available():
        result = _finbert.analyze(text)
        return {'compound': result['compound'], 'pos': result['pos'],
                'neg': result['neg'], 'neu': result['neu']}
    scores = _vader.polarity_scores(text)
    return {'compound': scores['compound'], 'pos': scores['pos'],
            'neg': scores['neg'], 'neu': scores['neu']}


def _score_batch(texts: list[str]) -> list[dict]:
    """
    Score a list of texts.  Uses FinBERT batch inference when available
    (much faster than one-at-a-time), falls back to VADER.
    """
    if _finbert.is_available():
        results = _finbert.analyze_batch(texts)
        return [{'compound': r['compound'], 'pos': r['pos'],
                 'neg': r['neg'], 'neu': r['neu']} for r in results]
    return [_score_text(t) for t in texts]


def _classify_label(compound: float) -> str:
    """Map VADER compound score to a sentiment label."""
    if compound >= 0.05:
        return 'positive'
    elif compound <= -0.05:
        return 'negative'
    else:
        return 'neutral'


def _build_explanation(ticker: str, label: str, compound: float,
                       articles: list[dict], total_count: int) -> str:
    """Generate a human-readable explanation of why the sentiment is what it is."""
    if not articles:
        return f"No recent news articles found for {ticker} to analyze."

    pos_articles = [a for a in articles if a.get('label') == 'positive']
    neg_articles = [a for a in articles if a.get('label') == 'negative']
    neu_articles = [a for a in articles if a.get('label') == 'neutral']

    parts = []

    strength = abs(compound)
    if strength > 0.5:
        intensity = "strongly"
    elif strength > 0.2:
        intensity = "moderately"
    else:
        intensity = "slightly"

    if label == 'positive':
        parts.append(f"News coverage for {ticker} is {intensity} positive.")
    elif label == 'negative':
        parts.append(f"News coverage for {ticker} is {intensity} negative.")
    else:
        parts.append(f"News coverage for {ticker} is mixed with no clear direction.")

    parts.append(
        f"Based on {total_count} article{'s' if total_count != 1 else ''}: "
        f"{len(pos_articles)} positive, {len(neg_articles)} negative, {len(neu_articles)} neutral."
    )

    if pos_articles:
        strongest_pos = max(pos_articles, key=lambda a: a.get('compound', 0))
        parts.append(f"Most bullish: \"{strongest_pos['title'][:80]}\" ({strongest_pos['source']})")

    if neg_articles:
        strongest_neg = min(neg_articles, key=lambda a: a.get('compound', 0))
        parts.append(f"Most bearish: \"{strongest_neg['title'][:80]}\" ({strongest_neg['source']})")

    return " ".join(parts)


def _fetch_articles(ticker: str, company_name: str) -> list[dict]:
    """Fetch news articles from GNews API (legacy fallback when no scraped data exists)."""
    if not GNEWS_KEY:
        return []

    query = f'{ticker} OR "{company_name}" stock'
    try:
        resp = http.get(
            f'{GNEWS_BASE}/search',
            params={'q': query, 'lang': 'en', 'max': 6, 'token': GNEWS_KEY},
            timeout=10,
        )
        if not resp.ok:
            return []
        data = resp.json()
        return data.get('articles', [])
    except Exception:
        return []


def ensure_sentiment_scores(stock: Stock) -> int:
    """
    Find narratives without a SentimentScore and analyze them.
    Uses FinBERT (financial-domain NLP) when available, falls back to VADER.
    Batches all texts in one model call for speed.
    Returns count of new scores created.
    """
    unscored = list(
        Narrative.objects.filter(stock=stock)
        .exclude(sentiment__isnull=False)
        .order_by('-published_at')[:50]
    )
    if not unscored:
        return 0

    texts = [
        f"{n.title}. {n.content}" if n.content else n.title
        for n in unscored
    ]

    all_scores = _score_batch(texts)

    created = 0
    for narrative, scores in zip(unscored, all_scores):
        compound = scores['compound']
        label = _classify_label(compound)
        SentimentScore.objects.create(
            narrative=narrative,
            stock=stock,
            label=label,
            positive_score=scores['pos'],
            negative_score=scores['neg'],
            neutral_score=scores['neu'],
            compound_score=compound,
        )
        created += 1

    return created


def analyze_stock_sentiment(ticker: str, company_name: str) -> dict:
    """
    Full sentiment analysis pipeline for a stock:
    1. Get or create Stock record
    2. If no recent narratives exist (from scrapers), fetch from GNews as fallback
    3. Ensure all narratives have sentiment scores
    4. Return aggregate results
    """
    ticker = ticker.upper()

    stock, _ = Stock.objects.get_or_create(
        ticker=ticker,
        defaults={'name': company_name or ticker},
    )

    # Check if we have recent narratives from scrapers
    recent_cutoff = timezone.now() - timedelta(hours=48)
    recent_narratives = Narrative.objects.filter(
        stock=stock, published_at__gte=recent_cutoff
    ).count()

    # Fallback: if no scraped data, fetch from GNews directly
    if recent_narratives == 0:
        articles = _fetch_articles(ticker, company_name or stock.name)
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '')
            description = article.get('description', '')
            source_name = article.get('source', {}).get('name', '')
            published_str = article.get('publishedAt', '')

            try:
                published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                published_at = timezone.now()

            if url and Narrative.objects.filter(url=url).exists():
                continue

            Narrative.objects.create(
                stock=stock,
                title=title,
                content=description,
                source='news',
                source_name=source_name,
                url=url,
                published_at=published_at,
            )

    # Ensure all narratives have sentiment scores
    ensure_sentiment_scores(stock)

    # Build results from recent scores — exponential decay weighting
    # Articles from today carry full weight; weight halves every 3 days.
    # lambda = ln(2) / 3  →  half-life of 3 days
    DECAY_LAMBDA = math.log(2) / 3.0

    recent_scores = list(
        SentimentScore.objects.filter(stock=stock)
        .select_related('narrative')
        .order_by('-analyzed_at')[:20]
    )
    count = len(recent_scores)

    if count == 0:
        return {
            'ticker': ticker,
            'label': 'neutral',
            'compound': 0.0,
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 1.0,
            'article_count': 0,
            'explanation': f'No recent news articles found for {ticker} to analyze.',
            'articles': [],
        }

    now = timezone.now()
    weights = []
    for s in recent_scores:
        age_days = max((now - s.analyzed_at).total_seconds() / 86400.0, 0)
        weights.append(math.exp(-DECAY_LAMBDA * age_days))

    total_weight = sum(weights) or 1.0
    avg_compound = sum(s.compound_score * w for s, w in zip(recent_scores, weights)) / total_weight
    avg_positive = sum(s.positive_score * w for s, w in zip(recent_scores, weights)) / total_weight
    avg_negative = sum(s.negative_score * w for s, w in zip(recent_scores, weights)) / total_weight
    avg_neutral  = sum(s.neutral_score  * w for s, w in zip(recent_scores, weights)) / total_weight

    overall_label = _classify_label(avg_compound)

    # Build analyzed_articles list for explanation
    analyzed_articles = []
    for s in recent_scores:
        analyzed_articles.append({
            'title': s.narrative.title,
            'source': s.narrative.source_name,
            'label': s.label,
            'compound': s.compound_score,
            'positive': s.positive_score,
            'negative': s.negative_score,
            'neutral': s.neutral_score,
        })

    explanation = _build_explanation(ticker, overall_label, avg_compound, analyzed_articles, count)

    return {
        'ticker': ticker,
        'label': overall_label,
        'compound': round(avg_compound, 3),
        'positive': round(avg_positive, 3),
        'negative': round(avg_negative, 3),
        'neutral': round(avg_neutral, 3),
        'article_count': count,
        'explanation': explanation,
        'articles': analyzed_articles,
    }


def compute_velocity(ticker: str) -> dict:
    """
    Compute narrative velocity — how fast mentions are growing/declining.
    Compares recent window (last 24h) vs previous window (24-48h ago).
    """
    ticker = ticker.upper()
    try:
        stock = Stock.objects.get(ticker=ticker)
    except Stock.DoesNotExist:
        return {
            'ticker': ticker,
            'score': 0.0,
            'trend': 'stable',
            'mention_count': 0,
            'change_percent': 0.0,
            'explanation': f'No data available for {ticker} yet.',
        }

    now = timezone.now()
    recent_start = now - timedelta(hours=24)
    prev_start = now - timedelta(hours=48)

    recent_count = Narrative.objects.filter(
        stock=stock, published_at__gte=recent_start
    ).count()
    prev_count = Narrative.objects.filter(
        stock=stock, published_at__gte=prev_start, published_at__lt=recent_start
    ).count()

    total_count = Narrative.objects.filter(stock=stock).count()

    if prev_count == 0 and recent_count == 0:
        velocity_score = 0.0
        change_pct = 0.0
        trend = 'stable'
    elif prev_count == 0:
        velocity_score = min(recent_count * 20.0, 100.0)
        change_pct = 100.0
        trend = 'accelerating'
    else:
        change_pct = ((recent_count - prev_count) / prev_count) * 100
        velocity_score = min(abs(change_pct), 100.0)
        if change_pct > 10:
            trend = 'accelerating'
        elif change_pct < -10:
            trend = 'decelerating'
        else:
            trend = 'stable'

    VelocityMetric.objects.create(
        stock=stock,
        mention_count=total_count,
        velocity_score=round(velocity_score, 1),
        acceleration=round(change_pct, 1),
        trend=trend,
        window_start=prev_start,
        window_end=now,
    )

    explanation = _build_velocity_explanation(ticker, trend, recent_count, prev_count, total_count)

    return {
        'ticker': ticker,
        'score': round(velocity_score, 1),
        'trend': trend,
        'mention_count': total_count,
        'change_percent': round(change_pct, 1),
        'explanation': explanation,
    }


def _build_velocity_explanation(ticker: str, trend: str, recent: int,
                                 previous: int, total: int) -> str:
    """Generate explanation for velocity score."""
    if total == 0:
        return f"No narratives tracked for {ticker} yet."

    parts = []
    if trend == 'accelerating':
        parts.append(f"Attention around {ticker} is increasing.")
        parts.append(f"{recent} mention{'s' if recent != 1 else ''} in the last 24h vs {previous} in the prior 24h.")
        if recent > previous * 2 and previous > 0:
            parts.append("This is a significant spike in coverage — worth monitoring closely.")
        else:
            parts.append("The uptick suggests growing market interest.")
    elif trend == 'decelerating':
        parts.append(f"Attention around {ticker} is fading.")
        parts.append(f"{recent} mention{'s' if recent != 1 else ''} in the last 24h vs {previous} in the prior 24h.")
        parts.append("Declining coverage could mean the narrative is losing steam.")
    else:
        parts.append(f"Coverage for {ticker} is steady.")
        parts.append(f"{total} total article{'s' if total != 1 else ''} tracked so far.")
        parts.append("No unusual spikes or drops in attention detected.")

    return " ".join(parts)


def compute_hype_score(ticker: str) -> dict:
    """
    Compute hype risk score (0-100) combining:
    - Sentiment imbalance: how one-sided is the sentiment?
    - Velocity factor: is attention spiking?
    - Source diversity: are articles from varied sources?
    """
    ticker = ticker.upper()
    try:
        stock = Stock.objects.get(ticker=ticker)
    except Stock.DoesNotExist:
        return {
            'ticker': ticker,
            'score': 0.0,
            'level': 'low',
            'explanation': f'No data available for {ticker} yet.',
        }

    recent_sentiments = SentimentScore.objects.filter(stock=stock).order_by('-analyzed_at')[:20]
    count = recent_sentiments.count()

    if count == 0:
        return {
            'ticker': ticker,
            'score': 0.0,
            'level': 'low',
            'explanation': f'No sentiment data for {ticker} to compute hype risk.',
        }

    # --- Factor 1: Sentiment imbalance (0-40 points) ---
    pos_count = sum(1 for s in recent_sentiments if s.label == 'positive')
    neg_count = sum(1 for s in recent_sentiments if s.label == 'negative')
    if count > 0:
        dominant = max(pos_count, neg_count)
        imbalance = dominant / count
        sentiment_imbalance_score = max(0, (imbalance - 0.5) * 2) * 40
    else:
        imbalance = 0.0
        sentiment_imbalance_score = 0.0

    # --- Factor 2: Velocity factor (0-35 points) ---
    latest_velocity = VelocityMetric.objects.filter(stock=stock).order_by('-computed_at').first()
    if latest_velocity:
        velocity_factor = min(latest_velocity.velocity_score / 100.0, 1.0) * 35
        velocity_raw = latest_velocity.velocity_score
    else:
        velocity_factor = 0.0
        velocity_raw = 0.0

    # --- Factor 3: Source concentration (0-25 points) ---
    recent_narratives = Narrative.objects.filter(stock=stock).order_by('-published_at')[:20]
    sources = set(n.source_name for n in recent_narratives if n.source_name)
    narrative_count = recent_narratives.count()
    if narrative_count > 1:
        diversity = len(sources) / narrative_count
        source_concentration_score = max(0, (1.0 - diversity)) * 25
    else:
        source_concentration_score = 0.0

    # --- Final score ---
    raw_score = sentiment_imbalance_score + velocity_factor + source_concentration_score
    score = round(min(raw_score, 100.0), 1)

    if score >= 70:
        level = 'extreme'
    elif score >= 45:
        level = 'high'
    elif score >= 20:
        level = 'moderate'
    else:
        level = 'low'

    HypeScore.objects.create(
        stock=stock,
        score=score,
        level=level,
        sentiment_imbalance=round(imbalance, 3) if count > 0 else 0.0,
        social_news_ratio=0.0,
        velocity_factor=round(velocity_raw, 1),
        explanation='',
    )

    explanation = _build_hype_explanation(ticker, level, score, imbalance,
                                          velocity_raw, len(sources), narrative_count)

    return {
        'ticker': ticker,
        'score': score,
        'level': level,
        'sentiment_imbalance': round(sentiment_imbalance_score, 1),
        'velocity_factor': round(velocity_factor, 1),
        'source_concentration': round(source_concentration_score, 1),
        'explanation': explanation,
    }


def _build_hype_explanation(ticker: str, level: str, score: float,
                             imbalance: float, velocity: float,
                             source_count: int, article_count: int) -> str:
    """Generate explanation for hype risk score."""
    parts = []

    level_text = {
        'low': 'low',
        'moderate': 'moderate',
        'high': 'elevated',
        'extreme': 'very high',
    }
    parts.append(f"Hype risk for {ticker} is {level_text.get(level, level)} ({score:.0f}/100).")

    if imbalance > 0.8:
        parts.append(f"Sentiment is heavily one-sided ({imbalance:.0%} in one direction), which is a strong hype signal.")
    elif imbalance > 0.6:
        parts.append(f"Sentiment leans one direction ({imbalance:.0%}), suggesting some narrative bias.")
    else:
        parts.append("Sentiment is relatively balanced across articles.")

    if velocity > 50:
        parts.append("Attention is spiking rapidly, which often precedes overreaction.")
    elif velocity > 20:
        parts.append("Coverage is picking up pace — moderate attention growth.")

    if article_count > 1:
        if source_count <= 2:
            parts.append(f"Only {source_count} source{'s' if source_count != 1 else ''} covering this — limited perspective.")
        else:
            parts.append(f"Coverage spans {source_count} different sources, providing diverse viewpoints.")

    return " ".join(parts)
