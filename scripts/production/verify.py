#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def health() -> None:
    env = load_env(ROOT / ".env.production")
    domain = os.getenv("API_DOMAIN") or env.get("API_DOMAIN")
    if not domain:
        fail("API_DOMAIN is not configured")
    url = domain if domain.startswith("http") else f"https://{domain}"
    with urllib.request.urlopen(f"{url.rstrip('/')}/api/health", timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
    if body.get("status") != "ok":
        fail(f"public health status is {body.get('status')!r}")
    platform = str(body.get("platform") or body.get("service") or "").strip().lower().replace("_", "-")
    if platform not in {"buffer blaster", "buffer-blaster"}:
        fail(f"public platform identity is still {platform!r}")
    ledger = body.get("ledger") or {}
    if ledger.get("backend") != "supabase" or ledger.get("persistent") is not True or ledger.get("canonical") is not True:
        fail(f"public ledger contract is not canonical persistent Supabase: {ledger!r}")
    if body.get("approval_gate") is not True:
        fail("public health does not prove approval_gate=true")
    print("PUBLIC_HEALTH_OK")


def provider_report(path: Path) -> None:
    if not path.exists():
        fail(f"provider report missing: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    for key in (
        "meta_access_token",
        "tiktok_access_token",
        "shopify_admin_access_token",
        "shopify_webhook_secret",
        "supabase_service_key",
    ):
        for match in re.finditer(rf"(?im)^\s*{re.escape(key)}\s*[:=]\s*(.+)$", text):
            value = match.group(1).strip().strip("`'")
            if value and value.lower() not in {"present", "configured", "redacted", "[redacted]", "true", "false"}:
                fail(f"report appears to expose {key}")
    if "live_verified" not in lowered:
        fail("provider report has no live_verified field")
    if not re.search(r"live_verified[^\n|]*(?:\||:|=)\s*(?:true|pass|yes)", lowered):
        # Markdown tables normally put the value in a later pipe-separated cell, so accept any verified true row.
        if "| true |" not in lowered and "live_verified=true" not in lowered and "live_verified: true" not in lowered:
            fail("no provider is live_verified=true; first production provider subset is unresolved")
    if "recommend" not in lowered or "provider" not in lowered:
        fail("report does not contain a recommended provider subset")
    if "zero spend" not in lowered and "no-spend" not in lowered and "no spend" not in lowered:
        fail("report does not state zero-spend proof")
    print("PROVIDER_REPORT_OK")


def run(cmd: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)


def runtime() -> None:
    ps = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], timeout=15)
    if ps.returncode:
        fail(ps.stderr.strip() or "docker ps failed")
    rows = ps.stdout.lower()
    api_name = next((line.split()[0] for line in ps.stdout.splitlines() if "api" in line.lower() and "healthy" in line.lower()), None)
    worker_name = next((line.split()[0] for line in ps.stdout.splitlines() if "money-loop-worker" in line.lower() and "up" in line.lower()), None)
    if not api_name:
        fail(f"healthy API container not found: {rows}")
    if not worker_name:
        fail(f"running money-loop worker not found: {rows}")
    probe = run([
        "docker", "exec", api_name, "python3", "-c",
        "import os,httpx; u=os.environ['SUPABASE_URL']; k=os.environ['SUPABASE_SERVICE_KEY']; h={'apikey':k,'Authorization':'Bearer '+k,'Accept-Profile':'buffer_blaster'}; r=httpx.get(u+'/rest/v1/workspaces?select=id&limit=1',headers=h,timeout=5); assert r.status_code==200,r.status_code; print('POSTGREST_OK')",
    ], timeout=20)
    if probe.returncode or "POSTGREST_OK" not in probe.stdout:
        fail("API container cannot prove authenticated self-hosted PostgREST access")
    print("RUNTIME_OK")


def identity() -> None:
    roots = [ROOT / "frontend" / "app", ROOT / "frontend" / "components"]
    files = [ROOT / "api" / "app.py"]
    for root in roots:
        if root.exists():
            files.extend(p for p in root.rglob("*") if p.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".md", ".mdx"})
    violations: list[str] = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for forbidden in ("stavarai", "postatees"):
            if forbidden in text:
                violations.append(f"{path.relative_to(ROOT)}:{forbidden}")
    if violations:
        fail("user-facing legacy identity remains: " + ", ".join(violations[:20]))
    print("IDENTITY_OK")


def prd(path: Path) -> None:
    if not path.exists():
        fail(f"PRD missing: {path}")
    pending = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.lstrip().startswith("- [ ]")]
    if pending:
        fail(f"{len(pending)} production PRD tasks remain unchecked")
    print("PRD_COMPLETE_OK")


def gauntlet(path: Path) -> None:
    if not path.exists():
        fail(f"gauntlet receipt missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    reference = str(data.get("reference_url", "")).lower()
    if "adpanel.io" not in reference:
        fail("gauntlet receipt does not use AdPanel as the named reference")
    if data.get("critic_independent") is not True:
        fail("gauntlet critic is not recorded as independent")
    if data.get("desktop_compared") is not True or data.get("mobile_compared") is not True:
        fail("gauntlet did not compare both desktop and mobile")
    winner = str(data.get("winner", "")).strip().lower().replace("_", "-")
    if winner not in {"buffer-blaster", "ours"}:
        fail(f"independent critic did not pick Buffer Blaster: {winner!r}")
    remaining = data.get("remaining_differences") or []
    for item in remaining:
        if not isinstance(item, dict) or item.get("non_applicable") is not True or not item.get("reason"):
            fail("remaining gauntlet differences must be explicitly non-applicable with a reason")
    print("FINAL_GAUNTLET_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    p_report = sub.add_parser("provider-report")
    p_report.add_argument("path")
    sub.add_parser("runtime")
    sub.add_parser("identity")
    p_prd = sub.add_parser("prd")
    p_prd.add_argument("path")
    p_gauntlet = sub.add_parser("gauntlet")
    p_gauntlet.add_argument("path")
    args = parser.parse_args()

    if args.command == "health":
        health()
    elif args.command == "provider-report":
        provider_report(Path(args.path))
    elif args.command == "runtime":
        runtime()
    elif args.command == "identity":
        identity()
    elif args.command == "prd":
        prd(Path(args.path))
    elif args.command == "gauntlet":
        gauntlet(Path(args.path))


if __name__ == "__main__":
    main()
