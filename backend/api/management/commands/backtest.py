"""
Backtest: Does sentiment analysis actually predict next-day stock returns?

Fetches historical news via GNews, historical prices via yfinance,
scores each article with VADER and/or FinBERT, then measures correlation
and directional accuracy against actual next-day returns.

Usage:
    python manage.py backtest                        # VADER + FinBERT comparison
    python manage.py backtest --model vader          # VADER only
    python manage.py backtest --model finbert        # FinBERT only
    python manage.py backtest --tickers AAPL,TSLA --days 30
    python manage.py backtest --verbose              # show each article-return pair
"""

import os
import time
import requests
from datetime import datetime, timedelta, date

from django.core.management.base import BaseCommand

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

DEFAULT_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'META', 'MSFT', 'AMZN', 'GOOGL', 'GME']

_vader_analyzer = SentimentIntensityAnalyzer()


def _vader_score(text: str) -> dict:
    s = _vader_analyzer.polarity_scores(text)
    return {'compound': s['compound'], 'pos': s['pos'], 'neg': s['neg'], 'neu': s['neu']}


def _finbert_score_batch(texts: list[str]) -> list[dict]:
    from api.nlp import finbert
    results = finbert.analyze_batch(texts)
    return [{'compound': r['compound'], 'pos': r['pos'], 'neg': r['neg'], 'neu': r['neu']}
            for r in results]


