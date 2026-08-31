"""Meta Marketing API adapter.

Requires explicit runtime configuration. The Graph API version is deliberately
not hardcoded so upgrades are an operator decision rather than silent drift.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import ProviderMetrics


class MetaAdsProvider:
    name = "meta"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("META_ACCESS_TOKEN") and os.getenv("META_AD_ACCOUNT_ID") and os.getenv("META_GRAPH_API_VERSION"))

    def status(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": self.configured, "account_configured": bool(os.getenv("META_AD_ACCOUNT_ID")), "api_version_configured": bool(os.getenv("META_GRAPH_API_VERSION"))}

    def _base(self) -> str:
        version = os.getenv("META_GRAPH_API_VERSION", "").strip()
        return f"https://graph.facebook.com/{version}"

    def _token(self) -> str:
        return os.getenv("META_ACCESS_TOKEN", "")

    async def create_experiment(self, payload: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "meta_not_configured"}
        campaign = dict(payload.get("campaign") or {})
        if not campaign:
            return {"ok": False, "error": "campaign_payload_required"}
        campaign.setdefault("status", "PAUSED")
        account = os.getenv("META_AD_ACCOUNT_ID", "").removeprefix("act_")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self._base()}/act_{account}/campaigns", data={**campaign, "access_token": self._token()})
        data = response.json() if response.content else {}
        return {"ok": response.is_success, "provider": self.name, "campaign_id": data.get("id"), "status": response.status_code, "response": data}

    async def pause_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        campaign_id = str(external_ref.get("campaign_id") or "")
        if not self.configured or not campaign_id:
            return {"ok": False, "error": "meta_not_configured_or_campaign_missing"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self._base()}/{campaign_id}", data={"status": "PAUSED", "access_token": self._token()})
        return {"ok": response.is_success, "provider": self.name, "campaign_id": campaign_id, "status": response.status_code}

    async def read_experiment(self, external_ref: dict[str, Any]) -> dict[str, Any]:
        campaign_id = str(external_ref.get("campaign_id") or "")
        if not self.configured or not campaign_id:
            return {"ok": False, "error": "meta_not_configured_or_campaign_missing"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self._base()}/{campaign_id}", params={"fields": "id,name,status,effective_status", "access_token": self._token()})
        return {"ok": response.is_success, "provider": self.name, "status": response.status_code, "data": response.json() if response.content else {}}

    async def get_metrics(self, external_ref: dict[str, Any], *, since: str | None = None, until: str | None = None) -> ProviderMetrics | dict[str, Any]:
        ad_id = str(external_ref.get("ad_id") or external_ref.get("campaign_id") or "")
        if not self.configured or not ad_id:
            return {"ok": False, "error": "meta_not_configured_or_ad_missing"}
        params: dict[str, Any] = {"fields": "spend,impressions,clicks,ctr,cpc,cpm,actions,action_values", "access_token": self._token()}
        if since and until:
            params["time_range"] = f'{{"since":"{since}","until":"{until}"}}'
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self._base()}/{ad_id}/insights", params=params)
        if not response.is_success:
            return {"ok": False, "error": "meta_insights_failed", "status": response.status_code}
        body = response.json()
        row = (body.get("data") or [{}])[0]
        actions = {item.get("action_type"): float(item.get("value", 0)) for item in row.get("actions", [])}
        action_values = {item.get("action_type"): float(item.get("value", 0)) for item in row.get("action_values", [])}
        metrics = {
            "spend_cents": round(float(row.get("spend", 0)) * 100, 2),
            "impressions": float(row.get("impressions", 0)),
            "clicks": float(row.get("clicks", 0)),
            "ctr": float(row.get("ctr", 0)),
            "cpc_cents": round(float(row.get("cpc", 0)) * 100, 2),
            "cpm_cents": round(float(row.get("cpm", 0)) * 100, 2),
            "purchases": actions.get("purchase", actions.get("omni_purchase", 0.0)),
            "purchase_value_cents": round(action_values.get("purchase", action_values.get("omni_purchase", 0.0)) * 100, 2),
        }
        spend = metrics["spend_cents"]
        metrics["roas"] = round(metrics["purchase_value_cents"] / spend, 4) if spend else 0.0
        return ProviderMetrics(provider=self.name, external_ad_id=ad_id, observed_at=datetime.now(timezone.utc).isoformat(), metrics=metrics, raw=row)
