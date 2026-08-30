"use client";

import { useState } from "react";
import { CalendarDays, Check, Loader2, Sparkles } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { createCampaignPlan, type CampaignPlan } from "@/lib/campaign-api";

export default function CampaignsPage() {
  const [brand, setBrand] = useState("Cella Coffee");
  const [objective, setObjective] = useState("Launch our summer offer and drive qualified Shopify sales without sounding promotional.");
  const [audience, setAudience] = useState("Busy coffee drinkers who buy premium products online");
  const [offer, setOffer] = useState("20% off first order");
  const [days, setDays] = useState(7);
  const [platforms, setPlatforms] = useState(["instagram", "facebook", "tiktok"]);
  const [plan, setPlan] = useState<CampaignPlan | null>(null);
  const [simulated, setSimulated] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    setWorking(true);
    setError("");
    try {
      const result = await createCampaignPlan({ brand, objective, audience, offer, duration_days: days, platforms });
      setPlan(result.plan);
      setSimulated(Boolean(result.simulated));
    } catch (requestError) {
      setPlan(null);
      setSimulated(false);
      setError(requestError instanceof Error ? requestError.message : "Campaign planning failed.");
    } finally {
      setWorking(false);
    }
  }

  function togglePlatform(value: string) {
    setPlatforms((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }

  return <StudioShell eyebrow="Campaign orchestration">
    <PageHeader kicker="Campaigns" title="Give the agent an outcome, not a to-do list." body="The campaign planner now calls the same canonical campaign service used by REST and MCP. In live mode, the returned plan is persisted before it appears here." action={<StatusPill tone={simulated ? "amber" : "green"}>{simulated ? "Simulation only" : "Human gate on"}</StatusPill>} />
    <div className="grid gap-5 p-6 xl:grid-cols-[.72fr_1.28fr] lg:p-10">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <p className="text-xs font-medium">Campaign brief</p>
        <Field label="Brand" value={brand} onChange={setBrand}/>
        <label className="mt-4 block text-xs text-black/45">Objective<textarea value={objective} onChange={(event)=>setObjective(event.target.value)} rows={5} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 outline-none focus:border-[#2357ff]" /></label>
        <Field label="Audience" value={audience} onChange={setAudience}/>
        <Field label="Offer" value={offer} onChange={setOffer}/>
        <label className="mt-4 block text-xs text-black/45">Length<select value={days} onChange={(event)=>setDays(Number(event.target.value))} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm"><option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option></select></label>
        <div className="mt-4"><p className="text-xs text-black/45">Platforms</p><div className="mt-2 flex flex-wrap gap-2">{["instagram","facebook","tiktok","youtube"].map((platform)=><button key={platform} type="button" onClick={()=>togglePlatform(platform)} className={`rounded-full border px-3 py-2 text-xs capitalize ${platforms.includes(platform)?"border-black bg-black text-white":"border-black/10 bg-white text-black/50"}`}>{platform}</button>)}</div></div>
        <button onClick={()=>void generate()} disabled={working || !brand.trim() || !objective.trim() || platforms.length === 0} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:opacity-40">{working?<Loader2 className="h-4 w-4 animate-spin"/>:<Sparkles className="h-4 w-4"/>}{working?"Planning…":"Generate canonical campaign"}</button>
        {error ? <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p> : null}
      </section>
      <section className="rounded-[22px] border border-black/7 bg-[#f5f5f2] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Plan</p><h3 className="mt-1 text-xl font-semibold tracking-tight">{plan ? `${plan.days.length}-day sequence` : "No plan generated yet"}</h3></div><CalendarDays className="h-5 w-5 text-black/30"/></div>
        {plan ? <div className="mt-5 space-y-2">{plan.days.map((item)=><div key={item.day} className="grid grid-cols-[44px_1fr_auto] items-center gap-3 rounded-2xl border border-black/6 bg-white p-3.5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f2f2ef] text-xs font-semibold">{item.day}</div><div><p className="text-sm font-medium capitalize">{item.format.replaceAll("_"," ")}</p><p className="mt-1 text-[11px] text-black/40">{item.angle} · {item.state}</p><p className="mt-1 text-[10px] text-black/30">{item.platforms.join(" · ")}</p></div><StatusPill tone={simulated?"amber":"neutral"}>{simulated?"simulation":"draft"}</StatusPill></div>)}</div> : <div className="mt-5 grid min-h-[320px] place-items-center rounded-2xl border border-dashed border-black/10 bg-white p-8 text-center"><div><Sparkles className="mx-auto h-8 w-8 text-black/20"/><p className="mt-4 text-sm font-medium">No invented campaign cards</p><p className="mx-auto mt-2 max-w-md text-xs leading-5 text-black/42">Generate a plan to see the exact response from the campaign service. Live mode persists it to the canonical ledger first.</p></div></div>}
        <div className="mt-5 rounded-2xl bg-[#10110f] p-4 text-white"><div className="flex items-start gap-3"><Check className="mt-0.5 h-4 w-4 text-[#b9ff66]"/><div><p className="text-sm font-medium">Safe autonomy boundary</p><p className="mt-1 text-xs leading-5 text-white/50">The agent can plan and prepare. Scheduling remains a separate action and is rejected without explicit human approval.</p></div></div></div>
      </section>
    </div>
  </StudioShell>;
}

function Field({label,value,onChange}:{label:string;value:string;onChange:(value:string)=>void}) { return <label className="mt-4 block text-xs text-black/45">{label}<input value={value} onChange={(event)=>onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]" /></label>; }
