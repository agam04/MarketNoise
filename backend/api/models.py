from django.db import models


class Stock(models.Model):
    """A tracked stock ticker."""
    ticker = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=100, blank=True, default='')
    exchange = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ticker']

    def __str__(self):
        return f"{self.ticker} — {self.name}"


class Narrative(models.Model):
    """A news article or social media post about a stock."""
    SOURCE_CHOICES = [
        ('news', 'News'),
        ('rss', 'RSS Feed'),
        ('reddit', 'Reddit'),
        ('twitter', 'Twitter/X'),
        ('other', 'Other'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='narratives')
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, default='')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_name = models.CharField(max_length=200, blank=True, default='')
    url = models.URLField(max_length=500, blank=True, default='')
    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['stock', '-published_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['url'],
                condition=~models.Q(url=''),
                name='unique_narrative_url',
            ),
        ]

    def __str__(self):
        return f"[{self.source}] {self.title[:80]}"


class SentimentScore(models.Model):
    """Sentiment analysis result for a narrative."""
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('mixed', 'Mixed'),
    ]

    narrative = models.OneToOneField(Narrative, on_delete=models.CASCADE, related_name='sentiment')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='sentiment_scores')
    label = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    positive_score = models.FloatField(default=0.0)
    negative_score = models.FloatField(default=0.0)
    neutral_score = models.FloatField(default=0.0)
    compound_score = models.FloatField(default=0.0)  # Overall score (-1 to 1)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['stock', '-analyzed_at']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} — {self.label} ({self.compound_score:.2f})"


class VelocityMetric(models.Model):
    """Narrative velocity measurement over a time window."""
    TREND_CHOICES = [
        ('accelerating', 'Accelerating'),
        ('decelerating', 'Decelerating'),
        ('stable', 'Stable'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='velocity_metrics')
    mention_count = models.IntegerField(default=0)
    velocity_score = models.FloatField(default=0.0)  # Rate of change in mentions
    acceleration = models.FloatField(default=0.0)     # Change in velocity
    trend = models.CharField(max_length=15, choices=TREND_CHOICES, default='stable')
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-computed_at']
        indexes = [
            models.Index(fields=['stock', '-computed_at']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} — velocity {self.velocity_score:.2f} ({self.trend})"


class HypeScore(models.Model):
    """Hype risk assessment for a stock at a point in time."""
    LEVEL_CHOICES = [
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('extreme', 'Extreme'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='hype_scores')
    score = models.FloatField(default=0.0)       # 0-100 hype risk score
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='low')
    sentiment_imbalance = models.FloatField(default=0.0)   # How skewed sentiment is
    social_news_ratio = models.FloatField(default=0.0)     # Social mentions / news mentions
    velocity_factor = models.FloatField(default=0.0)       # How fast attention is growing
    explanation = models.TextField(blank=True, default='')  # Why this score was given
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-computed_at']
        indexes = [
            models.Index(fields=['stock', '-computed_at']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} — hype {self.score:.0f}/100 ({self.level})"


class Watchlist(models.Model):
    """A user's saved tickers."""
    user  = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='watchlist')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='watchers')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'stock')]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} → {self.stock.ticker}"


class PriceImpact(models.Model):
    """Tracks how a narrative impacted stock price over time."""
    DIRECTION_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
        ('flat', 'Flat'),
    ]

    narrative = models.OneToOneField(Narrative, on_delete=models.CASCADE, related_name='price_impact')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='price_impacts')

    # Prices at different time offsets after the article was published
    price_at_publish = models.FloatField(null=True, blank=True)
    price_1h = models.FloatField(null=True, blank=True)
    price_4h = models.FloatField(null=True, blank=True)
    price_24h = models.FloatField(null=True, blank=True)

    # Computed percentage changes
    impact_1h = models.FloatField(null=True, blank=True)
    impact_4h = models.FloatField(null=True, blank=True)
    impact_24h = models.FloatField(null=True, blank=True)

    # Classification label (the ML training target)
    direction_24h = models.CharField(max_length=5, choices=DIRECTION_CHOICES, blank=True, default='')

    # Tracking which price checks have been completed
    price_fetched_at_publish = models.BooleanField(default=False)
    price_fetched_1h = models.BooleanField(default=False)
    price_fetched_4h = models.BooleanField(default=False)
    price_fetched_24h = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
            models.Index(fields=['direction_24h']),
        ]

    def compute_impacts(self):
        """Calculate percentage changes and direction label from prices."""
        if not self.price_at_publish or self.price_at_publish <= 0:
            return

        if self.price_1h is not None:
            self.impact_1h = ((self.price_1h - self.price_at_publish) / self.price_at_publish) * 100

        if self.price_4h is not None:
            self.impact_4h = ((self.price_4h - self.price_at_publish) / self.price_at_publish) * 100

        if self.price_24h is not None:
            self.impact_24h = ((self.price_24h - self.price_at_publish) / self.price_at_publish) * 100
            # Classify: >0.15% up, <-0.15% down, else flat
            if self.impact_24h > 0.15:
                self.direction_24h = 'up'
            elif self.impact_24h < -0.15:
                self.direction_24h = 'down'
            else:
                self.direction_24h = 'flat'

        self.save()

    def __str__(self):
        direction = self.direction_24h or 'pending'
        impact = f"{self.impact_24h:+.2f}%" if self.impact_24h is not None else '?'
        return f"{self.stock.ticker} — {direction} ({impact})"
