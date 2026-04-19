from django.contrib import admin
from .models import Stock, Narrative, SentimentScore, VelocityMetric, HypeScore, PriceImpact


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'name', 'sector', 'exchange', 'is_active']
    search_fields = ['ticker', 'name']
    list_filter = ['is_active', 'sector']


@admin.register(Narrative)
class NarrativeAdmin(admin.ModelAdmin):
    list_display = ['title_short', 'stock', 'source', 'source_name', 'published_at']
    list_filter = ['source', 'stock']
    search_fields = ['title']

    def title_short(self, obj):
        return obj.title[:80]


@admin.register(SentimentScore)
class SentimentScoreAdmin(admin.ModelAdmin):
    list_display = ['stock', 'label', 'compound_score', 'analyzed_at']
    list_filter = ['label', 'stock']


@admin.register(VelocityMetric)
class VelocityMetricAdmin(admin.ModelAdmin):
    list_display = ['stock', 'velocity_score', 'trend', 'mention_count', 'computed_at']
    list_filter = ['trend', 'stock']


@admin.register(HypeScore)
class HypeScoreAdmin(admin.ModelAdmin):
    list_display = ['stock', 'score', 'level', 'computed_at']
    list_filter = ['level', 'stock']


@admin.register(PriceImpact)
class PriceImpactAdmin(admin.ModelAdmin):
    list_display = [
        'stock', 'direction_24h', 'price_at_publish', 'impact_24h',
        'price_fetched_at_publish', 'price_fetched_1h', 'price_fetched_4h', 'price_fetched_24h',
        'created_at',
    ]
    list_filter = ['direction_24h', 'stock', 'price_fetched_24h']
    search_fields = ['stock__ticker', 'narrative__title']
    readonly_fields = ['impact_1h', 'impact_4h', 'impact_24h', 'direction_24h']
