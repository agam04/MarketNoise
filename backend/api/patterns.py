"""
Narrative Pattern Library.

Classifies the current narrative state of a stock into one of six archetypal
hype/risk patterns. These patterns give users a plain-language answer to:
"What kind of story is being told about this stock right now?"

Patterns are ordered by priority — the first one whose conditions are met wins.
The fallback is always 'balanced_coverage'.

Each pattern has:
  - id:          machine key
  - name:        human-readable label shown in the UI
  - description: explanation of what this pattern means and why it matters
  - risk:        'extreme' | 'high' | 'moderate' | 'low'
  - color:       hex accent colour for the UI
  - signals:     list of signal labels that contributed (shown as tags)
"""

from __future__ import annotations
from typing import TypedDict


class SentimentInput(TypedDict):
    compound: float
    positive: float
    negative: float
    neutral:  float
    label:    str


class VelocityInput(TypedDict):
    score:          float
    trend:          str   # 'accelerating' | 'decelerating' | 'stable'
    change_percent: float
    mention_count:  int


class HypeInput(TypedDict):
    score:                float
    level:                str   # 'low' | 'moderate' | 'high' | 'extreme'
    sentiment_imbalance:  float
    velocity_factor:      float
    source_concentration: float


# ── Pattern definitions ────────────────────────────────────────────────────

_PATTERNS = [
    {
        'id':    'short_squeeze',
        'name':  'Short Squeeze Dynamics',
        'description': (
            'Extreme one-sided bullish sentiment is accelerating rapidly, concentrated '
            'in retail-driven sources. This mirrors the early stages of meme-stock '
            'squeezes (GME, AMC). Narrative momentum is detached from fundamentals — '
            'price action is being driven by attention, not information. '
            'Sharp reversals are common once momentum stalls.'
        ),
        'risk':  'extreme',
        'color': '#ef4444',
    },
    {
        'id':    'macro_fear',
        'name':  'Macro Fear Pattern',
        'description': (
            'Negative sentiment is elevated and spreading rapidly. Coverage suggests '
            'broad market anxiety — macro events, regulatory concerns, or sector-wide '
            'pressure rather than company-specific news. The narrative is reactive '
            'and emotionally charged. Fear-driven narratives often overshoot '
            'fundamental reality in both directions.'
        ),
        'risk':  'high',
        'color': '#f87171',
    },
    {
        'id':    'theme_hype',
        'name':  'Theme / Sector Wave',
        'description': (
            'Positive narrative is broad and accelerating, driven by a macro theme '
            '(AI, crypto, clean energy) rather than company-specific catalysts. '
            'Coverage is wide across many sources. This pattern is common during '
            'sector rotations and thematic hype cycles — the stock rises with the '
            'tide, not necessarily because of its own fundamentals.'
        ),
        'risk':  'high',
        'color': '#f59e0b',
    },
    {
        'id':    'narrative_cooloff',
        'name':  'Narrative Cool-off',
        'description': (
            'Attention is decelerating after a period of elevated coverage. '
            'The narrative is losing momentum — volume is dropping, tone is '
            'normalising. This often follows a hype peak. The story may not be '
            'over, but the emotional intensity that drove attention is fading.'
        ),
        'risk':  'moderate',
        'color': '#60a5fa',
    },
    {
        'id':    'pre_catalyst',
        'name':  'Pre-Catalyst Build',
        'description': (
            'Coverage is accelerating with mixed or neutral sentiment — a pattern '
            'typical ahead of a known catalyst: earnings, product launch, regulatory '
            'decision, or analyst day. The market is forming an opinion. Sentiment '
            'will likely resolve strongly in one direction after the event.'
        ),
        'risk':  'moderate',
        'color': '#a78bfa',
    },
    {
        'id':    'balanced_coverage',
        'name':  'Balanced Coverage',
        'description': (
            'Coverage is steady, sentiment is mixed across sources, and no unusual '
            'hype signals are present. The narrative appears to reflect normal '
            'information flow rather than emotional amplification. '
            'This is the healthiest narrative state for a stock.'
        ),
        'risk':  'low',
        'color': '#22c55e',
    },
]


