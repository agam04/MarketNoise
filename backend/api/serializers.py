from rest_framework import serializers
from .models import Stock, Narrative, SentimentScore, VelocityMetric, HypeScore


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'ticker', 'name', 'sector', 'exchange', 'is_active', 'created_at']


class SentimentScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentScore
        fields = [
            'id', 'label', 'positive_score', 'negative_score',
            'neutral_score', 'compound_score', 'analyzed_at',
        ]


class NarrativeSerializer(serializers.ModelSerializer):
    sentiment = SentimentScoreSerializer(read_only=True)

    class Meta:
        model = Narrative
        fields = [
            'id', 'title', 'content', 'source', 'source_name',
            'url', 'published_at', 'fetched_at', 'sentiment',
        ]


class VelocityMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = VelocityMetric
        fields = [
            'id', 'mention_count', 'velocity_score', 'acceleration',
            'trend', 'window_start', 'window_end', 'computed_at',
        ]


class HypeScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HypeScore
        fields = [
            'id', 'score', 'level', 'sentiment_imbalance',
            'social_news_ratio', 'velocity_factor', 'explanation',
            'computed_at',
        ]


class StockAnalysisSerializer(serializers.Serializer):
    """Combined analysis view for a stock — used by the dashboard."""
    stock = StockSerializer()
    latest_sentiment = serializers.SerializerMethodField()
    latest_velocity = serializers.SerializerMethodField()
    latest_hype = serializers.SerializerMethodField()
    recent_narratives = NarrativeSerializer(many=True)

    def get_latest_sentiment(self, obj):
        scores = obj.get('sentiment_scores', [])
        if scores:
            return SentimentScoreSerializer(scores[0]).data
        return None

    def get_latest_velocity(self, obj):
        metrics = obj.get('velocity_metrics', [])
        if metrics:
            return VelocityMetricSerializer(metrics[0]).data
        return None

    def get_latest_hype(self, obj):
        hype = obj.get('hype_scores', [])
        if hype:
            return HypeScoreSerializer(hype[0]).data
        return None
