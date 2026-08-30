import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const OFFERS = {
  "trial-7": { priceEnv: "STRIPE_TRIAL_7_PRICE_ID", linkEnv: "STRIPE_TRIAL_7_PAYMENT_LINK", mode: "payment" },
  "trial-30": { priceEnv: "STRIPE_TRIAL_30_PRICE_ID", linkEnv: "STRIPE_TRIAL_30_PAYMENT_LINK", mode: "payment" },
  "starter-monthly": { priceEnv: "STRIPE_STARTER_PRICE_ID", linkEnv: "STRIPE_STARTER_PAYMENT_LINK", mode: "subscription" },
  "pro-monthly": { priceEnv: "STRIPE_PRO_PRICE_ID", linkEnv: "STRIPE_PRO_PAYMENT_LINK", mode: "subscription" },
} as const;

type OfferId = keyof typeof OFFERS;

function isOfferId(value: string): value is OfferId {
  return value in OFFERS;
}

export async function POST(request: Request) {
  const input = (await request.json().catch(() => ({}))) as { offer?: string };
  const offer = String(input.offer || "");
  if (!isOfferId(offer)) return NextResponse.json({ detail: "Unknown offer." }, { status: 400 });

  const config = OFFERS[offer];
  const paymentLink = process.env[config.linkEnv]?.trim();
  if (paymentLink) return NextResponse.json({ url: paymentLink, offer });

  const secretKey = process.env.STRIPE_SECRET_KEY?.trim();
  const priceId = process.env[config.priceEnv]?.trim();
  const siteUrl = process.env.SITE_URL?.trim().replace(/\/$/, "");
  if (!secretKey || !priceId || !siteUrl) {
    return NextResponse.json({ detail: `Stripe checkout is not configured for ${offer}.` }, { status: 503 });
  }

  const successUrl = `${siteUrl}/studio/create?checkout=success&session_id={CHECKOUT_SESSION_ID}`;
  const cancelUrl = `${siteUrl}/pricing?checkout=cancelled&offer=${encodeURIComponent(offer)}`;
  const form = new URLSearchParams({
    mode: config.mode,
    "line_items[0][price]": priceId,
    "line_items[0][quantity]": "1",
    success_url: successUrl,
    cancel_url: cancelUrl,
    allow_promotion_codes: "true",
    "metadata[offer]": offer,
  });

  let response: Response;
  try {
    response = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: { Authorization: `Bearer ${secretKey}`, "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return NextResponse.json({ detail: "Stripe checkout could not be reached." }, { status: 502 });
  }

  const payload = (await response.json().catch(() => ({}))) as { url?: string; error?: { message?: string } };
  if (!response.ok || !payload.url) {
    return NextResponse.json({ detail: payload.error?.message ?? "Stripe checkout could not be created." }, { status: 502 });
  }
  return NextResponse.json({ url: payload.url, offer }, { headers: { "Cache-Control": "no-store" } });
}
