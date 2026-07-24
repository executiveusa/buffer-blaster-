"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Download,
  Film,
  Image as ImageIcon,
  Layers3,
  Search,
  Sparkles,
  Type,
} from "lucide-react";

type CreatorCard = {
  id: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  icon: "image" | "video" | "writing" | "workflow" | "brand" | "social";
  requiredInputs: string[];
  icmPath: string;
};

const CARDS: CreatorCard[] = [
  {
    id: "bb-workflow-launch-pack-001",
    title: "One Idea → Launch Pack",
    description:
      "Turn one idea into positioning, visual direction, a hero asset recipe, a reel concept, caption, and portable agent pack.",
    category: "Workflow",
    tags: ["launch", "campaign", "creator", "icm", "social"],
    icon: "workflow",
    requiredInputs: ["idea", "audience", "brand voice"],
    icmPath: "10_workflows/product_launch/one-idea-launch-pack",
  },
  {
    id: "bb-video-launch-reel-001",
    title: "Cinematic Launch Reel",
    description:
      "Build a coherent 15–30 second vertical launch reel with a strong opening, clear visual language, and a deliberate payoff.",
    category: "Video",
    tags: ["video", "reel", "instagram", "tiktok", "cinematic", "launch"],
    icon: "video",
    requiredInputs: ["subject", "audience", "tone", "platform"],
    icmPath: "02_video/social_shortform/cinematic-launch-reel",
  },
  {
    id: "bb-image-product-studio-001",
    title: "Clean Product Studio Shot",
    description:
      "Create a premium product hero image while preserving the product identity, proportions, materials, and campaign-ready composition.",
    category: "Images",
    tags: ["product", "ecommerce", "studio", "photography", "hero"],
    icon: "image",
    requiredInputs: ["product", "background", "lighting"],
    icmPath: "01_images/product_photography/clean-product-studio-shot",
  },
  {
    id: "bb-social-ugc-ad-001",
    title: "UGC Problem → Proof → Offer",
    description:
      "A phone-filmable creator ad structure that starts with a real problem, shows believable proof, and ends with one action.",
    category: "Social",
    tags: ["ugc", "ad", "creator", "social", "script", "conversion"],
    icon: "social",
    requiredInputs: ["product", "audience", "voice"],
    icmPath: "04_social/ugc/problem-proof-offer",
  },
  {
    id: "bb-brand-moodboard-001",
    title: "Brand World Moodboard",
    description:
      "Translate a brand idea into a coherent visual world before generating final campaign assets.",
    category: "Brand",
    tags: ["brand", "moodboard", "creative direction", "visual identity"],
    icon: "brand",
    requiredInputs: ["brand", "idea"],
    icmPath: "06_brand/creative_direction/brand-world-moodboard",
  },
  {
    id: "bb-writing-short-script-001",
    title: "60-Second Story Script",
    description:
      "A compact beginning–tension–turn–payoff structure for voiceovers, reels, and creator stories without filler.",
    category: "Writing",
    tags: ["writing", "script", "story", "voiceover", "short form"],
    icon: "writing",
    requiredInputs: ["topic", "audience", "voice"],
    icmPath: "03_writing/scripts/60-second-story-script",
  },
];

const ICONS = {
  image: ImageIcon,
  video: Film,
  writing: Type,
  workflow: Layers3,
  brand: Sparkles,
  social: Bot,
};

function score(card: CreatorCard, query: string) {
  const tokens = query
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
  const haystack = `${card.title} ${card.description} ${card.category} ${card.tags.join(" ")}`.toLowerCase();
  return tokens.reduce((total, token) => total + (haystack.includes(token) ? 1 : 0), 0);
}

