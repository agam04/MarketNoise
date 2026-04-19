import logging
from abc import ABC, abstractmethod

from django.db import IntegrityError

from api.models import Stock, Narrative

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all news/social scrapers."""

    source: str  # 'news', 'rss', 'reddit', etc.
    source_name: str  # human-readable name, e.g. 'Yahoo Finance RSS'

    @abstractmethod
    def fetch(self, stock: Stock, lookback_days: int = 1) -> list[dict]:
        """
        Fetch articles/posts for a stock.

        Returns a list of dicts with keys:
            - title: str
            - content: str (can be empty)
            - url: str
            - published_at: datetime (timezone-aware)
            - source_name: str (overrides self.source_name if set)
        """
        pass

    def save_narratives(self, stock: Stock, articles: list[dict]) -> int:
        """Deduplicate by URL and save new narratives. Returns count saved."""
        saved = 0
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '')

            if not title:
                continue

            # Skip if URL already exists (also enforced by DB constraint)
            if url and Narrative.objects.filter(url=url).exists():
                continue

            try:
                Narrative.objects.create(
                    stock=stock,
                    title=title[:500],
                    content=article.get('content', ''),
                    source=self.source,
                    source_name=article.get('source_name', self.source_name),
                    url=url,
                    published_at=article['published_at'],
                )
                saved += 1
            except IntegrityError:
                # URL uniqueness constraint hit (race condition)
                continue
            except Exception as e:
                logger.warning(f"Failed to save narrative: {e}")
                continue

        return saved
