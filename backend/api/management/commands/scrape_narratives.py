from django.core.management.base import BaseCommand

from api.models import Stock
from api.analysis import ensure_sentiment_scores
from api.scrapers import RSSScraper, RedditScraper, GNewsScraper


SCRAPER_MAP = {
    'rss': RSSScraper,
    'reddit': RedditScraper,
    'gnews': GNewsScraper,
}


class Command(BaseCommand):
    help = 'Scrape news/posts from RSS, Reddit, and/or GNews for stock tickers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Single ticker to scrape (e.g. AAPL)',
        )
        parser.add_argument(
            '--all-stocks',
            action='store_true',
            help='Scrape all active stocks in the database',
        )
        parser.add_argument(
            '--sources',
            type=str,
            default='rss,reddit,gnews',
            help='Comma-separated sources to use (default: rss,reddit,gnews)',
        )
        parser.add_argument(
            '--backfill-days',
            type=int,
            default=1,
            help='How many days back to look for articles (default: 1)',
        )
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Run VADER sentiment analysis on new narratives after scraping',
        )

    def handle(self, *args, **options):
        ticker = options['ticker']
        all_stocks = options['all_stocks']
        sources_str = options['sources']
        backfill_days = options['backfill_days']
        analyze = options['analyze']

        if not ticker and not all_stocks:
            self.stderr.write(self.style.ERROR(
                'Provide --ticker AAPL or --all-stocks'
            ))
            return

        # Parse sources
        source_names = [s.strip().lower() for s in sources_str.split(',')]
        scrapers = []
        for name in source_names:
            cls = SCRAPER_MAP.get(name)
            if cls:
                scrapers.append(cls())
            else:
                self.stderr.write(self.style.WARNING(
                    f"Unknown source '{name}' — skipping (options: {', '.join(SCRAPER_MAP.keys())})"
                ))

        if not scrapers:
            self.stderr.write(self.style.ERROR('No valid sources specified'))
            return

        # Get stocks to scrape
        if ticker:
            stock, created = Stock.objects.get_or_create(
                ticker=ticker.upper(),
                defaults={'name': ticker.upper()},
            )
            stocks = [stock]
            if created:
                self.stdout.write(f"Created new stock record: {stock.ticker}")
        else:
            stocks = list(Stock.objects.filter(is_active=True))
            if not stocks:
                self.stderr.write(self.style.WARNING(
                    'No active stocks in database. Use --ticker to add one.'
                ))
                return

        # Scrape each stock
        grand_total = 0
        for stock in stocks:
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(self.style.HTTP_INFO(f"Scraping {stock.ticker} ({stock.name})"))
            stock_total = 0

            for scraper in scrapers:
                try:
                    articles = scraper.fetch(stock, lookback_days=backfill_days)
                    saved = scraper.save_narratives(stock, articles)
                    stock_total += saved

                    source_label = scraper.__class__.__name__.replace('Scraper', '')
                    self.stdout.write(
                        f"  {source_label}: {len(articles)} fetched, {saved} new"
                    )
                except Exception as e:
                    self.stderr.write(self.style.ERROR(
                        f"  {scraper.__class__.__name__} error: {e}"
                    ))

            # Optionally analyze sentiment
            if analyze:
                scored = ensure_sentiment_scores(stock)
                self.stdout.write(f"  Sentiment: {scored} new scores created")

            self.stdout.write(self.style.SUCCESS(
                f"  Total: {stock_total} new narratives saved for {stock.ticker}"
            ))
            grand_total += stock_total

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(self.style.SUCCESS(
            f"Done! {grand_total} total new narratives across {len(stocks)} stock(s)"
        ))
