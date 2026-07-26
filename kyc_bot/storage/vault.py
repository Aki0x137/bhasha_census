"""Encrypted file vault: writes Fernet-encrypted blobs to disk."""
from __future__ import annotations

from pathlib import Path

from kyc_bot.storage import crypto


class Vault:
    """Stores encrypted files under `root`. Each blob is written as
    `<root>/<name>.enc` containing the Fernet ciphertext of the data."""

    def __init__(self, root: Path, key: bytes):
        self._root = Path(root)
        self._key = key

    def store(self, name: str, data: bytes) -> str:
        """Encrypt `data` and write it to `<root>/<name>.enc`. Returns the path."""
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / f"{name}.enc"
        path.write_bytes(crypto.encrypt(data, self._key))
        return str(path)

    def load(self, path: str) -> bytes:
        """Read and decrypt a previously stored file."""
        return crypto.decrypt(Path(path).read_bytes(), self._key)
