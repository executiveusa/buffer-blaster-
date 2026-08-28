import { ImagePlus, Link2, Upload } from "lucide-react";
import { PageHeader, StatusPill } from "@/components/studio-ui";
import { StudioShell } from "@/components/studio-shell";

const swatches = ["#d9bd9d", "#252525", "#f1e8da", "#8a9d7d", "#b9c7d9", "#c87a65"];

export default function MoodboardsPage() {
  return <StudioShell eyebrow="Reference system">
    <PageHeader kicker="Moodboards" title="Teach the studio what good looks like." body="Keep product shots, creator references, visual language, and campaign inspiration together. Future briefs can reference these boards instead of starting from zero." action={<button className="inline-flex items-center gap-2 rounded-xl bg-black px-4 py-2.5 text-sm font-medium text-white"><ImagePlus className="h-4 w-4"/>Add reference</button>} />
    <div className="p-6 lg:p-10">
      <div className="grid gap-5 xl:grid-cols-[.7fr_1.3fr]">
        <section className="rounded-[22px] border border-black/7 bg-white p-5 shadow-[0_16px_45px_rgba(0,0,0,.035)]">
          <div className="flex items-center justify-between"><div><p className="text-xs text-black/40">Brand board</p><h3 className="mt-1 text-xl font-semibold tracking-tight">Summer launch</h3></div><StatusPill tone="green">Referenced</StatusPill></div>
          <div className="mt-5 grid grid-cols-3 gap-2">{swatches.map((color,i)=><div key={color} className="aspect-square rounded-2xl border border-black/5" style={{background:`linear-gradient(145deg,${color},#f7f5f0)`}}><span className="m-2 inline-flex rounded-full bg-white/75 px-2 py-1 text-[9px] font-medium text-black/55">0{i+1}</span></div>)}</div>
          <div className="mt-5 rounded-2xl bg-[#f5f5f2] p-4"><p className="text-xs font-medium">Reference rules</p><ul className="mt-3 space-y-2 text-xs leading-5 text-black/48"><li>Natural daylight over studio polish.</li><li>Product visible within the first 2 seconds.</li><li>Understated creator reactions.</li><li>Warm neutrals; avoid loud gradients.</li></ul></div>
        </section>
        <section className="rounded-[22px] border border-black/7 bg-[#f6f6f3] p-5">
          <div className="grid min-h-[420px] place-items-center rounded-[20px] border border-dashed border-black/15 bg-white p-10 text-center">
            <div className="max-w-md"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#f0f0ed]"><Upload className="h-6 w-6 text-black/40"/></div><h3 className="mt-5 text-xl font-semibold tracking-tight">Add images or product references</h3><p className="mt-2 text-sm leading-6 text-black/45">Drop files here or paste public URLs. V1 uses links in briefs; private asset storage can be added without changing the campaign contract.</p><div className="mt-5 flex justify-center gap-2"><button className="rounded-xl bg-black px-4 py-2.5 text-sm font-medium text-white">Choose files</button><button className="inline-flex items-center gap-2 rounded-xl border border-black/10 bg-white px-4 py-2.5 text-sm font-medium"><Link2 className="h-4 w-4"/>Paste URL</button></div></div>
          </div>
        </section>
      </div>
    </div>
  </StudioShell>;
}
