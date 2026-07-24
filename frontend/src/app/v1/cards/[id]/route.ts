import { NextResponse } from "next/server";
import { ALL_CREATOR_CARDS } from "@/lib/creator-catalog";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const card = ALL_CREATOR_CARDS.find((item) => item.id === id);
  if (!card) return NextResponse.json({ detail: "card not found" }, { status: 404 });
  return NextResponse.json(card, { headers: { "Cache-Control": "public, max-age=300" } });
}
