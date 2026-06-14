# tests/test_auth.py
import os
import time
import pytest
from unittest.mock import MagicMock, patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey, RSAKey, KeySet

# Generate a test RSA key pair once for all auth tests
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)
_PUBLIC_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

_TEST_AUDIENCE = "test-audience"
_TEST_ISSUER = "https://authkit.example.com"


def _make_jose_key_set():
    """Build a joserfc KeySet from the test RSA public key."""
    rsa_key = RSAKey.import_key(_PUBLIC_PEM)
    return KeySet([rsa_key])


def _make_token(sub: str = "user_abc", exp_offset: int = 3600, **extra) -> str:
    """Create a signed JWT using the test private key via joserfc."""
    private_rsa_key = RSAKey.import_key(_PRIVATE_PEM)
    header = {"alg": "RS256"}
    payload = {
        "sub": sub,
        "aud": _TEST_AUDIENCE,
        "iss": _TEST_ISSUER,
        "exp": int(time.time()) + exp_offset,
        "iat": int(time.time()),
        **extra,
    }
    return jose_jwt.encode(header, payload, private_rsa_key)


# --- validate_token ---

@patch.dict(os.environ, {"WORKOS_AUDIENCE": _TEST_AUDIENCE, "WORKOS_ISSUER": _TEST_ISSUER})
@patch("auth._get_key_set")
def test_validate_token_valid(mock_key_set):
    mock_key_set.return_value = _make_jose_key_set()
    from auth import validate_token
    token = _make_token()
    payload = validate_token(token)
    assert payload["sub"] == "user_abc"


@patch.dict(os.environ, {"WORKOS_AUDIENCE": _TEST_AUDIENCE, "WORKOS_ISSUER": _TEST_ISSUER})
@patch("auth._get_key_set")
def test_validate_token_expired(mock_key_set):
    mock_key_set.return_value = _make_jose_key_set()
    from auth import validate_token
    token = _make_token(exp_offset=-10)  # already expired
    with pytest.raises(Exception):
        validate_token(token)


@patch.dict(os.environ, {"WORKOS_AUDIENCE": _TEST_AUDIENCE, "WORKOS_ISSUER": _TEST_ISSUER})
@patch("auth._get_key_set")
def test_validate_token_wrong_key(mock_key_set):
    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_public_pem = other_private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    mock_key_set.return_value = KeySet([RSAKey.import_key(other_public_pem)])
    from auth import validate_token
    token = _make_token()
    with pytest.raises(Exception):
        validate_token(token)


# --- check_rate_limit ---

@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "3", "RATELIMIT_WINDOW_SECONDS": "60"})
def test_rate_limit_allows_within_limit():
    from auth import check_rate_limit, _rate_store
    identity = "user_rate_test_allow"
    _rate_store.pop(identity, None)
    assert check_rate_limit(identity) is True
    assert check_rate_limit(identity) is True
    assert check_rate_limit(identity) is True


@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "3", "RATELIMIT_WINDOW_SECONDS": "60"})
def test_rate_limit_blocks_after_limit():
    from auth import check_rate_limit, _rate_store
    identity = "user_rate_test_block"
    _rate_store.pop(identity, None)
    check_rate_limit(identity)
    check_rate_limit(identity)
    check_rate_limit(identity)
    assert check_rate_limit(identity) is False  # 4th call exceeds limit of 3


@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "2", "RATELIMIT_WINDOW_SECONDS": "1"})
def test_rate_limit_resets_after_window():
    from auth import check_rate_limit, _rate_store
    identity = "user_rate_test_reset"
    _rate_store.pop(identity, None)
    check_rate_limit(identity)
    check_rate_limit(identity)
    assert check_rate_limit(identity) is False  # at limit

    # Manually expire the timestamps
    _rate_store[identity] = [t - 5 for t in _rate_store[identity]]
    assert check_rate_limit(identity) is True  # window expired, resets
