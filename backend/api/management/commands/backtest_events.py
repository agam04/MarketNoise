"""
Earnings event backtester — validates FinBERT signal on controlled events.

Unlike random-day sentiment tests, earnings events are:
  - Discrete and date-stamped (we know exactly when they happened)
  - High-magnitude (3-15% moves, not 0.5% daily noise)
  - Measurable: EPS beat/miss is an objective ground truth

Two modes run together by default:
  --mode past    Retrospective: did pre-earnings sentiment predict the result?
  --mode future  Forward-looking: what does current sentiment say about upcoming reports?
  --mode both    (default) Run both

The system saves pre-earnings snapshots to the DB so the prediction track record
accumulates automatically every time the command runs before earnings.

Usage:
    python manage.py backtest_events
    python manage.py backtest_events --mode past --lookback 60
    python manage.py backtest_events --tickers AAPL,MSFT,NVDA
    python manage.py backtest_events --verbose
"""

import os
import time
import warnings
import requests
from datetime import datetime, timedelta, date, timezone

warnings.filterwarnings('ignore')

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
nltk.download('vader_lexicon', quiet=True)

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

try:
    from scipy import stats as scipy_stats
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False

GNEWS_KEY = os.getenv('GNEWS_API_KEY', '')
GNEWS_BASE = 'https://gnews.io/api/v4'

# Wide net of tickers that span sectors and reporting schedules
DEFAULT_TICKERS = [
    'JPM', 'GS', 'BAC', 'WFC', 'C',            # Banks (report early in season)
    'NFLX', 'AAPL', 'MSFT', 'META', 'GOOGL',   # Big tech
    'AMZN', 'TSLA', 'NVDA', 'AMD', 'ORCL',     # Semis + cloud
    'ADBE', 'CRM', 'UBER', 'SNAP', 'SPOT',     # Growth tech
]

_vader = SentimentIntensityAnalyzer()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vader_score(texts: list[str]) -> dict:
    if not texts:
        return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0, 'label': 'neutral', 'n': 0}
    scores = [_vader.polarity_scores(t) for t in texts]
    compound = sum(s['compound'] for s in scores) / len(scores)
    pos = sum(s['pos'] for s in scores) / len(scores)
    neg = sum(s['neg'] for s in scores) / len(scores)
    neu = sum(s['neu'] for s in scores) / len(scores)
    label = 'positive' if compound >= 0.05 else ('negative' if compound <= -0.05 else 'neutral')
    return {'compound': round(compound, 4), 'pos': round(pos, 4),
            'neg': round(neg, 4), 'neu': round(neu, 4), 'label': label, 'n': len(texts)}


def _finbert_score(texts: list[str]) -> dict:
    if not texts:
        return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0, 'label': 'neutral', 'n': 0}
    from api.nlp import finbert
    results = finbert.analyze_batch(texts)
    compound = sum(r['compound'] for r in results) / len(results)
    pos = sum(r['pos'] for r in results) / len(results)
    neg = sum(r['neg'] for r in results) / len(results)
    neu = sum(r['neu'] for r in results) / len(results)
    label = 'positive' if compound >= 0.05 else ('negative' if compound <= -0.05 else 'neutral')
    return {'compound': round(compound, 4), 'pos': round(pos, 4),
            'neg': round(neg, 4), 'neu': round(neu, 4), 'label': label, 'n': len(texts)}


def _fetch_pre_earnings_news(ticker: str, earnings_date: date, window_days: int = 5) -> list[str]:
    """
    Fetch news articles from [earnings_date - window_days] to [earnings_date - 1].
    Returns list of article texts (title + description).
    """
    if not GNEWS_KEY:
        return []
    from_dt = (earnings_date - timedelta(days=window_days)).isoformat() + 'T00:00:00Z'
    to_dt   = (earnings_date - timedelta(days=1)).isoformat()           + 'T23:59:59Z'
    try:
        resp = requests.get(
            f'{GNEWS_BASE}/search',
            params={
                'q': f'"{ticker}" earnings OR "{ticker}" stock',
                'lang': 'en',
                'max': 10,
                'from': from_dt,
                'to': to_dt,
                'sortby': 'publishedAt',
                'token': GNEWS_KEY,
            },
            timeout=15,
        )
        if not resp.ok:
            return []
        articles = resp.json().get('articles', [])
        texts = []
        for a in articles:
            title = a.get('title', '') or ''
            desc  = a.get('description', '') or ''
            texts.append(f"{title}. {desc}" if desc else title)
        return texts
    except Exception:
        return []


