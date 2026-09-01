"""Meta Marketing API adapter.

The Graph API version is runtime-configured. Buffer Blaster creates a complete
campaign -> ad set -> creative -> ad hierarchy in PAUSED state, binds every
provider id, and requires a separate human-approved activation call before any
object is moved to ACTIVE.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import ProviderMetrics


class MetaAdsProvider:
    name = "meta"
    launch_scope = "full_delivery_hierarchy"
    delivery_ready = True

    @property
    def configured(self) -> bool:
        return bool(
            os.getenv("META_ACCESS_TOKEN")
            and os.getenv("META_AD_ACCOUNT_ID")
            and os.getenv("META_GRAPH_API_VERSION")
        )

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured,
            "account_configured": bool(os.getenv("META_AD_ACCOUNT_ID")),
            "api_version_configured": bool(os.getenv("META_GRAPH_API_VERSION")),
            "launch_scope": self.launch_scope,
            "delivery_ready": self.delivery_ready,
            "live_verified": False,
            "safe_create_state": "PAUSED",
        }

    def _base(self) -> str:
        version = os.getenv("META_GRAPH_API_VERSION", "").strip()
        return f"https://graph.facebook.com/{version}"

    def _token(self) -> str:
        return os.getenv("META_ACCESS_TOKEN", "")

    def _account(self) -> str:
        return os.getenv("META_AD_ACCOUNT_ID", "").removeprefix("act_")

    @staticmethod
    def _body(response: httpx.Response) -> dict[str, Any]:
        data = response.json() if response.content else {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _form(payload: dict[str, Any]) -> dict[str, Any]:
        """Encode nested Marketing API form fields as compact JSON strings."""
        return {
            key: json.dumps(value, separators=(",", ":")) if isinstance(value, (dict, list)) else value
            for key, value in payload.items()
        }

    async def _post_object(
        self,
        client: httpx.AsyncClient,
        path: str,
        payload: dict[str, Any],
    ) -> tuple[bool, dict[str, Any], int]:
        response = await client.post(
            f"{self._base()}/{path.lstrip('/')}",
            data={**self._form(payload), "access_token": self._token()},
        )
        data = self._body(response)
        return response.is_success and bool(data.get("id")), data, response.status_code

    async def _set_status(
        self,
        client: httpx.AsyncClient,
        object_id: str,
        status: str,
    ) -> tuple[bool, int, dict[str, Any]]:
        response = await client.post(
            f"{self._base()}/{object_id}",
            data={"status": status, "access_token": self._token()},
        )
        return response.is_success, response.status_code, self._body(response)

    @staticmethod
    def _required_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
        campaign = dict(payload.get("campaign") or {})
        adset = dict(payload.get("ad_set") or payload.get("adset") or {})
        creative = dict(payload.get("creative") or {})
        ad = dict(payload.get("ad") or {})
        if not all((campaign, adset, creative, ad)):
            return None
        return campaign, adset, creative, ad

    async def create_experiment(self, payload: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "meta_not_configured"}

        parts = self._required_payload(payload)
        if not parts:
            return {
                "ok": False,
                "error": "full_delivery_payload_required",
                "required": ["campaign", "ad_set", "creative", "ad"],
            }
        campaign, adset, creative, ad = parts
        campaign["status"] = "PAUSED"
        adset["status"] = "PAUSED"
        ad["status"] = "PAUSED"

        created: dict[str, str] = {}
        receipts: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            ok, data, status = await self._post_object(client, f"act_{self._account()}/campaigns", campaign)
            receipts.append({"stage": "campaign", "ok": ok, "status": status, "response": data})
            if not ok:
                return {"ok": False, "provider": self.name, "failed_stage": "campaign", "receipts": receipts}
            created["campaign_id"] = str(data["id"])

            adset["campaign_id"] = created["campaign_id"]
            ok, data, status = await self._post_object(client, f"act_{self._account()}/adsets", adset)
            receipts.append({"stage": "ad_set", "ok": ok, "status": status, "response": data})
            if not ok:
                await self._set_status(client, created["campaign_id"], "PAUSED")
                return {"ok": False, "provider": self.name, "failed_stage": "ad_set", "external_ref": created, "receipts": receipts}
            created["adset_id"] = str(data["id"])

            ok, data, status = await self._post_object(client, f"act_{self._account()}/adcreatives", creative)
            receipts.append({"stage": "creative", "ok": ok, "status": status, "response": data})
            if not ok:
                await self._set_status(client, created["adset_id"], "PAUSED")
                await self._set_status(client, created["campaign_id"], "PAUSED")
                return {"ok": False, "provider": self.name, "failed_stage": "creative", "external_ref": created, "receipts": receipts}
            created["creative_id"] = str(data["id"])

            ad["adset_id"] = created["adset_id"]
            ad.setdefault("creative", {"creative_id": created["creative_id"]})
            ok, data, status = await self._post_object(client, f"act_{self._account()}/ads", ad)
            receipts.append({"stage": "ad", "ok": ok, "status": status, "response": data})
            if not ok:
                await self._set_status(client, created["adset_id"], "PAUSED")
                await self._set_status(client, created["campaign_id"], "PAUSED")
                return {"ok": False, "provider": self.name, "failed_stage": "ad", "external_ref": created, "receipts": receipts}
            created["ad_id"] = str(data["id"])

            readback = await client.get(
                f"{self._base()}/{created['ad_id']}",
                params={
                    "fields": "id,name,status,effective_status,adset_id,campaign_id,creative",
                    "access_token": self._token(),
                },
            )
            readback_data = self._body(readback)
            receipts.append({"stage": "readback", "ok": readback.is_success, "status": readback.status_code, "response": readback_data})
            if not readback.is_success:
                await self._set_status(client, created["ad_id"], "PAUSED")
                await self._set_status(client, created["adset_id"], "PAUSED")
                await self._set_status(client, created["campaign_id"], "PAUSED")
                return {"ok": False, "provider": self.name, "failed_stage": "readback", "external_ref": created, "receipts": receipts}

        return {
            "ok": True,
            "provider": self.name,
            "external_ref": created,
            **created,
            "state": "PAUSED",
            "receipts": receipts,
            "launch_scope": self.launch_scope,
            "delivery_ready": self.delivery_ready,
            "live_verified": False,
        }

    async def activate_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "meta_not_configured"}
        required = ["campaign_id", "adset_id", "ad_id"]
        if any(not external_ref.get(key) for key in required):
            return {"ok": False, "error": "full_delivery_reference_required", "required": required}

        receipts: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for stage, key in (("campaign", "campaign_id"), ("ad_set", "adset_id"), ("ad", "ad_id")):
                ok, status, data = await self._set_status(client, str(external_ref[key]), "ACTIVE")
                receipts.append({"stage": stage, "ok": ok, "status": status, "response": data})
                if not ok:
                    for rollback_key in ("ad_id", "adset_id", "campaign_id"):
                        if external_ref.get(rollback_key):
                            await self._set_status(client, str(external_ref[rollback_key]), "PAUSED")
                    return {"ok": False, "provider": self.name, "failed_stage": stage, "receipts": receipts, "rolled_back_to": "PAUSED"}

            readback = await client.get(
                f"{self._base()}/{external_ref['ad_id']}",
                params={"fields": "id,status,effective_status,adset_id,campaign_id", "access_token": self._token()},
            )
            data = self._body(readback)
            receipts.append({"stage": "activation_readback", "ok": readback.is_success, "status": readback.status_code, "response": data})
            if not readback.is_success:
                for rollback_key in ("ad_id", "adset_id", "campaign_id"):
                    await self._set_status(client, str(external_ref[rollback_key]), "PAUSED")
                return {"ok": False, "provider": self.name, "failed_stage": "activation_readback", "receipts": receipts, "rolled_back_to": "PAUSED"}

        return {"ok": True, "provider": self.name, "state": "ACTIVE", "external_ref": external_ref, "receipts": receipts}

    async def pause_experiment(self, external_ref: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if not approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "meta_not_configured"}
        refs = [("ad", external_ref.get("ad_id")), ("ad_set", external_ref.get("adset_id")), ("campaign", external_ref.get("campaign_id"))]
        if not any(value for _, value in refs):
            return {"ok": False, "error": "meta_delivery_reference_missing"}
        receipts = []
        async with httpx.AsyncClient(timeout=30) as client:
            for stage, object_id in refs:
                if not object_id:
                    continue
                ok, status, data = await self._set_status(client, str(object_id), "PAUSED")
                receipts.append({"stage": stage, "ok": ok, "status": status, "response": data})
        return {"ok": all(row["ok"] for row in receipts), "provider": self.name, "state": "PAUSED", "external_ref": external_ref, "receipts": receipts}

    async def read_experiment(self, external_ref: dict[str, Any]) -> dict[str, Any]:
        object_id = str(external_ref.get("ad_id") or external_ref.get("campaign_id") or "")
        if not self.configured or not object_id:
            return {"ok": False, "error": "meta_not_configured_or_reference_missing"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self._base()}/{object_id}",
                params={"fields": "id,name,status,effective_status,adset_id,campaign_id,creative", "access_token": self._token()},
            )
        return {"ok": response.is_success, "provider": self.name, "status": response.status_code, "data": self._body(response), "external_ref": external_ref}

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
