import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def scrape_all_sources(ticker: str):
    """Scrape RSS, Reddit, and GNews for a single ticker."""
    from api.models import Stock, Narrative
    from api.scrapers import RSSScraper, RedditScraper, GNewsScraper
    from api.analysis import ensure_sentiment_scores

    ticker = ticker.upper()
    stock, _ = Stock.objects.get_or_create(
        ticker=ticker, defaults={'name': ticker}
    )

    # Track narrative IDs before scraping to find new ones
    existing_ids = set(
        Narrative.objects.filter(stock=stock).values_list('id', flat=True)
    )

    scrapers = [RSSScraper(), RedditScraper(), GNewsScraper()]
    total = 0

    for scraper in scrapers:
        try:
            articles = scraper.fetch(stock, lookback_days=1)
            saved = scraper.save_narratives(stock, articles)
            total += saved
            logger.info(f"{scraper.__class__.__name__}: {saved} new for {ticker}")
        except Exception as e:
            logger.warning(f"{scraper.__class__.__name__} error for {ticker}: {e}")

    # Auto-analyze sentiment on new narratives
    scored = ensure_sentiment_scores(stock)
    logger.info(f"Sentiment scored {scored} new narratives for {ticker}")

    # Schedule price tracking for newly scraped narratives
    new_narratives = Narrative.objects.filter(
        stock=stock
    ).exclude(id__in=existing_ids)

    for narrative in new_narratives:
        record_publish_price.delay(narrative.id)

    return total


@shared_task
def scrape_all_stocks():
    """Periodic task: scrape all active stocks."""
    from api.models import Stock

    tickers = list(
        Stock.objects.filter(is_active=True).values_list('ticker', flat=True)
    )
    logger.info(f"Scheduled scrape for {len(tickers)} stocks")

    for ticker in tickers:
        scrape_all_sources.delay(ticker)


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
