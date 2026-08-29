"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Check, CircleDollarSign, Loader2, Play, ReceiptText, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { createUGCFactoryPlan, type UGCFactoryPlan } from "@/lib/studio-api";
import { activateTrial, createTrialFactoryPlan, executeTrialFactoryAd, getTrialStatus, type TrialStatus } from "@/lib/trial-api";

const STAGE_LABELS: Record<string, string> = {
  "01_research": "Research truth",
  "02_script_gate": "Script gate",
  "03_cast": "Cast direction",
  "04_generate": "Generate",
  "05_seam_qa": "Seam QA",
  "06_deliver": "Deliver",
};

export default function CreateUGCPage() {
  const [product, setProduct] = useState("Cold brew concentrate");
  const [audience, setAudience] = useState("busy coffee drinkers who want cafe-quality cold brew at home");
  const [pain, setPain] = useState("I keep spending too much on cold brew that tastes inconsistent");
  const [mechanism, setMechanism] = useState("one measured concentrate-to-water ratio makes the result repeatable in seconds");
  const [offer, setOffer] = useState("15% off the first bottle");
  const [platform, setPlatform] = useState("instagram");
  const [plan, setPlan] = useState<UGCFactoryPlan | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [trial, setTrial] = useState<TrialStatus>({ ok: false, active: false });
  const [working, setWorking] = useState<"activate" | "plan" | "render" | null>(null);
  const [error, setError] = useState("");

  const brief = { product, audience, pain, mechanism, offer, platform };
  const canPlan = useMemo(() => [product, audience, pain, mechanism].every((value) => value.trim().length >= 4), [product, audience, pain, mechanism]);
  const estimatedCost = plan?.commercial.estimated_generation_cost_cents || 0;
  const estimatedCredits = plan ? Math.max(1, Math.ceil(estimatedCost / 100)) : 0;
  const hasEnoughCredits = Boolean(trial.active && trial.trial && trial.trial.remaining_ad_credits >= estimatedCredits);

  useEffect(() => {
    let alive = true;
    async function boot() {
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get("session_id");
      if (params.get("checkout") === "success" && sessionId) {
        setWorking("activate");
        try {
          await activateTrial(sessionId);
          window.history.replaceState({}, "", "/studio/create");
        } catch (requestError) {
          if (alive) setError(requestError instanceof Error ? requestError.message : "Could not activate the paid pass.");
        } finally {
          if (alive) setWorking(null);
        }
      }
      try {
        const status = await getTrialStatus();
        if (alive) setTrial(status);
      } catch {
        if (alive) setTrial({ ok: false, active: false });
      }
    }
    void boot();
    return () => { alive = false; };
  }, []);

  async function refreshTrial() {
    try { setTrial(await getTrialStatus()); } catch { setTrial({ ok: false, active: false }); }
  }

  async function buildPlan() {
    setWorking("plan");
    setError("");
    setResult(null);
    try {
      setPlan(trial.active ? await createTrialFactoryPlan(brief) : await createUGCFactoryPlan(brief));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not build the ad plan.");
    } finally {
      setWorking(null);
    }
  }

  async function approveAndBuildFinalAd() {
    if (!plan?.gate.passed || !trial.active) return;
    setWorking("render");
    setError("");
    try {
      const response = await executeTrialFactoryAd({ ...brief, approved: true });
      setResult(response);
      await refreshTrial();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not run the approved ad factory.");
      await refreshTrial();
    } finally {
      setWorking(null);
    }
  }

  const finalState = String(result?.state || "");
  const finalAsset = (result?.final_asset || null) as { signed_url?: string } | null;

  return <StudioShell eyebrow="UGC ad factory">
    <PageHeader
      kicker="Create"
      title="Find the angle. See the cost. Then approve the ad."
      body="Planning is free of provider spend. A paid generation starts only after the script gate passes, your active pass has enough credits, and you explicitly approve the estimated cost. The factory then runs both clips, continuity QA, stitching, storage, and the final receipt."
      action={<StatusPill tone={trial.active ? "green" : "blue"}>{trial.active ? `${trial.trial?.remaining_ad_credits ?? 0} credits left` : "Plan before spend"}</StatusPill>}
    />

    <div className="grid gap-5 p-6 lg:grid-cols-[.82fr_1.18fr] lg:p-10">
      <section className="space-y-4 rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        {working === "activate" ? <div className="flex items-center gap-2 rounded-xl bg-[#edf1ff] px-3 py-3 text-xs text-[#2357ff]"><Loader2 className="h-4 w-4 animate-spin" />Verifying payment and activating your credits…</div> : null}
        <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-[#2357ff]"/><h3 className="text-sm font-medium">Product truth</h3></div>
        <Field label="Product" value={product} onChange={setProduct} />
        <Field label="Audience" value={audience} onChange={setAudience} />
        <Area label="Customer pain" value={pain} onChange={setPain} rows={3} />
        <Area label="Product mechanism" value={mechanism} onChange={setMechanism} rows={3} />
        <Field label="Offer" value={offer} onChange={setOffer} />
        <label className="block text-xs text-black/45">Platform<select value={platform} onChange={(event)=>setPlatform(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black"><option value="instagram">Instagram</option><option value="tiktok">TikTok</option><option value="youtube">YouTube Shorts</option></select></label>
        <button onClick={buildPlan} disabled={!canPlan || working !== null} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:opacity-45">{working === "plan" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}Build ad plan</button>
        <p className="text-[11px] leading-5 text-black/38">Planning does not consume an Ad Credit and does not call a paid media model.</p>
        {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">{error}</p>}
      </section>

      <section className="space-y-4 rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Production contract</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Truth → gate → allowance → finished asset</h3></div><StatusPill tone={finalState === "finished" ? "green" : plan?.gate.passed ? "blue" : "neutral"}>{finalState === "finished" ? "Finished" : plan?.gate.passed ? "Gate passed" : "Draft"}</StatusPill></div>

        <div className="grid gap-2 sm:grid-cols-3">{(plan?.icm.stages || ["01_research","02_script_gate","03_cast","04_generate","05_seam_qa","06_deliver"]).map((stage, index) => <div key={stage} className={`rounded-xl border px-3 py-3 ${finalState === "finished" ? "border-[#159653]/20 bg-[#ecf8f1]" : plan && index < 3 ? "border-[#2357ff]/15 bg-[#edf1ff]" : "border-black/7 bg-white"}`}><p className="text-[9px] uppercase tracking-[.14em] text-black/35">0{index + 1}</p><p className="mt-1 text-xs font-medium">{STAGE_LABELS[stage] || stage}</p></div>)}</div>

        {!plan ? <div className="grid min-h-[330px] place-items-center rounded-[20px] border border-dashed border-black/10 bg-white px-8 text-center"><div><ShieldCheck className="mx-auto h-8 w-8 text-black/25"/><h4 className="mt-4 text-base font-medium">Build the plan before generation</h4><p className="mx-auto mt-2 max-w-md text-xs leading-5 text-black/42">You will see both scripts, the mechanical gate, estimated provider reserve, and required Ad Credits before a paid call can be approved.</p></div></div> : <>
          <div className="rounded-[20px] border border-black/7 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#159653]"/><p className="text-sm font-medium">Gate {plan.gate.passed ? "passed" : "blocked"}</p></div><span className="rounded-full bg-[#ecf8f1] px-3 py-1 text-[10px] font-semibold text-[#117341]">{plan.gate.checks.filter((check)=>check.passed).length}/{plan.gate.checks.length} CHECKS</span></div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">{plan.clips.map((clip)=><article key={clip.clip} className="rounded-2xl bg-[#f5f5f2] p-4"><p className="text-[10px] uppercase tracking-[.14em] text-black/35">Clip {clip.clip} · {clip.duration_seconds}s</p><p className="mt-3 text-sm leading-6 text-black/70">“{clip.script}”</p><p className="mt-3 text-[10px] text-black/35">{clip.script_word_count} spoken words · {clip.purpose.replaceAll("_", " ")}</p></article>)}</div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-black/7 bg-white p-4"><div className="flex items-center gap-2"><CircleDollarSign className="h-4 w-4 text-black/38"/><p className="text-xs font-medium">Estimated generation reserve</p></div><p className="mt-3 text-2xl font-semibold tracking-tight">${(estimatedCost / 100).toFixed(2)}</p><p className="mt-1 text-[10px] leading-4 text-black/38">Conservative estimate includes the bounded continuity retry budget.</p></div>
            <div className="rounded-2xl border border-black/7 bg-white p-4"><div className="flex items-center gap-2"><WalletCards className="h-4 w-4 text-[#2357ff]"/><p className="text-xs font-medium">Credits required</p></div><p className="mt-3 text-2xl font-semibold tracking-tight">{estimatedCredits}</p><p className="mt-1 text-[10px] leading-4 text-black/38">{trial.active ? `${trial.trial?.remaining_ad_credits ?? 0} available on your ${trial.trial?.offer_id}.` : "Start a paid pass to authorize generation."}</p></div>
          </div>

          {trial.active ? <button onClick={approveAndBuildFinalAd} disabled={!plan.gate.passed || !hasEnoughCredits || working !== null} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#2357ff] px-4 py-3 text-sm font-medium text-white disabled:opacity-45">{working === "render" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}Approve {estimatedCredits} credit{estimatedCredits === 1 ? "" : "s"} & build final ad</button> : <Link href="/pricing" className="flex w-full items-center justify-center rounded-xl bg-[#2357ff] px-4 py-3 text-sm font-medium text-white">Start with a paid test pass</Link>}
          {trial.active && !hasEnoughCredits ? <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">This plan needs {estimatedCredits} Ad Credits. Your active pass has {trial.trial?.remaining_ad_credits ?? 0}. Choose a lower-cost request or upgrade before generation.</p> : null}
        </>}

        <div className="rounded-[20px] border border-black/7 bg-[#10110f] p-5 text-white">
          <div className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-[#b9ff66]"/><h4 className="text-sm font-medium">Factory receipt</h4></div>
          {result ? <div className="mt-4 grid gap-2 text-xs text-white/58"><ReceiptRow label="State" value={String(result.state || result.error || "unknown")} /><ReceiptRow label="Job" value={String(result.job_id || "not returned")} /><ReceiptRow label="QA" value={String((result.qa as { seam_passed?: boolean } | undefined)?.seam_passed === true ? "seam passed" : "see job receipt")} /><ReceiptRow label="Publish" value="Still requires human approval" />{finalAsset?.signed_url ? <a href={finalAsset.signed_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-[#b9ff66] underline underline-offset-4">Open final asset</a> : null}</div> : <p className="mt-3 text-xs leading-5 text-white/40">No paid generation has been approved in this session.</p>}
        </div>
      </section>
    </div>
  </StudioShell>;
}

function Field({label,value,onChange}:{label:string;value:string;onChange:(value:string)=>void}){return <label className="block text-xs text-black/45">{label}<input value={value} onChange={(event)=>onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black outline-none focus:border-[#2357ff]" /></label>}
function Area({label,value,onChange,rows}:{label:string;value:string;onChange:(value:string)=>void;rows:number}){return <label className="block text-xs text-black/45">{label}<textarea value={value} onChange={(event)=>onChange(event.target.value)} rows={rows} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 text-black outline-none focus:border-[#2357ff]" /></label>}
function ReceiptRow({label,value}:{label:string;value:string}){return <div className="grid grid-cols-[72px_1fr] gap-3"><span className="text-white/32">{label}</span><span className="break-all text-white/65">{value}</span></div>}
