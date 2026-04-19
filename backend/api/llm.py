"""
LLM integration for MarketNoise AI Chat + Narrative Summaries.
Supports Google Gemini and Groq (Llama 3.3 70B).

Two modes:
  - Chat (market_chat view): uses the *user's own* Gemini/Groq key.
  - Narrative summary (market_narrative_summary view): uses a server-side key
    from env vars (GEMINI_API_KEY / GROQ_API_KEY) so all users see summaries,
    even unauthenticated ones.
"""

import logging
import os

from .analysis import analyze_stock_sentiment, compute_velocity, compute_hype_score
from .models import Narrative

logger = logging.getLogger(__name__)

# Server-side keys for public narrative summaries (optional — summaries are
# silently disabled if neither key is set)
_SERVER_GEMINI_KEY = os.getenv('GEMINI_API_KEY', '')
_SERVER_GROQ_KEY   = os.getenv('GROQ_API_KEY', '')


def _build_context(ticker: str, company_name: str) -> str:
    """Build a context string from our analysis data for the LLM."""
    parts = []

    # Sentiment
    try:
        sentiment = analyze_stock_sentiment(ticker, company_name)
        parts.append(
            f"Sentiment: {sentiment.get('label', 'unknown')} "
            f"(compound: {sentiment.get('compound', 0):.2f}, "
            f"{sentiment.get('article_count', 0)} articles analyzed)"
        )

        # Recent headlines with sentiment labels
        articles = sentiment.get('articles', [])[:8]
        if articles:
            headlines = []
            for a in articles:
                headlines.append(f"  - [{a.get('label', '?')}] {a.get('title', 'Untitled')}")
            parts.append("Recent headlines:\n" + "\n".join(headlines))
    except Exception as e:
        logger.warning(f"Failed to get sentiment for {ticker}: {e}")

    # Velocity
    try:
        velocity = compute_velocity(ticker)
        parts.append(
            f"Narrative velocity: {velocity.get('trend', 'unknown')} "
            f"({velocity.get('change_percent', 0):.0f}% change vs prior 24h, "
            f"{velocity.get('mention_count', 0)} mentions)"
        )
    except Exception as e:
        logger.warning(f"Failed to get velocity for {ticker}: {e}")

    # Hype
    try:
        hype = compute_hype_score(ticker)
        parts.append(
            f"Hype risk: {hype.get('score', 0):.0f}/100 ({hype.get('level', 'unknown')})"
        )
    except Exception as e:
        logger.warning(f"Failed to get hype for {ticker}: {e}")

    # ML prediction (if available)
    try:
        from .ml.predictor import predict_impact
        latest = Narrative.objects.filter(
            stock__ticker=ticker
        ).order_by('-published_at').first()
        if latest:
            prediction = predict_impact(latest)
            if prediction:
                parts.append(
                    f"ML prediction: {prediction['predicted_direction']} "
                    f"(confidence: {prediction['confidence']})"
                )
    except Exception:
        pass  # Model not trained yet, skip silently

    return "\n".join(parts) if parts else "No analysis data available yet."


SYSTEM_PROMPT = """You are MarketNoise AI, a stock narrative analyst. You help retail investors
understand WHY news and social media are moving a stock. You provide data-driven insights
grounded in sentiment analysis, narrative velocity, and hype risk scores.

RULES:
- Answer in 2-4 concise sentences. Be direct and insightful.
- Ground every answer in the data provided below. Cite specific numbers.
- Do NOT give trading advice, price predictions, or buy/sell recommendations.
- Do NOT make up information. If data is insufficient, say so honestly.
- If asked about something outside your data, explain what you can analyze instead.

Current analysis for {ticker} ({company_name}):
{context}
"""


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def ask_gemini(ticker: str, question: str, company_name: str, gemini_key: str) -> str:
    """Call Google Gemini with analysis context."""
    from google import genai

    context = _build_context(ticker, company_name)
    system = SYSTEM_PROMPT.format(ticker=ticker, company_name=company_name, context=context)

    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']
    client = genai.Client(api_key=gemini_key)

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=question,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system,
                ),
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            logger.warning(f"Gemini {model_name} failed: {e}")

            if 'quota' in error_str or 'resource_exhausted' in error_str or '429' in error_str:
                continue
            if 'api key' in error_str or 'invalid' in error_str or '403' in error_str:
                return "Invalid Gemini API key. Please check your key in Settings."
            continue

    return None  # Signal that Gemini failed so we can try Groq


# ---------------------------------------------------------------------------
# Groq provider (Llama 3.3 70B)
# ---------------------------------------------------------------------------

def ask_groq(ticker: str, question: str, company_name: str, groq_key: str) -> str:
    """Call Groq (Llama 3.3 70B) with analysis context."""
    from groq import Groq

    context = _build_context(ticker, company_name)
    system = SYSTEM_PROMPT.format(ticker=ticker, company_name=company_name, context=context)

    client = Groq(api_key=groq_key)

    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': question},
            ],
            temperature=0.4,
            max_tokens=512,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e).lower()
        logger.warning(f"Groq failed: {e}")

        if 'authentication' in error_str or 'invalid' in error_str or '401' in error_str:
            return "Invalid Groq API key. Please check your key in Settings."
        if 'rate' in error_str or '429' in error_str:
            return "Groq rate limit reached. Please wait a moment and try again."
        return f"AI chat error: {e}"