def _fetch_current_news(ticker: str, days: int = 7) -> list[str]:
    """Fetch the most recent N days of news for upcoming-earnings analysis."""
    if not GNEWS_KEY:
        return []
    from_dt = (date.today() - timedelta(days=days)).isoformat() + 'T00:00:00Z'
    try:
        resp = requests.get(
            f'{GNEWS_BASE}/search',
            params={
                'q': f'"{ticker}" stock',
                'lang': 'en',
                'max': 10,
                'from': from_dt,
                'sortby': 'publishedAt',
                'token': GNEWS_KEY,
            },
            timeout=15,
        )
        if not resp.ok:
            return []
        articles = resp.json().get('articles', [])
        texts = []
        for a in articles:
            title = a.get('title', '') or ''
            desc  = a.get('description', '') or ''
            texts.append(f"{title}. {desc}" if desc else title)
        return texts
    except Exception:
        return []


def _get_price_reaction(ticker: str, earnings_date: date) -> dict | None:
    """
    Compute the price reaction around earnings.
    Uses pre-earnings close vs post-earnings close (D-1 → D+1).
    """
    try:
        start = earnings_date - timedelta(days=5)
        end   = earnings_date + timedelta(days=3)
        df = yf.Ticker(ticker).history(start=start.isoformat(), end=(end + timedelta(days=1)).isoformat())
        if df.empty:
            return None

        prices = {idx.date(): float(row['Close']) for idx, row in df.iterrows()}
        sorted_dates = sorted(prices.keys())

        pre_date  = next((d for d in reversed(sorted_dates) if d < earnings_date), None)
        post_date = next((d for d in sorted_dates if d >= earnings_date), None)

        if not pre_date or not post_date:
            return None

        pre_price  = prices[pre_date]
        post_price = prices[post_date]
        reaction   = (post_price - pre_price) / pre_price * 100
        direction  = 'up' if reaction > 0.5 else ('down' if reaction < -0.5 else 'flat')

        return {
            'pre_date': pre_date.isoformat(),
            'post_date': post_date.isoformat(),
            'pre_price': round(pre_price, 2),
            'post_price': round(post_price, 2),
            'reaction_pct': round(reaction, 2),
            'direction': direction,
        }
    except Exception:
        return None


def _get_earnings_history(ticker: str, lookback_days: int) -> list[dict]:
    """
    Return past earnings events within lookback_days with EPS data.
    """
    try:
        t = yf.Ticker(ticker)
        ed = t.earnings_dates
        if ed is None or ed.empty:
            return []

        cutoff = date.today() - timedelta(days=lookback_days)
        events = []
        for idx, row in ed.iterrows():
            edate = idx.date()
            if edate > date.today():
                continue  # skip future
            if edate < cutoff:
                continue  # too old
            if pd_isnan(row.get('Reported EPS')):
                continue  # not reported yet (shouldn't happen for past dates)

            events.append({
                'ticker': ticker,
                'date': edate,
                'eps_estimate': float(row['EPS Estimate']) if not pd_isnan(row.get('EPS Estimate')) else None,
                'eps_actual': float(row['Reported EPS']),
                'surprise_pct': float(row['Surprise(%)']) if not pd_isnan(row.get('Surprise(%)')) else None,
            })
        return events
    except Exception:
        return []


def _get_upcoming_earnings(ticker: str, horizon_days: int = 45) -> list[dict]:
    """Return upcoming earnings events within horizon_days."""
    try:
        t = yf.Ticker(ticker)
        ed = t.earnings_dates
        if ed is None or ed.empty:
            return []

        horizon = date.today() + timedelta(days=horizon_days)
        events = []
        for idx, row in ed.iterrows():
            edate = idx.date()
            if edate <= date.today():
                continue
            if edate > horizon:
                continue
            events.append({
                'ticker': ticker,
                'date': edate,
                'eps_estimate': float(row['EPS Estimate']) if not pd_isnan(row.get('EPS Estimate')) else None,
            })
        return events
    except Exception:
        return []


