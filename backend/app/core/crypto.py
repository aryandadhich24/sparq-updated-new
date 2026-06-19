"""
Fernet-based encryption for sensitive values stored at rest (OAuth tokens, etc.).
Derives a stable Fernet key from the application SECRET_KEY.
"""

import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

from .config import settings


def _derive_key(secret: str) -> bytes:
    """Derive a URL-safe 32-byte key from the application secret."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_key(settings.SECRET_KEY))


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return the ciphertext as a UTF-8 string."""
    if not plaintext:
        return plaintext
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns empty string on failure."""
    if not ciphertext:
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # If decryption fails, the value may have been stored before encryption
        # was enabled — return it as-is (backward compat for migration period).
        return ciphertext
