# tests/test_ratelimit.py
import os
from unittest.mock import patch

from ratelimit import check_rate_limit, _rate_store


@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "3", "RATELIMIT_WINDOW_SECONDS": "60"})
def test_rate_limit_allows_within_limit():
    identity = "ip_rate_test_allow"
    _rate_store.pop(identity, None)
    assert check_rate_limit(identity) is True
    assert check_rate_limit(identity) is True
    assert check_rate_limit(identity) is True


@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "3", "RATELIMIT_WINDOW_SECONDS": "60"})
def test_rate_limit_blocks_after_limit():
    identity = "ip_rate_test_block"
    _rate_store.pop(identity, None)
    check_rate_limit(identity)
    check_rate_limit(identity)
    check_rate_limit(identity)
    assert check_rate_limit(identity) is False  # 4th call exceeds limit of 3


@patch.dict(os.environ, {"RATELIMIT_REQUESTS": "2", "RATELIMIT_WINDOW_SECONDS": "1"})
def test_rate_limit_resets_after_window():
    identity = "ip_rate_test_reset"
    _rate_store.pop(identity, None)
    check_rate_limit(identity)
    check_rate_limit(identity)
    assert check_rate_limit(identity) is False  # at limit

    # Manually expire the timestamps
    _rate_store[identity] = [t - 5 for t in _rate_store[identity]]
    assert check_rate_limit(identity) is True  # window expired, resets
