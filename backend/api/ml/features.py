"""
Feature extraction for the ML price-impact prediction model.
Converts Narrative + SentimentScore data into numerical feature vectors.
"""

import pandas as pd

from api.models import Narrative, SentimentScore, PriceImpact


def extract_features(narrative: Narrative) -> dict:
    """Extract ML features from a single narrative."""
    # Sentiment features (from VADER)
    try:
        sentiment = narrative.sentiment
        compound = sentiment.compound_score
        positive = sentiment.positive_score
        negative = sentiment.negative_score
        neutral = sentiment.neutral_score
    except SentimentScore.DoesNotExist:
        compound = positive = negative = neutral = 0.0

    # Text features
    title_len = len(narrative.title)
    content_len = len(narrative.content)

    # Source features (one-hot)
    source_news = 1 if narrative.source in ('news', 'rss') else 0
    source_reddit = 1 if narrative.source == 'reddit' else 0

    # Temporal features
    pub = narrative.published_at
    hour = pub.hour
    dow = pub.weekday()

    return {
        'compound_score': compound,
        'positive_score': positive,
        'negative_score': negative,
        'neutral_score': neutral,
        'title_length': title_len,
        'content_length': content_len,
        'source_news': source_news,
        'source_reddit': source_reddit,
        'hour_of_day': hour,
        'day_of_week': dow,
        'is_weekend': 1 if dow >= 5 else 0,
        'is_market_hours': 1 if 9 <= hour <= 16 else 0,
    }


FEATURE_COLUMNS = [
    'compound_score', 'positive_score', 'negative_score', 'neutral_score',
    'title_length', 'content_length',
    'source_news', 'source_reddit',
    'hour_of_day', 'day_of_week', 'is_weekend', 'is_market_hours',
]


def build_training_dataframe() -> pd.DataFrame:
    """
    Build a training DataFrame from all fully-labeled PriceImpact records.
    Each row = one narrative with features + direction_24h target.
    """
    impacts = PriceImpact.objects.filter(
        direction_24h__in=['up', 'down', 'flat'],
        price_at_publish__isnull=False,
        price_24h__isnull=False,
    ).select_related('narrative', 'stock')

    rows = []
    for impact in impacts:
        narrative = impact.narrative

        # Skip narratives without sentiment
        try:
            _ = narrative.sentiment
        except SentimentScore.DoesNotExist:
            continue

        features = extract_features(narrative)
        features['direction_24h'] = impact.direction_24h
        features['ticker'] = impact.stock.ticker
        features['impact_24h'] = impact.impact_24h
        rows.append(features)

    return pd.DataFrame(rows)
