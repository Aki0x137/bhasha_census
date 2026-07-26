# kyc_bot/config.py
"""Env-driven configuration for the SIR bot."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Base data directory (holds the vault and the SQLite db)."""
    return Path(os.environ.get("KYC_DATA_DIR", "./data"))


def vault_dir() -> Path:
    return data_dir() / "vault"


def db_path() -> Path:
    return data_dir() / "submissions.db"
