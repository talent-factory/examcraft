"""Tests for ``utils.secret_encryption`` (TF-336)."""

from __future__ import annotations

import os

import pytest

from utils.secret_encryption import (
    SecretEncryptionError,
    decrypt_secret,
    encrypt_secret,
    reset_cache_for_tests,
)


@pytest.fixture(autouse=True)
def _isolate_keys(monkeypatch):
    """Each test starts with a clean Fernet cache so monkeypatched
    keys actually take effect."""
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def test_round_trip_with_secret_key_fallback() -> None:
    cipher = encrypt_secret("hello-moodle")
    assert cipher != "hello-moodle"
    assert decrypt_secret(cipher) == "hello-moodle"


def test_round_trip_with_explicit_fernet_key(monkeypatch) -> None:
    from cryptography.fernet import Fernet

    monkeypatch.setenv("MOODLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    reset_cache_for_tests()
    cipher = encrypt_secret("token-1234")
    assert decrypt_secret(cipher) == "token-1234"


def test_invalid_explicit_key_raises(monkeypatch) -> None:
    monkeypatch.setenv("MOODLE_TOKEN_ENCRYPTION_KEY", "nope")
    reset_cache_for_tests()
    with pytest.raises(SecretEncryptionError):
        encrypt_secret("anything")


def test_decrypt_with_rotated_key_raises(monkeypatch) -> None:
    cipher = encrypt_secret("secret-A")

    # Rotate the key.
    from cryptography.fernet import Fernet

    monkeypatch.setenv("MOODLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    reset_cache_for_tests()
    with pytest.raises(SecretEncryptionError):
        decrypt_secret(cipher)


def test_encrypt_rejects_non_string() -> None:
    with pytest.raises(SecretEncryptionError):
        encrypt_secret(b"bytes-not-allowed")  # type: ignore[arg-type]


def test_decrypt_rejects_non_string() -> None:
    with pytest.raises(SecretEncryptionError):
        decrypt_secret(b"bytes-not-allowed")  # type: ignore[arg-type]


def test_missing_keys_raises(monkeypatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    reset_cache_for_tests()
    with pytest.raises(SecretEncryptionError):
        encrypt_secret("anything")
    # Also restore for the rest of the tests.
    os.environ["SECRET_KEY"] = "dev-secret-key-for-tests"