# ---------------------------------------------------------------------------
# Unified dispatcher — tries available providers
# ---------------------------------------------------------------------------

def ask_llm(ticker: str, question: str, company_name: str,
            gemini_key: str | None = None, groq_key: str | None = None) -> str:
    """
    Try available LLM providers in order:
      1. Gemini (if user has a key)
      2. Groq (if user has a key)
    Returns the first successful response.
    """
    # Try Gemini first
    if gemini_key:
        result = ask_gemini(ticker, question, company_name, gemini_key)
        if result is not None:
            return result
        logger.info(f"Gemini failed for {ticker}, falling back to Groq")

    # Try Groq
    if groq_key:
        return ask_groq(ticker, question, company_name, groq_key)

    # No keys at all
    return "No AI API key configured. Add a Gemini or Groq key in Settings to use AI Chat."


# ---------------------------------------------------------------------------
# Narrative summary — uses server-side keys, no user auth required
# ---------------------------------------------------------------------------

SUMMARY_SYSTEM_PROMPT = """You are a concise financial narrative analyst.
Given structured market data about a stock, write a single fluid paragraph
(3-4 sentences) summarising the current narrative state.

Rules:
- Write in plain English for a retail investor audience.
- Ground every sentence in the numbers provided. Be specific.
- Do NOT give buy/sell advice or price predictions.
- Do NOT invent information. Only use what is given.
- Output only the paragraph — no headers, no bullet points, no preamble.
"""


def _build_summary_context(
    ticker: str,
    company_name: str,
    analysis: dict,
    drift: dict | None,
) -> str:
    """Build a compact context block for the narrative summary prompt."""
    s = analysis.get('sentiment', {})
    v = analysis.get('velocity', {})
    h = analysis.get('hype', {})
    p = analysis.get('pattern', {})

    lines = [
        f"Stock: {ticker} ({company_name})",
        f"Sentiment: {s.get('label','unknown')} | compound {s.get('compound',0):+.3f} | {s.get('article_count',0)} articles",
        f"Velocity: {v.get('trend','stable')} | {v.get('change_percent',0):+.0f}% vs prior 24h",
        f"Hype score: {h.get('score',0):.0f}/100 ({h.get('level','low')})",
        f"Narrative pattern: {p.get('name','Balanced Coverage')} — signals: {', '.join(p.get('signals_matched', []))}",
    ]

    if drift and drift.get('data_available'):
        w30 = drift.get('windows', {}).get('30d')
        w7  = drift.get('windows', {}).get('7d')
        if w30:
            lines.append(
                f"30-day drift: avg compound {w30['avg_compound']:+.3f} | "
                f"trend {w30['drift_direction']} | {w30['article_count']} articles"
            )
        if w7:
            lines.append(
                f"7-day drift: avg compound {w7['avg_compound']:+.3f} | "
                f"trend {w7['drift_direction']}"
            )
        shift = drift.get('shift', {})
        if shift.get('detected'):
            lines.append(f"Narrative shift: {shift.get('description','')}")

    return "\n".join(lines)


def _call_gemini_summary(context: str, key: str) -> str | None:
    try:
        from google import genai
        client = genai.Client(api_key=key)
        for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=context,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=SUMMARY_SYSTEM_PROMPT,
                    ),
                )
                return resp.text.strip()
            except Exception as e:
                logger.warning(f"Gemini summary {model_name} failed: {e}")
                continue
    except Exception as e:
        logger.warning(f"Gemini summary import/init failed: {e}")
    return None


def _call_groq_summary(context: str, key: str) -> str | None:
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': SUMMARY_SYSTEM_PROMPT},
                {'role': 'user',   'content': context},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq summary failed: {e}")
    return None


def generate_narrative_summary(
    ticker: str,
    company_name: str,
    analysis: dict,
    drift: dict | None = None,
    gemini_key: str = '',
    groq_key: str = '',
) -> str | None:
    """
    Generate a 3-4 sentence plain-English summary of a stock's narrative state.

    Key order:
      1. Caller-supplied gemini_key (user key from chat flow, if passed)
      2. Caller-supplied groq_key
      3. Server-side GEMINI_API_KEY env var
      4. Server-side GROQ_API_KEY env var

    Returns None if no keys are available or all calls fail.
    """
    context = _build_summary_context(ticker, company_name, analysis, drift)

    # Prefer explicitly passed keys, fall back to server-side keys
    g_key = gemini_key or _SERVER_GEMINI_KEY
    r_key = groq_key   or _SERVER_GROQ_KEY

    if g_key:
        result = _call_gemini_summary(context, g_key)
        if result:
            return result

    if r_key:
        result = _call_groq_summary(context, r_key)
        if result:
            return result

    return None
