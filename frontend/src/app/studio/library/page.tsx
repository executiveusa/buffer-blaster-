"use client";

import Link from "next/link";
import { FileVideo2, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { listCreativeJobs, type CreativeJob } from "@/lib/studio-state";

export default function LibraryPage() {
  const [jobs, setJobs] = useState<CreativeJob[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listCreativeJobs(100)
      .then(setJobs)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Library state unavailable."))
      .finally(() => setLoaded(true));
  }, []);

  const active = jobs.filter((job) => ["planned", "render_queued", "rendering", "rendering_clip_1", "stitching"].some((state) => job.state.startsWith(state))).length;
  const completed = jobs.filter((job) => job.state === "finished").length;
  return <StudioShell eyebrow="Creative library">
    <PageHeader kicker="My ads" title="Everything you have made — backed by real receipts." body="This library is generated from canonical creative-job receipts. Nothing appears here merely because a mock card exists in the frontend." action={<Link href="/studio/create" className="inline-flex items-center gap-2 rounded-xl bg-black px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4"/>Create</Link>} />
    <div className="p-6 lg:p-10">
      <div className="mb-6 rounded-2xl border border-black/7 bg-white p-5"><div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Canonical queue</p><p className="mt-1 text-sm font-medium">{active} active · {completed} finished · {jobs.length} total receipts</p></div><StatusPill tone={active ? "blue" : "neutral"}>{active ? "Processing" : "No active jobs"}</StatusPill></div></div>
      {error ? <p className="rounded-2xl bg-amber-50 p-4 text-xs text-amber-800">{error}. Synthetic assets are intentionally hidden.</p> : null}
      {loaded && jobs.length === 0 ? <div className="grid min-h-[360px] place-items-center rounded-[24px] border border-dashed border-black/10 bg-white p-8 text-center"><div><FileVideo2 className="mx-auto h-9 w-9 text-black/20"/><h2 className="mt-4 text-lg font-semibold">No generated assets yet</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-black/45">Approve your first full-ad generation. Its job receipt and final asset will appear here after the factory reaches a truthful finished state.</p><Link href="/studio/create" className="mt-5 inline-flex rounded-xl bg-black px-4 py-3 text-sm font-medium text-white">Create the first ad</Link></div></div> : null}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{jobs.map((job) => {
        const output = job.output || {};
        const finalAsset = output.final_asset as { signed_url?: string } | undefined;
        const qa = output.qa as { seam_passed?: boolean; paid_generation_calls?: number } | undefined;
        return <article key={job.id} className="rounded-2xl border border-black/7 bg-white p-5 shadow-[0_12px_35px_rgba(0,0,0,.035)]"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-medium capitalize">{job.kind.replaceAll("_", " ")}</p><p className="mt-1 max-w-[220px] truncate font-mono text-[10px] text-black/32">{job.id}</p></div><StatusPill tone={job.state === "finished" ? "green" : job.state.includes("fail") ? "amber" : "blue"}>{job.state.replaceAll("_", " ")}</StatusPill></div><div className="mt-5 grid grid-cols-2 gap-2 text-xs"><Fact label="Est. provider" value={`$${((job.estimated_provider_cost_cents || 0) / 100).toFixed(2)}`} /><Fact label="Paid calls" value={String(qa?.paid_generation_calls ?? "—")} /><Fact label="Seam QA" value={qa?.seam_passed === true ? "Passed" : "—"} /><Fact label="Offer" value={job.offer_id || "—"} /></div>{finalAsset?.signed_url ? <a href={finalAsset.signed_url} target="_blank" rel="noreferrer" className="mt-5 flex w-full items-center justify-center rounded-xl bg-black px-4 py-3 text-sm font-medium text-white">Open final asset</a> : <p className="mt-5 rounded-xl bg-[#f5f5f2] px-3 py-3 text-xs leading-5 text-black/42">No final asset receipt yet.</p>}</article>;
      })}</div>
    </div>
  </StudioShell>;
}

function Fact({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-[#f5f5f2] p-3"><p className="text-[9px] uppercase tracking-[.12em] text-black/30">{label}</p><p className="mt-1 font-medium text-black/65">{value}</p></div>; }
