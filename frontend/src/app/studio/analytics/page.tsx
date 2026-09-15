import Link from "next/link";
import { BarChart3, FileSearch, TrendingUp } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

export default function AnalyticsPage() {
  return <StudioShell eyebrow="Performance learning">
    <PageHeader kicker="Analytics" title="Results." body="Results appear after a published ad sends back data." action={<StatusPill tone="neutral">Waiting for data</StatusPill>} />
    <div className="grid gap-5 p-6 lg:p-10 xl:grid-cols-[1.2fr_.8fr]">
      <section className="grid min-h-[420px] place-items-center rounded-[22px] border border-dashed border-black/10 bg-white p-8 text-center shadow-[0_16px_45px_rgba(0,0,0,.025)]"><div className="max-w-lg"><BarChart3 className="mx-auto h-10 w-10 text-black/18"/><h2 className="mt-5 text-2xl font-semibold tracking-tight">No results yet</h2><p className="mt-3 text-sm leading-6 text-black/45">Publish an approved ad and connect its channel to see results.</p><div className="mt-6 flex justify-center gap-2"><Link href="/studio/create" className="rounded-xl bg-black px-4 py-3 text-sm font-medium text-white">Create an ad</Link><Link href="/studio/library" className="rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-medium">View receipts</Link></div></div></section>
      <section className="rounded-[22px] border border-black/7 bg-[#10110f] p-6 text-white"><p className="text-xs text-white/38">What is needed</p><h3 className="mt-2 text-xl font-semibold tracking-tight">Before results appear</h3><div className="mt-6 space-y-3"><Requirement icon={<FileSearch className="h-4 w-4"/>} title="1. Content receipt" body="A canonical content item or finished creative job identifies exactly what ran."/><Requirement icon={<TrendingUp className="h-4 w-4"/>} title="2. Performance event" body="Reach, clicks, purchases, or other metrics must name their source and observed time."/><Requirement icon={<BarChart3 className="h-4 w-4"/>} title="3. Comparable evidence" body="Only then can the studio compare hooks, formats, or offers and form the next hypothesis."/></div><p className="mt-6 rounded-xl bg-white/[0.06] p-4 text-xs leading-5 text-white/45">This page stays empty until real channel data arrives.</p></section>
    </div>
  </StudioShell>;
}

function Requirement({icon,title,body}:{icon:React.ReactNode;title:string;body:string}){return <div className="rounded-2xl bg-white/[0.06] p-4"><div className="flex items-center gap-2 text-[#b9ff66]">{icon}<p className="text-xs font-medium text-white">{title}</p></div><p className="mt-2 text-xs leading-5 text-white/48">{body}</p></div>}
