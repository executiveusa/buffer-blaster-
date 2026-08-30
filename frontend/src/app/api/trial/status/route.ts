import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendBaseUrl, backendHeaders, TRIAL_COOKIE, verifyTrialSession } from "@/lib/trial-session";

export const dynamic = "force-dynamic";

export async function GET() {
  const store = await cookies();
  const session = verifyTrialSession(store.get(TRIAL_COOKIE)?.value);
  if (!session) return NextResponse.json({ ok: false, active: false }, { status: 401 });

  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl()}/api/studio/billing/wallet/${encodeURIComponent(session.walletId)}`, {
      headers: backendHeaders(),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return NextResponse.json({ ok: false, active: false, detail: "Wallet service unavailable." }, { status: 502 });
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body?.ok || !body?.wallet) return NextResponse.json({ ok: false, active: false }, { status: 401 });
  return NextResponse.json({
    ok: true,
    active: body.wallet.state === "active",
    trial: {
      offer_id: body.wallet.offer_id,
      state: body.wallet.state,
      remaining_ad_credits: body.wallet.remaining_ad_credits,
      expires_at: body.wallet.expires_at,
    },
  }, { headers: { "Cache-Control": "no-store" } });
}
