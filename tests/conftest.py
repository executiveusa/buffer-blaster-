"""Pytest config — makes the repo root importable + resets the auth rate-limit
bucket between tests so the rate-limit test isn't poisoned by prior runs.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Demo mode + a known password for tests.
os.environ.setdefault("DEMO_PASSWORD", "BLASTER2026")
os.environ.setdefault("MASTER_ENCRYPTION_KEY", "stavarai-test-key")


import pytest
from api.services.native import get_core


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the auth rate-limit buckets before each test."""
    get_core().rate_limiter._buckets.clear()
    yield
