from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import market_views

router = DefaultRouter()
router.register(r'stocks', views.StockViewSet)
router.register(r'narratives', views.NarrativeViewSet, basename='narrative')
router.register(r'sentiment', views.SentimentViewSet, basename='sentiment')
router.register(r'velocity', views.VelocityViewSet, basename='velocity')
router.register(r'hype', views.HypeViewSet, basename='hype')

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    # Market proxy endpoints
    path('market/quote/<str:ticker>/', market_views.market_quote, name='market-quote'),
    path('market/chart/<str:ticker>/', market_views.market_chart, name='market-chart'),
    path('market/search/', market_views.market_search, name='market-search'),
    path('market/news/<str:ticker>/', market_views.market_news, name='market-news'),
    path('market/analyze/<str:ticker>/', market_views.market_analyze, name='market-analyze'),
    path('market/drift/<str:ticker>/',   market_views.market_drift,   name='market-drift'),
    path('market/predict/<str:ticker>/', market_views.market_predict, name='market-predict'),
    path('market/narrative-summary/<str:ticker>/', market_views.market_narrative_summary, name='market-narrative-summary'),
    path('market/trending/', market_views.market_trending, name='market-trending'),
    path('market/watchlist/', market_views.market_watchlist, name='market-watchlist'),
    path('market/watchlist/<str:ticker>/', market_views.market_watchlist_check, name='market-watchlist-check'),
    path('market/chat/<str:ticker>/', market_views.market_chat, name='market-chat'),
    path('', include(router.urls)),
]
