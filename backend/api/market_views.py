import os
from datetime import datetime

import requests as http
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

TWELVEDATA_KEY = os.getenv('TWELVEDATA_API_KEY', '')
GNEWS_KEY = os.getenv('GNEWS_API_KEY', '')
TWELVEDATA_BASE = 'https://api.twelvedata.com'
GNEWS_BASE = 'https://gnews.io/api/v4'

RANGE_MAP = {
    '1D': {'interval': '15min', 'outputsize': 26},
    '7D': {'interval': '1h', 'outputsize': 50},
    '1M': {'interval': '1day', 'outputsize': 22},
    '3M': {'interval': '1day', 'outputsize': 66},
}


@api_view(['GET'])
@permission_classes([AllowAny])
def market_quote(request, ticker):
    """Proxy Twelve Data quote endpoint. Cached 10 min."""
    ticker = ticker.upper()
    cache_key = f'quote:{ticker}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    resp = http.get(
        f'{TWELVEDATA_BASE}/quote',
        params={'symbol': ticker, 'apikey': TWELVEDATA_KEY},
        timeout=10,
    )
    if not resp.ok:
        return Response({'error': 'Upstream error'}, status=status.HTTP_502_BAD_GATEWAY)

    data = resp.json()
    if 'code' in data:
        return Response({'error': data.get('message', 'API error')}, status=status.HTTP_400_BAD_REQUEST)

    result = {
        'regularMarketPrice': float(data['close']),
        'regularMarketChange': float(data['change']),
        'regularMarketChangePercent': float(data['percent_change']),
        'regularMarketPreviousClose': float(data['previous_close']),
        'shortName': data.get('name', ticker),
    }
    cache.set(cache_key, result, timeout=600)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_chart(request, ticker):
    """Proxy Twelve Data time_series endpoint. Cached 10 min."""
    ticker = ticker.upper()
    time_range = request.query_params.get('range', '7D')
    if time_range not in RANGE_MAP:
        return Response({'error': 'Invalid range'}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = f'chart:{ticker}:{time_range}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    mapping = RANGE_MAP[time_range]
    resp = http.get(
        f'{TWELVEDATA_BASE}/time_series',
        params={
            'symbol': ticker,
            'interval': mapping['interval'],
            'outputsize': mapping['outputsize'],
            'apikey': TWELVEDATA_KEY,
        },
        timeout=10,
    )
    if not resp.ok:
        return Response({'error': 'Upstream error'}, status=status.HTTP_502_BAD_GATEWAY)

    data = resp.json()
    if 'code' in data:
        return Response({'error': data.get('message', 'API error')}, status=status.HTTP_400_BAD_REQUEST)
    if not data.get('values'):
        return Response({'error': 'No price data'}, status=status.HTTP_404_NOT_FOUND)

    points = []
    for v in reversed(data['values']):
        dt = datetime.fromisoformat(v['datetime'])
        label = dt.strftime('%-I:%M %p') if time_range == '1D' else dt.strftime('%b %-d')
        points.append({'date': label, 'price': round(float(v['close']), 2)})

    cache.set(cache_key, points, timeout=600)
    return Response(points)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_search(request):
    """Proxy Twelve Data symbol_search. Cached 30 min."""
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response([])

    cache_key = f'search:{query.lower()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    resp = http.get(
        f'{TWELVEDATA_BASE}/symbol_search',
        params={'symbol': query, 'outputsize': 8, 'apikey': TWELVEDATA_KEY},
        timeout=10,
    )
    if not resp.ok:
        return Response([])

    data = resp.json()
    if not data.get('data'):
        return Response([])

    stocks = [
        {
            'ticker': item['symbol'],
            'name': item['instrument_name'],
            'sector': item['exchange'],
        }
        for item in data['data']
        if item.get('country') == 'United States'
        and item.get('instrument_type') in ('Common Stock', 'ETF')
    ][:6]

    cache.set(cache_key, stocks, timeout=1800)
    return Response(stocks)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_news(request, ticker):
    """Proxy GNews search. Cached 15 min."""
    ticker = ticker.upper()
    company_name = request.query_params.get('name', ticker)

    cache_key = f'news:{ticker}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    query = f'{ticker} OR "{company_name}" stock'
    resp = http.get(
        f'{GNEWS_BASE}/search',
        params={'q': query, 'lang': 'en', 'max': 6, 'token': GNEWS_KEY},
        timeout=10,
    )
    if not resp.ok:
        return Response([])

    data = resp.json()
    if not data.get('articles'):
        return Response([])

    articles = [
        {
            'id': f'news-{i}',
            'headline': a['title'],
            'source': a['source']['name'],
            'timestamp': a['publishedAt'],
            'sentiment': 'neutral',
            'url': a['url'],
        }
        for i, a in enumerate(data['articles'])
    ]

    cache.set(cache_key, articles, timeout=900)
    return Response(articles)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_analyze(request, ticker):
    """Run full analysis pipeline: sentiment + velocity + hype + pattern. Cached 15 min."""
    from .analysis import analyze_stock_sentiment, compute_velocity, compute_hype_score
    from .patterns import classify_pattern

    ticker = ticker.upper()
    company_name = request.query_params.get('name', ticker)

    cache_key = f'analyze:{ticker}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    # Run pipeline in order: sentiment first (ingests articles), then velocity, then hype
    sentiment = analyze_stock_sentiment(ticker, company_name)
    velocity  = compute_velocity(ticker)
    hype      = compute_hype_score(ticker)

    # Classify the narrative pattern from the composite signals
    pattern = classify_pattern(sentiment, velocity, hype)

    result = {
        'sentiment': sentiment,
        'velocity':  velocity,
        'hype':      hype,
        'pattern':   pattern,
    }
    cache.set(cache_key, result, timeout=900)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_drift(request, ticker):
    """
    Narrative drift analysis: how has the story evolved over 7 / 30 / 90 days?
    Cached 30 min — more expensive than the single-point analyze call.
    """
    from .drift import compute_narrative_drift

    ticker = ticker.upper()
    cache_key = f'drift:{ticker}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    result = compute_narrative_drift(ticker)
    cache.set(cache_key, result, timeout=1800)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_predict(request, ticker):
    """Predict price-impact direction for a stock's recent narratives."""
    from .models import Narrative
    from .ml.predictor import predict_impact

    ticker = ticker.upper()

    narratives = Narrative.objects.filter(
        stock__ticker=ticker,
    ).select_related('sentiment', 'stock').order_by('-published_at')[:5]

    if not narratives:
        return Response({
            'ticker': ticker,
            'predictions': [],
            'model_loaded': False,
            'message': f'No narratives found for {ticker}. Run scrapers first.',
        })

    predictions = []
    model_loaded = False

    for n in narratives:
        pred = predict_impact(n)
        if pred:
            model_loaded = True
            predictions.append({
                'narrative_id': n.id,
                'title': n.title[:120],
                'source': n.source_name,
                'published_at': n.published_at.isoformat(),
                'predicted_direction': pred['predicted_direction'],
                'confidence': pred['confidence'],
            })

    return Response({
        'ticker': ticker,
        'predictions': predictions,
        'model_loaded': model_loaded,
        'message': 'Model not trained yet. Run: python manage.py train_model' if not model_loaded else None,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def market_narrative_summary(request, ticker):
    """
    GET /api/market/narrative-summary/<ticker>/
    Returns a 3-4 sentence plain-English summary of the stock's current narrative.
    Uses cached analysis + drift data — no extra API calls beyond the LLM.
    Cached 15 min. Returns {summary: null} if no LLM key is configured.
    """
    from .llm import generate_narrative_summary
    from .drift import compute_narrative_drift

    ticker = ticker.upper()
    company_name = request.query_params.get('name', ticker)

    cache_key = f'narrative_summary:{ticker}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    # Use cached analysis if available, otherwise run the pipeline
    analysis = cache.get(f'analyze:{ticker}')
    if not analysis:
        from .analysis import analyze_stock_sentiment, compute_velocity, compute_hype_score
        from .patterns import classify_pattern
        sentiment = analyze_stock_sentiment(ticker, company_name)
        velocity  = compute_velocity(ticker)
        hype      = compute_hype_score(ticker)
        pattern   = classify_pattern(sentiment, velocity, hype)
        analysis  = {'sentiment': sentiment, 'velocity': velocity,
                     'hype': hype, 'pattern': pattern}

    drift = cache.get(f'drift:{ticker}') or compute_narrative_drift(ticker)

    summary_text = generate_narrative_summary(
        ticker=ticker,
        company_name=company_name,
        analysis=analysis,
        drift=drift,
    )

    result = {'ticker': ticker, 'summary': summary_text}
    cache.set(cache_key, result, timeout=900)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_trending(request):
    """
    Return top stocks by narrative activity (hype + velocity composite).
    Only returns stocks that already have analysis data in the DB — no API calls.
    Cached 10 min.
    """
    from .models import Stock, HypeScore, VelocityMetric, SentimentScore
    from .patterns import classify_pattern
    from .analysis import _classify_label
    from django.utils import timezone
    from datetime import timedelta

    cache_key = 'trending:top'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    cutoff = timezone.now() - timedelta(hours=48)

    # Find all stocks that have hype scores computed in the last 48h
    stock_ids = list(
        HypeScore.objects.filter(computed_at__gte=cutoff)
        .values_list('stock_id', flat=True)
        .distinct()
    )

    if not stock_ids:
        return Response([])

    results = []
    for stock in Stock.objects.filter(id__in=stock_ids):
        ticker = stock.ticker

        # Latest DB records (no API calls)
        latest_hype = HypeScore.objects.filter(stock=stock).order_by('-computed_at').first()
        latest_vel = VelocityMetric.objects.filter(stock=stock).order_by('-computed_at').first()
        recent_sents = list(
            SentimentScore.objects.filter(stock=stock).order_by('-analyzed_at')[:20]
        )

        if not latest_hype or not latest_vel or not recent_sents:
            continue

        count = len(recent_sents)
        avg_compound = sum(s.compound_score for s in recent_sents) / count
        avg_pos = sum(s.positive_score for s in recent_sents) / count
        avg_neg = sum(s.negative_score for s in recent_sents) / count
        avg_neu = sum(s.neutral_score for s in recent_sents) / count
        overall_label = _classify_label(avg_compound)

        # Reconstruct the hype factor points the classifier expects
        raw_imbalance = latest_hype.sentiment_imbalance          # 0.0–1.0 ratio
        sentiment_imbalance_pts = max(0.0, (raw_imbalance - 0.5) * 2.0) * 40.0
        velocity_pts = min(latest_hype.velocity_factor / 100.0, 1.0) * 35.0

        sentiment_d = {
            'compound': round(avg_compound, 3),
            'positive': round(avg_pos, 3),
            'negative': round(avg_neg, 3),
            'neutral': round(avg_neu, 3),
            'label': overall_label,
        }
        velocity_d = {
            'score': latest_vel.velocity_score,
            'trend': latest_vel.trend,
            'change_percent': latest_vel.acceleration,
            'mention_count': latest_vel.mention_count,
        }
        hype_d = {
            'score': latest_hype.score,
            'level': latest_hype.level,
            'sentiment_imbalance': round(sentiment_imbalance_pts, 1),
            'velocity_factor': round(velocity_pts, 1),
            'source_concentration': 0.0,
        }

        pattern = classify_pattern(sentiment_d, velocity_d, hype_d)

        # Composite interest score (hype weighted heavier)
        composite = latest_hype.score * 0.6 + latest_vel.velocity_score * 0.4

        results.append({
            'ticker': ticker,
            'name': stock.name,
            'hype_score': latest_hype.score,
            'hype_level': latest_hype.level,
            'velocity_trend': latest_vel.trend,
            'velocity_score': round(latest_vel.velocity_score, 1),
            'compound': round(avg_compound, 3),
            'sentiment_label': overall_label,
            'article_count': count,
            'pattern': pattern,
            'composite_score': round(composite, 1),
        })

    results.sort(key=lambda x: x['composite_score'], reverse=True)

    cache.set(cache_key, results[:12], timeout=600)
    return Response(results[:12])


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def market_watchlist(request):
    """
    GET    /api/market/watchlist/          List user's watchlist with latest signals
    POST   /api/market/watchlist/          Add ticker  { "ticker": "AAPL" }
    DELETE /api/market/watchlist/          Remove ticker { "ticker": "AAPL" }
    """
    from .models import Watchlist, Stock, HypeScore, VelocityMetric, SentimentScore
    from .analysis import _classify_label
    import math

    if request.method == 'GET':
        items = (
            Watchlist.objects
            .filter(user=request.user)
            .select_related('stock')
        )

        result = []
        for wl in items:
            stock = wl.stock
            latest_hype = HypeScore.objects.filter(stock=stock).order_by('-computed_at').first()
            latest_vel  = VelocityMetric.objects.filter(stock=stock).order_by('-computed_at').first()
            recent_sents = list(
                SentimentScore.objects.filter(stock=stock).order_by('-analyzed_at')[:10]
            )

            compound = None
            sentiment_label = None
            if recent_sents:
                from django.utils import timezone
                DECAY_LAMBDA = math.log(2) / 3.0
                now = timezone.now()
                weights = [math.exp(-DECAY_LAMBDA * max((now - s.analyzed_at).total_seconds() / 86400.0, 0))
                           for s in recent_sents]
                total_w = sum(weights) or 1.0
                compound = round(sum(s.compound_score * w for s, w in zip(recent_sents, weights)) / total_w, 3)
                sentiment_label = _classify_label(compound)

            result.append({
                'ticker':          stock.ticker,
                'name':            stock.name,
                'added_at':        wl.added_at.isoformat(),
                'hype_score':      latest_hype.score      if latest_hype else None,
                'hype_level':      latest_hype.level      if latest_hype else None,
                'velocity_trend':  latest_vel.trend       if latest_vel  else None,
                'compound':        compound,
                'sentiment_label': sentiment_label,
                'has_data':        latest_hype is not None,
            })

        return Response(result)

    ticker = (request.data.get('ticker') or '').strip().upper()
    if not ticker:
        return Response({'error': 'ticker is required'}, status=status.HTTP_400_BAD_REQUEST)

    stock, _ = Stock.objects.get_or_create(
        ticker=ticker,
        defaults={'name': ticker},
    )

    if request.method == 'POST':
        _, created = Watchlist.objects.get_or_create(user=request.user, stock=stock)
        return Response(
            {'ticker': ticker, 'watching': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    if request.method == 'DELETE':
        Watchlist.objects.filter(user=request.user, stock=stock).delete()
        return Response({'ticker': ticker, 'watching': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_watchlist_check(request, ticker):
    """GET /api/market/watchlist/<ticker>/ — is this ticker in the user's watchlist?"""
    from .models import Watchlist, Stock
    ticker = ticker.upper()
    watching = Watchlist.objects.filter(
        user=request.user,
        stock__ticker=ticker,
    ).exists()
    return Response({'ticker': ticker, 'watching': watching})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def market_chat(request, ticker):
    """POST /api/market/chat/<ticker>/ — AI chat powered by Gemini or Groq."""
    from .llm import ask_llm
    from users.models import UserAPIKey
    from users.encryption import decrypt_key

    ticker = ticker.upper()
    question = request.data.get('question', '').strip()
    company_name = request.data.get('company_name', ticker)

    if not question:
        return Response(
            {'error': 'A "question" field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get user's LLM API keys (whichever they have)
    gemini_key = None
    groq_key = None

    for key_obj in UserAPIKey.objects.filter(user=request.user, service__in=['gemini', 'groq']):
        decrypted = decrypt_key(key_obj.encrypted_key)
        if key_obj.service == 'gemini':
            gemini_key = decrypted
        elif key_obj.service == 'groq':
            groq_key = decrypted

    if not gemini_key and not groq_key:
        return Response({
            'answer': 'No AI API key found. Add a Gemini or Groq key in Settings to use AI Chat.',
            'ticker': ticker,
            'needs_key': True,
        })

    answer = ask_llm(ticker, question, company_name, gemini_key=gemini_key, groq_key=groq_key)

    return Response({
        'answer': answer,
        'ticker': ticker,
    })
