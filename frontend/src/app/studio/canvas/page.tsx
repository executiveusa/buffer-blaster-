import { ImageIcon, Play, Plus, Sparkles, WandSparkles } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const Node = ({ title, eyebrow, children, className = "" }: { title: string; eyebrow: string; children: React.ReactNode; className?: string }) => <div className={`relative rounded-2xl border border-black/10 bg-white p-4 shadow-[0_16px_45px_rgba(0,0,0,.08)] ${className}`}><span className="absolute -left-2 top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white bg-[#2357ff] shadow"/><p className="text-[9px] font-semibold uppercase tracking-[0.15em] text-black/35">{eyebrow}</p><h3 className="mt-1 text-sm font-semibold">{title}</h3><div className="mt-4">{children}</div><span className="absolute -right-2 top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white bg-black shadow"/></div>;

export default function CanvasPage() {
  return <StudioShell eyebrow="Workflow canvas">
    <PageHeader kicker="Canvas" title="Build the creative flow visually." body="A compact V1 canvas for product → prompt → render → review → publish. The same stages are available to agents through MCP and REST." action={<StatusPill tone="blue">Agent-readable</StatusPill>} />
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="studio-grid relative min-h-[680px] overflow-hidden rounded-[24px] border border-black/7 bg-[#f8f8f6] p-8 lg:p-12">
        <div className="absolute left-[16%] right-[12%] top-1/2 hidden h-px bg-black/10 xl:block" aria-hidden />
        <div className="relative grid gap-6 xl:grid-cols-4 xl:items-center">
          <Node title="Add product" eyebrow="Input"><div className="grid aspect-[4/3] place-items-center rounded-xl border border-dashed border-black/15 bg-[#fafaf8]"><div className="text-center"><ImageIcon className="mx-auto h-6 w-6 text-black/30"/><p className="mt-2 text-[11px] text-black/40">Image or URL</p></div></div></Node>
          <Node title="Creative brief" eyebrow="Agent"><div className="rounded-xl bg-[#f5f5f2] p-3 text-xs leading-5 text-black/50">“Make a natural 10s UGC ad for our cold brew. Quiet kitchen, morning light, product in frame.”</div><div className="mt-3 flex items-center gap-2 text-[10px] text-[#2357ff]"><Sparkles className="h-3.5 w-3.5"/>Prompt compiled</div></Node>
          <Node title="Video render" eyebrow="Media"><div className="flex items-center justify-between rounded-xl border border-black/8 px-3 py-3 text-xs"><span>Configured provider</span><WandSparkles className="h-4 w-4 text-black/35"/></div><button className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#b673ff] px-3 py-2.5 text-xs font-semibold text-black"><Play className="h-3.5 w-3.5 fill-black"/>Run render</button></Node>
          <Node title="Approve & schedule" eyebrow="Publish"><div className="space-y-2"><div className="flex items-center justify-between rounded-xl bg-[#f5f5f2] px-3 py-2.5 text-xs"><span>Human approval</span><span className="h-2.5 w-2.5 rounded-full bg-[#18a957]"/></div><div className="flex items-center justify-between rounded-xl bg-[#f5f5f2] px-3 py-2.5 text-xs"><span>TryPost receipt</span><span className="text-black/35">waiting</span></div></div></Node>
        </div>
        <button className="absolute bottom-6 left-6 grid h-11 w-11 place-items-center rounded-xl border border-black/10 bg-white shadow-sm"><Plus className="h-5 w-5"/></button>
        <div className="absolute bottom-6 right-6 rounded-xl border border-black/8 bg-white px-4 py-3 text-[10px] leading-5 text-black/45 shadow-sm">Factory state is explicit.<br/>Agents do not own hidden campaign state.</div>
      </div>
    </div>
  </StudioShell>;
}
