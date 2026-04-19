from django.core.management.base import BaseCommand

from api.models import Stock, Narrative, SentimentScore, PriceImpact
from api.price_tracker import get_daily_api_usage


class Command(BaseCommand):
    help = 'Show dataset statistics — how much training data is available'

    def handle(self, *args, **options):
        self.stdout.write(f"\n{'='*55}")
        self.stdout.write("  MarketNoise Dataset Statistics")
        self.stdout.write(f"{'='*55}\n")

        # Stocks
        total_stocks = Stock.objects.count()
        active_stocks = Stock.objects.filter(is_active=True).count()
        self.stdout.write(f"  Stocks:          {total_stocks} total, {active_stocks} active")

        # Narratives by source
        total_narratives = Narrative.objects.count()
        by_source = {}
        for n in Narrative.objects.values('source'):
            src = n['source']
            by_source[src] = by_source.get(src, 0) + 1

        self.stdout.write(f"  Narratives:      {total_narratives} total")
        for src, count in sorted(by_source.items()):
            self.stdout.write(f"    {src:15s} {count}")

        # Sentiment scores
        scored = SentimentScore.objects.count()
        unscored = total_narratives - scored
        self.stdout.write(f"\n  Sentiment Scored: {scored} ({unscored} unscored)")

        # PriceImpact coverage
        total_impacts = PriceImpact.objects.count()
        has_publish = PriceImpact.objects.filter(price_fetched_at_publish=True).count()
        has_1h = PriceImpact.objects.filter(price_fetched_1h=True).count()
        has_4h = PriceImpact.objects.filter(price_fetched_4h=True).count()
        has_24h = PriceImpact.objects.filter(price_fetched_24h=True).count()

        self.stdout.write(f"\n  Price Impacts:    {total_impacts} total")
        self.stdout.write(f"    publish price:  {has_publish}")
        self.stdout.write(f"    +1h price:      {has_1h}")
        self.stdout.write(f"    +4h price:      {has_4h}")
        self.stdout.write(f"    +24h price:     {has_24h}")

        # Label distribution (ML training readiness)
        labeled = PriceImpact.objects.filter(direction_24h__in=['up', 'down', 'flat'])
        up = labeled.filter(direction_24h='up').count()
        down = labeled.filter(direction_24h='down').count()
        flat = labeled.filter(direction_24h='flat').count()
        total_labeled = up + down + flat

        self.stdout.write(f"\n  ML Training Labels:")
        self.stdout.write(f"    Up:    {up}")
        self.stdout.write(f"    Down:  {down}")
        self.stdout.write(f"    Flat:  {flat}")
        self.stdout.write(f"    Total: {total_labeled}")

        if total_labeled < 50:
            self.stdout.write(self.style.WARNING(
                f"\n  Need at least 50 labeled samples to train. "
                f"Currently {total_labeled}. Keep scraping + backfilling!"
            ))
        elif total_labeled < 200:
            self.stdout.write(self.style.WARNING(
                f"\n  {total_labeled} samples — enough for a basic model. "
                f"200+ recommended for better accuracy."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n  {total_labeled} samples — ready for model training! "
                f"Run: python manage.py train_model"
            ))

        # API usage
        usage = get_daily_api_usage()
        self.stdout.write(
            f"\n  Twelve Data API: {usage['calls_today']}/{usage['daily_limit']} "
            f"used today ({usage['remaining']} remaining)"
        )

        self.stdout.write(f"\n{'='*55}")
