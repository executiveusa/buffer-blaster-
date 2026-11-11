"""S4 usage API: spend ledger reads (any authenticated identity incl. viewer)."""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, Response

from ..services.integration_auth import verify_operator
from ..services import usage_ledger

router = APIRouter(prefix="/api/studio", tags=["studio"])

_COLUMNS = ["group", "events", "estimated_cents", "actual_cents",
            "actual_reported_events", "tokens_in", "tokens_out", "wallet_credits"]


def _csv_safe(value):
    """Spreadsheet formula-injection guard: neutralize = + - @ and control
    prefixes so opening the CSV cannot execute a cell."""
    text = str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


@router.get("/usage")
async def get_usage(group_by: str = "day", format: str = "json",
                    identity: str = Depends(verify_operator)) -> Any:
    report = await usage_ledger.usage_report(group_by=group_by)
    if not report.get("ok"):
        return report
    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({k: _csv_safe(row[k]) for k in _COLUMNS})
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=usage.csv"})
    return report
