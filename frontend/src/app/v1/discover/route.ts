import { NextResponse } from "next/server";
import { discoverDemoCards } from "@/lib/creator-demo";

export const dynamic = "force-dynamic";

// Phase 8 intentionally serves the bundled provenance-verified corpus as the
// production source of truth. The FastAPI service still contains only the
// older curated catalog, so proxying it would silently hide imported cards.
// A later bounded phase can restore upstream proxying after both indexes share
// the same generated verified-corpus artifact.
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

  const cards = discoverDemoCards(intent, limit);
  return NextResponse.json({ intent, count: cards.length, cards, mode: "verified-library" });
}
