import logging
from datetime import datetime, timezone as dt_tz

from api.models import Stock
from .base import BaseScraper

logger = logging.getLogger(__name__)


class YahooFinanceScraper(BaseScraper):
    """
    Uses yfinance Ticker.news to pull Yahoo Finance articles.
    No API key needed, no rate limit documented — treat like RSS (every 5–10 min is fine).
    Returns richer article set than the Yahoo RSS headline feed.
    """
    source = 'yahoo'
    source_name = 'Yahoo Finance'

    def fetch(self, stock: Stock, lookback_days: int = 1) -> list[dict]:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed — skipping YahooFinanceScraper")
            return []

        try:
            ticker_obj = yf.Ticker(stock.ticker)
            raw_news = ticker_obj.news or []
        except Exception as e:
            logger.warning(f"YahooFinance: failed to fetch news for {stock.ticker}: {e}")
            return []

        cutoff_ts = datetime.now(dt_tz.utc).timestamp() - (lookback_days * 86400)
        articles = []

        for item in raw_news:
            try:
                content = item.get('content', {})
                if not isinstance(content, dict):
                    continue

                pub_ts = content.get('pubDate') or ''
                if pub_ts:
                    try:
                        published_at = datetime.fromisoformat(pub_ts.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                else:
                    # fallback: providerPublishTime is a unix timestamp on older yfinance versions
                    raw_ts = item.get('providerPublishTime')
                    if not raw_ts:
                        continue
                    published_at = datetime.fromtimestamp(raw_ts, tz=dt_tz.utc)

                if published_at.timestamp() < cutoff_ts:
                    continue

                title = (content.get('title') or item.get('title') or '').strip()
                if not title:
                    continue

                url = (
                    content.get('canonicalUrl', {}).get('url')
                    or content.get('clickThroughUrl', {}).get('url')
                    or item.get('link', '')
                )

                summary = content.get('summary') or content.get('description') or ''
                publisher = (
                    content.get('provider', {}).get('displayName')
                    or item.get('publisher', self.source_name)
                )

                articles.append({
                    'title': title,
                    'content': summary[:2000],
                    'url': url,
                    'published_at': published_at,
                    'source_name': publisher,
                })

            except Exception as e:
                logger.warning(f"YahooFinance: error parsing article for {stock.ticker}: {e}")
                continue

        logger.info(f"YahooFinance: fetched {len(articles)} articles for {stock.ticker}")
        return articles
