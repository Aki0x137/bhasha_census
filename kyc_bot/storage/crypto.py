"""Symmetric encryption helpers (Fernet) for at-rest PII and image storage.

The key is a urlsafe-base64 Fernet key supplied via the KYC_MASTER_KEY env var.
For MVP a single symmetric key is used; a later slice can move this to a KMS.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet


def load_key() -> bytes:
    """Return the Fernet key from KYC_MASTER_KEY, or raise if unset."""
    key = os.environ.get("KYC_MASTER_KEY")
    if not key:
        raise RuntimeError(
            "KYC_MASTER_KEY env var is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"`"
        )
    return key.encode()


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt raw bytes, returning a Fernet token (bytes)."""
    return Fernet(key).encrypt(data)


def decrypt(token: bytes, key: bytes) -> bytes:
    """Decrypt a Fernet token back to raw bytes."""
    return Fernet(key).decrypt(token)


def encrypt_str(text: str, key: bytes) -> str:
    """Encrypt a string, returning a str token (utf-8 decoded)."""
    return encrypt(text.encode("utf-8"), key).decode("utf-8")


def decrypt_str(token: str, key: bytes) -> str:
    """Decrypt a str token back to the original string."""
    return decrypt(token.encode("utf-8"), key).decode("utf-8")