# ── Classifier ─────────────────────────────────────────────────────────────

def classify_pattern(
    sentiment: SentimentInput,
    velocity:  VelocityInput,
    hype:      HypeInput,
) -> dict:
    """
    Classify the current narrative into the best-matching pattern.

    Returns the full pattern dict plus a `signals_matched` list explaining
    which conditions triggered the classification.
    """
    compound    = sentiment.get('compound', 0.0)
    pos         = sentiment.get('positive', 0.0)
    neg         = sentiment.get('negative', 0.0)
    v_trend     = velocity.get('trend', 'stable')
    v_change    = velocity.get('change_percent', 0.0)
    v_score     = velocity.get('score', 0.0)
    h_score     = hype.get('score', 0.0)
    h_level     = hype.get('level', 'low')
    h_imbalance = hype.get('sentiment_imbalance', 0.0)
    h_src_conc  = hype.get('source_concentration', 0.0)

    # ── SHORT SQUEEZE ───────────────────────────────────────────────────────
    squeeze_signals = []
    if compound >= 0.3:
        squeeze_signals.append('extreme positive sentiment')
    if v_trend == 'accelerating' and v_change >= 40:
        squeeze_signals.append('rapid attention spike')
    if h_imbalance >= 10:   # sentiment_imbalance points (0-40)
        squeeze_signals.append('one-sided narrative')
    if h_score >= 60:
        squeeze_signals.append('extreme hype score')

    if len(squeeze_signals) >= 3:
        return _build('short_squeeze', squeeze_signals)

    # ── MACRO FEAR ──────────────────────────────────────────────────────────
    fear_signals = []
    if compound <= -0.15:
        fear_signals.append('elevated negative sentiment')
    if neg >= 0.35:
        fear_signals.append('high negative article ratio')
    if v_trend in ('accelerating', 'stable') and h_score >= 30:
        fear_signals.append('sustained fearful coverage')

    if len(fear_signals) >= 2:
        return _build('macro_fear', fear_signals)

    # ── THEME HYPE ──────────────────────────────────────────────────────────
    theme_signals = []
    if compound >= 0.15:
        theme_signals.append('broad positive sentiment')
    if v_trend == 'accelerating':
        theme_signals.append('accelerating coverage')
    if h_src_conc <= 10 and h_score >= 30:  # diverse sources = theme-wide, not company-specific
        theme_signals.append('wide source distribution')
    if h_score >= 40:
        theme_signals.append('elevated hype score')

    if len(theme_signals) >= 3:
        return _build('theme_hype', theme_signals)

    # ── NARRATIVE COOL-OFF ──────────────────────────────────────────────────
    cooloff_signals = []
    if v_trend == 'decelerating':
        cooloff_signals.append('declining attention')
    if h_score >= 25:
        cooloff_signals.append('previously elevated hype')
    if v_change <= -20:
        cooloff_signals.append('significant coverage drop')

    if len(cooloff_signals) >= 2:
        return _build('narrative_cooloff', cooloff_signals)

    # ── PRE-CATALYST ────────────────────────────────────────────────────────
    catalyst_signals = []
    if v_trend == 'accelerating' and abs(compound) < 0.2:
        catalyst_signals.append('rising volume with neutral tone')
    if 0.05 <= abs(compound) < 0.25 and v_score >= 20:
        catalyst_signals.append('building anticipation')

    if len(catalyst_signals) >= 1:
        return _build('pre_catalyst', catalyst_signals)

    # ── FALLBACK ─────────────────────────────────────────────────────────────
    return _build('balanced_coverage', ['no unusual signals detected'])


def _build(pattern_id: str, signals: list[str]) -> dict:
    pattern = next(p for p in _PATTERNS if p['id'] == pattern_id)
    return {
        **pattern,
        'signals_matched': signals,
    }


def risk_sort_key(risk: str) -> int:
    """Sortable integer for risk levels."""
    return {'extreme': 4, 'high': 3, 'moderate': 2, 'low': 1}.get(risk, 0)
