"use client";

import { useMemo, useState } from "react";
import { CalendarDays, CheckCircle2, Clock3, Loader2, Network, ShieldCheck } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { listSocialAccounts, scheduleDrop, type SocialAccount } from "@/lib/studio-api";

type Receipt = { external_id?: string; scheduled_at?: string; recorded_at?: string };

function platformKey(value: string) { return value.trim().toLowerCase().replace(/\s+/g, ""); }

export default function CalendarPage() {
  const [platform, setPlatform] = useState("instagram");
  const [format, setFormat] = useState("post");
  const [content, setContent] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [approved, setApproved] = useState(false);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [accountId, setAccountId] = useState("");
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [simulated, setSimulated] = useState(false);

  const matchingAccounts = useMemo(() => accounts.filter((account) => platformKey(account.platform) === platformKey(platform) && account.is_active !== false), [accounts, platform]);

  async function loadAccounts() {
    setLoadingAccounts(true);
    setError("");
    setReceipt(null);
    try {
      const response = await listSocialAccounts();
      setAccounts(response.accounts);
      setProvider(response.provider);
      setSimulated(Boolean(response.simulated));
      const first = response.accounts.find((account) => platformKey(account.platform) === platformKey(platform) && account.is_active !== false);
      setAccountId(first?.id || "");
      if (!first) setError(`No active ${platform} account is available. Connect an optional publishing integration first.`);
    } catch (requestError) {
      setAccounts([]);
      setAccountId("");
      setProvider(null);
      setError(requestError instanceof Error ? requestError.message : "Unable to load social accounts.");
    } finally {
      setLoadingAccounts(false);
    }
  }

  async function scheduleSelected() {
    setError("");
    setReceipt(null);
    if (!approved) return setError("Human approval is required before scheduling.");
    if (!accountId) return setError("Choose a connected social account before scheduling.");
    if (!content.trim()) return setError("Enter the exact content that should be scheduled.");
    if (!scheduledAt) return setError("Choose a future schedule date and time.");
    const scheduledDate = new Date(scheduledAt);
    if (Number.isNaN(scheduledDate.getTime()) || scheduledDate.getTime() <= Date.now()) return setError("Schedule time must be in the future.");

    setScheduling(true);
    try {
      const response = await scheduleDrop({
        id: `calendar-${Date.now()}`,
        content: content.trim(),
        format,
        platforms: [{ social_account_id: accountId, content_type: format }],
        scheduled_at: scheduledDate.toISOString(),
        approved: true,
      });
      setReceipt((response.receipt || null) as Receipt | null);
      setSimulated(Boolean(response.simulated));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Scheduling failed.");
    } finally {
      setScheduling(false);
    }
  }

  const ready = approved && Boolean(accountId) && Boolean(content.trim()) && Boolean(scheduledAt) && !scheduling;

  return <StudioShell eyebrow="Publishing calendar">
    <PageHeader kicker="Calendar" title="See what goes live before it does." body="This surface no longer invents scheduled posts. Resolve a real connected account, enter the exact content and time, approve it, and keep the returned scheduling receipt." action={<StatusPill tone={receipt ? "green" : "neutral"}>{receipt ? "Receipt recorded" : "No queued fiction"}</StatusPill>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[1fr_1fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Schedule state</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Only receipts count as scheduled</h3></div><CalendarDays className="h-5 w-5 text-black/30"/></div>
        <div className="mt-5 grid min-h-[360px] place-items-center rounded-2xl border border-dashed border-black/10 bg-[#fafaf8] p-8 text-center">
          {receipt ? <div className="max-w-md"><CheckCircle2 className="mx-auto h-9 w-9 text-[#159653]"/><h4 className="mt-4 text-lg font-semibold">Scheduling receipt returned</h4><p className="mt-3 break-all font-mono text-xs text-black/45">{receipt.external_id || "provider did not return an external ID"}</p><p className="mt-2 text-xs text-black/42">{receipt.scheduled_at || scheduledAt}</p>{simulated ? <div className="mt-4"><StatusPill tone="amber">Simulation only</StatusPill></div> : null}</div> : <div className="max-w-md"><Clock3 className="mx-auto h-9 w-9 text-black/20"/><h4 className="mt-4 text-lg font-semibold">No schedule receipt in this session</h4><p className="mt-2 text-sm leading-6 text-black/45">The old seeded calendar cards were removed. A scheduled state appears only after the publishing adapter returns evidence.</p></div>}
        </div>
      </section>

      <section className="rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Approved scheduling</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Prepare one exact drop</h3></div><ShieldCheck className="h-5 w-5 text-[#2357ff]"/></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-black/45">Platform<select value={platform} onChange={(event)=>{setPlatform(event.target.value);setAccountId("");setReceipt(null);}} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm"><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="tiktok">TikTok</option><option value="youtube">YouTube</option><option value="linkedin">LinkedIn</option></select></label>
          <label className="text-xs text-black/45">Format<select value={format} onChange={(event)=>setFormat(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm"><option value="post">Post</option><option value="reel">Reel</option><option value="story">Story</option><option value="carousel">Carousel</option></select></label>
        </div>
        <button type="button" onClick={()=>void loadAccounts()} disabled={loadingAccounts} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-black/10 bg-white px-4 py-3 text-xs font-medium disabled:opacity-45">{loadingAccounts?<Loader2 className="h-4 w-4 animate-spin"/>:<Network className="h-4 w-4"/>}{loadingAccounts?"Checking accounts…":"Resolve connected accounts"}</button>
        <p className="mt-2 text-[10px] text-black/35">Publisher: {provider || (simulated ? "demo simulation" : "not connected")}</p>
        {accounts.length > 0 ? <label className="mt-3 block text-xs text-black/45">Social account<select value={accountId} onChange={(event)=>setAccountId(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm"><option value="">Choose account</option>{matchingAccounts.map((account)=><option key={account.id} value={account.id}>{account.display_name || account.username || account.id}</option>)}</select></label> : null}
        <label className="mt-3 block text-xs text-black/45">Exact content<textarea value={content} onChange={(event)=>setContent(event.target.value)} rows={5} placeholder="Review and paste the exact copy that may go live." className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white px-3 py-3 text-sm leading-5 outline-none focus:border-[#2357ff]"/></label>
        <label className="mt-3 block text-xs text-black/45">Schedule date and time<input type="datetime-local" value={scheduledAt} onChange={(event)=>setScheduledAt(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-sm"/></label>
        <label className="mt-4 flex cursor-pointer items-center justify-between rounded-xl border border-black/8 bg-white px-3 py-3"><span><span className="block text-xs font-medium">Human approval</span><span className="mt-1 block text-[10px] text-black/38">Required before the schedule API fires</span></span><input type="checkbox" checked={approved} onChange={(event)=>setApproved(event.target.checked)} className="h-4 w-4 accent-black"/></label>
        <button type="button" onClick={()=>void scheduleSelected()} disabled={!ready} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:bg-black/15 disabled:text-black/35">{scheduling?<Loader2 className="h-4 w-4 animate-spin"/>:<CheckCircle2 className="h-4 w-4"/>}{scheduling?"Scheduling…":ready?"Schedule approved content":"Complete review first"}</button>
        {error ? <p className="mt-3 rounded-xl bg-[#fff4dd] px-3 py-2 text-[11px] leading-5 text-[#7a5312]" role="alert">{error}</p> : null}
      </section>
    </div>
  </StudioShell>;
}
