"""Security utilities: password hashing and JWT token management.

Uses PBKDF2-SHA256 for password hashing and HMAC-SHA256 for JWT signing.
Standard library only — no external crypto dependencies.
"""

import hashlib
import hmac
import json
import time
import base64
import os

from .config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_HASH_ALGORITHM = "pbkdf2_sha256"
_HASH_ROUNDS = 210000
_SALT_BYTES = 16

_JWT_HEADER = base64.urlsafe_b64encode(
    json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
).rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# Password hashing — PBKDF2-SHA256
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash *password* and return an encoded string suitable for storage.

    Format: ``pbkdf2_sha256$210000$<salt_b64>$<digest_b64>``
    """
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        _HASH_ROUNDS,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).rstrip(b"=").decode()
    digest_b64 = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return f"{_HASH_ALGORITHM}${_HASH_ROUNDS}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded: str) -> bool:
    """Verify *password* against the stored *encoded* hash.

    Returns ``True`` on match, ``False`` otherwise.
    """
    parts = encoded.split("$")
    if len(parts) != 4:
        return False
    _alg, rounds_str, salt_b64, digest_b64 = parts
    if _alg != _HASH_ALGORITHM:
        return False
    try:
        rounds = int(rounds_str)
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected_digest = base64.urlsafe_b64decode(digest_b64 + "==")
    except (ValueError, Exception):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        rounds,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


# ---------------------------------------------------------------------------
# JWT — HMAC-SHA256
# ---------------------------------------------------------------------------

def _b64_encode(data: bytes) -> str:
    """Base64url-encode *data* without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    """Decode unpadded base64url string *s*."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(user_id: int, role: str) -> str:
    """Create a signed JWT for *user_id* with the given *role*.

    The token expires after ``settings.token_minutes``.
    Returns the three-part JWT string.
    """
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": now + settings.token_minutes * 60,
    }
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())

    message = f"{_JWT_HEADER}.{payload_b64}".encode()
    signature = hmac.new(
        settings.app_secret.encode(),
        message,
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64_encode(signature)

    return f"{_JWT_HEADER}.{payload_b64}.{signature_b64}"


def decode_token(token: str) -> dict | None:
    """Verify and decode *token*.

    Returns the payload ``dict`` if the signature is valid and the token has
    not expired, otherwise ``None``.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, signature_b64 = parts

    message = f"{header_b64}.{payload_b64}".encode()

    try:
        signature = _b64_decode(signature_b64)
    except Exception:
        return None

    expected_signature = hmac.new(
        settings.app_secret.encode(),
        message,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes)
    except Exception:
        return None

    exp = payload.get("exp")
    if exp is None or int(time.time()) > exp:
        return None

    return payload
