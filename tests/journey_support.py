"""Shared fakes for the journey-truth walk.

These fakes replace ONLY the paid/external boundary (media provider, asset
storage, ffmpeg ops, Redis wallet store, durable ledger) so the A-to-Z journey
can be proven without spend. Route logic, approval gates, wallet economics,
idempotency, and executor state machines all run for real.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

TEST_OPERATOR_KEY = "journey-walk-operator-key"


class FakeRedis:
    """In-memory async Redis subset covering the usage-wallet commands.

    ``eval`` mirrors the reserve Lua script semantics exactly; anything else
    raises so an unexpected command can never pass silently.
    """

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hset(self, key: str, field: str | None = None, value: Any = None, mapping: dict | None = None) -> int:
        h = self.hashes.setdefault(key, {})
        if mapping:
            h.update({str(k): str(v) for k, v in mapping.items()})
        elif field is not None:
            h[str(field)] = str(value)
        return 1

    async def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    async def hincrby(self, key: str, field: str, amount: int) -> int:
        h = self.hashes.setdefault(key, {})
        h[field] = str(int(h.get(field, "0")) + int(amount))
        return int(h[field])

    async def get(self, key: str) -> str | None:
        return self.strings.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> Any:
        if nx and key in self.strings:
            return None
        self.strings[key] = str(value)
        return True

    async def exists(self, key: str) -> int:
        return int(key in self.hashes or key in self.strings)

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    def pipeline(self, transaction: bool = True) -> "FakePipeline":
        return FakePipeline(self)

    async def eval(self, script: str, numkeys: int, *args: Any) -> list:
        key, reservation_key = str(args[0]), str(args[1])
        now_epoch, cost, credits_needed = int(args[2]), int(args[3]), int(args[4])
        if not await self.exists(key):
            return ["ERR", "wallet_not_found"]
        if reservation_key and await self.exists(reservation_key):
            prev_cost = int(await self.hget(reservation_key, "estimated_provider_cost_cents") or "-1")
            prev_credits = int(await self.hget(reservation_key, "ad_credits_required") or "-1")
            if prev_cost != cost or prev_credits != credits_needed:
                return ["ERR", "reservation_idempotency_conflict"]
            return [
                "REPLAY",
                await self.hget(reservation_key, "remaining_provider_budget_after_cents") or "0",
                await self.hget(reservation_key, "remaining_ad_credits_after") or "0",
            ]
        state = await self.hget(key, "state") or ""
        if state != "active":
            return ["ERR", "wallet_not_active"]
        expires_at = int(await self.hget(key, "expires_at_epoch") or "0")
        if expires_at > 0 and expires_at <= now_epoch:
            await self.hset(key, "state", "expired")
            return ["ERR", "wallet_expired"]
        budget = int(await self.hget(key, "remaining_provider_budget_cents") or "0")
        credits = int(await self.hget(key, "remaining_ad_credits") or "0")
        if budget < cost:
            return ["ERR", "provider_budget_exceeded", str(budget), str(credits)]
        if credits < credits_needed:
            return ["ERR", "ad_credits_exhausted", str(budget), str(credits)]
        new_budget = await self.hincrby(key, "remaining_provider_budget_cents", -cost)
        new_credits = await self.hincrby(key, "remaining_ad_credits", -credits_needed)
        await self.hset(key, "updated_at_epoch", str(now_epoch))
        if reservation_key:
            await self.hset(reservation_key, mapping={
                "estimated_provider_cost_cents": str(cost),
                "ad_credits_required": str(credits_needed),
                "remaining_provider_budget_after_cents": str(new_budget),
                "remaining_ad_credits_after": str(new_credits),
                "created_at_epoch": str(now_epoch),
            })
        return ["OK", str(new_budget), str(new_credits)]

    async def aclose(self) -> None:
        return None


class FakePipeline:
    def __init__(self, client: FakeRedis) -> None:
        self.client = client
        self.ops: list = []

    def hset(self, key: str, mapping: dict | None = None) -> "FakePipeline":
        self.ops.append(("hset", key, mapping))
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        self.ops.append(("expire", key, seconds))
        return self

    def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> "FakePipeline":
        self.ops.append(("set", key, value, nx))
        return self

    async def execute(self) -> list:
        results = []
        for op in self.ops:
            if op[0] == "hset":
                results.append(await self.client.hset(op[1], mapping=op[2]))
            elif op[0] == "expire":
                results.append(await self.client.expire(op[1], op[2]))
            elif op[0] == "set":
                results.append(await self.client.set(op[1], op[2], nx=op[3]))
        return results


class JourneyFakeProvider:
    """Media provider double: configured, no network, deterministic output."""

    def __init__(self) -> None:
        self.calls = 0
        self.configured = True

    def status(self) -> dict[str, Any]:
        return {"configured": True, "provider": "journey-fake", "paid": False}

    async def submit_video(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        return {
            "ok": True,
            "provider": "journey-fake",
            "model": "fake/model",
            "request_id": f"req-{self.calls}",
            "response_url": f"https://provider.example/response/{self.calls}",
            "status_url": f"https://provider.example/status/{self.calls}",
        }

    async def fetch_url(self, url: str) -> dict[str, Any]:
        clip = "clip2" if url.endswith("/2") else "clip1"
        return {"ok": True, "data": {"status": "COMPLETED", "video": {"url": f"https://cdn.example/{clip}.mp4"}}}


class JourneyFakeStorage:
    def __init__(self) -> None:
        self.configured = True

    def status(self) -> dict[str, Any]:
        return {"configured": True, "backend": "journey-fake"}

    async def download_url(self, url: str, destination: Path) -> dict[str, Any]:
        destination.write_bytes(b"fake-video-bytes")
        return {"ok": True, "path": str(destination), "source_url": url}

    async def upload_file(self, source: Path, *, object_name: str, content_type: str) -> dict[str, Any]:
        return {"ok": True, "path": object_name, "signed_url": f"https://storage.example/{object_name}", "backend": "journey-fake"}


class JourneyFakeMediaOps:
    def available(self) -> bool:
        return True

    def trim_tail(self, source: Path, destination: Path, seconds: float = 0.35) -> dict[str, Any]:
        destination.write_bytes(b"trimmed")
        return {"ok": True, "path": str(destination)}

    def extract_last_frame(self, source: Path, destination: Path) -> dict[str, Any]:
        destination.write_bytes(b"seed")
        return {"ok": True, "path": str(destination)}

    def extract_first_frame(self, source: Path, destination: Path) -> dict[str, Any]:
        destination.write_bytes(b"first")
        return {"ok": True, "path": str(destination)}

    def seam_diff(self, left: Path, right: Path) -> float:
        return 0.01

    def stitch(self, first: Path, second: Path, destination: Path) -> dict[str, Any]:
        destination.write_bytes(b"final")
        return {"ok": True, "path": str(destination), "audio": True}


class InMemoryLedger:
    """Durable-ledger double recording every state transition for assertions."""

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}
        self.transitions: list[tuple[str, str]] = []

    async def create_job(self, **kwargs: Any) -> dict[str, Any]:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        record = {"id": job_id, **kwargs}
        self.jobs[job_id] = record
        self.transitions.append((job_id, str(kwargs.get("state") or "unknown")))
        return record

    async def update_job(self, job_id: str, **changes: Any) -> dict[str, Any]:
        record = self.jobs.setdefault(job_id, {"id": job_id})
        record.update(changes)
        self.transitions.append((job_id, str(changes.get("state") or "update")))
        return record


def patch_journey_boundary(*, target_modules: list[str] | None = None) -> dict[str, Any]:
    """Patch the paid/external boundary in-process. Returns the doubles."""
    import api.routers.studio as studio_router
    import api.services.ugc_executor as executor
    import api.services.usage_wallet as wallet

    provider = JourneyFakeProvider()
    storage = JourneyFakeStorage()
    media_ops = JourneyFakeMediaOps()
    ledger = InMemoryLedger()
    redis = FakeRedis()

    studio_router.get_media_provider = lambda: provider  # type: ignore[assignment]
    studio_router.get_asset_storage = lambda: storage  # type: ignore[assignment]
    studio_router.get_media_ops = lambda: media_ops  # type: ignore[assignment]
    executor.get_media_provider = lambda: provider  # type: ignore[assignment]
    executor.get_asset_storage = lambda: storage  # type: ignore[assignment]
    executor.get_media_ops = lambda: media_ops  # type: ignore[assignment]
    executor.create_job = ledger.create_job  # type: ignore[assignment]
    executor.update_job = ledger.update_job  # type: ignore[assignment]
    wallet._client = lambda: redis  # type: ignore[assignment]

    return {"provider": provider, "storage": storage, "media_ops": media_ops, "ledger": ledger, "redis": redis}
