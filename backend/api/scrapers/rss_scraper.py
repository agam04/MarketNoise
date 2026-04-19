import logging
import re
from datetime import datetime, timedelta, timezone as dt_tz
from time import mktime

import feedparser

from api.models import Stock
from .base import BaseScraper

logger = logging.getLogger(__name__)

# RSS feeds — {url} is replaced with ticker, {query} with ticker+company name
RSS_FEEDS = [
    {
        'name': 'Yahoo Finance',
        'url': 'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US',
        'ticker_in_url': True,
    },
    {
        'name': 'MarketWatch',
        'url': 'https://feeds.marketwatch.com/marketwatch/topstories/',
        'ticker_in_url': False,
    },
    {
        'name': 'Google Finance News',
        'url': 'https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en',
        'ticker_in_url': True,
    },
]


class RSSScraper(BaseScraper):
    source = 'rss'
    source_name = 'RSS'

    def fetch(self, stock: Stock, lookback_days: int = 1) -> list[dict]:
        cutoff = datetime.now(dt_tz.utc) - timedelta(days=lookback_days)
        articles = []

        for feed_config in RSS_FEEDS:
            try:
                url = feed_config['url'].format(
                    ticker=stock.ticker,
                    query=f"{stock.ticker} {stock.name}",
                )
                feed = feedparser.parse(url)

                for entry in feed.entries:
                    # Parse published date
                    published_at = self._parse_date(entry)
                    if published_at is None:
                        continue
                    if published_at < cutoff:
                        continue

                    title = entry.get('title', '').strip()
                    if not title:
                        continue

                    # For non-ticker-specific feeds, filter by relevance
                    if not feed_config['ticker_in_url']:
                        if not self._is_relevant(title, stock):
                            continue

                    summary = entry.get('summary', entry.get('description', ''))
                    # Strip HTML tags from summary
                    summary = re.sub(r'<[^>]+>', '', summary).strip()

                    link = entry.get('link', '')

                    articles.append({
                        'title': title,
                        'content': summary[:2000],
                        'url': link,
                        'published_at': published_at,
                        'source_name': feed_config['name'],
                    })

            except Exception as e:
                logger.warning(f"RSS feed error ({feed_config['name']}): {e}")
                continue

        logger.info(f"RSS: fetched {len(articles)} articles for {stock.ticker}")
        return articles

    def _parse_date(self, entry) -> datetime | None:
        """Parse date from feedparser entry."""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime.fromtimestamp(
                    mktime(entry.published_parsed), tz=dt_tz.utc
                )
            except (ValueError, OverflowError):
                pass

        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime.fromtimestamp(
                    mktime(entry.updated_parsed), tz=dt_tz.utc
                )
            except (ValueError, OverflowError):
                pass

        return None

    def _is_relevant(self, title: str, stock: Stock) -> bool:
        """Check if a title mentions the stock ticker or company name."""
        title_upper = title.upper()
        # Match ticker as a whole word
        if re.search(rf'\b{re.escape(stock.ticker)}\b', title_upper):
            return True
        # Match company name (first word, at least 4 chars, to avoid false positives)
        name_parts = stock.name.split()
        if name_parts:
            primary_name = name_parts[0]
            if len(primary_name) >= 4 and primary_name.lower() in title.lower():
                return True
        return False
