"use client";

import Link from "next/link";
import { AlertCircle, Film, Plus, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { AgentCommand } from "@/components/agent-command";
import { Metric, PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { getLedgerSummary, listCreativeJobs, type CreativeJob, type LedgerSummary } from "@/lib/studio-state";

export default function StudioOverview() {
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [jobs, setJobs] = useState<CreativeJob[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getLedgerSummary(), listCreativeJobs(6)])
      .then(([nextSummary, nextJobs]) => { setSummary(nextSummary); setJobs(nextJobs); })
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Canonical Studio state is unavailable."));
  }, []);

  const canonical = summary?.ledger.canonical === true;
  return <StudioShell eyebrow="Agentic social operations">
    <PageHeader kicker="Today" title="Run social from one command." body="Plan campaigns, make UGC, review the work, and keep every paid generation attached to a real job receipt. Public posting remains a separate approval-gated step." action={<Link href="/studio/create" className="inline-flex items-center gap-2 rounded-full bg-black px-5 py-3 text-sm font-medium text-white"><Plus className="h-4 w-4" />Create</Link>} />
    <div className="space-y-6 p-6 lg:p-10">
      <AgentCommand />
      {error ? <div className="flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800"><AlertCircle className="h-4 w-4" />{error}. No synthetic production metrics are shown.</div> : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Campaigns" value={String(summary?.campaigns ?? 0)} detail={canonical ? `Ledger: ${summary?.ledger.backend}` : "No canonical live ledger yet"} />
        <Metric label="Active creative jobs" value={String(summary?.jobs_active ?? 0)} detail="Rendering / processing / stitching" />
        <Metric label="Completed assets" value={String(summary?.jobs_completed ?? 0)} detail="Only durable completed receipts" />
        <Metric label="Failed jobs" value={String(summary?.jobs_failed ?? 0)} detail="Failures stay visible for repair" />
      </div>
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Canonical production ledger</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Recent creative jobs</h3></div><Link href="/studio/library" className="text-xs font-medium text-black/50 hover:text-black">View library</Link></div>
        {jobs.length ? <div className="mt-5 divide-y divide-black/6">{jobs.map((job) => <div key={job.id} className="flex items-center gap-4 py-4"><div className="grid h-11 w-11 place-items-center rounded-xl bg-[#f1f1ee]"><Film className="h-5 w-5 text-black/55" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{job.kind.replaceAll("_", " ")}</p><p className="mt-0.5 truncate text-xs text-black/40">{job.id} · est. ${((job.estimated_provider_cost_cents || 0) / 100).toFixed(2)}</p></div><StatusPill tone={job.state === "finished" ? "green" : job.state.includes("fail") ? "amber" : "blue"}>{job.state.replaceAll("_", " ")}</StatusPill></div>)}</div> : <div className="mt-5 rounded-2xl border border-dashed border-black/10 bg-[#fafaf8] p-8 text-center"><p className="text-sm font-medium">No creative jobs yet</p><p className="mt-2 text-xs leading-5 text-black/42">Build a plan and approve a paid generation. The first real job receipt will appear here.</p></div>}
      </section>
      <div className="flex items-center gap-2 rounded-2xl border border-black/7 bg-white px-4 py-3 text-xs text-black/45"><Send className="h-4 w-4" /><span>Publishing:</span><strong className="text-black/65">optional downstream integration</strong><span>· human approval gate remains on</span></div>
    </div>
  </StudioShell>;
}
