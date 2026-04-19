"""
Price impact tracking — fetches stock prices at various time offsets
after a narrative is published to build labeled training data.

Uses Twelve Data API (800 req/day free tier).
Includes a daily rate limiter to stay within limits.
"""

import logging
import os
import time
from datetime import timedelta

import requests as http
from django.core.cache import cache
from django.utils import timezone

from .models import Narrative, PriceImpact

logger = logging.getLogger(__name__)

TWELVEDATA_KEY = os.getenv('TWELVEDATA_API_KEY', '')
TWELVEDATA_BASE = 'https://api.twelvedata.com'

# Daily rate limit — leave a buffer of 20 calls for manual browsing
DAILY_LIMIT = 780

# Per-minute rate limit — Twelve Data free tier allows ~8 req/min
MIN_CALL_INTERVAL = 8.0  # seconds between API calls to stay under 8/min


def _check_rate_limit() -> bool:
    """Return True if we can make another Twelve Data call today."""
    key = f'twelvedata_calls:{timezone.now().strftime("%Y-%m-%d")}'
    count = cache.get(key, 0)
    if count >= DAILY_LIMIT:
        logger.warning(f"Twelve Data daily limit reached ({count}/{DAILY_LIMIT})")
        return False
    return True


def _increment_rate_counter():
    """Increment today's Twelve Data API call counter."""
    key = f'twelvedata_calls:{timezone.now().strftime("%Y-%m-%d")}'
    count = cache.get(key, 0)
    cache.set(key, count + 1, timeout=86400)


def _throttled_get(url: str, params: dict, max_retries: int = 2) -> dict | None:
    """Make a Twelve Data API call with throttling and 429 retry logic."""
    if not _check_rate_limit():
        return None

    for attempt in range(max_retries + 1):
        try:
            # Throttle: wait between calls to respect per-minute limit
            time.sleep(MIN_CALL_INTERVAL)

            resp = http.get(url, params=params, timeout=10)
            _increment_rate_counter()

            if resp.status_code == 429:
                # Rate limited — wait and retry
                wait = 60 if attempt < max_retries else 0
                logger.warning(f"Twelve Data 429 rate limit, waiting {wait}s (attempt {attempt + 1})")
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                return None

            if not resp.ok:
                return None

            data = resp.json()
            # Check for API-level error responses
            if data.get('code') == 429:
                wait = 60 if attempt < max_retries else 0
                logger.warning(f"Twelve Data API rate limit, waiting {wait}s")
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                return None

            return data

        except Exception as e:
            logger.warning(f"Twelve Data request error: {e}")
            return None

    return None


def get_current_price(ticker: str) -> float | None:
    """Fetch current/latest price from Twelve Data quote endpoint."""
    if not TWELVEDATA_KEY:
        logger.warning("TWELVEDATA_API_KEY not set")
        return None

    data = _throttled_get(
        f'{TWELVEDATA_BASE}/quote',
        {'symbol': ticker, 'apikey': TWELVEDATA_KEY},
    )
    if data is None:
        return None

    if 'close' in data:
        return float(data['close'])
    if 'price' in data:
        return float(data['price'])

    return None


