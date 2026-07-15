"""Parity tests: the pure-Python core must satisfy the same contracts as the
Rust crate. These run on any machine with Python — no C toolchain required —
so the hot-path behaviour is verifiable everywhere. When the prebuilt Rust lib
is present, `get_core()` uses it instead and these same tests cover it too.

Mirrors: rust_core/stavarai_core/tests/{encryption,auth,rate_limiter,job_queue}.rs
"""
from __future__ import annotations

import time

import pytest

from api.services.native import Encryption, JobQueue, JobStatus, RateLimiter, SessionStore

TEST_KEY = "stavarai-test-key"


# ── Encryption ────────────────────────────────────────────────────

class TestEncryption:
    def setup_method(self):
        self.enc = Encryption(TEST_KEY)

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "sk-ant-test-api-key-1234567890"
        ct = self.enc.encrypt(plaintext)
        assert self.enc.decrypt(ct) == plaintext

    def test_ciphertext_is_not_plaintext(self):
        plaintext = "sk-ant-test-api-key-1234567890"
        ct = self.enc.encrypt(plaintext)
        assert ct != plaintext
        assert "sk-ant" not in ct

    def test_wrong_key_fails(self):
        ct = Encryption(TEST_KEY).encrypt("secret")
        with pytest.raises(Exception):
            Encryption("wrong-key").decrypt(ct)

    def test_mask_shows_last_4(self):
        masked = Encryption.mask_key("sk-ant-api03-abcdefghijklmnop-1234")
        assert masked.endswith("1234")
        assert "•" in masked
        assert "sk-ant" not in masked

    def test_random_nonce_different_ciphertext(self):
        p = "same-plaintext"
        c1 = self.enc.encrypt(p)
        c2 = self.enc.encrypt(p)
        assert c1 != c2
        assert self.enc.decrypt(c1) == self.enc.decrypt(c2) == p

    def test_empty_plaintext_roundtrips(self):
        ct = self.enc.encrypt("")
        assert self.enc.decrypt(ct) == ""

    def test_malformed_ciphertext_errors(self):
        with pytest.raises(Exception):
            self.enc.decrypt("not-valid-base64!!!")
        with pytest.raises(Exception):
            self.enc.decrypt("")


# ── Auth / sessions ───────────────────────────────────────────────

class TestSessionStore:
    def setup_method(self):
        self.store = SessionStore()

    def test_token_is_long_and_url_safe(self):
        token = self.store.issue()
        assert len(token) >= 43
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_tokens_are_unique(self):
        assert self.store.issue() != self.store.issue()

    def test_correct_password_verifies(self):
        assert self.store.verify_password("BLASTER2026", "BLASTER2026") is True

    def test_wrong_password_rejected(self):
        assert self.store.verify_password("wrong", "BLASTER2026") is False

    def test_issued_token_validates(self):
        token = self.store.issue()
        assert self.store.validate(token) is True

    def test_random_token_does_not_validate(self):
        assert self.store.validate("not-a-real-token") is False
        assert self.store.validate("") is False

    def test_logout_invalidates(self):
        token = self.store.issue()
        assert self.store.validate(token)
        self.store.invalidate(token)
        assert not self.store.validate(token)


# ── Rate limiter ──────────────────────────────────────────────────

class TestRateLimiter:
    def test_allows_then_blocks(self):
        rl = RateLimiter()
        for _ in range(5):
            ok, _ = rl.check("ip:1.2.3.4", 5.0, 5.0 / 60.0)
            assert ok
        ok, retry = rl.check("ip:1.2.3.4", 5.0, 5.0 / 60.0)
        assert not ok
        assert retry > 0

    def test_independent_keys(self):
        rl = RateLimiter()
        for _ in range(3):
            ok, _ = rl.check("a", 3.0, 1.0)
            assert ok
        assert rl.check("a", 3.0, 1.0)[0] is False
        assert rl.check("b", 3.0, 1.0)[0] is True

    def test_bucket_refills(self):
        rl = RateLimiter()
        rl.check("k", 1.0, 100.0)  # drain
        assert rl.check("k", 1.0, 100.0)[0] is False
        time.sleep(0.02)  # 20ms → 2 tokens at 100/s
        assert rl.check("k", 1.0, 100.0)[0] is True


# ── Job queue ────────────────────────────────────────────────────

class TestJobQueue:
    def setup_method(self):
        self.q = JobQueue()

    def test_enqueue_returns_id(self):
        assert self.q.enqueue("pipeline_run", {"client": "a"})

    def test_dequeue_returns_running_job(self):
        jid = self.q.enqueue("pipeline_run", {"client": "a"})
        job = self.q.dequeue()
        assert job["id"] == jid
        assert job["job_type"] == "pipeline_run"
        assert job["status"] == JobStatus.RUNNING

    def test_fifo_order(self):
        a = self.q.enqueue("a", {})
        b = self.q.enqueue("b", {})
        c = self.q.enqueue("c", {})
        assert self.q.dequeue()["id"] == a
        assert self.q.dequeue()["id"] == b
        assert self.q.dequeue()["id"] == c

    def test_dequeue_empty_returns_none(self):
        assert self.q.dequeue() is None

    def test_complete(self):
        jid = self.q.enqueue("t", {})
        self.q.dequeue()
        self.q.complete(jid)
        assert self.q.status(jid) == JobStatus.COMPLETED

    def test_fail_with_reason(self):
        jid = self.q.enqueue("t", {})
        self.q.dequeue()
        self.q.fail(jid, "timeout")
        assert "Failed(timeout)" in self.q.status(jid)

    def test_unique_ids(self):
        assert self.q.enqueue("t", {}) != self.q.enqueue("t", {})

    def test_payload_preserved(self):
        payload = {"client": "x", "niche": "food-beverage", "n_posts": 15}
        jid = self.q.enqueue("pipeline_run", payload)
        assert self.q.dequeue()["payload"] == payload
