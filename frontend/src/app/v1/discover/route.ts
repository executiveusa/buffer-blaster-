import { NextResponse } from "next/server";
import { discoverCreatorCards } from "@/lib/creator-search";

export const dynamic = "force-dynamic";

type DiscoverBody = { intent?: unknown; limit?: unknown };

export async function POST(request: Request) {
  let body: DiscoverBody;
  try { body = (await request.json()) as DiscoverBody; }
  catch { return NextResponse.json({ detail: "invalid JSON" }, { status: 400 }); }

  const intent = typeof body.intent === "string" ? body.intent.trim() : "";
  const rawLimit = typeof body.limit === "number" ? body.limit : 3;
  const limit = Math.max(1, Math.min(Math.trunc(rawLimit), 12));
  if (!intent) return NextResponse.json({ detail: "intent is required" }, { status: 422 });

  const cards = discoverCreatorCards(intent, limit);
  return NextResponse.json({ intent, count: cards.length, cards, mode: "verified-hybrid-library" }, { headers: { "Cache-Control": "no-store" } });
}
