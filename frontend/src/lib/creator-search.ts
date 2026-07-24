import { CREATOR_CARDS, type CreatorCard } from "@/lib/creator-demo";

const MEDIA_TERMS: Record<string, string[]> = {
  video: ["video", "reel", "tiktok", "short", "cinematic", "motion"],
  image: ["image", "photo", "poster", "flyer", "thumbnail", "portrait", "product"],
  text: ["write", "writing", "script", "caption", "copy", "story"],
  workflow: ["workflow", "campaign", "launch", "pack", "system"],
};

function tokens(value: string) {
  return new Set(value.toLowerCase().match(/[a-z0-9]+/g) ?? []);
}

function overlap(a: Set<string>, b: Set<string>, weight: number) {
  let score = 0;
  for (const token of a) if (b.has(token)) score += weight;
  return score;
}

function inferredMedia(intent: string): string | null {
  const lower = intent.toLowerCase();
  let best: { type: string; hits: number } | null = null;
  for (const [type, terms] of Object.entries(MEDIA_TERMS)) {
    const hits = terms.filter((term) => lower.includes(term)).length;
    if (hits && (!best || hits > best.hits)) best = { type, hits };
  }
  return best?.type ?? null;
}

function scoreCard(card: CreatorCard, intent: string) {
  const intentTokens = tokens(intent);
  const title = tokens(card.title);
  const description = tokens(card.description);
  const category = tokens(`${card.category} ${card.subcategory}`);
  const tags = new Set(card.tags.map((tag) => tag.toLowerCase()));
  const media = inferredMedia(intent);

  return (
    overlap(intentTokens, title, 10) +
    overlap(intentTokens, tags, 7) +
    overlap(intentTokens, category, 4) +
    overlap(intentTokens, description, 3) +
    (media && card.media_type === media ? 12 : 0) +
    Math.floor(card.quality_score / 10) +
    (card.source.license_verified ? 3 : -100)
  );
}

export function discoverCreatorCards(intent: string, limit = 3): CreatorCard[] {
  const capped = Math.max(1, Math.min(Math.trunc(limit), 12));
  const seen = new Set<string>();
  return [...CREATOR_CARDS]
    .sort((a, b) => scoreCard(b, intent) - scoreCard(a, intent) || b.quality_score - a.quality_score || a.id.localeCompare(b.id))
    .filter((card) => {
      const fingerprint = `${card.category}:${card.title.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()}`;
      if (seen.has(fingerprint)) return false;
      seen.add(fingerprint);
      return true;
    })
    .slice(0, capped);
}
