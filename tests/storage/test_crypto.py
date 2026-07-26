import pytest
from cryptography.fernet import Fernet

from kyc_bot.storage import crypto


def test_encrypt_decrypt_bytes_roundtrip():
    key = Fernet.generate_key()
    token = crypto.encrypt(b"secret bytes", key)
    assert token != b"secret bytes"
    assert crypto.decrypt(token, key) == b"secret bytes"


def test_encrypt_decrypt_str_roundtrip():
    key = Fernet.generate_key()
    token = crypto.encrypt_str("Ravi Kumar", key)
    assert isinstance(token, str)
    assert token != "Ravi Kumar"
    assert crypto.decrypt_str(token, key) == "Ravi Kumar"


def test_load_key_reads_env(monkeypatch):
    k = Fernet.generate_key().decode()
    monkeypatch.setenv("KYC_MASTER_KEY", k)
    assert crypto.load_key() == k.encode()


def test_load_key_missing_raises(monkeypatch):
    monkeypatch.delenv("KYC_MASTER_KEY", raising=False)
    with pytest.raises(RuntimeError, match="KYC_MASTER_KEY"):
        crypto.load_key()
