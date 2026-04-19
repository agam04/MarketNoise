import logging
import os
import re
from datetime import datetime, timedelta, timezone as dt_tz

from api.models import Stock
from .base import BaseScraper

logger = logging.getLogger(__name__)

SUBREDDITS = ['wallstreetbets', 'stocks', 'investing']

# Time filter mapping for Reddit search
LOOKBACK_TO_FILTER = {
    1: 'day',
    7: 'week',
    30: 'month',
    365: 'year',
}


def _get_time_filter(lookback_days: int) -> str:
    """Map lookback_days to Reddit's time_filter values."""
    for threshold, filter_val in sorted(LOOKBACK_TO_FILTER.items()):
        if lookback_days <= threshold:
            return filter_val
    return 'year'


class RedditScraper(BaseScraper):
    source = 'reddit'
    source_name = 'Reddit'

    def __init__(self):
        self._reddit = None

    def _get_client(self):
        """Lazy-init PRAW client. Returns None if credentials missing."""
        if self._reddit is not None:
            return self._reddit

        client_id = os.getenv('REDDIT_CLIENT_ID', '')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET', '')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'MarketNoise/1.0')

        if not client_id or not client_secret:
            logger.warning("Reddit credentials not configured (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)")
            return None

        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
            return self._reddit
        except ImportError:
            logger.warning("praw not installed — run: pip install praw")
            return None
        except Exception as e:
            logger.warning(f"Failed to init Reddit client: {e}")
            return None

    def fetch(self, stock: Stock, lookback_days: int = 1) -> list[dict]:
        reddit = self._get_client()
        if reddit is None:
            return []

        cutoff = datetime.now(dt_tz.utc) - timedelta(days=lookback_days)
        time_filter = _get_time_filter(lookback_days)
        articles = []

        for sub_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(sub_name)
                # Search for posts mentioning the ticker
                results = subreddit.search(
                    stock.ticker,
                    sort='new',
                    time_filter=time_filter,
                    limit=25,
                )

                for post in results:
                    created_at = datetime.fromtimestamp(post.created_utc, tz=dt_tz.utc)
                    if created_at < cutoff:
                        continue

                    title = post.title.strip()
                    if not title:
                        continue

                    # Verify ticker actually appears in title (avoid false positives)
                    if not re.search(rf'\b{re.escape(stock.ticker)}\b', title.upper()):
                        # Also check selftext for short posts
                        selftext = (post.selftext or '')[:500].upper()
                        if not re.search(rf'\b{re.escape(stock.ticker)}\b', selftext):
                            continue

                    articles.append({
                        'title': title,
                        'content': (post.selftext or '')[:2000],
                        'url': f'https://reddit.com{post.permalink}',
                        'published_at': created_at,
                        'source_name': f'r/{sub_name}',
                    })

            except Exception as e:
                logger.warning(f"Reddit scrape error (r/{sub_name}): {e}")
                continue

        logger.info(f"Reddit: fetched {len(articles)} posts for {stock.ticker}")
        return articles
