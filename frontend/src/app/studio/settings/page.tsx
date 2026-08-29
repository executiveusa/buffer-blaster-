"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, Database, KeyRound, Loader2, Network, RefreshCw, ShieldCheck, Video } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { getStudioStatus } from "@/lib/studio-api";

type Status = {
  ok?: boolean;
  simulated?: boolean;
  media?: { provider?: string; configured?: boolean; text_video?: boolean; image_video?: boolean };
  storage?: { backend?: string; configured?: boolean };
  media_ops?: { ffmpeg?: boolean };
  publishing?: { provider?: string | null; configured?: boolean; enabled?: boolean; required_for_core?: boolean };
  ledger?: { backend?: string; canonical?: boolean; jobs?: number };
  approval_gate?: boolean;
  interfaces?: string[];
};

export default function SettingsPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    try { setStatus(await getStudioStatus() as Status); }
    catch (requestError) { setStatus(null); setError(requestError instanceof Error ? requestError.message : "Studio status unavailable."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, []);

  const connections = [
    { kind: "Media generation", name: status?.media?.provider || "Media provider", detail: status?.media?.configured ? "Configured" : "Not configured", Icon: Video, ready: Boolean(status?.media?.configured) },
    { kind: "Private asset storage", name: status?.storage?.backend || "Asset storage", detail: status?.storage?.configured ? "Configured" : "Not configured", Icon: Database, ready: Boolean(status?.storage?.configured) },
    { kind: "Publishing", name: status?.publishing?.provider || "Optional publisher", detail: status?.publishing?.enabled ? "Enabled" : "Disabled / optional", Icon: Network, ready: Boolean(status?.publishing?.configured && status?.publishing?.enabled) },
    { kind: "Media processing", name: "FFmpeg", detail: status?.media_ops?.ffmpeg ? "Available" : "Unavailable", Icon: Video, ready: Boolean(status?.media_ops?.ffmpeg) },
  ];

  return <StudioShell eyebrow="Workspace settings">
    <PageHeader kicker="Settings" title="Connect the engines. Keep the product yours." body="Connection state comes from the live Studio status endpoint. Provider choices stay behind adapters, and publishing remains optional and separately approval-gated." action={<button onClick={()=>void refresh()} disabled={loading} className="inline-flex items-center gap-2 rounded-xl border border-black/10 bg-white px-4 py-2.5 text-sm font-medium disabled:opacity-50">{loading?<Loader2 className="h-4 w-4 animate-spin"/>:<RefreshCw className="h-4 w-4"/>}Refresh</button>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[1.1fr_.9fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center justify-between"><p className="text-xs text-black/40">Live readiness</p>{status?.simulated?<StatusPill tone="amber">Simulation only</StatusPill>:status?.ok?<StatusPill tone="green">Status loaded</StatusPill>:<StatusPill tone="neutral">Unknown</StatusPill>}</div>
        {error ? <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">{error}</p> : null}
        <div className="mt-4 divide-y divide-black/6">{connections.map(({kind,name,detail,Icon,ready})=><div key={`${kind}-${name}`} className="flex items-center gap-4 py-4"><div className="grid h-11 w-11 place-items-center rounded-xl bg-[#f2f2ef]"><Icon className="h-5 w-5 text-black/48"/></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{name}</p><p className="mt-1 text-xs text-black/40">{kind} · {detail}</p></div>{ready?<CheckCircle2 className="h-5 w-5 text-[#159653]"/>:<Circle className="h-5 w-5 text-black/18"/>}</div>)}</div>
        <div className="mt-4 rounded-xl bg-[#f5f5f2] p-3 text-[11px] leading-5 text-black/45"><strong className="text-black/65">Ledger:</strong> {status?.ledger?.backend || "unresolved"} · canonical state {status?.ledger?.canonical === true ? "on" : status?.simulated ? "simulated" : "unverified"}</div>
      </section>
      <div className="space-y-5">
        <section className="rounded-[22px] border border-black/7 bg-[#10110f] p-5 text-white"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 text-[#b9ff66]"/><div><p className="text-sm font-medium">Publishing safety</p><p className="mt-2 text-xs leading-5 text-white/48">Every publishing interface checks the same explicit human approval flag. A configured scheduler still cannot bypass that gate.</p></div></div><div className="mt-4 rounded-xl bg-white/[0.06] p-3 font-mono text-[10px] leading-5 text-white/55">approved=false → blocked<br/>approved=true → optional publisher adapter</div></section>
        <section className="rounded-[22px] border border-black/7 bg-white p-5"><div className="flex items-center gap-2"><KeyRound className="h-4 w-4 text-black/40"/><p className="text-xs font-medium">Operator interfaces</p></div><div className="mt-4 flex flex-wrap gap-2">{(status?.interfaces || ["ui","rest","mcp","cli","plugin","voice"]).map((item)=><span key={item} className="rounded-full border border-black/8 bg-[#fafaf8] px-3 py-2 text-xs font-medium uppercase">{item}</span>)}</div><p className="mt-4 text-xs leading-5 text-black/42">For secret presence and real provider handshakes, use the authenticated admin Settings screen.</p><Link href="/admin/settings" className="mt-4 inline-flex rounded-xl bg-black px-4 py-2.5 text-xs font-medium text-white">Open provider verification</Link></section>
      </div>
    </div>
  </StudioShell>;
}
