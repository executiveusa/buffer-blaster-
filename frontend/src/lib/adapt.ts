import type { CreatorCard } from "@/lib/creator-demo";

export function normalizeInputs(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, String(item ?? "").trim()]));
}

export function adaptCardPrompt(card: CreatorCard, inputs: Record<string, string>): string {
  let output = card.prompt;
  for (const [key, value] of Object.entries(inputs)) {
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    output = output
      .replace(new RegExp(`\\{\\{\\s*${escaped}\\s*\\}\\}`, "gi"), value)
      .replace(new RegExp(`\\{argument name=["']${escaped}["'][^}]*\\}`, "gi"), value);
  }
  return output;
}
