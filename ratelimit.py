from __future__ import annotations

import os
from collections import defaultdict
from threading import Lock
from time import time

# In-process rate limit store: {identity: [timestamp, ...]}
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()


def check_rate_limit(identity: str) -> bool:
    """Return True if the identity is within its rate limit, False if exceeded.

    Fixed window: counts requests within the last RATELIMIT_WINDOW_SECONDS seconds.
    """
    max_requests = int(os.environ.get("RATELIMIT_REQUESTS", "60"))
    window = int(os.environ.get("RATELIMIT_WINDOW_SECONDS", "3600"))
    now = time()
    cutoff = now - window

    with _rate_lock:
        timestamps = _rate_store[identity]
        timestamps[:] = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        return True
