"use client";

import { useMemo, useState } from "react";
import { Check, CircleDollarSign, Loader2, Play, ReceiptText, ShieldCheck, Sparkles } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { createUGCFactoryPlan, renderUGCFactoryClip, type FactoryRenderResult, type UGCFactoryPlan } from "@/lib/studio-api";

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
  const [imageUrl, setImageUrl] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [plan, setPlan] = useState<UGCFactoryPlan | null>(null);
  const [receipt, setReceipt] = useState<FactoryRenderResult | null>(null);
  const [working, setWorking] = useState<"plan" | "render" | null>(null);
  const [error, setError] = useState("");

  const canPlan = useMemo(
    () => [product, audience, pain, mechanism].every((value) => value.trim().length >= 4),
    [product, audience, pain, mechanism],
  );

  const brief = { product, audience, pain, mechanism, offer, platform };

  async function buildPlan() {
    setWorking("plan");
    setError("");
    setReceipt(null);
    try {
      setPlan(await createUGCFactoryPlan(brief));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not build the batch plan.");
    } finally {
      setWorking(null);
    }
  }

  async function approveAndRender() {
    if (!plan?.gate.passed) return;
    setWorking("render");
    setError("");
    try {
      setReceipt(await renderUGCFactoryClip({ ...brief, clip_number: 1, approved: true, image_url: imageUrl || undefined }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not queue the approved render.");
    } finally {
      setWorking(null);
    }
  }

  return <StudioShell eyebrow="UGC ad factory">
    <PageHeader
      kicker="Create"
      title="Find the angle before you spend on the render."
      body="Describe the customer problem and why the product solves it. The studio turns that truth into a gated UGC production plan. You approve the paid generation only after you can inspect the scripts and flow."
      action={<StatusPill tone="blue">Agent-callable</StatusPill>}
    />

    <div className="grid gap-5 p-6 lg:grid-cols-[.82fr_1.18fr] lg:p-10">
      <section className="space-y-4 rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-[#2357ff]"/><h3 className="text-sm font-medium">Product truth</h3></div>
        <Field label="Product" value={product} onChange={setProduct} />
        <Field label="Audience" value={audience} onChange={setAudience} />
        <Area label="Customer pain" value={pain} onChange={setPain} rows={3} />
        <Area label="Product mechanism" value={mechanism} onChange={setMechanism} rows={3} />
        <Field label="Offer" value={offer} onChange={setOffer} />
        <Field label="Product / reference image URL" value={imageUrl} onChange={setImageUrl} placeholder="https://… optional" />
        <label className="block text-xs text-black/45">Platform<select value={platform} onChange={(event)=>setPlatform(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black"><option value="instagram">Instagram</option><option value="tiktok">TikTok</option><option value="youtube">YouTube Shorts</option></select></label>

        <button onClick={buildPlan} disabled={!canPlan || working !== null} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:opacity-45">
          {working === "plan" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}Build batch plan
        </button>
        <p className="text-[11px] leading-5 text-black/38">Planning does not publish anything or approve a paid media call.</p>
        {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">{error}</p>}
      </section>

      <section className="space-y-4 rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Production contract</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Truth → gate → approval → receipt</h3></div><StatusPill tone={receipt?.ok ? "green" : plan?.gate.passed ? "blue" : "neutral"}>{receipt?.ok ? "Render queued" : plan?.gate.passed ? "Gate passed" : "Draft"}</StatusPill></div>

        <div className="grid gap-2 sm:grid-cols-3">
          {(plan?.icm.stages || ["01_research","02_script_gate","03_cast","04_generate","05_seam_qa","06_deliver"]).map((stage, index) => {
            const active = plan ? index < 3 : index === 0;
            const queued = receipt?.ok && index === 3;
            return <div key={stage} className={`rounded-xl border px-3 py-3 ${queued ? "border-[#159653]/20 bg-[#ecf8f1]" : active ? "border-[#2357ff]/15 bg-[#edf1ff]" : "border-black/7 bg-white"}`}><p className="text-[9px] uppercase tracking-[.14em] text-black/35">0{index + 1}</p><p className="mt-1 text-xs font-medium">{STAGE_LABELS[stage] || stage}</p></div>;
          })}
        </div>

        {!plan ? <div className="grid min-h-[390px] place-items-center rounded-[20px] border border-dashed border-black/10 bg-white px-8 text-center"><div><ShieldCheck className="mx-auto h-8 w-8 text-black/25"/><h4 className="mt-4 text-base font-medium">Build the plan before generation</h4><p className="mx-auto mt-2 max-w-md text-xs leading-5 text-black/42">The plan exposes the scripts, mechanical gate, production stages, and estimated economics before a paid render can be approved.</p></div></div> : <>
          <div className="rounded-[20px] border border-black/7 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#159653]"/><p className="text-sm font-medium">Gate passed</p></div><span className="rounded-full bg-[#ecf8f1] px-3 py-1 text-[10px] font-semibold text-[#117341]">{plan.gate.checks.filter((check)=>check.passed).length}/{plan.gate.checks.length} CHECKS</span></div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">{plan.clips.map((clip)=><article key={clip.clip} className="rounded-2xl bg-[#f5f5f2] p-4"><p className="text-[10px] uppercase tracking-[.14em] text-black/35">Clip {clip.clip} · {clip.duration_seconds}s</p><p className="mt-3 text-sm leading-6 text-black/70">“{clip.script}”</p><p className="mt-3 text-[10px] text-black/35">{clip.script_word_count} spoken words · {clip.purpose.replaceAll("_", " ")}</p></article>)}</div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-black/7 bg-white p-4"><div className="flex items-center gap-2"><CircleDollarSign className="h-4 w-4 text-black/38"/><p className="text-xs font-medium">Plan economics</p></div><p className="mt-3 text-2xl font-semibold tracking-tight">${(plan.commercial.price_cents / 100).toFixed(0)} <span className="text-xs font-normal text-black/35">reference unit</span></p><p className="mt-1 text-[10px] leading-4 text-black/38">Estimate only. Planning never charges the customer.</p></div>
            <div className="rounded-2xl border border-black/7 bg-white p-4"><div className="flex items-center gap-2"><Check className="h-4 w-4 text-[#159653]"/><p className="text-xs font-medium">Human gates</p></div><p className="mt-3 text-xs leading-5 text-black/52">Paid render requires this click. Publishing remains a separate approval later.</p></div>
          </div>

          <button onClick={approveAndRender} disabled={!plan.gate.passed || working !== null} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#2357ff] px-4 py-3 text-sm font-medium text-white disabled:opacity-45">{working === "render" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}Approve & render clip 1</button>
        </>}

        <div className="rounded-[20px] border border-black/7 bg-[#10110f] p-5 text-white">
          <div className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-[#b9ff66]"/><h4 className="text-sm font-medium">Render receipt</h4></div>
          {receipt ? <div className="mt-4 grid gap-2 text-xs text-white/58"><ReceiptRow label="State" value={receipt.state || (receipt.ok ? "queued" : "failed")} /><ReceiptRow label="Provider" value={receipt.provider || (receipt.simulated ? "demo" : "not returned")} /><ReceiptRow label="Request" value={receipt.request_id || receipt.error || "not returned"} /><ReceiptRow label="Publish" value="Still requires human approval" /></div> : <p className="mt-3 text-xs leading-5 text-white/40">No paid render has been approved in this session.</p>}
        </div>
      </section>
    </div>
  </StudioShell>;
}

function Field({label,value,onChange,placeholder}:{label:string;value:string;onChange:(value:string)=>void;placeholder?:string}){return <label className="block text-xs text-black/45">{label}<input value={value} onChange={(event)=>onChange(event.target.value)} placeholder={placeholder} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black outline-none focus:border-[#2357ff]" /></label>}
function Area({label,value,onChange,rows}:{label:string;value:string;onChange:(value:string)=>void;rows:number}){return <label className="block text-xs text-black/45">{label}<textarea value={value} onChange={(event)=>onChange(event.target.value)} rows={rows} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 text-black outline-none focus:border-[#2357ff]" /></label>}
function ReceiptRow({label,value}:{label:string;value:string}){return <div className="grid grid-cols-[72px_1fr] gap-3"><span className="text-white/32">{label}</span><span className="break-all text-white/65">{value}</span></div>}
