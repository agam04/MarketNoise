import time

from django.core.management.base import BaseCommand

from api.models import Stock, Narrative, PriceImpact
from api.price_tracker import backfill_price_impact, get_daily_api_usage


class Command(BaseCommand):
    help = 'Backfill PriceImpact records for historical narratives using Twelve Data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Single ticker to backfill (e.g. AAPL)',
        )
        parser.add_argument(
            '--all-stocks',
            action='store_true',
            help='Backfill all active stocks',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Max narratives to process (default: 50). Each uses up to 4 API calls.',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Seconds to wait between API calls (default: 1.0)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making API calls',
        )

    def handle(self, *args, **options):
        ticker = options['ticker']
        all_stocks = options['all_stocks']
        limit = options['limit']
        delay = options['delay']
        dry_run = options['dry_run']

        if not ticker and not all_stocks:
            self.stderr.write(self.style.ERROR(
                'Provide --ticker AAPL or --all-stocks'
            ))
            return

        # Get stocks
        if ticker:
            try:
                stock = Stock.objects.get(ticker=ticker.upper())
            except Stock.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Stock {ticker.upper()} not found"))
                return
            stocks = [stock]
        else:
            stocks = list(Stock.objects.filter(is_active=True))

        # Find narratives without complete PriceImpact records
        narratives = Narrative.objects.filter(
            stock__in=stocks
        ).exclude(
            price_impact__price_fetched_24h=True
        ).order_by('-published_at')[:limit]

        total = narratives.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No narratives need backfilling."))
            return

        # Show API usage
        usage = get_daily_api_usage()
        self.stdout.write(f"Twelve Data API: {usage['calls_today']}/{usage['daily_limit']} used today, {usage['remaining']} remaining")
        self.stdout.write(f"Narratives to process: {total} (up to {total * 4} API calls)")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--- DRY RUN ---"))
            for n in narratives:
                has_impact = hasattr(n, 'price_impact')
                status = 'partial' if has_impact else 'new'
                self.stdout.write(
                    f"  [{status}] {n.stock.ticker} | {n.published_at:%Y-%m-%d %H:%M} | {n.title[:60]}"
                )
            self.stdout.write(self.style.WARNING(f"\nWould process {total} narratives. Run without --dry-run to execute."))
            return

        # Process narratives
        success = 0
        skipped = 0

        for i, narrative in enumerate(narratives, 1):
            # Check rate limit before each narrative (uses up to 4 calls)
            usage = get_daily_api_usage()
            if usage['remaining'] < 4:
                self.stderr.write(self.style.WARNING(
                    f"\nRate limit approaching ({usage['remaining']} calls left). Stopping."
                ))
                break

            self.stdout.write(
                f"[{i}/{total}] {narrative.stock.ticker} | "
                f"{narrative.published_at:%Y-%m-%d %H:%M} | "
                f"{narrative.title[:50]}...",
                ending=' '
            )

            try:
                impact = backfill_price_impact(narrative)
                if impact and impact.price_fetched_at_publish:
                    parts = []
                    if impact.price_at_publish:
                        parts.append(f"pub=${impact.price_at_publish:.2f}")
                    if impact.price_24h:
                        parts.append(f"24h=${impact.price_24h:.2f}")
                    if impact.direction_24h:
                        parts.append(f"dir={impact.direction_24h}")

                    self.stdout.write(self.style.SUCCESS(f"OK ({', '.join(parts)})"))
                    success += 1
                else:
                    self.stdout.write(self.style.WARNING("SKIPPED (rate limited)"))
                    skipped += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR: {e}"))
                skipped += 1

            # Rate limit delay
            time.sleep(delay)

        # Summary
        self.stdout.write(f"\n{'='*50}")
        usage = get_daily_api_usage()
        self.stdout.write(self.style.SUCCESS(
            f"Done! {success} backfilled, {skipped} skipped. "
            f"API calls remaining today: {usage['remaining']}"
        ))

        # Show label distribution
        labeled = PriceImpact.objects.filter(
            stock__in=stocks,
            direction_24h__in=['up', 'down', 'flat'],
        )
        up = labeled.filter(direction_24h='up').count()
        down = labeled.filter(direction_24h='down').count()
        flat = labeled.filter(direction_24h='flat').count()

        if up + down + flat > 0:
            self.stdout.write(f"\nLabel distribution:")
            self.stdout.write(f"  Up:   {up}")
            self.stdout.write(f"  Down: {down}")
            self.stdout.write(f"  Flat: {flat}")
            self.stdout.write(f"  Total labeled: {up + down + flat}")
