"use client";

import { useEffect, useState } from "react";
import { getContent } from "@/lib/api";
import { DEMO_CLIENTS, type ContentUnit } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<ContentUnit["status"], string> = {
  approved: "text-success",
  pending: "text-warning",
  rejected: "text-danger",
  draft: "text-text-dim",
  published: "text-accent-soft",
};

export default function ContentPage() {
  const [slug, setSlug] = useState(DEMO_CLIENTS[0].slug);
  const [units, setUnits] = useState<ContentUnit[]>([]);

  useEffect(() => {
    getContent(slug).then(setUnits);
  }, [slug]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Content queue</h1>
      <p className="mt-1 text-sm text-text-muted">
        Scored posts awaiting your approval. Top three per platform.
      </p>

      <div className="mt-6 flex gap-2">
        {DEMO_CLIENTS.map((c) => (
          <button
            key={c.slug}
            onClick={() => setSlug(c.slug)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm transition",
              slug === c.slug
                ? "bg-bg-card text-text"
                : "text-text-muted hover:text-text",
            )}
          >
            {c.name}
          </button>
        ))}
      </div>

      <div className="mt-8 space-y-3">
        {units.map((u) => (
          <div
            key={u.id}
            className="rounded-xl border border-border bg-bg-card p-5"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm">{u.hook}</p>
                <p className="mt-1 text-xs text-text-dim">{u.caption}</p>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-mono text-2xl font-semibold">
                  {u.raw_score}
                </div>
                <div className="text-[10px] text-text-dim">/ 100</div>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4 text-xs">
              <span className="rounded bg-bg-elevated px-2 py-0.5 font-mono text-text-dim">
                {u.platform}
              </span>
              <span className={cn("font-medium", STATUS_STYLES[u.status])}>
                {u.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
