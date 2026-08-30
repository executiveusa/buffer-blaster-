import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendBaseUrl, backendHeaders, TRIAL_COOKIE, verifyTrialSession } from "@/lib/trial-session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request) {
  const store = await cookies();
  const session = verifyTrialSession(store.get(TRIAL_COOKIE)?.value);
  if (!session) return NextResponse.json({ detail: "Active paid trial required." }, { status: 401 });
  const brief = (await request.json().catch(() => null)) as Record<string, unknown> | null;
  if (!brief || typeof brief !== "object") return NextResponse.json({ detail: "Invalid brief." }, { status: 400 });

  const payload = { ...brief, wallet_id: session.walletId };
  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl()}/api/studio/ugc/factory/execute`, {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(15 * 60 * 1000),
    });
  } catch {
    return NextResponse.json({ detail: "Factory execution service could not be reached." }, { status: 502 });
  }
  const body = await response.json().catch(() => ({}));
  return NextResponse.json(body, { status: response.status, headers: { "Cache-Control": "no-store" } });
}
