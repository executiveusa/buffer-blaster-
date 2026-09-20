import { NextRequest, NextResponse } from "next/server";

function backendBaseUrl() {
  return (process.env.BLASTER_API_URL || process.env.NEXT_PUBLIC_API_URL || "").trim().replace(/\/$/, "");
}

export async function POST(request: NextRequest) {
  const base = backendBaseUrl();
  if (!base) return NextResponse.json({ ok: false, error: "inquiry_store_unavailable" }, { status: 503 });
  const body = await request.json().catch(() => ({}));
  const forwarded = request.headers.get("x-forwarded-for") || "";
  const response = await fetch(`${base}/api/install-inquiries`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(forwarded ? { "x-forwarded-for": forwarded } : {}) },
    body: JSON.stringify(body),
    cache: "no-store",
  }).catch(() => null);
  if (!response) return NextResponse.json({ ok: false, error: "inquiry_store_unavailable" }, { status: 503 });
  const payload = await response.json().catch(() => ({ ok: false, error: "inquiry_store_failed" }));
  return NextResponse.json(payload, { status: response.ok && payload.ok ? 200 : response.status >= 400 ? response.status : 503 });
}
