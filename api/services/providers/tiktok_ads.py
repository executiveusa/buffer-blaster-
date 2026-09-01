"""TikTok Marketing API adapter.

The API base URL is runtime-configured. Buffer Blaster creates a complete
campaign -> ad group -> ad hierarchy with delivery disabled, binds every
provider id, and requires a separate human-approved activation call.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import ProviderMetrics


class TikTokAdsProvider:
    name = "tiktok"
    launch_scope = "full_delivery_hierarchy"
    delivery_ready = True

    @property
    def configured(self) -> bool:
        return bool(
            os.getenv("TIKTOK_ACCESS_TOKEN")
            and os.getenv("TIKTOK_ADVERTISER_ID")
            and os.getenv("TIKTOK_API_BASE_URL")
        )

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured,
            "advertiser_configured": bool(os.getenv("TIKTOK_ADVERTISER_ID")),
            "api_base_configured": bool(os.getenv("TIKTOK_API_BASE_URL")),
            "launch_scope": self.launch_scope,
            "delivery_ready": self.delivery_ready,
            "live_verified": False,
            "safe_create_state": "DISABLE",
        }

    def _base(self) -> str:
        return os.getenv("TIKTOK_API_BASE_URL", "").rstrip("/")

    def _advertiser(self) -> str:
        return os.getenv("TIKTOK_ADVERTISER_ID", "")

    def _headers(self) -> dict[str, str]:
        return {"Access-Token": os.getenv("TIKTOK_ACCESS_TOKEN", ""), "Content-Type": "application/json"}

    @staticmethod
    def _body(response: httpx.Response) -> dict[str, Any]:
        data = response.json() if response.content else {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _success(response: httpx.Response, data: dict[str, Any]) -> bool:
        return response.is_success and data.get("code") in {0, "0", None}

    async def _post(
        self,
        client: httpx.AsyncClient,
        path: str,
        payload: dict[str, Any],
    ) -> tuple[bool, dict[str, Any], int]:
        response = await client.post(f"{self._base()}/{path.lstrip('/')}", headers=self._headers(), json=payload)
        data = self._body(response)
        return self._success(response, data), data, response.status_code

    async def _set_status(
        self,
        client: httpx.AsyncClient,
        level: str,
        object_id: str,
        operation_status: str,
    ) -> tuple[bool, int, dict[str, Any]]:
        plural = {"campaign": "campaign_ids", "adgroup": "adgroup_ids", "ad": "ad_ids"}[level]
        payload = {
            "advertiser_id": self._advertiser(),
            plural: [object_id],
            "operation_status": operation_status,
        }
        ok, data, status = await self._post(client, f"{level}/status/update/", payload)
        return ok, status, data

    @staticmethod
    def _required_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
        campaign = dict(payload.get("campaign") or {})
        adgroup = dict(payload.get("ad_group") or payload.get("adgroup") or {})
        ad = dict(payload.get("ad") or {})
        if not all((campaign, adgroup, ad)):
            return None
        return campaign, adgroup, ad

    async def create_experiment(self, payload: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "tiktok_not_configured"}

        parts = self._required_payload(payload)
        if not parts:
            return {
                "ok": False,
                "error": "full_delivery_payload_required",
                "required": ["campaign", "ad_group", "ad"],
            }
        campaign, adgroup, ad = parts
        advertiser = self._advertiser()
        campaign.setdefault("advertiser_id", advertiser)
        adgroup.setdefault("advertiser_id", advertiser)
        adgroup["operation_status"] = "DISABLE"
        ad.setdefault("advertiser_id", advertiser)
        ad["operation_status"] = "DISABLE"

        created: dict[str, str] = {}
        receipts: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            ok, data, status = await self._post(client, "campaign/create/", campaign)
            campaign_id = str(((data.get("data") or {}).get("campaign_id")) or "")
            ok = ok and bool(campaign_id)
            receipts.append({"stage": "campaign", "ok": ok, "status": status, "response": data})
            if not ok:
                return {"ok": False, "provider": self.name, "failed_stage": "campaign", "receipts": receipts}
            created["campaign_id"] = campaign_id

            disabled, disable_status, disable_data = await self._set_status(client, "campaign", campaign_id, "DISABLE")
            receipts.append({"stage": "campaign_disable", "ok": disabled, "status": disable_status, "response": disable_data})
            if not disabled:
                return {"ok": False, "provider": self.name, "failed_stage": "campaign_disable", "external_ref": created, "receipts": receipts}

            adgroup["campaign_id"] = campaign_id
            ok, data, status = await self._post(client, "adgroup/create/", adgroup)
            adgroup_id = str(((data.get("data") or {}).get("adgroup_id")) or "")
            ok = ok and bool(adgroup_id)
            receipts.append({"stage": "ad_group", "ok": ok, "status": status, "response": data})
            if not ok:
                await self._set_status(client, "campaign", campaign_id, "DISABLE")
                return {"ok": False, "provider": self.name, "failed_stage": "ad_group", "external_ref": created, "receipts": receipts}
            created["adgroup_id"] = adgroup_id

            ad["adgroup_id"] = adgroup_id
            ok, data, status = await self._post(client, "ad/create/", ad)
            ad_id = str(((data.get("data") or {}).get("ad_id")) or "")
            ok = ok and bool(ad_id)
            receipts.append({"stage": "ad", "ok": ok, "status": status, "response": data})
            if not ok:
                await self._set_status(client, "adgroup", adgroup_id, "DISABLE")
                await self._set_status(client, "campaign", campaign_id, "DISABLE")
                return {"ok": False, "provider": self.name, "failed_stage": "ad", "external_ref": created, "receipts": receipts}
            created["ad_id"] = ad_id

            readback = await client.get(
                f"{self._base()}/ad/get/",
                headers=self._headers(),
                params={
                    "advertiser_id": advertiser,
                    "filtering": f'{{"ad_ids":["{ad_id}"]}}',
                },
            )
            readback_data = self._body(readback)
            readback_ok = self._success(readback, readback_data)
            receipts.append({"stage": "readback", "ok": readback_ok, "status": readback.status_code, "response": readback_data})
            if not readback_ok:
                await self._set_status(client, "ad", ad_id, "DISABLE")
                await self._set_status(client, "adgroup", adgroup_id, "DISABLE")
                await self._set_status(client, "campaign", campaign_id, "DISABLE")
                return {"ok": False, "provider": self.name, "failed_stage": "readback", "external_ref": created, "receipts": receipts}

        return {
            "ok": True,
            "provider": self.name,
            "external_ref": created,
            **created,
            "state": "DISABLE",
            "receipts": receipts,
            "launch_scope": self.launch_scope,
            "delivery_ready": self.delivery_ready,
            "live_verified": False,
        }

    async def activate_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "tiktok_not_configured"}
        required = ["campaign_id", "adgroup_id", "ad_id"]
        if any(not external_ref.get(key) for key in required):
            return {"ok": False, "error": "full_delivery_reference_required", "required": required}

        receipts: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for level, key in (("campaign", "campaign_id"), ("adgroup", "adgroup_id"), ("ad", "ad_id")):
                ok, status, data = await self._set_status(client, level, str(external_ref[key]), "ENABLE")
                receipts.append({"stage": level, "ok": ok, "status": status, "response": data})
                if not ok:
                    for rollback_level, rollback_key in (("ad", "ad_id"), ("adgroup", "adgroup_id"), ("campaign", "campaign_id")):
                        if external_ref.get(rollback_key):
                            await self._set_status(client, rollback_level, str(external_ref[rollback_key]), "DISABLE")
                    return {"ok": False, "provider": self.name, "failed_stage": level, "receipts": receipts, "rolled_back_to": "DISABLE"}

            readback = await client.get(
                f"{self._base()}/ad/get/",
                headers=self._headers(),
                params={"advertiser_id": self._advertiser(), "filtering": f'{{"ad_ids":["{external_ref["ad_id"]}"]}}'},
            )
            data = self._body(readback)
            ok = self._success(readback, data)
            receipts.append({"stage": "activation_readback", "ok": ok, "status": readback.status_code, "response": data})
            if not ok:
                for rollback_level, rollback_key in (("ad", "ad_id"), ("adgroup", "adgroup_id"), ("campaign", "campaign_id")):
                    await self._set_status(client, rollback_level, str(external_ref[rollback_key]), "DISABLE")
                return {"ok": False, "provider": self.name, "failed_stage": "activation_readback", "receipts": receipts, "rolled_back_to": "DISABLE"}

        return {"ok": True, "provider": self.name, "state": "ENABLE", "external_ref": external_ref, "receipts": receipts}

    async def pause_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "tiktok_not_configured"}
        refs = [("ad", external_ref.get("ad_id")), ("adgroup", external_ref.get("adgroup_id")), ("campaign", external_ref.get("campaign_id"))]
        if not any(value for _, value in refs):
            return {"ok": False, "error": "tiktok_delivery_reference_missing"}
        receipts = []
        async with httpx.AsyncClient(timeout=30) as client:
            for level, object_id in refs:
                if not object_id:
                    continue
                ok, status, data = await self._set_status(client, level, str(object_id), "DISABLE")
                receipts.append({"stage": level, "ok": ok, "status": status, "response": data})
        return {"ok": all(row["ok"] for row in receipts), "provider": self.name, "state": "DISABLE", "external_ref": external_ref, "receipts": receipts}

    async def read_experiment(self, external_ref: dict[str, Any]) -> dict[str, Any]:
        ad_id = str(external_ref.get("ad_id") or "")
        campaign_id = str(external_ref.get("campaign_id") or "")
        if not self.configured or not (ad_id or campaign_id):
            return {"ok": False, "error": "tiktok_not_configured_or_reference_missing"}
        if ad_id:
            path = "ad/get/"
            filtering = f'{{"ad_ids":["{ad_id}"]}}'
        else:
            path = "campaign/get/"
            filtering = f'{{"campaign_ids":["{campaign_id}"]}}'
        params = {"advertiser_id": self._advertiser(), "filtering": filtering}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self._base()}/{path}", headers=self._headers(), params=params)
        data = self._body(response)
        return {"ok": self._success(response, data), "provider": self.name, "status": response.status_code, "data": data, "external_ref": external_ref}

    async def get_metrics(self, external_ref: dict[str, Any], *, since: str | None = None, until: str | None = None) -> ProviderMetrics | dict[str, Any]:
        ad_id = str(external_ref.get("ad_id") or external_ref.get("campaign_id") or "")
        if not self.configured or not ad_id:
            return {"ok": False, "error": "tiktok_not_configured_or_ad_missing"}
        dimensions = ["ad_id"] if external_ref.get("ad_id") else ["campaign_id"]
        metrics = ["spend", "impressions", "clicks", "ctr", "cpc", "cpm", "conversion", "total_purchase_value"]
        params: dict[str, Any] = {
            "advertiser_id": self._advertiser(),
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