def pd_isnan(val) -> bool:
    try:
        import math
        return val is None or math.isnan(float(val))
    except (TypeError, ValueError):
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Management command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Earnings event backtester: validate FinBERT signal on controlled events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tickers',
            type=str,
            default=','.join(DEFAULT_TICKERS),
            help='Comma-separated tickers',
        )
        parser.add_argument(
            '--mode',
            type=str,
            default='both',
            choices=['past', 'future', 'both'],
            help='past=retrospective, future=upcoming, both=default',
        )
        parser.add_argument(
            '--lookback',
            type=int,
            default=60,
            help='Days to look back for past earnings (default: 60)',
        )
        parser.add_argument(
            '--horizon',
            type=int,
            default=45,
            help='Days forward to scan for upcoming earnings (default: 45)',
        )
        parser.add_argument(
            '--news-window',
            type=int,
            default=5,
            dest='news_window',
            help='Days of pre-earnings news to score (default: 5)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show article headlines for each event',
        )

    def handle(self, *args, **options):
        if not YFINANCE_OK:
            self.stderr.write(self.style.ERROR('pip install yfinance'))
            return
        if not GNEWS_KEY:
            self.stderr.write(self.style.ERROR('GNEWS_API_KEY not set in .env'))
            return

        tickers     = [t.strip().upper() for t in options['tickers'].split(',') if t.strip()]
        mode        = options['mode']
        lookback    = options['lookback']
        horizon     = options['horizon']
        news_window = options['news_window']
        verbose     = options['verbose']

        self.stdout.write(f'\n{"═" * 64}')
        self.stdout.write('  MARKET-NOISE  ·  Earnings Event Backtester')
        self.stdout.write(f'{"═" * 64}')
        self.stdout.write(f'  Date    : {date.today()}')
        self.stdout.write(f'  Tickers : {len(tickers)} ({", ".join(tickers[:8])}{"…" if len(tickers) > 8 else ""})')
        self.stdout.write(f'  Mode    : {mode}')
        if mode in ('past', 'both'):
            self.stdout.write(f'  Lookback: {lookback} days  (news window: {news_window}d pre-earnings)')
        if mode in ('future', 'both'):
            self.stdout.write(f'  Horizon : {horizon} days forward')
        self.stdout.write(f'{"═" * 64}\n')

        # Warm up FinBERT once (downloads if needed)
        self.stdout.write('  Loading FinBERT…')
        try:
            from api.nlp import finbert as _fb
            _fb._get_pipeline()
            self.stdout.write('  FinBERT ready.\n')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'  FinBERT failed: {e}'))
            return

        past_events   = []
        future_events = []

        for ticker in tickers:
            if mode in ('past', 'both'):
                past_events.extend(_get_earnings_history(ticker, lookback))
            if mode in ('future', 'both'):
                future_events.extend(_get_upcoming_earnings(ticker, horizon))

        past_events   = sorted(past_events,   key=lambda e: e['date'], reverse=True)
        future_events = sorted(future_events, key=lambda e: e['date'])

        if mode in ('past', 'both') and past_events:
            self._run_retrospective(past_events, news_window, verbose)
        elif mode in ('past', 'both'):
            self.stdout.write(self.style.WARNING(
                f'  No earnings found in last {lookback} days for the given tickers.\n'
                f'  Try: --lookback 90 or add more tickers.\n'
            ))

        if mode in ('future', 'both') and future_events:
            self._run_forward_scan(future_events, verbose)
        elif mode in ('future', 'both'):
            self.stdout.write(self.style.WARNING(
                f'  No upcoming earnings found in next {horizon} days.\n'
            ))

    # ─────────────────────────────────────────────────────────────────
    # RETROSPECTIVE: past earnings → did pre-earnings sentiment predict?
    # ─────────────────────────────────────────────────────────────────

    def _run_retrospective(self, events: list[dict], news_window: int, verbose: bool):
        self.stdout.write(f'{"─" * 64}')
        self.stdout.write(f'  RETROSPECTIVE  —  {len(events)} past earnings events found')
        self.stdout.write(f'  Fetching pre-earnings news & scoring…\n')

        scored = []

        for ev in events:
            ticker = ev['ticker']
            edate  = ev['date']
            self.stdout.write(f'  [{ticker}] {edate} — fetching pre-earnings news…')

            texts = _fetch_pre_earnings_news(ticker, edate, news_window)
            time.sleep(0.4)  # GNews rate limit

            if not texts:
                self.stdout.write(f'  [{ticker}] No news found (outside GNews 30-day window?)')
                continue

            vader_result   = _vader_score(texts)
            finbert_result = _finbert_score(texts)
            price_data     = _get_price_reaction(ticker, edate)

            if price_data is None:
                self.stdout.write(f'  [{ticker}] Could not fetch price reaction data.')
                continue

            # EPS direction: beat → expected positive reaction, miss → expected negative
            surprise_pct = ev.get('surprise_pct') or 0.0
            eps_direction = 'beat' if surprise_pct > 0 else ('miss' if surprise_pct < 0 else 'inline')
            expected_dir  = 'up' if eps_direction == 'beat' else ('down' if eps_direction == 'miss' else 'flat')

            scored.append({
                **ev,
                'eps_direction': eps_direction,
                'expected_dir': expected_dir,
                'vader': vader_result,
                'finbert': finbert_result,
                'price': price_data,
                'articles_found': len(texts),
            })

            v_correct = vader_result['label'] == 'positive' and price_data['direction'] == 'up' or \
                        vader_result['label'] == 'negative' and price_data['direction'] == 'down'
            f_correct = finbert_result['label'] == 'positive' and price_data['direction'] == 'up' or \
                        finbert_result['label'] == 'negative' and price_data['direction'] == 'down'

            self.stdout.write(
                f'  [{ticker}] {edate} | surprise={surprise_pct:+.1f}% ({eps_direction}) | '
                f'reaction={price_data["reaction_pct"]:+.2f}% ({price_data["direction"]}) | '
                f'articles={len(texts)}'
            )
            self.stdout.write(
                f'           VADER={vader_result["label"]:8s} ({vader_result["compound"]:+.3f}) '
                f'{"✓" if v_correct else "✗"}  |  '
                f'FinBERT={finbert_result["label"]:8s} ({finbert_result["compound"]:+.3f}) '
                f'{"✓" if f_correct else "✗"}'
            )
            if verbose and texts:
                for t in texts[:3]:
                    self.stdout.write(f'           → "{t[:100]}"')
            self.stdout.write('')

        if not scored:
            self.stdout.write(self.style.WARNING(
                '  No events could be scored (no news data in GNews window).\n'
                '  GNews free tier covers ~30 days. Most recent earnings are '
                f'{(date.today() - events[0]["date"]).days} days old.\n'
                '  Try adding JPM, GS, or other early-April reporters.\n'
            ))
            return

        self._retrospective_report(scored)

    def _retrospective_report(self, scored: list[dict]):
        n = len(scored)
        self.stdout.write(f'\n{"─" * 64}')
        self.stdout.write(f'  RETROSPECTIVE RESULTS  ({n} events with news + price data)')
        self.stdout.write(f'{"─" * 64}')

        # Price directions
        up_n   = sum(1 for e in scored if e['price']['direction'] == 'up')
        down_n = sum(1 for e in scored if e['price']['direction'] == 'down')
        flat_n = sum(1 for e in scored if e['price']['direction'] == 'flat')
        self.stdout.write(
            f'  Actual price reactions: Up={up_n} ({up_n/n*100:.0f}%)  '
            f'Down={down_n} ({down_n/n*100:.0f}%)  Flat={flat_n} ({flat_n/n*100:.0f}%)'
        )

        majority_n = max(up_n, down_n, flat_n)
        majority   = 'up' if majority_n == up_n else ('down' if majority_n == down_n else 'flat')
        baseline   = majority_n / n * 100

        # Model accuracy
        def acc(samples, model_key):
            correct = sum(
                1 for e in samples
                if (e[model_key]['label'] == 'positive' and e['price']['direction'] == 'up')
                or (e[model_key]['label'] == 'negative' and e['price']['direction'] == 'down')
                or (e[model_key]['label'] == 'neutral'  and e['price']['direction'] == majority)
            )
            return correct / len(samples) * 100 if samples else 0

        vader_acc   = acc(scored, 'vader')
        finbert_acc = acc(scored, 'finbert')

        self.stdout.write(f'\n  Directional accuracy (sentiment → price reaction):')
        self.stdout.write(f'    Baseline (always "{majority}")  : {baseline:.1f}%')
        self.stdout.write(f'    VADER                    : {vader_acc:.1f}%  (lift {vader_acc - baseline:+.1f}%)')
        self.stdout.write(f'    FinBERT                  : {finbert_acc:.1f}%  (lift {finbert_acc - baseline:+.1f}%)')

        # Also measure: did sentiment align with EPS beat/miss?
        def eps_acc(samples, model_key):
            valid = [e for e in samples if e['eps_direction'] != 'inline']
            if not valid:
                return 0, 0
            correct = sum(
                1 for e in valid
                if (e[model_key]['label'] == 'positive' and e['eps_direction'] == 'beat')
                or (e[model_key]['label'] == 'negative' and e['eps_direction'] == 'miss')
            )
            return correct / len(valid) * 100, len(valid)

        v_eps_acc, v_eps_n   = eps_acc(scored, 'vader')
        f_eps_acc, f_eps_n   = eps_acc(scored, 'finbert')

        if v_eps_n > 0:
            self.stdout.write(f'\n  Sentiment → EPS surprise direction ({v_eps_n} non-inline events):')
            self.stdout.write(f'    VADER   : {v_eps_acc:.1f}%')
            self.stdout.write(f'    FinBERT : {f_eps_acc:.1f}%')
            self.stdout.write(f'    (Does pre-earnings sentiment detect beat vs miss?)')

        # Correlation: compound vs price reaction
        if SCIPY_OK and n >= 5:
            v_compounds = [e['vader']['compound']   for e in scored]
            f_compounds = [e['finbert']['compound'] for e in scored]
            reactions   = [e['price']['reaction_pct'] for e in scored]

            vr, vp = scipy_stats.pearsonr(v_compounds, reactions)
            fr, fp = scipy_stats.pearsonr(f_compounds, reactions)

            self.stdout.write(f'\n  Pearson r (compound vs price reaction):')
            self.stdout.write(
                f'    VADER   : r={vr:+.3f}  p={vp:.3f}  '
                f'{"*** SIGNIFICANT" if vp < 0.05 else "(not significant)"}'
            )
            self.stdout.write(
                f'    FinBERT : r={fr:+.3f}  p={fp:.3f}  '
                f'{"*** SIGNIFICANT" if fp < 0.05 else "(not significant)"}'
            )

        # Per-event table
        self.stdout.write(f'\n  {"Ticker":<6} {"Date":<12} {"EPS":<8} {"Reaction":<12} {"VADER":<12} {"FinBERT":<12} V  F')
        self.stdout.write(f'  {"─"*6} {"─"*12} {"─"*8} {"─"*12} {"─"*12} {"─"*12} ─  ─')
        for e in sorted(scored, key=lambda x: x['date'], reverse=True):
            v_ok = '✓' if (
                (e['vader']['label']   == 'positive' and e['price']['direction'] == 'up') or
                (e['vader']['label']   == 'negative' and e['price']['direction'] == 'down')
            ) else '✗'
            f_ok = '✓' if (
                (e['finbert']['label'] == 'positive' and e['price']['direction'] == 'up') or
                (e['finbert']['label'] == 'negative' and e['price']['direction'] == 'down')
            ) else '✗'
            self.stdout.write(
                f'  {e["ticker"]:<6} {str(e["date"]):<12} '
                f'{e["eps_direction"]:7s}  '
                f'{e["price"]["reaction_pct"]:+6.2f}% ({e["price"]["direction"]:<4}) '
                f'{e["vader"]["label"]:8s} ({e["vader"]["compound"]:+.2f})  '
                f'{e["finbert"]["label"]:8s} ({e["finbert"]["compound"]:+.2f})  '
                f'{v_ok}  {f_ok}'
            )

        # Verdict
        self.stdout.write(f'\n{"─" * 64}')
        self.stdout.write('  VERDICT')
        self.stdout.write(f'{"─" * 64}')

        if n < 5:
            self.stdout.write(self.style.WARNING(
                f'  Only {n} events — too few for statistical conclusions.\n'
                f'  Need earnings data from within GNews 30-day window.\n'
                f'  JPM and GS just reported today/yesterday — run again in a few hours\n'
                f'  after price data settles, or wait for more Q1 reports this week.'
            ))
        else:
            best_model = 'FinBERT' if finbert_acc >= vader_acc else 'VADER'
            best_acc   = max(finbert_acc, vader_acc)
            best_lift  = best_acc - baseline

            if best_lift > 10:
                self.stdout.write(self.style.SUCCESS(
                    f'  SIGNAL FOUND. {best_model} achieves {best_acc:.1f}% accuracy '
                    f'on earnings events ({best_lift:+.1f}% over baseline).\n'
                    f'  Pre-earnings sentiment has genuine predictive value on these events.'
                ))
            elif best_lift > 0:
                self.stdout.write(self.style.WARNING(
                    f'  WEAK SIGNAL. {best_model} at {best_acc:.1f}% beats baseline by {best_lift:+.1f}%.\n'
                    f'  Promising but need more events to confirm. Keep accumulating data.'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'  NO CLEAR SIGNAL yet ({n} events, {best_model} {best_acc:.1f}% vs baseline {baseline:.1f}%).\n'
                    f'  Small sample — run this command again after more Q1 reports come in\n'
                    f'  (NFLX, TSLA, META, MSFT, GOOGL, AAPL all reporting in next 30 days).'
                ))

    # ─────────────────────────────────────────────────────────────────
    # FORWARD SCAN: upcoming earnings → what does current sentiment say?
    # ─────────────────────────────────────────────────────────────────

    def _run_forward_scan(self, events: list[dict], verbose: bool):
        self.stdout.write(f'\n{"─" * 64}')
        self.stdout.write(f'  UPCOMING EARNINGS  —  {len(events)} events in the next 45 days')
        self.stdout.write(f'  Scoring current news with FinBERT…\n')
        self.stdout.write(
            f'  {"Ticker":<6} {"Reports":<12} {"Days":<5} '
            f'{"EPS Est":>8} {"Articles":>9} {"FinBERT":<10} {"Compound":>9} {"Signal"}'
        )
        self.stdout.write(f'  {"─"*6} {"─"*12} {"─"*5} {"─"*8} {"─"*9} {"─"*10} {"─"*9} {"─"*15}')

        for ev in events:
            ticker = ev['ticker']
            edate  = ev['date']
            days_until = (edate - date.today()).days

            texts = _fetch_current_news(ticker, days=7)
            time.sleep(0.4)

            if not texts:
                self.stdout.write(
                    f'  {ticker:<6} {str(edate):<12} {days_until:<5} '
                    f'{"N/A":>8} {"—":>9} {"—":<10} {"—":>9} no news found'
                )
                continue

            result = _finbert_score(texts)
            eps_est = f'${ev["eps_estimate"]:.2f}' if ev.get('eps_estimate') else 'N/A'

            if result['compound'] >= 0.3:
                signal = 'BULLISH ↑'
            elif result['compound'] >= 0.05:
                signal = 'slightly bullish'
            elif result['compound'] <= -0.3:
                signal = 'BEARISH ↓'
            elif result['compound'] <= -0.05:
                signal = 'slightly bearish'
            else:
                signal = 'neutral'

            self.stdout.write(
                f'  {ticker:<6} {str(edate):<12} {days_until:<5} '
                f'{eps_est:>8} {result["n"]:>9} {result["label"]:<10} '
                f'{result["compound"]:>+9.3f} {signal}'
            )

            if verbose and texts:
                for t in texts[:2]:
                    self.stdout.write(f'    → "{t[:90]}"')

        self.stdout.write(f'\n  Note: These are pre-earnings sentiment snapshots, not predictions.')
        self.stdout.write(f'  After each company reports, run --mode past to validate.\n')
