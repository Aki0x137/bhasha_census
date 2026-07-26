from cryptography.fernet import Fernet

from kyc_bot.storage.vault import Vault


def test_store_then_load_roundtrips(tmp_path):
    key = Fernet.generate_key()
    vault = Vault(root=tmp_path / "vault", key=key)
    path = vault.store("epic_abc", b"\x89PNG-image-bytes")
    assert vault.load(path) == b"\x89PNG-image-bytes"


def test_stored_file_is_not_plaintext(tmp_path):
    key = Fernet.generate_key()
    vault = Vault(root=tmp_path / "vault", key=key)
    path = vault.store("epic_abc", b"PLAINTEXT-MARKER")
    assert path == str(tmp_path / "vault" / "epic_abc.enc")
    on_disk = (tmp_path / "vault" / "epic_abc.enc").read_bytes()
    assert b"PLAINTEXT-MARKER" not in on_disk


def test_store_creates_root_dir(tmp_path):
    key = Fernet.generate_key()
    root = tmp_path / "nested" / "vault"
    vault = Vault(root=root, key=key)
    vault.store("x", b"data")
    assert root.is_dir()
