"""Pytest config — makes the repo root importable + resets the auth rate-limit
bucket between tests so the rate-limit test isn't poisoned by prior runs.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests use synthetic credentials that are unrelated to any operator/runtime secret.
os.environ.setdefault("DEMO_PASSWORD", "buffer-blaster-test-password")
os.environ.setdefault("MASTER_ENCRYPTION_KEY", "buffer-blaster-test-key")


import pytest
from api.services.native import get_core


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the auth rate-limit buckets before each test."""
    get_core().rate_limiter._buckets.clear()
    try:
        from api.services.operator_sessions import _redis, _AUTH_PREFIX
        client = _redis()
        if client is not None:
            for k in client.keys(f"{_AUTH_PREFIX}*"):
                client.delete(k)
    except Exception:
        pass
    yield
