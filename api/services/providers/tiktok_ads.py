"""TikTok Marketing API adapter.

The API base URL is runtime-configured to avoid silently pinning an obsolete
version. All spend-changing calls remain human-gated.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import ProviderMetrics


class TikTokAdsProvider:
    name = "tiktok"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("TIKTOK_ACCESS_TOKEN") and os.getenv("TIKTOK_ADVERTISER_ID") and os.getenv("TIKTOK_API_BASE_URL"))

    def status(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": self.configured, "advertiser_configured": bool(os.getenv("TIKTOK_ADVERTISER_ID")), "api_base_configured": bool(os.getenv("TIKTOK_API_BASE_URL"))}

    def _base(self) -> str:
        return os.getenv("TIKTOK_API_BASE_URL", "").rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Access-Token": os.getenv("TIKTOK_ACCESS_TOKEN", ""), "Content-Type": "application/json"}

    async def create_experiment(self, payload: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "tiktok_not_configured"}
        campaign = dict(payload.get("campaign") or {})
        if not campaign:
            return {"ok": False, "error": "campaign_payload_required"}
        campaign.setdefault("advertiser_id", os.getenv("TIKTOK_ADVERTISER_ID"))
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self._base()}/campaign/create/", headers=self._headers(), json=campaign)
        data = response.json() if response.content else {}
        campaign_id = ((data.get("data") or {}).get("campaign_id")) if isinstance(data, dict) else None
        return {"ok": response.is_success and data.get("code") in {0, "0", None}, "provider": self.name, "campaign_id": campaign_id, "status": response.status_code, "response": data}

    async def pause_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        campaign_id = str(external_ref.get("campaign_id") or "")
        if not self.configured or not campaign_id:
            return {"ok": False, "error": "tiktok_not_configured_or_campaign_missing"}
        body = {"advertiser_id": os.getenv("TIKTOK_ADVERTISER_ID"), "campaign_ids": [campaign_id], "operation_status": "DISABLE"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self._base()}/campaign/status/update/", headers=self._headers(), json=body)
        data = response.json() if response.content else {}
        return {"ok": response.is_success and data.get("code") in {0, "0", None}, "provider": self.name, "campaign_id": campaign_id, "status": response.status_code, "response": data}

    async def read_experiment(self, external_ref: dict[str, Any]) -> dict[str, Any]:
        campaign_id = str(external_ref.get("campaign_id") or "")
        if not self.configured or not campaign_id:
            return {"ok": False, "error": "tiktok_not_configured_or_campaign_missing"}
        params = {"advertiser_id": os.getenv("TIKTOK_ADVERTISER_ID"), "filtering": f'{{"campaign_ids":["{campaign_id}"]}}'}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self._base()}/campaign/get/", headers=self._headers(), params=params)
        return {"ok": response.is_success, "provider": self.name, "status": response.status_code, "data": response.json() if response.content else {}}

    async def get_metrics(self, external_ref: dict[str, Any], *, since: str | None = None, until: str | None = None) -> ProviderMetrics | dict[str, Any]:
        ad_id = str(external_ref.get("ad_id") or external_ref.get("campaign_id") or "")
        if not self.configured or not ad_id:
            return {"ok": False, "error": "tiktok_not_configured_or_ad_missing"}
        dimensions = ["ad_id"] if external_ref.get("ad_id") else ["campaign_id"]
        metrics = ["spend", "impressions", "clicks", "ctr", "cpc", "cpm", "conversion", "total_purchase_value"]
        params: dict[str, Any] = {
            "advertiser_id": os.getenv("TIKTOK_ADVERTISER_ID"),
            "report_type": "BASIC",
            "data_level": "AUCTION_AD" if external_ref.get("ad_id") else "AUCTION_CAMPAIGN",
            "dimensions": str(dimensions).replace("'", '"'),
            "metrics": str(metrics).replace("'", '"'),
            "filtering": f'{{"{dimensions[0]}":["{ad_id}"]}}',
        }
        if since:
            params["start_date"] = since
        if until:
            params["end_date"] = until
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self._base()}/report/integrated/get/", headers=self._headers(), params=params)
        if not response.is_success:
            return {"ok": False, "error": "tiktok_report_failed", "status": response.status_code}
        body = response.json()
        rows = ((body.get("data") or {}).get("list") or []) if isinstance(body, dict) else []
        row = rows[0].get("metrics", {}) if rows else {}
        normalized = {
            "spend_cents": round(float(row.get("spend", 0)) * 100, 2),
            "impressions": float(row.get("impressions", 0)),
            "clicks": float(row.get("clicks", 0)),
            "ctr": float(row.get("ctr", 0)),
            "cpc_cents": round(float(row.get("cpc", 0)) * 100, 2),
            "cpm_cents": round(float(row.get("cpm", 0)) * 100, 2),
            "purchases": float(row.get("conversion", 0)),
            "purchase_value_cents": round(float(row.get("total_purchase_value", 0)) * 100, 2),
        }
        spend = normalized["spend_cents"]
        normalized["roas"] = round(normalized["purchase_value_cents"] / spend, 4) if spend else 0.0
        return ProviderMetrics(provider=self.name, external_ad_id=ad_id, observed_at=datetime.now(timezone.utc).isoformat(), metrics=normalized, raw=row)
