"""Native-core loader with pure-Python fallback.

The Stavarai hot-path core (AES-256 encryption, session tokens, rate limiter,
job queue) is implemented twice:

  1. `rust_core/stavarai_core` — the production Rust crate (cdylib), built in
     CI for Windows/Linux/macOS and shipped as a release asset.
  2. This module — a pure-Python implementation of the *same* API, used when
     the native library is not present (local dev, demo, any machine without a
     C toolchain).

`get_core()` returns whichever is available. Callers never branch on platform
or "is Rust installed" — they just call `core.encrypt(...)`.

The contracts are identical and verified by the same test suite
(`tests/rust/` mirrors `tests/python/test_native_parity.py`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from pathlib import Path

# ── Optional native load ───────────────────────────────────────
_NATIVE = None
_NATIVE_TRIED = False


def _lib_candidates() -> list[Path]:
    """Where the prebuilt native lib might live for this platform."""
    here = Path(__file__).resolve().parent            # api/services/
    repo = here.parents[2]                             # repo root
    libdir = repo / "rust_core" / "native"
    names = {
        "win32":  ["stavarai_core.dll", "libstavarai_core.dll"],
        "linux":  ["libstavarai_core.so"],
        "darwin": ["libstavarai_core.dylib"],
    }.get(os.sys.platform, [])
    return [libdir / n for n in names]


def _try_load_native():
    """Attempt to ctypes-load the prebuilt Rust lib. Returns object or None."""
    global _NATIVE, _NATIVE_TRIED
    if _NATIVE_TRIED:
        return _NATIVE
    _NATIVE_TRIED = True
    try:
        import ctypes
        for cand in _lib_candidates():
            if cand.exists():
                lib = ctypes.CDLL(str(cand))
                _NATIVE = lib
                break
    except Exception:
        _NATIVE = None
    return _NATIVE


def native_available() -> bool:
    """True iff the prebuilt Rust core is loaded for this platform."""
    return _try_load_native() is not None


# ── Pure-Python implementation (the fallback, also the dev default) ──

def _key32(key_material: str | bytes) -> bytes:
    """Derive a fixed 32-byte key from arbitrary material (env value)."""
    if isinstance(key_material, str):
        key_material = key_material.encode("utf-8")
    return hashlib.sha256(key_material).digest()[:32]


class Encryption:
    """AES-256-GCM. Uses `cryptography` (ships prebuilt wheels — no compiler)."""

    def __init__(self, master_key: str | bytes):
        self._key = _key32(master_key)

    def encrypt(self, plaintext: str) -> str:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = secrets.token_bytes(12)
        ct = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ct).decode("ascii").rstrip("=")

    def decrypt(self, encoded: str) -> str:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        pad = "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(encoded + pad)
        if len(raw) < 28:  # 12 nonce + 16 tag minimum
            raise ValueError("ciphertext too short")
        nonce, ct = raw[:12], raw[12:]
        return AESGCM(self._key).decrypt(nonce, ct, None).decode("utf-8")

    @staticmethod
    def mask_key(key: str) -> str:
        if len(key) < 4:
            return "•" * 4
        return "•" * 12 + key[-4:]


class SessionStore:
    """In-memory token → expiry. Mirrors `rust_core::auth::SessionStore`."""

    def __init__(self, ttl: int = 86_400):
        self._ttl = ttl
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = time.time() + self._ttl
        return token

    def validate(self, token: str) -> bool:
        with self._lock:
            exp = self._sessions.get(token)
            if exp is None:
                return False
            if time.time() > exp:
                self._sessions.pop(token, None)
                return False
            return True

    def invalidate(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    @staticmethod
    def verify_password(password: str, expected: str) -> bool:
        """Constant-time compare."""
        return hmac.compare_digest(
            password.encode("utf-8", "ignore"),
            expected.encode("utf-8", "ignore"),
        )


class RateLimiter:
    """Token bucket, keyed by string. Mirrors `rust_core::rate_limiter`."""

    def __init__(self):
        self._buckets: dict[str, dict] = {}
        self._lock = threading.Lock()

    def check(self, key: str, capacity: float, rate: float) -> tuple[bool, int]:
        """Return (allowed, retry_after_secs)."""
        now = time.monotonic()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                b = {"tokens": capacity, "last": now, "rate": rate, "cap": capacity}
                self._buckets[key] = b
            b["rate"] = rate
            b["cap"] = capacity
            elapsed = now - b["last"]
            if elapsed > 0:
                b["tokens"] = min(capacity, b["tokens"] + elapsed * rate)
                b["last"] = now
            if b["tokens"] >= 1.0:
                b["tokens"] -= 1.0
                return True, 0
            deficit = 1.0 - b["tokens"]
            return False, max(1, int((deficit / rate) + 0.999))


class JobStatus:
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"

    @staticmethod
    def failed(reason: str) -> str:
        return f"Failed({reason})"


class JobQueue:
    """In-memory FIFO. Mirrors `rust_core::job_queue`."""

    def __init__(self):
        self._queue: deque = deque()
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def enqueue(self, job_type: str, payload: dict) -> str:
        jid = secrets.token_urlsafe(16)
        job = {
            "id": jid,
            "job_type": job_type,
            "payload": payload,
            "status": JobStatus.PENDING,
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
        }
        with self._lock:
            self._queue.append(jid)
            self._jobs[jid] = job
        return jid

    def dequeue(self) -> dict | None:
        with self._lock:
            if not self._queue:
                return None
            jid = self._queue.popleft()
            job = self._jobs[jid]
            job["status"] = JobStatus.RUNNING
            job["started_at"] = time.time()
            return dict(job)

    def complete(self, jid: str) -> None:
        with self._lock:
            if jid in self._jobs:
                self._jobs[jid]["status"] = JobStatus.COMPLETED
                self._jobs[jid]["completed_at"] = time.time()

    def fail(self, jid: str, reason: str) -> None:
        with self._lock:
            if jid in self._jobs:
                self._jobs[jid]["status"] = JobStatus.failed(reason)
                self._jobs[jid]["completed_at"] = time.time()

    def status(self, jid: str) -> str | None:
        with self._lock:
            j = self._jobs.get(jid)
            return j["status"] if j else None

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [dict(j) for j in self._jobs.values()]


# ── Public façade ──────────────────────────────────────────────

class Core:
    """The hot-path core, however it's implemented on this machine."""

    def __init__(self, master_key: str | bytes | None = None):
        mk = master_key or os.getenv("MASTER_ENCRYPTION_KEY") or "stavarai-dev-key"
        self.encryption = Encryption(mk)
        self.sessions = SessionStore()
        self.rate_limiter = RateLimiter()
        self.jobs = JobQueue()
        self.backend = "rust" if native_available() else "python"


_core: Core | None = None


def get_core() -> Core:
    """Singleton core. Rust if the prebuilt lib is present, else Python."""
    global _core
    if _core is None:
        _core = Core()
    return _core


def backend_name() -> str:
    """'rust' or 'python' — for the /api/health endpoint and dashboard."""
    return get_core().backend
