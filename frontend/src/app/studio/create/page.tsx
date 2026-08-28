"use client";

import { useMemo, useState } from "react";
import { ImagePlus, Loader2, Play, Sparkles, Video } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { createUGCPrompt, queueUGCRender } from "@/lib/studio-api";

export default function CreateUGCPage() {
  const [product, setProduct] = useState("Cold brew concentrate");
  const [idea, setIdea] = useState("A creator opens the bottle, pours it over ice, takes a sip, and reacts with understated surprise at how smooth it tastes.");
  const [dialogue, setDialogue] = useState("I stopped buying $7 cold brew after this showed up.");
  const [imageUrl, setImageUrl] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [duration, setDuration] = useState("10");
  const [prompt, setPrompt] = useState("");
  const [job, setJob] = useState<Record<string, unknown> | null>(null);
  const [working, setWorking] = useState(false);
  const canRun = useMemo(() => idea.trim().length > 12, [idea]);

  async function buildPrompt() {
    setWorking(true);
    try {
      const result = await createUGCPrompt({ idea, product, dialogue, image_url: imageUrl || undefined, platform, duration, aspect_ratio: "9:16", style: "realistic commercial", motion: "natural creator movement, product remains visible, one continuous take" });
      setPrompt(result.prompt);
    } finally { setWorking(false); }
  }

  async function render() {
    setWorking(true);
    try {
      const result = await queueUGCRender({ idea, product, dialogue, image_url: imageUrl || undefined, platform, duration, aspect_ratio: "9:16", style: "realistic commercial", motion: "natural creator movement, product remains visible, one continuous take" });
      setJob(result);
    } finally { setWorking(false); }
  }

  return <StudioShell eyebrow="UGC production">
    <PageHeader kicker="Create" title="Turn a product into an ad." body="Start with the product and the idea. The studio compiles a clean video prompt, then routes the render through the configured media provider." action={<StatusPill tone="blue">Agent-ready</StatusPill>} />
    <div className="grid gap-5 p-6 lg:grid-cols-[.82fr_1.18fr] lg:p-10">
      <section className="space-y-4 rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center gap-2"><ImagePlus className="h-4 w-4 text-black/45"/><h3 className="text-sm font-medium">Creative brief</h3></div>
        <label className="block text-xs text-black/45">Product<input value={product} onChange={e=>setProduct(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black outline-none focus:border-[#2357ff]" /></label>
        <label className="block text-xs text-black/45">Product / reference image URL<input value={imageUrl} onChange={e=>setImageUrl(e.target.value)} placeholder="https://… optional" className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black outline-none focus:border-[#2357ff]" /></label>
        <label className="block text-xs text-black/45">What should happen?<textarea value={idea} onChange={e=>setIdea(e.target.value)} rows={5} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 text-black outline-none focus:border-[#2357ff]" /></label>
        <label className="block text-xs text-black/45">Dialogue<textarea value={dialogue} onChange={e=>setDialogue(e.target.value)} rows={3} className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm leading-6 text-black outline-none focus:border-[#2357ff]" /></label>
        <div className="grid grid-cols-2 gap-3"><label className="text-xs text-black/45">Platform<select value={platform} onChange={e=>setPlatform(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black"><option value="instagram">Instagram</option><option value="tiktok">TikTok</option><option value="youtube">YouTube Shorts</option></select></label><label className="text-xs text-black/45">Length<select value={duration} onChange={e=>setDuration(e.target.value)} className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm text-black"><option>5</option><option>10</option><option>15</option><option>30</option></select></label></div>
        <div className="grid grid-cols-2 gap-2 pt-2"><button onClick={buildPrompt} disabled={!canRun||working} className="inline-flex items-center justify-center gap-2 rounded-xl border border-black/10 px-4 py-3 text-sm font-medium disabled:opacity-45"><Sparkles className="h-4 w-4"/>Build prompt</button><button onClick={render} disabled={!canRun||working} className="inline-flex items-center justify-center gap-2 rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:opacity-45">{working?<Loader2 className="h-4 w-4 animate-spin"/>:<Play className="h-4 w-4"/>}Queue render</button></div>
      </section>

      <section className="rounded-[22px] border border-black/7 bg-[#f4f4f1] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Production flow</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Product → prompt → video</h3></div><StatusPill tone={job?"green":"neutral"}>{job?"Queued":"Draft"}</StatusPill></div>
        <div className="studio-grid mt-5 min-h-[520px] rounded-[20px] border border-black/6 bg-[#fafaf9] p-5 sm:p-8">
          <div className="grid gap-5 xl:grid-cols-[.9fr_1.1fr_1fr] xl:items-center">
            <div className="rounded-2xl border border-black/9 bg-white p-4 shadow-sm"><p className="text-xs font-medium">1 · Product</p><div className="mt-3 grid aspect-[4/3] place-items-center rounded-xl border border-dashed border-black/15 bg-[#fafaf8] text-center"><div><ImagePlus className="mx-auto h-6 w-6 text-black/28"/><p className="mt-2 text-xs text-black/42">{imageUrl?"Reference linked":"Text-first render"}</p></div></div><p className="mt-3 truncate text-xs text-black/45">{product}</p></div>
            <div className="rounded-2xl border border-black/9 bg-white p-4 shadow-sm"><p className="text-xs font-medium">2 · Prompt compiler</p><div className="mt-3 min-h-48 rounded-xl bg-[#f5f5f2] p-3 font-mono text-[10px] leading-5 text-black/55 whitespace-pre-wrap">{prompt||"Scene → camera → subject → environment → lighting → motion → dialogue"}</div><button onClick={buildPrompt} className="mt-3 w-full rounded-xl bg-[#2357ff] px-3 py-2.5 text-xs font-medium text-white">Compile</button></div>
            <div className="rounded-2xl border border-black/9 bg-white p-4 shadow-sm"><div className="flex items-center justify-between"><p className="text-xs font-medium">3 · Video render</p><Video className="h-4 w-4 text-black/35"/></div><div className="mt-3 grid aspect-[9/12] place-items-center rounded-xl bg-[#11120f] px-5 text-center text-white"><div>{job?<><div className="mx-auto h-8 w-8 rounded-full border-2 border-white/25 border-t-white animate-spin"/><p className="mt-4 text-xs">Render queued</p><p className="mt-1 break-all text-[10px] text-white/40">{String(job.request_id||"")}</p></>:<><Play className="mx-auto h-7 w-7 text-white/55"/><p className="mt-3 text-xs text-white/65">Waiting for a render</p></>}</div></div></div>
          </div>
        </div>
      </section>
    </div>
  </StudioShell>;
}
