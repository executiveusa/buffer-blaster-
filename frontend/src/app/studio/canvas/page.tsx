import Link from "next/link";
import { CheckCircle2, ImageIcon, LockKeyhole, Sparkles, WandSparkles } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const Node = ({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) => <div className="relative rounded-2xl border border-black/10 bg-white p-4 shadow-[0_16px_45px_rgba(0,0,0,.06)]"><span className="absolute -left-2 top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white bg-[#2357ff] shadow"/><p className="text-[9px] font-semibold uppercase tracking-[0.15em] text-black/35">{eyebrow}</p><h3 className="mt-1 text-sm font-semibold">{title}</h3><div className="mt-4">{children}</div><span className="absolute -right-2 top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white bg-black shadow"/></div>;

export default function CanvasPage() {
  return <StudioShell eyebrow="Workflow canvas">
    <PageHeader kicker="Canvas" title="See the real creative path." body="This view is an honest map of the executable factory. Editing and arbitrary node composition stay disabled until they can write a canonical workflow graph; the live action opens the same full-ad factory used by REST and MCP." action={<StatusPill tone="green">Canonical flow</StatusPill>} />
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="studio-grid relative min-h-[650px] overflow-hidden rounded-[24px] border border-black/7 bg-[#f8f8f6] p-8 lg:p-12">
        <div className="absolute left-[16%] right-[12%] top-1/2 hidden h-px bg-black/10 xl:block" aria-hidden />
        <div className="relative grid gap-6 xl:grid-cols-4 xl:items-center">
          <Node title="Product truth + references" eyebrow="Input"><div className="grid aspect-[4/3] place-items-center rounded-xl border border-dashed border-black/15 bg-[#fafaf8]"><div className="text-center"><ImageIcon className="mx-auto h-6 w-6 text-black/30"/><p className="mt-2 text-[11px] text-black/40">Product brief + saved references</p></div></div><Link href="/studio/moodboards" className="mt-3 block text-[10px] font-medium text-[#2357ff]">Open real reference board →</Link></Node>
          <Node title="Plan + script gate" eyebrow="Agent"><div className="rounded-xl bg-[#f5f5f2] p-3 text-xs leading-5 text-black/50">Product truth becomes two bounded scripts. The gate runs before any provider spend.</div><div className="mt-3 flex items-center gap-2 text-[10px] text-[#2357ff]"><Sparkles className="h-3.5 w-3.5"/>No-spend planning</div></Node>
          <Node title="Full UGC executor" eyebrow="Media"><div className="space-y-2 text-[10px] leading-5 text-black/48"><p>Clip 1 → trim → seed</p><p>Clip 2 → seam QA → bounded retry</p><p>Stitch → private storage → receipt</p></div><Link href="/studio/create" className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#b9ff66] px-3 py-2.5 text-xs font-semibold text-black"><WandSparkles className="h-3.5 w-3.5"/>Run the real factory</Link></Node>
          <Node title="Final asset + approval" eyebrow="Deliver"><div className="space-y-2"><div className="flex items-center justify-between rounded-xl bg-[#f5f5f2] px-3 py-2.5 text-xs"><span>Generation allowance</span><LockKeyhole className="h-4 w-4 text-[#2357ff]"/></div><div className="flex items-center justify-between rounded-xl bg-[#f5f5f2] px-3 py-2.5 text-xs"><span>Final asset receipt</span><CheckCircle2 className="h-4 w-4 text-[#159653]"/></div><div className="flex items-center justify-between rounded-xl bg-[#f5f5f2] px-3 py-2.5 text-xs"><span>Publish approval</span><span className="text-black/35">separate gate</span></div></div></Node>
        </div>
        <div className="absolute bottom-6 left-6 max-w-md rounded-xl border border-black/8 bg-white px-4 py-3 text-[10px] leading-5 text-black/45 shadow-sm"><strong className="text-black/65">Node editing is intentionally locked.</strong><br/>The old “+” and dead render controls were removed. A visual editor becomes interactive only when its graph is persisted and executable.</div>
        <div className="absolute bottom-6 right-6 rounded-xl border border-black/8 bg-white px-4 py-3 text-[10px] leading-5 text-black/45 shadow-sm">Same factory contract:<br/>UI · REST · MCP</div>
      </div>
    </div>
  </StudioShell>;
}
