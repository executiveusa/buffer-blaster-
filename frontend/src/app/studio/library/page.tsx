import Link from "next/link";
import { Grid2X2, List, Play, Plus } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const ads = [
  ["Cold brew reveal", "UGC", "#d7ad7a", "Ready"],
  ["Skincare routine", "Beauty", "#e3c7bd", "Scheduled"],
  ["Unboxing cut", "UGC", "#b8c9a7", "Review"],
  ["Summer try-on", "UGC", "#ccb69e", "Ready"],
  ["Product proof", "Tutorial", "#a8b9ca", "Rendering"],
  ["Founder story", "UGC", "#cfb5aa", "Scheduled"],
  ["Three ways to style", "UGC", "#c8b7d2", "Ready"],
  ["Before / after", "Beauty", "#d8c7a8", "Review"],
  ["Desk setup", "Tutorial", "#b8b7ab", "Ready"],
  ["Ingredient proof", "Beauty", "#d3bfb1", "Scheduled"],
  ["Problem / solution", "UGC", "#c5c8b4", "Ready"],
  ["15-second hook", "UGC", "#b8c2cc", "Rendering"],
] as const;

export default function LibraryPage() {
  return <StudioShell eyebrow="Creative library"><PageHeader kicker="My ads" title="Everything you have made." body="Renders, approved variants, scheduled assets, and campaign outputs stay in one reviewable library." action={<div className="flex gap-2"><button className="grid h-10 w-10 place-items-center rounded-xl border border-black/10 bg-white"><Grid2X2 className="h-4 w-4"/></button><button className="grid h-10 w-10 place-items-center rounded-xl border border-black/10 bg-white text-black/35"><List className="h-4 w-4"/></button><Link href="/studio/create" className="inline-flex items-center gap-2 rounded-xl bg-black px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4"/>Create</Link></div>} />
  <div className="p-6 lg:p-10"><div className="mb-6 rounded-2xl border border-black/7 bg-white p-5"><div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Render queue</p><p className="mt-1 text-sm font-medium">2 videos processing · 3 awaiting review</p></div><StatusPill tone="blue">Live queue</StatusPill></div><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-black/6"><div className="h-full w-[42%] rounded-full bg-[#2357ff]"/></div></div>
  <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">{ads.map(([name,type,color,status],i)=><article key={name} className="group overflow-hidden rounded-2xl border border-black/7 bg-white shadow-[0_12px_35px_rgba(0,0,0,.035)]"><div className="relative aspect-[4/5]" style={{background:`linear-gradient(145deg, ${color}, #f4f1ea 64%)`}}><div className="absolute inset-x-3 top-3 flex justify-between"><span className="rounded-full bg-black/70 px-2 py-1 text-[10px] font-medium text-white backdrop-blur">{type}</span><span className="rounded-full bg-white/75 px-2 py-1 text-[10px] font-medium text-black/65 backdrop-blur">{i+1}</span></div><div className="absolute inset-0 grid place-items-center"><div className="grid h-12 w-12 place-items-center rounded-full bg-white/80 shadow-lg transition group-hover:scale-105"><Play className="h-5 w-5 fill-black"/></div></div><div className="absolute inset-x-3 bottom-3 rounded-xl bg-black/70 p-3 text-white backdrop-blur"><p className="text-sm font-medium">{name}</p><p className="mt-1 text-[10px] text-white/55">9:16 · 10 sec</p></div></div><div className="flex items-center justify-between p-3"><p className="text-xs text-black/42">Score {78+i%8}</p><StatusPill tone={status==="Ready"?"green":status==="Review"?"amber":"neutral"}>{status}</StatusPill></div></article>)}</div></div></StudioShell>;
}
