"""
Fernet-based encryption for storing API keys at rest.
Uses FIELD_ENCRYPTION_KEY from Django settings.
"""

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the configured encryption key."""
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not key:
        raise ValueError(
            'FIELD_ENCRYPTION_KEY is not set. '
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    # If the key is already a valid 32-byte base64 Fernet key, use directly.
    # Otherwise derive one from the provided string.
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Derive a valid Fernet key from an arbitrary string
        derived = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_key(plaintext: str) -> str:
    """Encrypt a plaintext API key. Returns a base64-encoded ciphertext string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to the original API key."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
