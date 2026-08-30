"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ExternalLink, ImagePlus, Link2, Loader2, Upload } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";
import { addReferenceUrl, listReferences, uploadReference, type ReferenceAsset } from "@/lib/studio-references";

export default function MoodboardsPage() {
  const [assets, setAssets] = useState<ReferenceAsset[]>([]);
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try { setAssets(await listReferences()); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "References are unavailable."); }
  }

  useEffect(() => {
    let active = true;
    listReferences()
      .then((items) => { if (active) setAssets(items); })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : "References are unavailable."); });
    return () => { active = false; };
  }, []);

  async function submitUrl(event: FormEvent) {
    event.preventDefault();
    if (!url.trim()) return;
    setWorking(true); setError("");
    try { await addReferenceUrl(url.trim(), label.trim()); setUrl(""); setLabel(""); await refresh(); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not add reference."); }
    finally { setWorking(false); }
  }

  async function chooseFile(file?: File) {
    if (!file) return;
    setWorking(true); setError("");
    try { await uploadReference(file, label.trim()); setLabel(""); await refresh(); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not upload reference."); }
    finally { setWorking(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  return <StudioShell eyebrow="Reference system">
    <PageHeader kicker="Moodboards" title="Teach the studio what good looks like." body="Product shots, creator references, and campaign inspiration now persist as canonical source assets instead of frontend-only decoration." action={<StatusPill tone={assets.length ? "green" : "neutral"}>{assets.length} references</StatusPill>} />
    <div className="grid gap-5 p-6 lg:p-10 xl:grid-cols-[.7fr_1.3fr]">
      <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
        <div className="flex items-center gap-2"><ImagePlus className="h-4 w-4 text-[#2357ff]"/><h3 className="text-sm font-medium">Add a reference</h3></div>
        <form onSubmit={submitUrl} className="mt-5 space-y-3"><label className="block text-xs text-black/45">Label<input value={label} onChange={(event)=>setLabel(event.target.value)} placeholder="Product hero, creator framing, kitchen light…" className="mt-2 w-full rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]"/></label><label className="block text-xs text-black/45">Public HTTPS URL<div className="mt-2 flex gap-2"><input value={url} onChange={(event)=>setUrl(event.target.value)} placeholder="https://…" className="min-w-0 flex-1 rounded-xl border border-black/10 bg-[#fafaf8] px-3 py-3 text-sm outline-none focus:border-[#2357ff]"/><button disabled={working || !url.trim()} className="inline-flex items-center gap-2 rounded-xl bg-black px-4 text-sm font-medium text-white disabled:opacity-40"><Link2 className="h-4 w-4"/>Add</button></div></label></form>
        <div className="my-5 flex items-center gap-3 text-[10px] uppercase tracking-[.14em] text-black/28"><span className="h-px flex-1 bg-black/8"/>or upload<span className="h-px flex-1 bg-black/8"/></div>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event)=>void chooseFile(event.target.files?.[0])}/>
        <button onClick={()=>inputRef.current?.click()} disabled={working} className="flex w-full items-center justify-center gap-2 rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-medium disabled:opacity-40">{working ? <Loader2 className="h-4 w-4 animate-spin"/> : <Upload className="h-4 w-4"/>}Choose image</button>
        <p className="mt-3 text-[11px] leading-5 text-black/38">JPEG, PNG, or WebP up to 25 MB. Uploaded references are private assets; the backend uses short-lived signed URLs when a generation workflow needs them.</p>
        {error ? <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p> : null}
      </section>

      <section className="rounded-[22px] border border-black/7 bg-[#f6f6f3] p-5">
        <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Canonical source assets</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Reference board</h3></div><StatusPill tone={assets.length ? "blue" : "neutral"}>{assets.length ? "Persisted" : "Empty"}</StatusPill></div>
        {assets.length ? <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{assets.map((asset)=><article key={asset.id} className="rounded-2xl border border-black/7 bg-white p-4"><div className="grid aspect-[4/3] place-items-center rounded-xl bg-[#f0f0ed]"><ImagePlus className="h-7 w-7 text-black/20"/></div><p className="mt-3 truncate text-xs font-medium">{asset.metadata?.label || asset.metadata?.filename || asset.kind}</p><p className="mt-1 truncate font-mono text-[9px] text-black/30">{asset.id}</p>{asset.source_url || asset.signed_url ? <a href={asset.source_url || asset.signed_url || "#"} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-[#2357ff]">Open reference <ExternalLink className="h-3 w-3"/></a> : <p className="mt-3 text-[10px] text-black/35">Private stored asset</p>}</article>)}</div> : <div className="mt-5 grid min-h-[360px] place-items-center rounded-[20px] border border-dashed border-black/15 bg-white p-10 text-center"><div className="max-w-md"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#f0f0ed]"><Upload className="h-6 w-6 text-black/40"/></div><h3 className="mt-5 text-xl font-semibold tracking-tight">No saved references yet</h3><p className="mt-2 text-sm leading-6 text-black/45">Add a real URL or upload an image. The board will only show records that exist in the canonical reference ledger.</p></div></div>}
      </section>
    </div>
  </StudioShell>;
}
