"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Copy, Download, Library, Save, Search } from "lucide-react";

type PublicCard = {
  id: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  required_inputs: string[];
  source: { attribution: string; license: string; license_verified: boolean };
};

type SavedAdaptation = {
  id: string;
  card: PublicCard;
  inputs: Record<string, string>;
  prompt: string;
  saved_at: string;
};

async function discover(intent: string): Promise<PublicCard[]> {
  const response = await fetch("/v1/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, limit: 3 }),
  });
  if (!response.ok) throw new Error("Discovery unavailable");
  return ((await response.json()) as { cards: PublicCard[] }).cards;
}

function initialSavedLibrary(): SavedAdaptation[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem("creator-studio-library") ?? "[]") as SavedAdaptation[];
  } catch {
    return [];
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function CreatePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicCard[]>([]);
  const [selected, setSelected] = useState<PublicCard | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [adaptedPrompt, setAdaptedPrompt] = useState("");
  const [saved, setSaved] = useState<SavedAdaptation[]>(initialSavedLibrary);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    discover("creator launch campaign")
      .then((cards) => {
        if (active) setResults(cards);
      })
      .catch(() => {
        if (active) setError("Discovery is temporarily unavailable.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const readyToAdapt = useMemo(
    () => (selected ? selected.required_inputs.every((key) => inputs[key]?.trim()) : false),
    [selected, inputs],
  );

  function selectCard(card: PublicCard) {
    setSelected(card);
    setInputs(Object.fromEntries(card.required_inputs.map((key) => [key, ""])));
    setAdaptedPrompt("");
    setNotice("");
    setError("");
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const intent = query.trim();
    if (!intent) return;
    setLoading(true);
    setError("");
    setSelected(null);
    setInputs({});
    setAdaptedPrompt("");
    try {
      setResults(await discover(intent));
    } catch {
      setError("Discovery is temporarily unavailable. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function adapt() {
    if (!selected || !readyToAdapt) return;
    setWorking(true);
    setError("");
    try {
      const response = await fetch("/v1/adapt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: selected.id, inputs }),
      });
      const payload = (await response.json()) as { adapted_prompt?: string; detail?: string };
      if (!response.ok || !payload.adapted_prompt) throw new Error(payload.detail ?? "Adapt failed");
      setAdaptedPrompt(payload.adapted_prompt);
      setNotice("Adapted recipe ready. Edit, save, copy, or export it.");
    } catch {
      setError("Could not adapt this recipe. Check the required inputs and try again.");
    } finally {
      setWorking(false);
    }
  }

  function saveCurrent() {
    if (!selected || !adaptedPrompt) return;
    const item: SavedAdaptation = {
      id: `${selected.id}-${Date.now()}`,
      card: selected,
      inputs,
      prompt: adaptedPrompt,
      saved_at: new Date().toISOString(),
    };
    const next = [item, ...saved].slice(0, 100);
    setSaved(next);
    window.localStorage.setItem("creator-studio-library", JSON.stringify(next));
    setNotice("Saved locally in this browser.");
  }

  function openSaved(item: SavedAdaptation) {
    setSelected(item.card);
    setInputs(item.inputs);
    setAdaptedPrompt(item.prompt);
    setNotice("Saved adaptation reopened.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function exportAgentPack() {
    if (!selected || working) return;
    setWorking(true);
    setError("");
    try {
      const response = await fetch("/v1/export/icm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: selected.id, inputs: adaptedPrompt ? inputs : undefined }),
      });
      if (!response.ok) throw new Error("Export failed");
      const disposition = response.headers.get("Content-Disposition") ?? "";
      const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "creator-agent-pack.zip";
      downloadBlob(await response.blob(), filename);
      setNotice("Portable agent pack exported.");
    } catch {
      setError("Agent pack export is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text">
            <ArrowLeft className="h-4 w-4" aria-hidden /> Creator Studio
          </Link>
          <span className="rounded-full border border-border bg-bg-elevated px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-text-dim">
            Local-first workspace
          </span>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 hero-grid" aria-hidden />
        <div className="absolute inset-0 glow" aria-hidden />
        <div className="relative mx-auto max-w-4xl px-6 py-16 text-center sm:py-24">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-text-dim">Discover → Adapt → Own</p>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-6xl">What do you want to make?</h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-text-muted">
            Describe the outcome. Get three useful choices, adapt one to your project, save it locally, and export it for any agent.
          </p>
          <form onSubmit={submit} className="mx-auto mt-10 max-w-2xl">
            <label htmlFor="creator-intent" className="sr-only">Describe what you want to make</label>
            <div className="flex gap-2 rounded-2xl border border-border bg-bg-card p-2">
              <Search className="ml-3 mt-3 h-5 w-5 shrink-0 text-text-dim" aria-hidden />
              <input id="creator-intent" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="A cinematic launch reel for my clothing brand…" className="min-w-0 flex-1 bg-transparent px-2 py-3 text-sm outline-none placeholder:text-text-dim" />
              <button type="submit" disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white disabled:opacity-60">
                {loading ? "Finding…" : "Find cards"} <ArrowRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </form>
          {error && <p className="mt-4 text-sm text-warning" role="status">{error}</p>}
          {notice && <p className="mt-4 text-sm text-success" role="status">{notice}</p>}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-text-dim">Best matches</p>
          <h2 className="mt-2 text-2xl font-semibold">Three useful choices. Not three hundred.</h2>
        </div>
        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {results.map((card) => (
            <button key={card.id} type="button" onClick={() => selectCard(card)} className={`rounded-2xl border p-6 text-left transition ${selected?.id === card.id ? "border-accent bg-bg-elevated" : "border-border bg-bg-card hover:border-border-strong"}`}>
              <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-text-dim">{card.category}</span>
              <h3 className="mt-6 text-lg font-medium">{card.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-text-muted">{card.description}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {card.tags.slice(0, 4).map((tag) => <span key={tag} className="rounded-md bg-bg-elevated px-2 py-1 text-[11px] text-text-dim">{tag}</span>)}
              </div>
            </button>
          ))}
        </div>

        {selected && (
          <section className="mt-8 rounded-2xl border border-border bg-bg-elevated p-6 sm:p-8">
            <div className="grid gap-8 lg:grid-cols-2">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent-soft">Adapt recipe</p>
                <h2 className="mt-3 text-2xl font-semibold">{selected.title}</h2>
                <p className="mt-3 text-sm text-text-muted">{selected.description}</p>
                <div className="mt-6 space-y-4">
                  {selected.required_inputs.map((key) => (
                    <label key={key} className="block text-sm">
                      <span className="mb-2 block text-text-muted">{key}</span>
                      <input value={inputs[key] ?? ""} onChange={(event) => setInputs({ ...inputs, [key]: event.target.value })} className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 outline-none focus:border-accent" placeholder={`Enter ${key}`} />
                    </label>
                  ))}
                </div>
                <button type="button" onClick={adapt} disabled={!readyToAdapt || working} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white disabled:opacity-50">
                  {working ? "Working…" : "Adapt this card"} <ArrowRight className="h-4 w-4" aria-hidden />
                </button>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-dim">Your adapted recipe</p>
                <textarea value={adaptedPrompt} onChange={(event) => setAdaptedPrompt(event.target.value)} placeholder="Fill the required inputs and adapt the card." className="mt-3 min-h-64 w-full rounded-xl border border-border bg-bg-card p-4 text-sm leading-relaxed outline-none focus:border-accent" />
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" onClick={() => adaptedPrompt && navigator.clipboard.writeText(adaptedPrompt)} disabled={!adaptedPrompt} className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-40"><Copy className="h-4 w-4" aria-hidden />Copy</button>
                  <button type="button" onClick={saveCurrent} disabled={!adaptedPrompt} className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-40"><Save className="h-4 w-4" aria-hidden />Save locally</button>
                  <button type="button" onClick={exportAgentPack} disabled={working} className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm"><Download className="h-4 w-4" aria-hidden />Export pack</button>
                </div>
                <p className="mt-4 text-xs text-text-dim">Source: {selected.source.attribution} · {selected.source.license}</p>
              </div>
            </div>
          </section>
        )}

        <section className="mt-12 border-t border-border pt-10">
          <div className="flex items-center gap-2"><Library className="h-5 w-5 text-accent-soft" aria-hidden /><h2 className="text-xl font-semibold">Your local library</h2></div>
          <p className="mt-2 text-sm text-text-muted">Saved adaptations stay in this browser. No account required.</p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {saved.map((item) => (
              <button key={item.id} type="button" onClick={() => openSaved(item)} className="rounded-xl border border-border bg-bg-card p-5 text-left">
                <p className="text-sm font-medium">{item.card.title}</p>
                <p className="mt-2 line-clamp-2 text-xs text-text-muted">{item.prompt}</p>
                <p className="mt-3 text-[10px] text-text-dim">Saved {new Date(item.saved_at).toLocaleString()}</p>
              </button>
            ))}
            {saved.length === 0 && <p className="text-sm text-text-dim">No saved adaptations yet.</p>}
          </div>
        </section>
      </section>
    </main>
  );
}
