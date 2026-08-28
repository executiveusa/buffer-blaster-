import Link from "next/link";
import { ArrowUpRight, CheckCircle2, Clock3, Film, Plus, Send } from "lucide-react";
import { AgentCommand } from "@/components/agent-command";
import { Metric, PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const queue = [
  ["Cold brew testimonial", "UGC · 9:16", "Rendering", "blue"],
  ["Summer launch hook A", "UGC · 9:16", "Ready", "green"],
  ["Product proof carousel", "Carousel · IG/LI", "Review", "amber"],
] as const;

export default function StudioOverview() {
  return <StudioShell eyebrow="Agentic social operations">
    <PageHeader kicker="Today" title="Run social from one command." body="Plan campaigns, make UGC, review the work, and schedule it across connected accounts. Agents can do the busywork; public posting still waits for your approval." action={<Link href="/studio/create" className="inline-flex items-center gap-2 rounded-full bg-black px-5 py-3 text-sm font-medium text-white"><Plus className="h-4 w-4" />Create</Link>} />
    <div className="space-y-6 p-6 lg:p-10">
      <AgentCommand />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Active campaigns" value="4" detail="2 due this week" />
        <Metric label="UGC renders" value="7" detail="3 ready to review" />
        <Metric label="Scheduled" value="18" detail="Across 6 social accounts" />
        <Metric label="Needs approval" value="5" detail="Nothing publishes without you" />
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
        <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
          <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Production queue</p><h3 className="mt-1 text-xl font-semibold tracking-tight">What the team is making</h3></div><Link href="/studio/library" className="text-xs font-medium text-black/50 hover:text-black">View all</Link></div>
          <div className="mt-5 divide-y divide-black/6">
            {queue.map(([name, meta, status, tone]) => <div key={name} className="flex items-center gap-4 py-4"><div className="grid h-11 w-11 place-items-center rounded-xl bg-[#f1f1ee]"><Film className="h-5 w-5 text-black/55" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{name}</p><p className="mt-0.5 text-xs text-black/40">{meta}</p></div><StatusPill tone={tone}>{status}</StatusPill></div>)}
          </div>
        </section>
        <section className="rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
          <p className="text-xs text-black/40">Approval inbox</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Five decisions</h3>
          <div className="mt-5 space-y-3">
            <div className="rounded-2xl bg-white p-4"><div className="flex items-start gap-3"><Clock3 className="mt-0.5 h-4 w-4 text-[#bd7a11]"/><div><p className="text-sm font-medium">3 posts ready</p><p className="mt-1 text-xs leading-5 text-black/45">Review copy, media, platform variants, and timing.</p></div></div></div>
            <div className="rounded-2xl bg-white p-4"><div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 text-[#159653]"/><div><p className="text-sm font-medium">2 UGC ads scored 82+</p><p className="mt-1 text-xs leading-5 text-black/45">Higher-scoring variants are ready for final eyes.</p></div></div></div>
          </div>
          <Link href="/studio/calendar" className="mt-4 flex items-center justify-between rounded-xl bg-black px-4 py-3 text-sm font-medium text-white">Open review queue <ArrowUpRight className="h-4 w-4" /></Link>
        </section>
      </div>
      <div className="flex items-center gap-2 rounded-2xl border border-black/7 bg-white px-4 py-3 text-xs text-black/45"><Send className="h-4 w-4" /><span>Publishing kernel:</span><strong className="text-black/65">TryPost adapter</strong><span>· human approval gate on</span></div>
    </div>
  </StudioShell>;
}
