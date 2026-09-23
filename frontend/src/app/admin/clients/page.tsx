"use client";

import { FormEvent, useEffect, useState } from "react";
import { createClient, getClients } from "@/lib/api";
import { NICHE_LABELS, type Client, type Niche } from "@/lib/demo-data";
import { CheckCircle2, Plus, X } from "lucide-react";

const NICHES: Niche[] = ["food-beverage", "beauty-skincare", "apparel", "home-lifestyle"];

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [niche, setNiche] = useState<Niche>("food-beverage");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getClients().then(setClients).catch((reason) => setError(reason instanceof Error ? reason.message : "Clients are unavailable."));
  }, []);

  function openForm() {
    setError("");
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setName("");
    setSlug("");
    setNiche("food-beverage");
    setError("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanSlug = slug.trim().toLowerCase();
    if (cleanName.length < 2 || !/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/.test(cleanSlug)) {
      setError("Enter a client name and a 3–50 character lowercase slug using letters, numbers, or hyphens.");
      return;
    }
    setWorking(true);
    setError("");
    try {
      const created = await createClient({ name: cleanName, niche, slug: cleanSlug });
      setClients((current) => current.some((item) => item.id === created.id || item.slug === created.slug) ? current : [...current, created]);
      closeForm();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create client.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
          <p className="mt-1 text-sm text-text-muted">Each client gets an isolated, encrypted schema.</p>
        </div>
        <button onClick={openForm} className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-text-muted transition hover:border-border-strong hover:text-text">
          <Plus className="h-4 w-4" />
          Add client
        </button>
      </div>

      {showForm ? (
        <form onSubmit={submit} className="mt-6 rounded-xl border border-border bg-bg-card p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-medium">New client</h2>
              <p className="mt-1 text-xs text-text-dim">Creates the client record and isolated schema through the authenticated backend.</p>
            </div>
            <button type="button" onClick={closeForm} aria-label="Close client form" className="grid h-8 w-8 place-items-center rounded-md text-text-dim hover:bg-bg-elevated"><X className="h-4 w-4" /></button>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-xs text-text-muted">Name<input value={name} onChange={(event)=>setName(event.target.value)} placeholder="Cella Coffee Roasters" className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 text-sm text-text outline-none focus:border-accent" /></label>
            <label className="text-xs text-text-muted">Slug<input value={slug} onChange={(event)=>setSlug(event.target.value)} placeholder="cella-coffee" className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 font-mono text-sm text-text outline-none focus:border-accent" /></label>
          </div>
          <label className="mt-4 block text-xs text-text-muted">Niche<select value={niche} onChange={(event)=>setNiche(event.target.value as Niche)} className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 text-sm text-text">{NICHES.map((value)=><option key={value} value={value}>{NICHE_LABELS[value]}</option>)}</select></label>
          {error ? <p className="mt-4 text-sm text-danger" role="alert">{error}</p> : null}
          <div className="mt-5 flex gap-2">
            <button type="submit" disabled={working || !name.trim() || !slug.trim()} className="rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-45">{working ? "Creating…" : "Create client"}</button>
            <button type="button" onClick={closeForm} className="rounded-lg border border-border px-4 py-2.5 text-sm text-text-muted">Cancel</button>
          </div>
        </form>
      ) : error ? <p className="mt-5 text-sm text-danger" role="alert">{error}</p> : null}

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {clients.map((client) => (
          <div key={client.id} className="rounded-xl border border-border bg-bg-card p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium">{client.name}</h3>
                <p className="mt-1 text-xs text-text-dim">{NICHE_LABELS[client.niche]}</p>
              </div>
              <span className="inline-flex items-center gap-1 text-xs text-success"><CheckCircle2 className="h-3 w-3" />{client.status}</span>
            </div>
            <div className="mt-4 flex gap-6 text-xs">
              <div><div className="font-mono text-lg text-text">{client.posts_scheduled}</div><div className="text-text-dim">scheduled</div></div>
              <div><div className="font-mono text-lg text-text">{client.avg_score.toFixed(1)}</div><div className="text-text-dim">avg score</div></div>
            </div>
            <p className="mt-4 font-mono text-[10px] text-text-dim">{client.schema}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