class Command(BaseCommand):
    help = 'Backtest whether sentiment analysis predicts next-day stock returns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tickers',
            type=str,
            default=','.join(DEFAULT_TICKERS),
            help='Comma-separated tickers (default: AAPL,TSLA,NVDA,META,MSFT,AMZN,GOOGL,GME)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Days of history (default: 30)',
        )
        parser.add_argument(
            '--model',
            type=str,
            default='both',
            choices=['vader', 'finbert', 'both'],
            help='Sentiment model to test (default: both)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print each article-return pair',
        )

    def handle(self, *args, **options):
        if not YFINANCE_OK:
            self.stderr.write(self.style.ERROR('yfinance not installed. Run: pip install yfinance'))
            return
        if not GNEWS_KEY:
            self.stderr.write(self.style.ERROR('GNEWS_API_KEY not set in .env'))
            return

        tickers = [t.strip().upper() for t in options['tickers'].split(',') if t.strip()]
        days = options['days']
        model_mode = options['model']
        verbose = options['verbose']

        use_finbert = model_mode in ('finbert', 'both')
        use_vader   = model_mode in ('vader',   'both')

        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  MARKET-NOISE BACKTEST')
        self.stdout.write(f'{"=" * 62}')
        self.stdout.write(f'  Tickers : {", ".join(tickers)}')
        self.stdout.write(f'  Period  : last {days} days')
        self.stdout.write(f'  Models  : {model_mode.upper()}')
        self.stdout.write(f'  Source  : GNews API + yfinance')
        self.stdout.write(f'{"=" * 62}\n')

        if use_finbert:
            self.stdout.write('  Loading FinBERT (ProsusAI/finbert)...')
            self.stdout.write('  First run downloads ~440MB to ~/.cache/huggingface\n')
            try:
                from api.nlp import finbert as _fb
                _fb._get_pipeline()  # warm up — triggers download on first run
                self.stdout.write('  FinBERT ready.\n')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  FinBERT failed to load: {e}'))
                return

        end_date = date.today()
        start_date = end_date - timedelta(days=days + 7)

        # raw_samples: list of dicts with article text + price data (no scores yet)
        raw_samples = []

        for ticker in tickers:
            self.stdout.write(f'  [{ticker}] Fetching data...')
            prices = self._fetch_prices(ticker, start_date, end_date)
            if len(prices) < 3:
                self.stdout.write(f'  [{ticker}] Skipping — not enough price data.')
                continue

            articles = self._fetch_news(ticker, days)
            if not articles:
                self.stdout.write(f'  [{ticker}] Skipping — no news returned.')
                continue

            self.stdout.write(f'  [{ticker}] {len(articles)} articles, {len(prices)} price days')
            matched = self._extract_raw(ticker, articles, prices)
            self.stdout.write(f'  [{ticker}] {len(matched)} article-return pairs\n')
            raw_samples.extend(matched)
            time.sleep(0.5)  # GNews rate limit courtesy delay

        if not raw_samples:
            self.stdout.write(self.style.ERROR('\nNo samples collected. Check GNEWS_API_KEY.'))
            return

        self.stdout.write(f'  Total samples: {len(raw_samples)}\n')

        # --- Score with selected model(s) ---
        texts = [s['text'] for s in raw_samples]

        vader_samples   = None
        finbert_samples = None

        if use_vader:
            self.stdout.write('  Scoring with VADER...')
            vader_scores = [_vader_score(t) for t in texts]
            vader_samples = self._attach_labels(raw_samples, vader_scores)
            self.stdout.write('  Done.\n')

        if use_finbert:
            self.stdout.write('  Scoring with FinBERT (batched, MPS)...')
            finbert_scores = _finbert_score_batch(texts)
            finbert_samples = self._attach_labels(raw_samples, finbert_scores)
            self.stdout.write('  Done.\n')

        if verbose:
            self._print_pairs(raw_samples, vader_samples, finbert_samples)

        # --- Report ---
        if model_mode == 'both' and vader_samples and finbert_samples:
            self._report_comparison(vader_samples, finbert_samples)
        elif vader_samples:
            self._report_single('VADER', vader_samples)
        elif finbert_samples:
            self._report_single('FinBERT', finbert_samples)

    # ------------------------------------------------------------------ #
    # Data helpers                                                         #
    # ------------------------------------------------------------------ #

    def _fetch_prices(self, ticker: str, start: date, end: date) -> dict:
        try:
            df = yf.Ticker(ticker).history(
                start=start.isoformat(),
                end=(end + timedelta(days=2)).isoformat(),
            )
            if df.empty:
                return {}
            return {
                idx.date(): {'open': float(row['Open']), 'close': float(row['Close'])}
                for idx, row in df.iterrows()
            }
        except Exception as e:
            self.stderr.write(f'  yfinance error for {ticker}: {e}')
            return {}

    def _fetch_news(self, ticker: str, days: int) -> list:
        from_ts = (date.today() - timedelta(days=days)).isoformat() + 'T00:00:00Z'
        try:
            resp = requests.get(
                f'{GNEWS_BASE}/search',
                params={
                    'q': f'"{ticker}" stock',
                    'lang': 'en',
                    'max': 10,
                    'from': from_ts,
                    'sortby': 'publishedAt',
                    'token': GNEWS_KEY,
                },
                timeout=15,
            )
            if not resp.ok:
                self.stderr.write(f'  GNews {resp.status_code}: {resp.text[:120]}')
                return []
            return resp.json().get('articles', [])
        except Exception as e:
            self.stderr.write(f'  GNews error: {e}')
            return []

    def _extract_raw(self, ticker: str, articles: list, prices: dict) -> list:
        """Match articles to next-day returns. Returns list without model scores."""
        sorted_dates = sorted(prices.keys())
        samples = []

        for article in articles:
            pub_str = article.get('publishedAt', '')
            if not pub_str:
                continue
            try:
                pub_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                continue

            current_date = next((d for d in reversed(sorted_dates) if d <= pub_date), None)
            next_date    = next((d for d in sorted_dates if d > pub_date), None)
            if current_date is None or next_date is None:
                continue

            current_close = prices[current_date]['close']
            next_close    = prices[next_date]['close']
            if current_close <= 0:
                continue

            ndr = (next_close - current_close) / current_close * 100
            actual_dir = 'up' if ndr > 0.15 else ('down' if ndr < -0.15 else 'flat')

            title = article.get('title', '') or ''
            desc  = article.get('description', '') or ''
            text  = f"{title}. {desc}" if desc else title

            samples.append({
                'ticker': ticker,
                'pub_date': pub_date.isoformat(),
                'title': title[:80],
                'text': text,
                'next_day_return': ndr,
                'actual_dir': actual_dir,
            })

        return samples

    @staticmethod
    def _attach_labels(raw_samples: list, scores: list[dict]) -> list:
        """Combine raw samples with model scores into final sample dicts."""
        result = []
        for raw, score in zip(raw_samples, scores):
            compound = score['compound']
            label = 'positive' if compound >= 0.05 else ('negative' if compound <= -0.05 else 'neutral')
            result.append({**raw, 'compound': compound, 'label': label,
                           'pos': score['pos'], 'neg': score['neg'], 'neu': score['neu']})
        return result

    # ------------------------------------------------------------------ #
    # Verbose output                                                       #
    # ------------------------------------------------------------------ #

    def _print_pairs(self, raw, vader_s, finbert_s):
        self.stdout.write(f'\n  {"─" * 58}')
        self.stdout.write(f'  Article detail (VADER vs FinBERT)')
        self.stdout.write(f'  {"─" * 58}')
        for i, raw_s in enumerate(raw):
            v_label = vader_s[i]['label']   if vader_s   else '—'
            v_comp  = vader_s[i]['compound'] if vader_s   else 0
            f_label = finbert_s[i]['label'] if finbert_s else '—'
            f_comp  = finbert_s[i]['compound'] if finbert_s else 0
            agree   = '✓' if v_label == f_label else '✗'
            self.stdout.write(
                f'  [{raw_s["ticker"]}][{raw_s["pub_date"]}]'
                f' return={raw_s["next_day_return"]:+.2f}% actual={raw_s["actual_dir"]}'
            )
            self.stdout.write(
                f'    VADER   : {v_label:8s} ({v_comp:+.3f})'
                f'  FinBERT : {f_label:8s} ({f_comp:+.3f})  agree={agree}'
            )
            self.stdout.write(f'    "{raw_s["title"][:70]}"')
        self.stdout.write('')

    # ------------------------------------------------------------------ #
    # Stats helpers                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_stats(samples: list) -> dict:
        n = len(samples)
        compounds = [s['compound'] for s in samples]
        returns   = [s['next_day_return'] for s in samples]

        up_n   = sum(1 for s in samples if s['actual_dir'] == 'up')
        down_n = sum(1 for s in samples if s['actual_dir'] == 'down')
        flat_n = sum(1 for s in samples if s['actual_dir'] == 'flat')

        majority_n     = max(up_n, down_n, flat_n)
        majority_class = 'up' if majority_n == up_n else ('down' if majority_n == down_n else 'flat')
        baseline_acc   = majority_n / n * 100

        correct = sum(
            1 for s in samples
            if (s['label'] == 'positive' and s['actual_dir'] == 'up')
            or (s['label'] == 'negative' and s['actual_dir'] == 'down')
            or (s['label'] == 'neutral'  and s['actual_dir'] == majority_class)
        )
        model_acc = correct / n * 100
        lift      = model_acc - baseline_acc

        pos_s = [s for s in samples if s['label'] == 'positive']
        neg_s = [s for s in samples if s['label'] == 'negative']
        neu_s = [s for s in samples if s['label'] == 'neutral']

        r, p = (None, None)
        r2, p2 = (None, None)
        if SCIPY_OK and n >= 5:
            r, p   = scipy_stats.pearsonr(compounds, returns)
            abs_c  = [abs(c) for c in compounds]
            abs_r  = [abs(rv) for rv in returns]
            r2, p2 = scipy_stats.pearsonr(abs_c, abs_r)

        return {
            'n': n,
            'up_n': up_n, 'down_n': down_n, 'flat_n': flat_n,
            'majority_class': majority_class,
            'baseline_acc': baseline_acc,
            'model_acc': model_acc,
            'lift': lift,
            'pos_n': len(pos_s), 'neg_n': len(neg_s), 'neu_n': len(neu_s),
            'pos_hit': sum(1 for s in pos_s if s['actual_dir'] == 'up'),
            'neg_hit': sum(1 for s in neg_s if s['actual_dir'] == 'down'),
            'neu_hit': sum(1 for s in neu_s if s['actual_dir'] == majority_class),
            'avg_pos_ret': sum(s['next_day_return'] for s in pos_s) / len(pos_s) if pos_s else 0,
            'avg_neg_ret': sum(s['next_day_return'] for s in neg_s) / len(neg_s) if neg_s else 0,
            'avg_neu_ret': sum(s['next_day_return'] for s in neu_s) / len(neu_s) if neu_s else 0,
            'avg_ret': sum(s['next_day_return'] for s in samples) / n,
            'pearson_r': r, 'pearson_p': p,
            'abs_r': r2, 'abs_p': p2,
        }

    # ------------------------------------------------------------------ #
    # Reporting                                                            #
    # ------------------------------------------------------------------ #

    def _print_stats_block(self, name: str, st: dict):
        n = st['n']
        self.stdout.write(f'  Model  : {name}')
        self.stdout.write(f'  Samples: {n}')
        self.stdout.write(
            f'\n  Actual distribution — '
            f'Up: {st["up_n"]} ({st["up_n"]/n*100:.1f}%)  '
            f'Flat: {st["flat_n"]} ({st["flat_n"]/n*100:.1f}%)  '
            f'Down: {st["down_n"]} ({st["down_n"]/n*100:.1f}%)'
        )
        self.stdout.write(
            f'\n  Accuracy:'
            f'\n    Baseline (always "{st["majority_class"]}"): {st["baseline_acc"]:.1f}%'
            f'\n    {name} directional accuracy: {st["model_acc"]:.1f}%'
            f'\n    Lift over baseline         : {st["lift"]:+.1f}%'
        )
        self.stdout.write(
            f'\n  Per-label accuracy:'
        )
        if st['pos_n']:
            self.stdout.write(
                f'    Positive (n={st["pos_n"]:3d}): '
                f'predicted "up"  , hit {st["pos_hit"]}/{st["pos_n"]} '
                f'({st["pos_hit"]/st["pos_n"]*100:.0f}%),  avg return = {st["avg_pos_ret"]:+.2f}%'
            )
        if st['neg_n']:
            self.stdout.write(
                f'    Negative (n={st["neg_n"]:3d}): '
                f'predicted "down", hit {st["neg_hit"]}/{st["neg_n"]} '
                f'({st["neg_hit"]/st["neg_n"]*100:.0f}%),  avg return = {st["avg_neg_ret"]:+.2f}%'
            )
        if st['neu_n']:
            self.stdout.write(
                f'    Neutral  (n={st["neu_n"]:3d}): '
                f'predicted "{st["majority_class"]:4s}", hit {st["neu_hit"]}/{st["neu_n"]} '
                f'({st["neu_hit"]/st["neu_n"]*100:.0f}%),  avg return = {st["avg_neu_ret"]:+.2f}%'
            )

        if st['pearson_r'] is not None:
            sig  = '*** SIGNIFICANT' if st['pearson_p'] < 0.05 else '(not significant)'
            sig2 = '*** SIGNIFICANT' if st['abs_p']     < 0.05 else '(not significant)'
            self.stdout.write(
                f'\n  Correlation:'
                f'\n    compound vs next-day return:  r={st["pearson_r"]:+.3f},  p={st["pearson_p"]:.3f}  {sig}'
                f'\n    |compound| vs |return|:       r={st["abs_r"]:+.3f},  p={st["abs_p"]:.3f}  {sig2}'
            )

        self.stdout.write(
            f'\n  Avg next-day return by label:'
            f'\n    Positive: {st["avg_pos_ret"]:+.3f}%'
            f'\n    Neutral : {st["avg_neu_ret"]:+.3f}%'
            f'\n    Negative: {st["avg_neg_ret"]:+.3f}%'
            f'\n    Overall : {st["avg_ret"]:+.3f}%'
        )

    def _verdict(self, name: str, st: dict) -> tuple[str, str]:
        """Return (style, message)."""
        n, lift = st['n'], st['lift']
        r, p = st['pearson_r'], st['pearson_p']

        if n < 20:
            return ('warning',
                    f'INCONCLUSIVE — only {n} samples. Need 50+ for meaningful stats.')

        if SCIPY_OK and r is not None:
            if p < 0.05 and abs(r) > 0.25 and lift > 3:
                return ('success',
                        f'SIGNAL FOUND ({name}). r={r:+.3f} significant (p={p:.3f}), '
                        f'lift={lift:+.1f}%. This model has predictive value.')
            if p < 0.05 and abs(r) > 0.15:
                return ('warning',
                        f'WEAK SIGNAL ({name}). Correlation significant (r={r:+.3f}, p={p:.3f}) '
                        f'but directional lift only {lift:+.1f}%.')
            if lift > 5:
                return ('warning',
                        f'MARGINAL ({name}). Lift={lift:+.1f}% but r={r:+.3f} not significant '
                        f'(p={p:.3f}). Likely noise — need more samples.')
            return ('error',
                    f'NO SIGNAL ({name}). r={r:+.3f} (p={p:.3f}), lift={lift:+.1f}%.\n'
                    f'  {name} does not predict next-day returns on these tickers / period.')
        else:
            if lift > 5:
                return ('warning', f'MARGINAL ({name}). Lift={lift:+.1f}%.')
            return ('error', f'NO CLEAR SIGNAL ({name}). Lift={lift:+.1f}%.')

    def _report_single(self, name: str, samples: list):
        st = self._compute_stats(samples)
        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  RESULTS')
        self.stdout.write(f'{"=" * 62}\n')
        self._print_stats_block(name, st)
        self._emit_verdict(name, st)

    def _report_comparison(self, vader_s: list, finbert_s: list):
        vst = self._compute_stats(vader_s)
        fst = self._compute_stats(finbert_s)

        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  RESULTS — VADER')
        self.stdout.write(f'{"=" * 62}\n')
        self._print_stats_block('VADER', vst)

        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  RESULTS — FinBERT')
        self.stdout.write(f'{"=" * 62}\n')
        self._print_stats_block('FinBERT', fst)

        # Head-to-head
        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  HEAD-TO-HEAD')
        self.stdout.write(f'{"=" * 62}')
        self.stdout.write(
            f'  Directional accuracy:  '
            f'VADER {vst["model_acc"]:.1f}%  vs  FinBERT {fst["model_acc"]:.1f}%'
        )
        self.stdout.write(
            f'  Lift over baseline:    '
            f'VADER {vst["lift"]:+.1f}%  vs  FinBERT {fst["lift"]:+.1f}%'
        )
        if vst['pearson_r'] is not None and fst['pearson_r'] is not None:
            self.stdout.write(
                f'  Pearson r:             '
                f'VADER {vst["pearson_r"]:+.3f} (p={vst["pearson_p"]:.3f})  '
                f'vs  FinBERT {fst["pearson_r"]:+.3f} (p={fst["pearson_p"]:.3f})'
            )
        diff = fst['model_acc'] - vst['model_acc']
        winner = 'FinBERT' if diff > 0 else ('VADER' if diff < 0 else 'Tie')
        self.stdout.write(f'  Winner: {winner} (FinBERT - VADER = {diff:+.1f}%)')

        # Label disagreements between models
        agree   = sum(1 for v, f in zip(vader_s, finbert_s) if v['label'] == f['label'])
        disagree = len(vader_s) - agree
        self.stdout.write(
            f'\n  Model agreement: {agree}/{len(vader_s)} articles '
            f'({agree/len(vader_s)*100:.0f}%),  disagreed on {disagree}'
        )
        if disagree:
            self.stdout.write('  When they disagreed, who was right?')
            v_right = f_right = both_wrong = 0
            for v, f in zip(vader_s, finbert_s):
                if v['label'] == f['label']:
                    continue
                v_correct = (v['label'] == 'positive' and v['actual_dir'] == 'up') or \
                            (v['label'] == 'negative' and v['actual_dir'] == 'down')
                f_correct = (f['label'] == 'positive' and f['actual_dir'] == 'up') or \
                            (f['label'] == 'negative' and f['actual_dir'] == 'down')
                if v_correct and not f_correct:
                    v_right += 1
                elif f_correct and not v_correct:
                    f_right += 1
                else:
                    both_wrong += 1
            self.stdout.write(
                f'    VADER right: {v_right}  |  FinBERT right: {f_right}  '
                f'|  Both wrong: {both_wrong}'
            )

        # Verdicts
        self.stdout.write(f'\n{"=" * 62}')
        self.stdout.write('  VERDICT')
        self.stdout.write(f'{"=" * 62}')
        self._emit_verdict('VADER',   vst)
        self.stdout.write('')
        self._emit_verdict('FinBERT', fst)
        self.stdout.write('')

        # What to do next
        if fst['lift'] > vst['lift'] + 3:
            self.stdout.write(self.style.SUCCESS(
                '  FinBERT shows meaningful improvement over VADER.\n'
                '  Recommendation: replace VADER with FinBERT as the primary scorer.\n'
                '  analysis.py already routes through FinBERT when available.'
            ))
        elif fst['lift'] <= vst['lift']:
            self.stdout.write(self.style.WARNING(
                '  FinBERT did not outperform VADER on this dataset.\n'
                '  Possible reasons: small sample, bull-market period (everything went up),\n'
                '  daily granularity too coarse. Try longer window or intraday data.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '  FinBERT slightly outperforms VADER but neither shows strong signal.\n'
                '  The domain understanding is better but the return signal itself is weak.'
            ))

        self.stdout.write(f'\n  (Run with --verbose to see each article pair)\n')

    def _emit_verdict(self, name: str, st: dict):
        style, msg = self._verdict(name, st)
        if style == 'success':
            self.stdout.write(self.style.SUCCESS(f'  {msg}'))
        elif style == 'warning':
            self.stdout.write(self.style.WARNING(f'  {msg}'))
        else:
            self.stdout.write(self.style.ERROR(f'  {msg}'))
