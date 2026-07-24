import { NextResponse } from "next/server";
import { CREATOR_CARDS } from "@/lib/creator-demo";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const card = CREATOR_CARDS.find((item) => item.id === id);
  if (!card) return NextResponse.json({ detail: "card not found" }, { status: 404 });
  return NextResponse.json(card, { headers: { "Cache-Control": "public, max-age=300" } });
}
