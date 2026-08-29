import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendBaseUrl, backendHeaders, signTrialSession, TRIAL_COOKIE } from "@/lib/trial-session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request) {
  const input = (await request.json().catch(() => ({}))) as { session_id?: string };
  const sessionId = String(input.session_id || "");
  if (!sessionId.startsWith("cs_")) return NextResponse.json({ detail: "Invalid checkout session." }, { status: 400 });

  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl()}/api/studio/billing/activate`, {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify({ checkout_session_id: sessionId }),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    return NextResponse.json({ detail: "Trial activation service could not be reached." }, { status: 502 });
  }
  const body = (await response.json().catch(() => ({}))) as {
    ok?: boolean;
    error?: string;
    wallet?: { id: string; offer_id: string; expires_at?: string | null; remaining_ad_credits: number; remaining_provider_budget_cents: number; state: string };
  };
  if (!response.ok || !body.ok || !body.wallet) {
    return NextResponse.json({ detail: body.error || "Trial activation failed." }, { status: response.status >= 400 ? response.status : 400 });
  }

  const expires = body.wallet.expires_at ? Math.floor(new Date(body.wallet.expires_at).getTime() / 1000) : Math.floor(Date.now() / 1000) + 7 * 86400;
  const token = signTrialSession({ walletId: body.wallet.id, offerId: body.wallet.offer_id, exp: expires });
  const store = await cookies();
  store.set(TRIAL_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(expires * 1000),
  });

  return NextResponse.json({
    ok: true,
    trial: {
      offer_id: body.wallet.offer_id,
      state: body.wallet.state,
      remaining_ad_credits: body.wallet.remaining_ad_credits,
      expires_at: body.wallet.expires_at,
    },
  }, { headers: { "Cache-Control": "no-store" } });
}
