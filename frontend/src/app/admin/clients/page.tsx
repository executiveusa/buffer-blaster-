"use client";

import { useEffect, useState } from "react";
import { getClients } from "@/lib/api";
import { NICHE_LABELS, type Client } from "@/lib/demo-data";
import { CheckCircle2, Plus } from "lucide-react";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);

  useEffect(() => {
    getClients().then(setClients);
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
          <p className="mt-1 text-sm text-text-muted">
            Each client gets an isolated, encrypted schema.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-text-muted transition hover:border-border-strong hover:text-text">
          <Plus className="h-4 w-4" />
          Add client
        </button>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {clients.map((c) => (
          <div
            key={c.id}
            className="rounded-xl border border-border bg-bg-card p-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium">{c.name}</h3>
                <p className="mt-1 text-xs text-text-dim">
                  {NICHE_LABELS[c.niche]}
                </p>
              </div>
              <span className="inline-flex items-center gap-1 text-xs text-success">
                <CheckCircle2 className="h-3 w-3" />
                {c.status}
              </span>
            </div>
            <div className="mt-4 flex gap-6 text-xs">
              <div>
                <div className="font-mono text-lg text-text">
                  {c.posts_scheduled}
                </div>
                <div className="text-text-dim">scheduled</div>
              </div>
              <div>
                <div className="font-mono text-lg text-text">
                  {c.avg_score.toFixed(1)}
                </div>
                <div className="text-text-dim">avg score</div>
              </div>
            </div>
            <p className="mt-4 font-mono text-[10px] text-text-dim">{c.schema}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
