import { NextResponse } from "next/server";
import { CREATOR_DEMO_CARDS } from "@/lib/creator-demo";
import { buildSingleCardAgentPack } from "@/lib/icm-export";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type ExportBody = { card_id?: unknown };

export async function POST(request: Request) {
  let body: ExportBody;
  try {
    body = (await request.json()) as ExportBody;
  } catch {
    return NextResponse.json({ detail: "invalid JSON" }, { status: 400 });
  }

  const cardId = typeof body.card_id === "string" ? body.card_id.trim() : "";
  if (!cardId) return NextResponse.json({ detail: "card_id is required" }, { status: 422 });

  const card = CREATOR_DEMO_CARDS.find((item) => item.id === cardId);
  if (!card) return NextResponse.json({ detail: "card not found" }, { status: 404 });
  if (!card.source.license_verified) {
    return NextResponse.json({ detail: "card license is not verified" }, { status: 409 });
  }

  const pack = buildSingleCardAgentPack(card);
  return new Response(new Uint8Array(pack.bytes), {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${pack.filename}"`,
      "Cache-Control": "no-store",
      "X-Buffer-Blaster-Sha256": pack.sha256,
    },
  });
}
