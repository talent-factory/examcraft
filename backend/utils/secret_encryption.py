"""Symmetric token encryption utility (TF-336).

Wraps ``cryptography.fernet.Fernet`` so we have one place to load the key
and the same encrypt/decrypt API for any future at-rest secret. Used by
``moodle_connections.token_encrypted`` and ready for additional secrets
(SCIM API tokens, webhook signing keys, etc.).

Key resolution (in order):

1. ``MOODLE_TOKEN_ENCRYPTION_KEY`` — explicit Fernet key (44 chars,
   urlsafe-base64). Set this in production.
2. ``SECRET_KEY`` (the JWT signing key) — derived via SHA-256 to a
   Fernet key. Lets dev/test environments work without an additional
   secret. Logged at WARNING because production should not rely on it.

We intentionally keep the abstraction tight: Fernet is fine for
storing-and-fetching secrets; for cases that need rotatable keys or
HSM-backed encryption, the right answer is a different module, not
adding knobs here.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache
from typing import NewType

from cryptography.fernet import Fernet, InvalidToken


logger = logging.getLogger(__name__)


# Type-level distinction between ciphertext and plaintext. ``NewType``
# is a static-only shim — at runtime an ``EncryptedSecret`` is a plain
# ``str``. Used so a typed reviewer notices when a function signature
# claims to return ciphertext but actually carries plaintext.
EncryptedSecret = NewType("EncryptedSecret", str)


class Plaintext(str):
    """A ``str`` subclass that hides its content in ``repr``.

    Standard string operations (==, slicing, encoding, urlencoding,
    JSON-serialisation, f-string interpolation via ``__format__`` →
    ``str``) keep working because ``Plaintext`` *is* a ``str``. We
    only override ``__repr__`` so the value never appears in
    ``logger.debug(repr(x))``, traceback locals, ``print(x)`` of a
    list/dict, or REPL inspection — those are the realistic accident
    paths. Functional callers (httpx form encoding, Fernet) keep
    working unchanged.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # noqa: D401 - dunder
        return "<Plaintext redacted>"

    def reveal(self) -> str:
        """Return the underlying ``str`` value. Use sparingly — every
        call site is a potential leak surface, so review carefully
        when adding one."""
        return str.__str__(self)


class SecretEncryptionError(RuntimeError):
    """Raised when a secret cannot be encrypted/decrypted."""


_DEV_KEY_WARNING_LOGGED = False


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Resolve the active Fernet key once per process."""
    explicit = os.getenv("MOODLE_TOKEN_ENCRYPTION_KEY")
    if explicit:
        try:
            return Fernet(explicit.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise SecretEncryptionError(
                "MOODLE_TOKEN_ENCRYPTION_KEY ist gesetzt aber kein "
                "gültiger Fernet-Schlüssel (44 Zeichen, urlsafe-base64)."
            ) from exc

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise SecretEncryptionError(
            "Weder MOODLE_TOKEN_ENCRYPTION_KEY noch SECRET_KEY ist "
            "gesetzt — kann keine Tokens ver-/entschlüsseln."
        )

    global _DEV_KEY_WARNING_LOGGED
    if not _DEV_KEY_WARNING_LOGGED:
        logger.warning(
            "secret_encryption: keine MOODLE_TOKEN_ENCRYPTION_KEY gesetzt "
            "— derive Fernet-Key aus SECRET_KEY. Für Produktion einen "
            "eigenen Key konfigurieren."
        )
        _DEV_KEY_WARNING_LOGGED = True
    derived = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_secret(plaintext: str | Plaintext) -> EncryptedSecret:
    """Encrypt a string and return the urlsafe-base64 token."""
    if not isinstance(plaintext, str):
        raise SecretEncryptionError(
            "encrypt_secret erwartet einen String — der Aufrufer hat "
            f"{type(plaintext).__name__} übergeben."
        )
    raw = plaintext.reveal() if isinstance(plaintext, Plaintext) else plaintext
    return EncryptedSecret(_get_fernet().encrypt(raw.encode("utf-8")).decode("ascii"))


def decrypt_secret(token: str | EncryptedSecret) -> Plaintext:
    """Decrypt the urlsafe-base64 token back to plaintext.

    Raises ``SecretEncryptionError`` if the token was created with a
    different key — surface this as a 500 to the operator rather than
    silently exposing the issue. A common cause is a key rotation
    without re-encryption of legacy rows.
    """
    if not isinstance(token, str):
        raise SecretEncryptionError(
            "decrypt_secret erwartet einen String — der Aufrufer hat "
            f"{type(token).__name__} übergeben."
        )
    try:
        raw = _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
        return Plaintext(raw)
    except InvalidToken as exc:
        raise SecretEncryptionError(
            "Token konnte nicht entschlüsselt werden — wahrscheinlich "
            "wurde der Encryption-Key gewechselt. Re-Verschlüsselung "
            "der Datenbank ist nötig."
        ) from exc


def reset_cache_for_tests() -> None:
    """Clear the cached Fernet so tests can switch keys per test.

    Production code should never need this. Pytest fixtures that
    monkey-patch ``MOODLE_TOKEN_ENCRYPTION_KEY`` should call this in
    setup and teardown so the cached Fernet does not leak between
    tests.
    """
    _get_fernet.cache_clear()
