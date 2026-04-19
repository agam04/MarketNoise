from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Stock, Narrative, SentimentScore, VelocityMetric, HypeScore
from .serializers import (
    StockSerializer,
    NarrativeSerializer,
    SentimentScoreSerializer,
    VelocityMetricSerializer,
    HypeScoreSerializer,
)


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/stocks/          — List all tracked stocks
    GET /api/stocks/{ticker}/ — Get stock details by ticker
    """
    queryset = Stock.objects.filter(is_active=True)
    serializer_class = StockSerializer
    lookup_field = 'ticker'
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(ticker__icontains=search) | Q(name__icontains=search)
            )
        return qs

    @action(detail=True, methods=['get'], url_path='analysis')
    def analysis(self, request, ticker=None):
        """GET /api/stocks/{ticker}/analysis/ — Full analysis for a stock."""
        stock = self.get_object()
        return Response({
            'stock': StockSerializer(stock).data,
            'sentiment': SentimentScoreSerializer(
                stock.sentiment_scores.first()
            ).data if stock.sentiment_scores.exists() else None,
            'velocity': VelocityMetricSerializer(
                stock.velocity_metrics.first()
            ).data if stock.velocity_metrics.exists() else None,
            'hype': HypeScoreSerializer(
                stock.hype_scores.first()
            ).data if stock.hype_scores.exists() else None,
            'narratives': NarrativeSerializer(
                stock.narratives.all()[:10], many=True
            ).data,
        })


class NarrativeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/narratives/?stock={ticker}  — Narratives for a stock
    """
    serializer_class = NarrativeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Narrative.objects.select_related('sentiment').all()
        ticker = self.request.query_params.get('stock')
        if ticker:
            qs = qs.filter(stock__ticker=ticker.upper())
        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(source=source)
        return qs


class SentimentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/sentiment/?stock={ticker}  — Sentiment scores for a stock
    """
    serializer_class = SentimentScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = SentimentScore.objects.all()
        ticker = self.request.query_params.get('stock')
        if ticker:
            qs = qs.filter(stock__ticker=ticker.upper())
        return qs


class VelocityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/velocity/?stock={ticker}  — Velocity metrics for a stock
    """
    serializer_class = VelocityMetricSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = VelocityMetric.objects.all()
        ticker = self.request.query_params.get('stock')
        if ticker:
            qs = qs.filter(stock__ticker=ticker.upper())
        return qs


class HypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/hype/?stock={ticker}  — Hype scores for a stock
    """
    serializer_class = HypeScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = HypeScore.objects.all()
        ticker = self.request.query_params.get('stock')
        if ticker:
            qs = qs.filter(stock__ticker=ticker.upper())
        return qs


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """GET /api/health/ — Simple health check endpoint."""
    return Response({'status': 'ok', 'service': 'marketnoise-api'})
