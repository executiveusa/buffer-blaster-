import { NextResponse } from "next/server";
import { ALL_CREATOR_CARDS } from "@/lib/creator-catalog";

export const dynamic = "force-dynamic";

type AdaptBody = { card_id?: unknown; inputs?: unknown };

function applyInputs(prompt: string, inputs: Record<string, string>) {
  let output = prompt;
  for (const [key, value] of Object.entries(inputs)) {
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    output = output
      .replace(new RegExp(`\\{\\{\\s*${escaped}\\s*\\}\\}`, "gi"), value)
      .replace(new RegExp(`\\{argument name=["']${escaped}["'][^}]*\\}`, "gi"), value);
  }
  return output;
}

export async function POST(request: Request) {
  let body: AdaptBody;
  try { body = (await request.json()) as AdaptBody; }
  catch { return NextResponse.json({ detail: "invalid JSON" }, { status: 400 }); }

  const cardId = typeof body.card_id === "string" ? body.card_id.trim() : "";
  if (!cardId) return NextResponse.json({ detail: "card_id is required" }, { status: 422 });
  const card = ALL_CREATOR_CARDS.find((item) => item.id === cardId);
  if (!card) return NextResponse.json({ detail: "card not found" }, { status: 404 });

  const rawInputs = body.inputs && typeof body.inputs === "object" && !Array.isArray(body.inputs) ? body.inputs : {};
  const inputs = Object.fromEntries(Object.entries(rawInputs as Record<string, unknown>).map(([key, value]) => [key, String(value ?? "").trim()]));
  const missing = card.required_inputs.filter((key) => !inputs[key]);
  if (missing.length) return NextResponse.json({ detail: "required inputs missing", missing }, { status: 422 });

  return NextResponse.json({
    card_id: card.id,
    title: card.title,
    adapted_prompt: applyInputs(card.prompt, inputs),
    inputs,
    source: card.source,
  });
}
