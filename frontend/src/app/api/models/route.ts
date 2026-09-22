import { NextResponse } from "next/server";
import { backendBaseUrl, backendHeaders } from "@/lib/trial-session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl()}/api/studio/providers/models`, {
      headers: backendHeaders(),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return NextResponse.json({ detail: "Model list service could not be reached." }, { status: 502 });
  }
  const body = await response.json().catch(() => ({}));
  return NextResponse.json(body, { status: response.status, headers: { "Cache-Control": "no-store" } });
}
