"use client";

import { useMemo, useState } from "react";
import { CalendarDays, CheckCircle2, ChevronLeft, ChevronRight, Clock3, Loader2, Network, ShieldCheck } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { listSocialAccounts, scheduleDrop, type SocialAccount } from "@/lib/studio-api";

const items = [
  { day: 1, title: "Cold brew hook", platform: "Instagram", time: "9:00 AM", tone: "#d6b58e", approved: true, format: "post" },
  { day: 2, title: "Product proof", platform: "Facebook", time: "12:30 PM", tone: "#b9c5d4", approved: true, format: "post" },
  { day: 3, title: "UGC testimonial", platform: "TikTok", time: "6:00 PM", tone: "#c7b7a7", approved: false, format: "reel" },
  { day: 4, title: "Carousel", platform: "Instagram", time: "10:15 AM", tone: "#aebe9d", approved: false, format: "carousel" },
  { day: 5, title: "Offer post", platform: "LinkedIn", time: "8:30 AM", tone: "#d8c7a9", approved: true, format: "post" },
  { day: 6, title: "Founder clip", platform: "YouTube", time: "5:00 PM", tone: "#b7afca", approved: false, format: "reel" },
] as const;

type Receipt = {
  external_id?: string;
  scheduled_at?: string;
  recorded_at?: string;
};

function platformKey(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, "");
}

