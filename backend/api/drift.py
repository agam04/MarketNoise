"""
Narrative Drift — how the story around a stock has changed over time.

This is the core of the product's value proposition: not just "what is the
sentiment today" but "how has the narrative evolved and when did it shift?"

The drift analysis gives us:
  - A daily timeline of FinBERT compound scores (for the chart)
  - Window statistics (7d / 30d / 90d): average compound, trend direction
  - Shift detection: the most recent point where the narrative meaningfully changed

All computation is derived from existing SentimentScore records — no new data
sources required.
"""

from datetime import date, timedelta
from collections import defaultdict

from django.utils import timezone

from .models import Stock, SentimentScore, Narrative


def compute_narrative_drift(ticker: str) -> dict:
    """
    Analyse how the narrative around `ticker` has evolved over the last 90 days.

    Returns:
        {
            'ticker':    str,
            'timeline':  [{ 'date': str, 'compound': float, 'count': int,
                            'label': str }],   # daily aggregates
            'windows':   {
                '7d':  { 'avg_compound', 'article_count', 'direction',
                          'drift_direction', 'drift_magnitude' } | None,
                '30d': ...,
                '90d': ...,
            },
            'shift': {
                'detected':    bool,
                'date':        str | None,    # ISO date of shift
                'from_label':  str | None,    # 'positive' | 'negative' | 'neutral'
                'to_label':    str | None,
                'description': str,
            },
            'data_available': bool,   # False when no history has accumulated yet
        }
    """
    ticker = ticker.upper()
    try:
        stock = Stock.objects.get(ticker=ticker)
    except Stock.DoesNotExist:
        return _empty_drift(ticker)

    cutoff = timezone.now() - timedelta(days=91)
    scores = (
        SentimentScore.objects
        .filter(stock=stock, narrative__published_at__gte=cutoff)
        .select_related('narrative')
        .order_by('narrative__published_at')
    )

    if not scores.exists():
        return _empty_drift(ticker)

    # ── 1. Aggregate by day ──────────────────────────────────────────────────
    daily: dict[date, dict] = defaultdict(lambda: {'compounds': [], 'labels': [], 'sources': []})

    for score in scores:
        pub_day = score.narrative.published_at.date()
        daily[pub_day]['compounds'].append(score.compound_score)
        daily[pub_day]['labels'].append(score.label)
        daily[pub_day]['sources'].append(score.narrative.source)

    timeline = []
    for day in sorted(daily.keys()):
        d = daily[day]
        n = len(d['compounds'])
        avg_c = sum(d['compounds']) / n
        dominant_label = max(
            ('positive', 'negative', 'neutral'),
            key=lambda lbl: d['labels'].count(lbl),
        )
        timeline.append({
            'date':     day.isoformat(),
            'compound': round(avg_c, 3),
            'count':    n,
            'label':    dominant_label,
        })

    # ── 2. Window statistics ─────────────────────────────────────────────────
    today = date.today()

    def _window(days_back: int) -> dict | None:
        cutoff_date = today - timedelta(days=days_back)
        pts = [t for t in timeline if t['date'] >= cutoff_date.isoformat()]
        if not pts:
            return None
        n_total = sum(p['count'] for p in pts)
        avg = sum(p['compound'] * p['count'] for p in pts) / n_total
        direction = (
            'positive' if avg >= 0.05 else
            'negative' if avg <= -0.05 else
            'neutral'
        )
        # Compare first half vs second half to detect drift within the window
        mid = len(pts) // 2
        if mid >= 1:
            fh_pts = pts[:mid]
            sh_pts = pts[mid:]
            fh_n = sum(p['count'] for p in fh_pts) or 1
            sh_n = sum(p['count'] for p in sh_pts) or 1
            fh_avg = sum(p['compound'] * p['count'] for p in fh_pts) / fh_n
            sh_avg = sum(p['compound'] * p['count'] for p in sh_pts) / sh_n
            delta = sh_avg - fh_avg
            drift_direction = (
                'improving' if delta >  0.05 else
                'worsening' if delta < -0.05 else
                'stable'
            )
            drift_magnitude = round(abs(delta), 3)
        else:
            drift_direction = 'stable'
            drift_magnitude = 0.0

        return {
            'avg_compound':     round(avg, 3),
            'article_count':    n_total,
            'direction':        direction,
            'drift_direction':  drift_direction,
            'drift_magnitude':  drift_magnitude,
        }

    windows = {
        '7d':  _window(7),
        '30d': _window(30),
        '90d': _window(90),
    }

    # ── 3. Shift detection ───────────────────────────────────────────────────
    shift = _detect_shift(timeline)

    return {
        'ticker':         ticker,
        'timeline':       timeline,
        'windows':        windows,
        'shift':          shift,
        'data_available': True,
    }


def _detect_shift(timeline: list[dict]) -> dict:
    """
    Find the most recent point where the narrative meaningfully changed label.

    Strategy: walk backward through the timeline looking for the last day where
    a 3-day rolling average crossed the neutral band (±0.05) or reversed sign.
    """
    no_shift = {
        'detected':    False,
        'date':        None,
        'from_label':  None,
        'to_label':    None,
        'description': 'No significant narrative shift detected in the available data.',
    }

    if len(timeline) < 4:
        return no_shift

    # Build smoothed 3-day rolling average
    smoothed = []
    for i in range(len(timeline)):
        window = timeline[max(0, i - 2): i + 1]
        w_n = sum(p['count'] for p in window) or 1
        avg = sum(p['compound'] * p['count'] for p in window) / w_n
        smoothed.append(avg)

    def _label(v: float) -> str:
        return 'positive' if v >= 0.05 else ('negative' if v <= -0.05 else 'neutral')

    # Walk backward to find last crossing or reversal
    for i in range(len(smoothed) - 1, 0, -1):
        curr_lbl = _label(smoothed[i])
        prev_lbl = _label(smoothed[i - 1])
        if curr_lbl != prev_lbl:
            shift_date = timeline[i]['date']
            description = _shift_description(prev_lbl, curr_lbl, shift_date)
            return {
                'detected':    True,
                'date':        shift_date,
                'from_label':  prev_lbl,
                'to_label':    curr_lbl,
                'description': description,
            }

    return no_shift


def _shift_description(from_lbl: str, to_lbl: str, shift_date: str) -> str:
    label_words = {
        'positive': 'bullish',
        'negative': 'bearish',
        'neutral':  'neutral',
    }
    try:
        days_ago = (date.today() - date.fromisoformat(shift_date)).days
        when = f"{days_ago} day{'s' if days_ago != 1 else ''} ago"
    except ValueError:
        when = f"on {shift_date}"

    fr = label_words.get(from_lbl, from_lbl)
    to = label_words.get(to_lbl, to_lbl)
    return f"Narrative shifted from {fr} to {to} ~{when}."


def _empty_drift(ticker: str) -> dict:
    return {
        'ticker':    ticker,
        'timeline':  [],
        'windows':   {'7d': None, '30d': None, '90d': None},
        'shift': {
            'detected':    False,
            'date':        None,
            'from_label':  None,
            'to_label':    None,
            'description': 'No narrative history yet. Data accumulates as articles are scraped.',
        },
        'data_available': False,
    }
