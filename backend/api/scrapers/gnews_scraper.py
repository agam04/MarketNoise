import logging
import os
from datetime import datetime, timedelta, timezone as dt_tz

import requests as http

from api.models import Stock
from .base import BaseScraper

logger = logging.getLogger(__name__)

GNEWS_KEY = os.getenv('GNEWS_API_KEY', '')
GNEWS_BASE = 'https://gnews.io/api/v4'


class GNewsScraper(BaseScraper):
    source = 'news'
    source_name = 'GNews'

    def fetch(self, stock: Stock, lookback_days: int = 1) -> list[dict]:
        if not GNEWS_KEY:
            logger.warning("GNEWS_API_KEY not set")
            return []

        query = f'{stock.ticker} OR "{stock.name}" stock'
        articles = []

        try:
            params = {
                'q': query,
                'lang': 'en',
                'max': 10,
                'token': GNEWS_KEY,
            }

            # GNews supports 'from' param for date filtering
            if lookback_days > 0:
                from_date = (datetime.now(dt_tz.utc) - timedelta(days=lookback_days))
                params['from'] = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

            resp = http.get(f'{GNEWS_BASE}/search', params=params, timeout=10)
            if not resp.ok:
                logger.warning(f"GNews API error: {resp.status_code}")
                return []

            data = resp.json()
            raw_articles = data.get('articles', [])

            for article in raw_articles:
                title = article.get('title', '').strip()
                if not title:
                    continue

                description = article.get('description', '')
                url = article.get('url', '')
                source_name = article.get('source', {}).get('name', 'GNews')
                published_str = article.get('publishedAt', '')

                try:
                    published_at = datetime.fromisoformat(
                        published_str.replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    published_at = datetime.now(dt_tz.utc)

                articles.append({
                    'title': title,
                    'content': description[:2000] if description else '',
                    'url': url,
                    'published_at': published_at,
                    'source_name': source_name,
                })

        except Exception as e:
            logger.warning(f"GNews scrape error: {e}")

        logger.info(f"GNews: fetched {len(articles)} articles for {stock.ticker}")
        return articles
