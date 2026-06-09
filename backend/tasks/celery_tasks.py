import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _run_scraper(scraper_cls, ticker: str, lookback_days: int = 1):
    """Shared helper: run one scraper for a ticker, save narratives, queue price tracking."""
    from api.models import Stock, Narrative

    ticker = ticker.upper()
    stock, _ = Stock.objects.get_or_create(ticker=ticker, defaults={'name': ticker})

    existing_ids = set(Narrative.objects.filter(stock=stock).values_list('id', flat=True))

    try:
        scraper = scraper_cls()
        articles = scraper.fetch(stock, lookback_days=lookback_days)
        saved = scraper.save_narratives(stock, articles)
        logger.info(f"{scraper_cls.__name__}: {saved} new for {ticker} (lookback={lookback_days}d)")
    except Exception as e:
        logger.warning(f"{scraper_cls.__name__} error for {ticker}: {e}")
        saved = 0

    if saved:
        # Queue FinBERT scoring on the 'sentiment' queue (solo-pool worker — no fork)
        score_sentiment.apply_async(args=[ticker], queue='sentiment')
        new_narratives = Narrative.objects.filter(stock=stock).exclude(id__in=existing_ids)
        for narrative in new_narratives:
            record_publish_price.delay(narrative.id)

    return saved


@shared_task(queue='sentiment')
def score_sentiment(ticker: str):
    """Run FinBERT sentiment scoring. Must run on a solo-pool worker to avoid fork+PyTorch crash."""
    from api.models import Stock
    from api.analysis import ensure_sentiment_scores

    ticker = ticker.upper()
    try:
        stock = Stock.objects.get(ticker=ticker)
        ensure_sentiment_scores(stock)
        logger.info(f"Sentiment scored for {ticker}")
    except Stock.DoesNotExist:
        logger.warning(f"score_sentiment: stock {ticker} not found")


@shared_task
def scrape_rss(ticker: str, lookback_days: int = 1):
    from api.scrapers import RSSScraper
    return _run_scraper(RSSScraper, ticker, lookback_days)


@shared_task
def scrape_reddit(ticker: str, lookback_days: int = 1):
    from api.scrapers import RedditScraper
    return _run_scraper(RedditScraper, ticker, lookback_days)


@shared_task
def scrape_gnews(ticker: str, lookback_days: int = 1):
    from api.scrapers import GNewsScraper
    return _run_scraper(GNewsScraper, ticker, lookback_days)


@shared_task
def scrape_yahoo(ticker: str, lookback_days: int = 1):
    from api.scrapers import YahooFinanceScraper
    return _run_scraper(YahooFinanceScraper, ticker, lookback_days)


@shared_task
def scrape_all_sources(ticker: str, lookback_days: int = 1):
    """Run all scrapers for a single ticker."""
    scrape_rss.delay(ticker, lookback_days)
    scrape_reddit.delay(ticker, lookback_days)
    scrape_gnews.delay(ticker, lookback_days)
    scrape_yahoo.delay(ticker, lookback_days)


# ── Per-scraper beat fans: each dispatches its own scraper to all active stocks ──

@shared_task
def beat_rss():
    """Beat task: RSS every 5 min — free feeds, no rate limit."""
    from api.models import Stock
    tickers = list(Stock.objects.filter(is_active=True).values_list('ticker', flat=True))
    logger.info(f"[RSS beat] scraping {len(tickers)} stocks")
    for t in tickers:
        scrape_rss.delay(t)


@shared_task
def beat_reddit():
    """Beat task: Reddit every 15 min — generous rate limit but still throttled."""
    from api.models import Stock
    tickers = list(Stock.objects.filter(is_active=True).values_list('ticker', flat=True))
    logger.info(f"[Reddit beat] scraping {len(tickers)} stocks")
    for t in tickers:
        scrape_reddit.delay(t)


@shared_task
def beat_gnews():
    """Beat task: GNews every 60 min — 100 req/day free tier, must conserve."""
    from api.models import Stock
    tickers = list(Stock.objects.filter(is_active=True).values_list('ticker', flat=True))
    logger.info(f"[GNews beat] scraping {len(tickers)} stocks")
    for t in tickers:
        scrape_gnews.delay(t)


@shared_task
def beat_yahoo():
    """Beat task: Yahoo Finance every 10 min — no API key, no documented rate limit."""
    from api.models import Stock
    tickers = list(Stock.objects.filter(is_active=True).values_list('ticker', flat=True))
    logger.info(f"[Yahoo beat] scraping {len(tickers)} stocks")
    for t in tickers:
        scrape_yahoo.delay(t)


@shared_task
def scrape_all_stocks():
    """Legacy beat task: kept for compatibility, triggers all three scrapers."""
    beat_rss.delay()
    beat_reddit.delay()
    beat_gnews.delay()


@shared_task
def record_publish_price(narrative_id: int):
    """Fetch and record the stock price at narrative publish time, then schedule follow-ups."""
    from api.models import Narrative
    from api.price_tracker import create_price_impact

    try:
        narrative = Narrative.objects.get(id=narrative_id)
    except Narrative.DoesNotExist:
        logger.warning(f"Narrative {narrative_id} not found")
        return

    impact = create_price_impact(narrative)
    if impact and impact.price_fetched_at_publish:
        # Schedule follow-up price checks
        check_price_offset.apply_async(
            args=[impact.id, '1h'], countdown=3600
        )
        check_price_offset.apply_async(
            args=[impact.id, '4h'], countdown=14400
        )
        check_price_offset.apply_async(
            args=[impact.id, '24h'], countdown=86400
        )
        logger.info(
            f"Price tracking scheduled for narrative {narrative_id} "
            f"({narrative.stock.ticker}): +1h, +4h, +24h"
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def check_price_offset(self, impact_id: int, offset_key: str):
    """Fetch price at a specific offset (+1h/+4h/+24h). Retries on failure."""
    from api.price_tracker import check_price_at_offset

    success = check_price_at_offset(impact_id, offset_key)
    if not success:
        logger.warning(
            f"Price check failed for impact {impact_id} at +{offset_key}, "
            f"retry {self.request.retries}/{self.max_retries}"
        )
        self.retry()


@shared_task
def run_full_pipeline(ticker: str):
    """Scrape + full analysis for one ticker."""
    from api.analysis import (
        analyze_stock_sentiment,
        compute_velocity,
        compute_hype_score,
    )

    scrape_all_sources(ticker)
    analyze_stock_sentiment(ticker, '')
    compute_velocity(ticker)
    compute_hype_score(ticker)