export default function CreatePage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [selected, setSelected] = useState<CreatorCard | null>(null);

  const results = useMemo(() => {
    if (!submittedQuery.trim()) return CARDS.slice(0, 3);
    return [...CARDS]
      .sort((a, b) => score(b, submittedQuery) - score(a, submittedQuery))
      .slice(0, 3);
  }, [submittedQuery]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelected(null);
    setSubmittedQuery(query.trim());
  }

  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text">
            <ArrowLeft className="h-4 w-4" />
            Buffer Blaster
          </Link>
          <span className="rounded-full border border-border bg-bg-elevated px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-text-dim">
            Creator OS Prototype
          </span>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 hero-grid" aria-hidden />
        <div className="absolute inset-0 glow" aria-hidden />
        <div className="relative mx-auto max-w-4xl px-6 py-20 text-center sm:py-28">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-text-dim">
            Discover → Adapt → Own
          </p>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            What do you want to make?
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-text-muted sm:text-lg">
            Describe the outcome. Buffer Blaster finds the best creative recipes and workflows without making you dig through thousands of prompts.
          </p>

          <form onSubmit={submit} className="mx-auto mt-10 max-w-2xl">
            <label htmlFor="creator-intent" className="sr-only">
              Describe what you want to make
            </label>
            <div className="flex gap-2 rounded-2xl border border-border bg-bg-card p-2 shadow-2xl shadow-black/10">
              <Search className="ml-3 mt-3 h-5 w-5 shrink-0 text-text-dim" aria-hidden />
              <input
                id="creator-intent"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="A cinematic launch reel for my clothing brand…"
                className="min-w-0 flex-1 bg-transparent px-2 py-3 text-sm text-text outline-none placeholder:text-text-dim"
              />
              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-soft"
              >
                Find cards
                <ArrowRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </form>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-text-dim">
              {submittedQuery ? "Best matches" : "Start here"}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">
              Three useful choices. Not three hundred.
            </h2>
          </div>
          <p className="max-w-md text-sm leading-relaxed text-text-muted">
            Each card is a reusable recipe with explicit inputs and an ICM path that can later export into your own agent workspace.
          </p>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {results.map((card) => {
            const Icon = ICONS[card.icon];
            const isSelected = selected?.id === card.id;
            return (
              <button
                key={card.id}
                type="button"
                onClick={() => setSelected(card)}
                className={`group rounded-2xl border p-6 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-soft ${
                  isSelected
                    ? "border-accent bg-bg-elevated"
                    : "border-border bg-bg-card hover:-translate-y-0.5 hover:border-border-strong"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-bg-elevated">
                    <Icon className="h-5 w-5 text-accent-soft" aria-hidden />
                  </div>
                  <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-text-dim">
                    {card.category}
                  </span>
                </div>
                <h3 className="mt-6 text-lg font-medium">{card.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-text-muted">{card.description}</p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {card.tags.slice(0, 4).map((tag) => (
                    <span key={tag} className="rounded-md bg-bg-elevated px-2 py-1 text-[11px] text-text-dim">
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {selected && (
          <aside className="mt-8 rounded-2xl border border-border bg-bg-elevated p-6 sm:p-8" aria-live="polite">
            <div className="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent-soft">Selected recipe</p>
                <h2 className="mt-3 text-2xl font-semibold tracking-tight">{selected.title}</h2>
                <p className="mt-4 max-w-2xl text-sm leading-relaxed text-text-muted">{selected.description}</p>

                <div className="mt-7 flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim"
                  >
                    Use this card
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-3 text-sm font-medium text-text transition hover:bg-bg-card"
                  >
                    <Download className="h-4 w-4" aria-hidden />
                    Export ICM pack
                  </button>
                </div>
                <p className="mt-3 text-xs text-text-dim">
                  Prototype actions are visible now; persistence/export wiring is the next implementation slice.
                </p>
              </div>

              <div className="rounded-xl border border-border bg-bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-dim">Needs from you</p>
                <ul className="mt-4 space-y-2">
                  {selected.requiredInputs.map((input) => (
                    <li key={input} className="flex items-center gap-2 text-sm text-text-muted">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-soft" aria-hidden />
                      {input}
                    </li>
                  ))}
                </ul>
                <div className="mt-6 border-t border-border pt-4">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-dim">Portable path</p>
                  <code className="mt-2 block break-all text-xs leading-relaxed text-text-muted">{selected.icmPath}</code>
                </div>
              </div>
            </div>
          </aside>
        )}
      </section>
    </main>
  );
}
