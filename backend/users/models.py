from django.db import models
from django.contrib.auth.models import User


class UserAPIKey(models.Model):
    """Stores encrypted API keys per user per service."""

    SERVICE_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('groq', 'Groq'),
        ('twelvedata', 'Twelve Data'),
        ('gnews', 'GNews'),
        ('reddit_id', 'Reddit Client ID'),
        ('reddit_secret', 'Reddit Client Secret'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    encrypted_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user.username} — {self.get_service_display()}"

    def masked_key(self) -> str:
        """Return first 4 and last 4 chars of the decrypted key, for display."""
        from .encryption import decrypt_key
        try:
            plain = decrypt_key(self.encrypted_key)
            if len(plain) <= 8:
                return plain[:2] + '...' + plain[-2:]
            return plain[:4] + '...' + plain[-4:]
        except Exception:
            return '****'
