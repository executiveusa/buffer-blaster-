import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request) {
  const paymentLink = process.env.STRIPE_FOUNDING_PAYMENT_LINK?.trim();
  if (paymentLink) return NextResponse.json({ url: paymentLink });

  const secretKey = process.env.STRIPE_SECRET_KEY?.trim();
  const priceId = process.env.STRIPE_FOUNDING_PRICE_ID?.trim();
  if (!secretKey || !priceId) {
    return NextResponse.json(
      { detail: "Stripe checkout is not configured yet." },
      { status: 503 },
    );
  }

  const origin = new URL(request.url).origin;
  const form = new URLSearchParams({
    mode: "payment",
    "line_items[0][price]": priceId,
    "line_items[0][quantity]": "1",
    success_url: `${origin}/founding?checkout=success`,
    cancel_url: `${origin}/founding?checkout=cancelled`,
    allow_promotion_codes: "true",
    "metadata[offer]": "founding-creator",
  });

  const response = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: form,
    cache: "no-store",
  });

  const payload = (await response.json()) as { url?: string; error?: { message?: string } };
  if (!response.ok || !payload.url) {
    return NextResponse.json(
      { detail: payload.error?.message ?? "Stripe checkout could not be created." },
      { status: 502 },
    );
  }

  return NextResponse.json({ url: payload.url }, { headers: { "Cache-Control": "no-store" } });
}
