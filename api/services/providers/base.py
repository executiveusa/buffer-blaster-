"""Common contract for paid-media adapters.

Adapters only translate provider state into Buffer Blaster state. They do not
choose winners and they never bypass the explicit spend approval gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ProviderMetrics:
    provider: str
    external_ad_id: str
    observed_at: str
    metrics: dict[str, float]
    raw: dict[str, Any]


class AdsProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def status(self) -> dict[str, Any]: ...

    async def create_experiment(self, payload: dict[str, Any], *, approved: bool) -> dict[str, Any]: ...

    async def pause_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]: ...

    async def read_experiment(self, external_ref: dict[str, Any]) -> dict[str, Any]: ...

    async def get_metrics(
        self,
        external_ref: dict[str, Any],
        *,
        since: str | None = None,
        until: str | None = None,
    ) -> ProviderMetrics | dict[str, Any]: ...