def get_historical_price(ticker: str, target_dt) -> float | None:
    """
    Fetch price closest to a specific datetime using Twelve Data time_series.
    Uses 1h interval with outputsize, then finds the closest data point.
    """
    if not TWELVEDATA_KEY:
        return None

    # Calculate how many hours back we need from now
    from django.utils import timezone as tz
    now = tz.now()
    hours_ago = max(1, int((now - target_dt).total_seconds() / 3600) + 2)
    # Cap at 5000 (Twelve Data max), use daily interval for older data
    if hours_ago > 500:
        interval = '1day'
        outputsize = min(hours_ago // 24 + 2, 100)
    else:
        interval = '1h'
        outputsize = min(hours_ago + 4, 500)

    try:
        data = _throttled_get(
            f'{TWELVEDATA_BASE}/time_series',
            {
                'symbol': ticker,
                'interval': interval,
                'outputsize': outputsize,
                'apikey': TWELVEDATA_KEY,
            },
        )
        if data is None:
            return None

        values = data.get('values', [])
        if not values:
            return None

        # Find the data point closest to target_dt
        from datetime import datetime as dt
        best_price = None
        best_diff = None

        for v in values:
            try:
                # Twelve Data returns naive datetimes in exchange timezone (US/Eastern for US stocks)
                point_dt = dt.strptime(v['datetime'], '%Y-%m-%d %H:%M:%S')
                # Make naive for comparison (approximate — good enough for hourly granularity)
                target_naive = target_dt.replace(tzinfo=None)
                diff = abs((point_dt - target_naive).total_seconds())
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_price = float(v['close'])
            except (ValueError, KeyError):
                continue

        return best_price
    except Exception as e:
        logger.warning(f"Historical price fetch error for {ticker} at {target_dt}: {e}")

    return None


def create_price_impact(narrative: Narrative) -> PriceImpact | None:
    """
    Create a PriceImpact record for a narrative and fetch the publish-time price.
    Returns the PriceImpact instance, or None if rate limited.
    """
    impact, created = PriceImpact.objects.get_or_create(
        narrative=narrative,
        defaults={'stock': narrative.stock},
    )

    if not impact.price_fetched_at_publish:
        # For recent articles (< 2h old), use current price as approximation
        age = timezone.now() - narrative.published_at
        if age < timedelta(hours=2):
            price = get_current_price(narrative.stock.ticker)
        else:
            price = get_historical_price(narrative.stock.ticker, narrative.published_at)

        if price is not None:
            impact.price_at_publish = price
            impact.price_fetched_at_publish = True
            impact.save()
            logger.info(f"Price at publish for {narrative.stock.ticker}: ${price:.2f}")
        else:
            logger.warning(f"Could not fetch publish price for narrative {narrative.id}")

    return impact


def check_price_at_offset(impact_id: int, offset_key: str) -> bool:
    """
    Fetch price for a specific time offset (1h, 4h, 24h) and update the PriceImpact.
    Returns True if successful.
    """
    try:
        impact = PriceImpact.objects.get(id=impact_id)
    except PriceImpact.DoesNotExist:
        logger.warning(f"PriceImpact {impact_id} not found")
        return False

    fetched_field = f'price_fetched_{offset_key}'

    # Already fetched this offset
    if getattr(impact, fetched_field, False):
        return True

    price = get_current_price(impact.stock.ticker)
    if price is None:
        return False

    setattr(impact, f'price_{offset_key}', price)
    setattr(impact, fetched_field, True)
    impact.save()

    # Recompute impacts and direction label
    impact.compute_impacts()

    logger.info(
        f"Price at +{offset_key} for {impact.stock.ticker}: ${price:.2f} "
        f"(publish: ${impact.price_at_publish or 0:.2f})"
    )
    return True


def backfill_price_impact(narrative: Narrative) -> PriceImpact | None:
    """
    For historical narratives, fetch all 4 price points using historical data.
    Used by the backfill management command.
    """
    impact, _ = PriceImpact.objects.get_or_create(
        narrative=narrative,
        defaults={'stock': narrative.stock},
    )

    ticker = narrative.stock.ticker
    pub_dt = narrative.published_at

    # Price at publish time
    if not impact.price_fetched_at_publish:
        price = get_historical_price(ticker, pub_dt)
        if price is not None:
            impact.price_at_publish = price
            impact.price_fetched_at_publish = True

    # Price at +1h
    if not impact.price_fetched_1h:
        price = get_historical_price(ticker, pub_dt + timedelta(hours=1))
        if price is not None:
            impact.price_1h = price
            impact.price_fetched_1h = True

    # Price at +4h
    if not impact.price_fetched_4h:
        price = get_historical_price(ticker, pub_dt + timedelta(hours=4))
        if price is not None:
            impact.price_4h = price
            impact.price_fetched_4h = True

    # Price at +24h
    if not impact.price_fetched_24h:
        price = get_historical_price(ticker, pub_dt + timedelta(hours=24))
        if price is not None:
            impact.price_24h = price
            impact.price_fetched_24h = True

    impact.save()
    impact.compute_impacts()

    return impact


def get_daily_api_usage() -> dict:
    """Return today's Twelve Data API usage stats."""
    key = f'twelvedata_calls:{timezone.now().strftime("%Y-%m-%d")}'
    count = cache.get(key, 0)
    return {
        'calls_today': count,
        'daily_limit': DAILY_LIMIT,
        'remaining': max(0, DAILY_LIMIT - count),
    }
