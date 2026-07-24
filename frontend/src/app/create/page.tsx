"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Download, Search } from "lucide-react";

type PublicCard = {
  id: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  required_inputs: string[];
  source: {
    attribution: string;
    license: string;
    license_verified: boolean;
  };
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function discover(intent: string): Promise<PublicCard[]> {
  const response = await fetch(`${API_BASE}/v1/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, limit: 3 }),
  });

  if (!response.ok) {
    throw new Error("Discovery is temporarily unavailable.");
  }

  const payload = (await response.json()) as { cards: PublicCard[] };
  return payload.cards;
}

export default function CreatePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicCard[]>([]);
  const [selected, setSelected] = useState<PublicCard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    discover("creator launch campaign")
      .then((cards) => {
        if (active) setResults(cards);
      })
      .catch(() => {
        if (active) setError("Discovery is temporarily unavailable in this preview.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const intent = query.trim();
    if (!intent) return;

    setLoading(true);
    setError("");
    setSelected(null);
    try {
      setResults(await discover(intent));
    } catch {
      setError("Discovery is temporarily unavailable. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Creator Studio
          </Link>
          <span className="rounded-full border border-border bg-bg-elevated px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-text-dim">
            Creator workspace
          </span>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 hero-grid" aria-hidden />
        <div className="absolute inset-0 glow" aria-hidden />
        <div className="relative mx-auto max-w-4xl px-6 py-20 text-center sm:py-28">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-text-dim">Discover → Adapt → Own</p>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            What do you want to make?
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-text-muted sm:text-lg">
            Describe the outcome. The studio finds a small set of useful creative recipes instead of making you dig through thousands of prompts.
          </p>

          <form onSubmit={submit} className="mx-auto mt-10 max-w-2xl">
            <label htmlFor="creator-intent" className="sr-only">Describe what you want to make</label>
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
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-soft"
              >
                {loading ? "Finding…" : "Find cards"}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </form>
          {error && <p className="mt-4 text-sm text-warning" role="status">{error}</p>}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-text-dim">Best matches</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Three useful choices. Not three hundred.</h2>
          </div>
          <p className="max-w-md text-sm leading-relaxed text-text-muted">
            Search and ranking come from the same discovery API used by agent integrations.
          </p>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {results.map((card) => {
            const isSelected = selected?.id === card.id;
            return (
              <button
                key={card.id}
                type="button"
                onClick={() => setSelected(card)}
                className={`group rounded-2xl border p-6 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-soft ${
                  isSelected ? "border-accent bg-bg-elevated" : "border-border bg-bg-card hover:-translate-y-0.5 hover:border-border-strong"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-text-dim">
                    {card.category}
                  </span>
                </div>
                <h3 className="mt-6 text-lg font-medium">{card.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-text-muted">{card.description}</p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {card.tags.slice(0, 4).map((tag) => (
                    <span key={tag} className="rounded-md bg-bg-elevated px-2 py-1 text-[11px] text-text-dim">{tag}</span>
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
                  <button type="button" className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim">
                    Use this card <ArrowRight className="h-4 w-4" aria-hidden />
                  </button>
                  <button type="button" className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-3 text-sm font-medium text-text transition hover:bg-bg-card">
                    <Download className="h-4 w-4" aria-hidden /> Export agent pack
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-bg-card p-5">
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-dim">Needs from you</p>
                <ul className="mt-4 space-y-2">
                  {selected.required_inputs.map((input) => (
                    <li key={input} className="flex items-center gap-2 text-sm text-text-muted">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-soft" aria-hidden />{input}
                    </li>
                  ))}
                </ul>
                <div className="mt-6 border-t border-border pt-4 text-xs text-text-dim">
                  Source: {selected.source.attribution} · {selected.source.license}
                </div>
              </div>
            </div>
          </aside>
        )}
      </section>
    </main>
  );
}
