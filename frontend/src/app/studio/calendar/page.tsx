"use client";

import { useState } from "react";
import { CalendarDays, CheckCircle2, ChevronLeft, ChevronRight, Clock3, ShieldCheck } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const items = [
  { day: 1, title: "Cold brew hook", platform: "Instagram", time: "9:00 AM", tone: "#d6b58e", approved: true },
  { day: 2, title: "Product proof", platform: "Facebook", time: "12:30 PM", tone: "#b9c5d4", approved: true },
  { day: 3, title: "UGC testimonial", platform: "TikTok", time: "6:00 PM", tone: "#c7b7a7", approved: false },
  { day: 4, title: "Carousel", platform: "Instagram", time: "10:15 AM", tone: "#aebe9d", approved: false },
  { day: 5, title: "Offer post", platform: "LinkedIn", time: "8:30 AM", tone: "#d8c7a9", approved: true },
  { day: 6, title: "Founder clip", platform: "YouTube", time: "5:00 PM", tone: "#b7afca", approved: false },
];

export default function CalendarPage() {
  const [selected, setSelected] = useState(items[2]);
  const [approved, setApproved] = useState(selected.approved);
  return <StudioShell eyebrow="Publishing calendar">
    <PageHeader kicker="Calendar" title="See what goes live before it does." body="Every scheduled item carries a platform, time, media state, and approval state. The publisher cannot bypass the approval check." action={<div className="flex items-center gap-2 rounded-xl border border-black/9 bg-white px-3 py-2 text-sm"><ChevronLeft className="h-4 w-4"/><span>Aug 2026</span><ChevronRight className="h-4 w-4"/></div>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[1.35fr_.65fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="grid grid-cols-7 gap-2 text-center text-[10px] font-semibold uppercase tracking-[0.14em] text-black/30">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(d=><div key={d} className="py-2">{d}</div>)}</div>
        <div className="mt-2 grid grid-cols-7 gap-2">{Array.from({length:21}).map((_,i)=>{const day=i+1;const item=items.find(x=>x.day===day);return <button key={day} onClick={()=>item&&(setSelected(item),setApproved(item.approved))} className={`min-h-28 rounded-2xl border p-2 text-left transition ${item&&selected.day===day?"border-[#2357ff] bg-[#f7f9ff]":"border-black/6 bg-[#fafaf8] hover:border-black/12"}`}><span className="text-[11px] text-black/35">{day}</span>{item&&<div className="mt-2 rounded-xl p-2.5" style={{background:`linear-gradient(145deg,${item.tone},#f4f1eb)`}}><p className="text-[10px] font-semibold">{item.title}</p><p className="mt-1 text-[9px] text-black/55">{item.time}</p><span className={`mt-2 inline-block h-1.5 w-1.5 rounded-full ${item.approved?"bg-[#148d4c]":"bg-[#d58a17]"}`} /></div>}</button>})}</div>
      </section>
      <aside className="space-y-4">
        <section className="rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
          <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Selected</p><h3 className="mt-1 text-lg font-semibold">{selected.title}</h3></div><CalendarDays className="h-5 w-5 text-black/28"/></div>
          <div className="mt-5 space-y-2 text-xs"><div className="flex justify-between rounded-xl bg-white px-3 py-3"><span className="text-black/42">Platform</span><strong>{selected.platform}</strong></div><div className="flex justify-between rounded-xl bg-white px-3 py-3"><span className="text-black/42">Time</span><strong>{selected.time}</strong></div><div className="flex justify-between rounded-xl bg-white px-3 py-3"><span className="text-black/42">Publisher</span><strong>TryPost</strong></div></div>
          <label className="mt-4 flex cursor-pointer items-center justify-between rounded-xl border border-black/8 bg-white px-3 py-3"><span><span className="block text-xs font-medium">Human approval</span><span className="mt-1 block text-[10px] text-black/38">Required before schedule API fires</span></span><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)} className="h-4 w-4 accent-black"/></label>
          <button disabled={!approved} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:bg-black/15 disabled:text-black/35">{approved?<CheckCircle2 className="h-4 w-4"/>:<ShieldCheck className="h-4 w-4"/>}{approved?"Ready to schedule":"Approval required"}</button>
        </section>
        <section className="rounded-[22px] border border-black/7 bg-white p-5"><div className="flex items-start gap-3"><Clock3 className="mt-0.5 h-4 w-4 text-[#b67711]"/><div><p className="text-sm font-medium">3 items need review</p><p className="mt-1 text-xs leading-5 text-black/42">Agents can prepare every detail. The final public action is yours.</p></div></div><div className="mt-4"><StatusPill tone="amber">Approval queue</StatusPill></div></section>
      </aside>
    </div>
  </StudioShell>;
}
