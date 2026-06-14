# auth.py — stub; Task 9 implements fully
from contextvars import ContextVar
from collections import defaultdict
from threading import Lock
from time import time
import os

current_identity: ContextVar[str] = ContextVar("current_identity", default="")

_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()


def check_rate_limit(identity: str) -> bool:
    max_req = int(os.environ.get("RATELIMIT_REQUESTS", "10"))
    window = int(os.environ.get("RATELIMIT_WINDOW_SECONDS", "3600"))
    now = time()
    cutoff = now - window
    with _rate_lock:
        ts = _rate_store[identity]
        ts[:] = [t for t in ts if t > cutoff]
        if len(ts) >= max_req:
            return False
        ts.append(now)
        return True
