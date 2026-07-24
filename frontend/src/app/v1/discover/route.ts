import { NextResponse } from "next/server";
import { discoverDemoCards } from "@/lib/creator-demo";

export const dynamic = "force-dynamic";

type DiscoverBody = { intent?: unknown; limit?: unknown };

export async function POST(request: Request) {
  let body: DiscoverBody;
  try {
    body = (await request.json()) as DiscoverBody;
  } catch {
    return NextResponse.json({ detail: "invalid JSON" }, { status: 400 });
  }

  const intent = typeof body.intent === "string" ? body.intent.trim() : "";
  const rawLimit = typeof body.limit === "number" ? body.limit : 3;
  const limit = Math.max(1, Math.min(Math.trunc(rawLimit), 12));
  if (!intent) return NextResponse.json({ detail: "intent is required" }, { status: 422 });

  const upstream = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

  if (upstream && !demoMode) {
    try {
      const response = await fetch(`${upstream}/v1/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent, limit }),
        cache: "no-store",
        signal: AbortSignal.timeout(10_000),
      });
      if (response.ok) {
        return NextResponse.json(await response.json(), { status: 200 });
      }
    } catch {
      // Fall through to the bounded demo corpus so the creator surface degrades safely.
    }
  }

  const cards = discoverDemoCards(intent, limit);
  return NextResponse.json({ intent, count: cards.length, cards, mode: "demo-fallback" });
}
