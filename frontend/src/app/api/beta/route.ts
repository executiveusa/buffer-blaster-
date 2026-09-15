import { NextResponse } from "next/server";
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({})) as { email?: string };
  const email = String(body.email || "").trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) return NextResponse.json({ detail: "Enter a valid email." }, { status: 400 });
  const endpoint = process.env.BETA_WAITLIST_ENDPOINT?.trim();
  if (!endpoint) return NextResponse.json({ detail: "The beta list is not connected yet." }, { status: 503 });
  const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, source: "buffer-blaster" }), cache: "no-store", signal: AbortSignal.timeout(10_000) }).catch(() => null);
  if (!response?.ok) return NextResponse.json({ detail: "Could not join the beta list." }, { status: 502 });
  return NextResponse.json({ ok: true });
}
