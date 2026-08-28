import { CheckCircle2, Circle, KeyRound, Mic, Network, ShieldCheck, Video } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const integrations = [
  ["Media generation", "Fal provider", "FAL_KEY + model env", Video, false],
  ["Publishing", "TryPost", "TRYPOST_URL + TRYPOST_API_KEY", Network, false],
  ["Agent API", "REST / MCP / CLI", "BLASTER_API_KEY", KeyRound, false],
  ["Voice", "Browser + server intents", "Built in", Mic, true],
] as const;

export default function SettingsPage() {
  return <StudioShell eyebrow="Workspace settings">
    <PageHeader kicker="Settings" title="Connect the engines. Keep the product yours." body="The studio keeps provider choices behind adapters. Swap media or publishing vendors without changing campaign state, UI workflows, or agent contracts." action={<StatusPill tone="green">Secrets stay server-side</StatusPill>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[1.1fr_.9fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]"><p className="text-xs text-black/40">Connections</p><div className="mt-4 divide-y divide-black/6">{integrations.map(([kind,name,detail,Icon,ready])=><div key={name} className="flex items-center gap-4 py-4"><div className="grid h-11 w-11 place-items-center rounded-xl bg-[#f2f2ef]"><Icon className="h-5 w-5 text-black/48"/></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{name}</p><p className="mt-1 text-xs text-black/40">{kind} · {detail}</p></div>{ready?<CheckCircle2 className="h-5 w-5 text-[#159653]"/>:<Circle className="h-5 w-5 text-black/18"/>}</div>)}</div></section>
      <div className="space-y-5"><section className="rounded-[22px] border border-black/7 bg-[#10110f] p-5 text-white"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 text-[#b9ff66]"/><div><p className="text-sm font-medium">Publishing safety</p><p className="mt-2 text-xs leading-5 text-white/48">Every publishing interface checks the same explicit human approval flag before it can call the external scheduler. There is no agent override.</p></div></div><div className="mt-4 rounded-xl bg-white/[0.06] p-3 font-mono text-[10px] leading-5 text-white/55">approved=false → blocked<br/>approved=true → publisher adapter</div></section>
      <section className="rounded-[22px] border border-black/7 bg-white p-5"><p className="text-xs text-black/40">Operator interfaces</p><div className="mt-4 flex flex-wrap gap-2">{["UI","REST API","MCP","CLI","Plugin","Voice"].map(x=><span key={x} className="rounded-full border border-black/8 bg-[#fafaf8] px-3 py-2 text-xs font-medium">{x}</span>)}</div><p className="mt-4 text-xs leading-5 text-black/42">Agency tier exposes API/MCP/CLI commercially. The internal operator can use every interface during V1.</p></section></div>
    </div>
  </StudioShell>;
}
