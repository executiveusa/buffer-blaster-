"use client";

import { useState } from "react";
import { ArrowRight, CalendarDays, Check, Sparkles } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const formats = ["UGC testimonial", "Product proof", "Carousel", "Offer post", "Founder story", "Tutorial reel", "Community proof"];

export default function CampaignsPage() {
  const [objective, setObjective] = useState("Launch our summer offer and drive qualified Shopify sales without sounding promotional.");
  const [days, setDays] = useState(7);
  const [generated, setGenerated] = useState(true);
  return <StudioShell eyebrow="Campaign orchestration">
    <PageHeader kicker="Campaigns" title="Give the agent an outcome, not a to-do list." body="The campaign planner turns one objective into a bounded sequence of content. Each item stays editable and nothing reaches publishing until you approve it." action={<StatusPill tone="green">Human gate on</StatusPill>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[.72fr_1.28fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <p className="text-xs font-medium">Campaign brief</p>
        <label className="mt-5 block text-xs text-black/45">Brand<input defaultValue="Cella Coffee" className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]" /></label>
        <label className="mt-4 block text-xs text-black/45">Objective<textarea value={objective} onChange={e=>setObjective(e.target.value)} rows={5} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 outline-none focus:border-[#2357ff]" /></label>
        <label className="mt-4 block text-xs text-black/45">Audience<input defaultValue="Busy coffee drinkers who buy premium products online" className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]" /></label>
        <label className="mt-4 block text-xs text-black/45">Offer<input defaultValue="20% off first order" className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]" /></label>
        <div className="mt-4 grid grid-cols-2 gap-3"><label className="text-xs text-black/45">Length<select value={days} onChange={e=>setDays(Number(e.target.value))} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm"><option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option></select></label><label className="text-xs text-black/45">Platforms<div className="mt-2 rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm">IG · FB · TikTok</div></label></div>
        <button onClick={()=>setGenerated(true)} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white"><Sparkles className="h-4 w-4"/>Generate campaign</button>
      </section>
      <section className="rounded-[22px] border border-black/7 bg-[#f5f5f2] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Plan</p><h3 className="mt-1 text-xl font-semibold tracking-tight">{days}-day launch sequence</h3></div><CalendarDays className="h-5 w-5 text-black/30"/></div>
        {generated && <div className="mt-5 space-y-2">{Array.from({length:Math.min(days,7)}).map((_,i)=><div key={i} className="grid grid-cols-[44px_1fr_auto] items-center gap-3 rounded-2xl border border-black/6 bg-white p-3.5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f2f2ef] text-xs font-semibold">{i+1}</div><div><p className="text-sm font-medium">{formats[i%formats.length]}</p><p className="mt-1 text-[11px] text-black/40">{["Problem + tension","Product proof","Use case","Offer + urgency","Founder proof","How it works","Community signal"][i%7]} · Draft</p></div><button className="grid h-9 w-9 place-items-center rounded-xl border border-black/8 text-black/45"><ArrowRight className="h-4 w-4"/></button></div>)}</div>}
        <div className="mt-5 rounded-2xl bg-[#10110f] p-4 text-white"><div className="flex items-start gap-3"><Check className="mt-0.5 h-4 w-4 text-[#b9ff66]"/><div><p className="text-sm font-medium">Safe autonomy boundary</p><p className="mt-1 text-xs leading-5 text-white/50">The agent can research, plan, draft, generate and score. Scheduling becomes legal only after a human approval receipt exists.</p></div></div></div>
      </section>
    </div>
  </StudioShell>;
}