export default function CalendarPage() {
  const [selected, setSelected] = useState(items[2]);
  const [approved, setApproved] = useState(selected.approved);
  const [content, setContent] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [format, setFormat] = useState<string>(selected.format);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [simulated, setSimulated] = useState(false);

  const matchingAccounts = useMemo(() => {
    const wanted = platformKey(selected.platform);
    return accounts.filter(account => platformKey(account.platform) === wanted && account.is_active !== false);
  }, [accounts, selected.platform]);

  function choose(item: typeof items[number]) {
    setSelected(item);
    setApproved(item.approved);
    setFormat(item.format);
    setContent("");
    setScheduledAt("");
    setAccountId("");
    setReceipt(null);
    setError(null);
    setSimulated(false);
  }

  async function loadAccounts() {
    setLoadingAccounts(true);
    setError(null);
    try {
      const response = await listSocialAccounts();
      setAccounts(response.accounts);
      setSimulated(Boolean(response.simulated));
      const wanted = platformKey(selected.platform);
      const first = response.accounts.find(account => platformKey(account.platform) === wanted && account.is_active !== false);
      setAccountId(first?.id || "");
      if (!first) setError(`No active ${selected.platform} account is available. Connect it in TryPost first.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load social accounts.");
    } finally {
      setLoadingAccounts(false);
    }
  }

  async function scheduleSelected() {
    setError(null);
    setReceipt(null);
    if (!approved) return setError("Human approval is required before scheduling.");
    if (!accountId) return setError("Choose a connected social account before scheduling.");
    if (!content.trim()) return setError("Review and enter the exact content that should be scheduled.");
    if (!scheduledAt) return setError("Choose a future schedule date and time.");

    const scheduledDate = new Date(scheduledAt);
    if (Number.isNaN(scheduledDate.getTime()) || scheduledDate.getTime() <= Date.now()) {
      return setError("Schedule time must be in the future.");
    }

    setScheduling(true);
    try {
      const response = await scheduleDrop({
        id: `calendar-${selected.day}-${Date.now()}`,
        content: content.trim(),
        format,
        platforms: [{ social_account_id: accountId, content_type: format }],
        scheduled_at: scheduledDate.toISOString(),
        approved: true,
      });
      setReceipt((response.receipt || null) as Receipt | null);
      setSimulated(Boolean(response.simulated));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scheduling failed.");
    } finally {
      setScheduling(false);
    }
  }

  const ready = approved && Boolean(accountId) && Boolean(content.trim()) && Boolean(scheduledAt) && !scheduling;

  return <StudioShell eyebrow="Publishing calendar">
    <PageHeader kicker="Calendar" title="See what goes live before it does." body="Every scheduled item carries a platform, time, exact content, connected account, and approval state. The publisher cannot bypass the approval check." action={<div className="flex items-center gap-2 rounded-xl border border-black/9 bg-white px-3 py-2 text-sm"><ChevronLeft className="h-4 w-4"/><span>Aug 2026</span><ChevronRight className="h-4 w-4"/></div>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[1.35fr_.65fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="grid grid-cols-7 gap-2 text-center text-[10px] font-semibold uppercase tracking-[0.14em] text-black/30">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(d=><div key={d} className="py-2">{d}</div>)}</div>
        <div className="mt-2 grid grid-cols-7 gap-2">{Array.from({length:21}).map((_,i)=>{const day=i+1;const item=items.find(x=>x.day===day);return <button key={day} onClick={()=>item&&choose(item)} className={`min-h-28 rounded-2xl border p-2 text-left transition ${item&&selected.day===day?"border-[#2357ff] bg-[#f7f9ff]":"border-black/6 bg-[#fafaf8] hover:border-black/12"}`}><span className="text-[11px] text-black/35">{day}</span>{item&&<div className="mt-2 rounded-xl p-2.5" style={{background:`linear-gradient(145deg,${item.tone},#f4f1eb)`}}><p className="text-[10px] font-semibold">{item.title}</p><p className="mt-1 text-[9px] text-black/55">{item.time}</p><span className={`mt-2 inline-block h-1.5 w-1.5 rounded-full ${item.approved?"bg-[#148d4c]":"bg-[#d58a17]"}`} /></div>}</button>})}</div>
      </section>
      <aside className="space-y-4">
        <section className="rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
          <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Selected</p><h3 className="mt-1 text-lg font-semibold">{selected.title}</h3></div><CalendarDays className="h-5 w-5 text-black/28"/></div>
          <div className="mt-5 space-y-2 text-xs"><div className="flex justify-between rounded-xl bg-white px-3 py-3"><span className="text-black/42">Platform</span><strong>{selected.platform}</strong></div><div className="flex justify-between rounded-xl bg-white px-3 py-3"><span className="text-black/42">Publisher</span><strong>TryPost</strong></div></div>

          <button type="button" onClick={() => void loadAccounts()} disabled={loadingAccounts} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-black/10 bg-white px-4 py-3 text-xs font-medium disabled:opacity-45">{loadingAccounts?<Loader2 className="h-4 w-4 animate-spin"/>:<Network className="h-4 w-4"/>}{loadingAccounts?"Checking accounts…":"Resolve connected accounts"}</button>
          {accounts.length > 0 && <label className="mt-3 block text-xs text-black/45">Social account<select value={accountId} onChange={e=>setAccountId(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm text-black"><option value="">Choose account</option>{matchingAccounts.map(account=><option key={account.id} value={account.id}>{account.display_name || account.username || account.id}</option>)}</select></label>}

          <label className="mt-3 block text-xs text-black/45">Format<select value={format} onChange={e=>setFormat(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm text-black"><option value="post">Post</option><option value="reel">Reel</option><option value="story">Story</option><option value="carousel">Carousel</option></select></label>
          <label className="mt-3 block text-xs text-black/45">Exact content<textarea value={content} onChange={e=>setContent(e.target.value)} rows={4} placeholder="Paste or review the exact copy that may be scheduled." className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white px-3 py-3 text-sm leading-5 text-black outline-none focus:border-[#2357ff]"/></label>
          <label className="mt-3 block text-xs text-black/45">Schedule date and time<input type="datetime-local" value={scheduledAt} onChange={e=>setScheduledAt(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm text-black"/></label>

          <label className="mt-4 flex cursor-pointer items-center justify-between rounded-xl border border-black/8 bg-white px-3 py-3"><span><span className="block text-xs font-medium">Human approval</span><span className="mt-1 block text-[10px] text-black/38">Required before schedule API fires</span></span><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)} className="h-4 w-4 accent-black"/></label>
          <button type="button" onClick={() => void scheduleSelected()} disabled={!ready} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:bg-black/15 disabled:text-black/35">{scheduling?<Loader2 className="h-4 w-4 animate-spin"/>:approved?<CheckCircle2 className="h-4 w-4"/>:<ShieldCheck className="h-4 w-4"/>}{scheduling?"Scheduling…":ready?"Schedule approved content":"Complete review first"}</button>
          {error && <p className="mt-3 rounded-xl bg-[#fff4dd] px-3 py-2 text-[11px] leading-5 text-[#7a5312]" role="alert">{error}</p>}
          {receipt && <div className="mt-3 rounded-xl bg-white p-3 text-xs"><div className="flex items-center justify-between"><strong>Schedule receipt</strong>{simulated&&<StatusPill tone="amber">Simulation only</StatusPill>}</div><p className="mt-2 break-all text-[10px] text-black/45">ID: {receipt.external_id || "pending"}</p><p className="mt-1 text-[10px] text-black/45">{receipt.scheduled_at}</p></div>}
        </section>
        <section className="rounded-[22px] border border-black/7 bg-white p-5"><div className="flex items-start gap-3"><Clock3 className="mt-0.5 h-4 w-4 text-[#b67711]"/><div><p className="text-sm font-medium">3 items need review</p><p className="mt-1 text-xs leading-5 text-black/42">Agents can prepare every detail. The final public action is yours.</p></div></div><div className="mt-4"><StatusPill tone="amber">Approval queue</StatusPill></div></section>
      </aside>
    </div>
  </StudioShell>;
}
