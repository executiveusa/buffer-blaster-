"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CalendarDays,
  Clapperboard,
  Command,
  Compass,
  GalleryVerticalEnd,
  LayoutDashboard,
  Library,
  Network,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

const nav = [
  ["/studio", "Overview", LayoutDashboard],
  ["/studio/create", "Create UGC", Clapperboard],
  ["/studio/library", "My ads", Library],
  ["/studio/moodboards", "Moodboards", GalleryVerticalEnd],
  ["/studio/canvas", "Canvas", Network],
  ["/studio/campaigns", "Campaigns", Sparkles],
  ["/studio/calendar", "Calendar", CalendarDays],
  ["/studio/analytics", "Analytics", BarChart3],
  ["/studio/settings", "Settings", Settings],
] as const;

export function StudioShell({ children, eyebrow }: { children: ReactNode; eyebrow?: string }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-[#e9e9e7] text-[#151613]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[68px] flex-col items-center border-r border-black/5 bg-[#dedfdd] py-5 lg:flex">
        <Link href="/" className="grid h-10 w-10 place-items-center rounded-xl bg-white text-lg font-semibold shadow-sm" aria-label="Home">B</Link>
        <div className="mt-7 h-10 w-10 rounded-full bg-[conic-gradient(from_20deg,#6c63ff,#35d9a2,#dfff59,#ff7b5f,#6c63ff)]" aria-hidden />
        <div className="mt-7 grid gap-3">
          {[Command, Compass, Network, BarChart3].map((Icon, i) => <div key={i} className={`grid h-11 w-11 place-items-center rounded-xl ${i === 0 ? "bg-white shadow-sm" : "text-black/65"}`}><Icon className="h-5 w-5" /></div>)}
        </div>
        <div className="mt-auto grid h-10 w-10 place-items-center rounded-full bg-[#1d4f27] text-sm font-semibold text-white">B.</div>
      </aside>

      <aside className="fixed inset-y-0 left-[68px] z-20 hidden w-[260px] flex-col border-r border-black/8 bg-[#f7f7f5] px-4 py-6 lg:flex">
        <div className="px-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-black/38">Buffer Blaster</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Create → prove</h1>
        </div>
        <nav className="mt-7 space-y-1">
          {nav.map(([href, label, Icon]) => {
            const active = href === "/studio" ? pathname === href : pathname.startsWith(href);
            return <Link key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] transition ${active ? "bg-[#e7edff] font-medium text-[#2357ff]" : "text-black/72 hover:bg-black/[0.035] hover:text-black"}`}><Icon className="h-[18px] w-[18px]" /><span>{label}</span></Link>;
          })}
        </nav>
        <div className="mt-5 border-t border-black/8 pt-5">
          <div className="rounded-2xl border border-black/8 bg-white p-4 shadow-[0_12px_35px_rgba(0,0,0,.04)]">
            <p className="text-xs font-medium">Agent mode</p>
            <div className="mt-3 flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[#18a957]" /><span className="text-xs text-black/55">Ready for commands</span></div>
            <Link href="/studio" className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-black px-3 py-2.5 text-xs font-medium text-white"><Command className="h-3.5 w-3.5" />Open command center</Link>
          </div>
        </div>
        <div className="mt-auto rounded-2xl bg-[#eeeeeb] p-4">
          <div className="flex items-center gap-2 text-xs font-medium"><ShieldCheck className="h-4 w-4 text-[#159653]"/><span>Approval gate</span></div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-black/48"><span>Planning</span><span className="font-medium text-[#117341]">No spend</span></div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-black/48"><span>Render / publish</span><span className="font-medium">Human approval</span></div>
          <p className="mt-3 text-[11px] leading-relaxed text-black/42">The system keeps paid generation and publishing behind explicit approval.</p>
        </div>
      </aside>

      <div className="lg:pl-[328px]">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-black/6 bg-[#f7f7f5]/90 px-5 backdrop-blur-xl lg:hidden">
          <Link href="/studio" className="font-semibold tracking-tight">Buffer Blaster</Link>
          <Link href="/studio/create" className="rounded-full bg-black px-4 py-2 text-xs font-medium text-white">Create</Link>
        </header>
        <main className="min-h-screen p-3 sm:p-5 lg:p-3">
          <div className="min-h-[calc(100vh-24px)] rounded-[26px] border border-black/5 bg-[#fbfbfa] shadow-[0_1px_0_rgba(255,255,255,.8)_inset]">
            {eyebrow && <div className="border-b border-black/6 px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-black/35">{eyebrow}</div>}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
