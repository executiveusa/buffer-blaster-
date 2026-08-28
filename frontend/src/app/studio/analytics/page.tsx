import { ArrowUpRight, BarChart3, Eye, MousePointerClick, ShoppingBag, TrendingUp } from "lucide-react";
import { Metric, PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const bars = [36,48,42,61,55,70,66,78,74,82,69,88];

export default function AnalyticsPage() {
  return <StudioShell eyebrow="Performance learning">
    <PageHeader kicker="Analytics" title="Make the next campaign from what worked." body="V1 keeps the important loop visible: creative → publish → results → next brief. TryPost is the publishing kernel; the studio owns the interpretation." action={<StatusPill tone="green">Learning loop</StatusPill>} />
    <div className="space-y-5 p-6 lg:p-10">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Reach" value="84.2K" detail="+18% vs prior period"/><Metric label="Engaged" value="6.4K" detail="7.6% engagement rate"/><Metric label="Clicks" value="1,284" detail="+22% from UGC"/><Metric label="Attributed orders" value="96" detail="7.5% click-to-order"/></div>
      <div className="grid gap-5 xl:grid-cols-[1.25fr_.75fr]">
        <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]"><div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Creative performance</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Engagement index</h3></div><TrendingUp className="h-5 w-5 text-[#159653]"/></div><div className="mt-8 flex h-64 items-end gap-2 rounded-2xl bg-[#f7f7f4] p-5">{bars.map((h,i)=><div key={i} className="flex-1 rounded-t-md bg-black/10 transition hover:bg-[#2357ff]" style={{height:`${h}%`}} title={`Index ${h}`}/>)}</div><div className="mt-4 flex justify-between text-[10px] text-black/32"><span>Aug 1</span><span>Aug 7</span><span>Aug 14</span><span>Aug 21</span><span>Aug 28</span></div></section>
        <section className="rounded-[22px] border border-black/7 bg-[#10110f] p-5 text-white"><p className="text-xs text-white/40">Agent read</p><h3 className="mt-1 text-xl font-semibold tracking-tight">What changed</h3><div className="mt-5 space-y-3"><Insight icon={<Eye className="h-4 w-4"/>} title="Product-on-screen opens win" body="Hooks showing the product in the first second beat talking-head opens by 19%."/><Insight icon={<MousePointerClick className="h-4 w-4"/>} title="Specific CTAs beat generic ones" body="Offer-specific CTAs drove 1.4× more clicks than “learn more.”"/><Insight icon={<ShoppingBag className="h-4 w-4"/>} title="UGC is carrying purchase intent" body="Two testimonial variants account for 31% of attributed orders."/></div><button className="mt-5 flex w-full items-center justify-between rounded-xl bg-white px-4 py-3 text-sm font-medium text-black">Use this in next campaign <ArrowUpRight className="h-4 w-4"/></button></section>
      </div>
    </div>
  </StudioShell>;
}

function Insight({icon,title,body}:{icon:React.ReactNode;title:string;body:string}){return <div className="rounded-2xl bg-white/[0.06] p-4"><div className="flex items-center gap-2 text-[#b9ff66]">{icon}<p className="text-xs font-medium text-white">{title}</p></div><p className="mt-2 text-xs leading-5 text-white/48">{body}</p></div>}
