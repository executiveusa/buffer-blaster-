import Link from "next/link";
import { ArrowRight, Bot, Check, CirclePlay, FileSearch, Film, ReceiptText, ShieldCheck, Sparkles } from "lucide-react";
import { BetaWaitlist } from "@/components/BetaWaitlist";

const steps = [
  { title: "Bring the product", body: "Add the product, audience, offer, brand context, and a reference ad when you have one.", icon: FileSearch },
  { title: "Find the angle", body: "Turn customer pain and reference mechanics into hooks, scripts, and original directions worth testing.", icon: ShieldCheck },
  { title: "Make the ad", body: "See the route and estimated generation cost before approved paid rendering begins.", icon: Film },
  { title: "Keep the evidence", body: "Attach the output, approval, spend, and result to the next creative decision.", icon: ReceiptText },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="flex items-baseline gap-2 text-lg font-semibold tracking-[-0.04em]">
          Buffer Blaster
          <span className="hidden text-[9px] font-semibold uppercase tracking-[0.16em] text-black/38 sm:inline">AI Ad Factory</span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-black/60 md:flex">
          <Link href="#proof">Proof</Link><Link href="#how">How it works</Link><Link href="#control">Control</Link><Link href="#agents">Agents</Link>
        </nav>
        <Link href="/studio/create" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Build an ad plan</Link>
      </header>

      <section className="mx-auto max-w-7xl px-5 pb-14 pt-10 sm:px-8 sm:pt-16 lg:pb-20">
        <div className="grid gap-12 lg:grid-cols-[.92fr_1.08fr] lg:items-center lg:gap-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-black/60">
              <Sparkles className="h-3.5 w-3.5 text-[#2357ff]" /> AI video ad factory
            </div>
            <h1 className="mt-6 max-w-3xl text-balance text-5xl font-semibold leading-[.92] tracking-[-0.075em] sm:text-7xl lg:text-[82px]">
              Turn one product into ads worth testing.
            </h1>
            <p className="mt-7 max-w-2xl text-balance text-base leading-7 text-black/62 sm:text-lg">
              Give Buffer Blaster your product, audience, and a reference—or start from scratch. It finds angles, builds UGC-style video ads, shows the generation cost, and keeps the approval and result with the work.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/studio/create" className="inline-flex items-center justify-center gap-2 rounded-full bg-black px-5 py-3 text-sm font-medium text-white">
                Build an ad plan <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="#proof" className="inline-flex items-center justify-center gap-2 rounded-full border border-black/12 bg-white px-5 py-3 text-sm font-medium text-black/75">
                <CirclePlay className="h-4 w-4" /> Watch real output
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-black/55">
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Plan before spend</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Video output, not mockups</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />UI, REST, MCP & CLI</span>
            </div>
          </div>
          <ProofStage />
        </div>
      </section>

      <section id="proof" className="border-y border-black/8 bg-[#11120f] text-white">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <div className="grid gap-8 lg:grid-cols-[.72fr_1.28fr] lg:items-end">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Actual output</p>
              <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[.98] tracking-[-0.06em] sm:text-5xl">Proof before promises.</h2>
              <p className="mt-5 max-w-lg text-base leading-7 text-white/58">These are working video outputs already in Buffer Blaster. The next proof slot is reserved for the Selva & Sea 15-second product ad.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <ProofVideo src="/media/ugc-skincare.mp4" title="Skincare" body="Problem-led UGC demo" />
              <ProofVideo src="/media/ugc-streetwear.mp4" title="Streetwear" body="Creator product demo" />
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-start">
          <div className="lg:sticky lg:top-12">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">From brief to ad</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Start with the product. End with something you can test.</h2>
            <p className="mt-5 max-w-lg text-base leading-7 text-black/60">The generation model is only one part of the job. Buffer Blaster keeps the angle, script, route, estimated cost, output, approval, and evidence in one creative loop.</p>
          </div>
          <div className="grid gap-x-6 gap-y-10 sm:grid-cols-2">
            {steps.map(({ title, body, icon: Icon }, index) => (
              <article key={title} className="border-t border-black/15 pt-5">
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#e9e9e5]"><Icon className="h-4 w-4" /></div>
                <p className="mt-6 text-[10px] uppercase tracking-[.15em] text-black/44">Step {index + 1}</p>
                <h3 className="mt-2 text-xl font-semibold tracking-tight">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-black/58">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="control" className="bg-[#dfff67] text-[#151613]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-24">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Cost control built into the creative loop</p>
            <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">See the plan and estimated cost before paid generation.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/62">Research and planning can happen first. Paid generation starts only after the creative direction and spend are visible and approved.</p>
          </div>
          <div className="rounded-[22px] border border-black/10 bg-black p-6 text-white">
            <div className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-[#dfff67]" /><p className="text-sm font-medium">Every job keeps a receipt</p></div>
            <div className="mt-6 space-y-4 text-xs">
              <ReceiptRow label="Angle" value="what we are testing" />
              <ReceiptRow label="Rights" value="what can be used" />
              <ReceiptRow label="Approval" value="who cleared the action" />
              <ReceiptRow label="Cost" value="what the action may spend" />
              <ReceiptRow label="Result" value="what actually happened" />
            </div>
          </div>
        </div>
      </section>

      <section id="agents" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Use it yourself or hand it to an agent</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">One ad factory. More than one doorway.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/60">Use the Studio in your browser or let an approved agent call the same workflow through REST, MCP, or CLI. The work and receipts stay in one system.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-[10px] font-medium"><span className="rounded-full border border-black/10 bg-white px-3 py-2">UI</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">MCP</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">REST</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">CLI</span></div>
          </div>
          <div className="rounded-[22px] border border-black/8 bg-white p-6 shadow-[0_22px_70px_rgba(0,0,0,.06)]">
            <div className="flex items-center gap-2 text-xs text-black/50"><Bot className="h-4 w-4 text-[#2357ff]" />Example request</div>
            <p className="mt-5 text-xl leading-7 tracking-[-0.03em]">“Use this product and reference. Give me three original angles, the scripts, the generation route, and the estimated cost before rendering.”</p>
            <div className="mt-6 grid gap-2 sm:grid-cols-2"><TrustCard title="Plan first" body="Research and creative planning do not need a paid render." /><TrustCard title="Approve spend" body="Paid generation remains an explicit operator decision." /></div>
          </div>
        </div>
      </section>

      <section id="beta" className="mx-auto max-w-6xl px-5 pb-24 sm:px-8">
        <div className="overflow-hidden rounded-[30px] bg-black px-6 py-12 text-white sm:px-10 lg:px-12 lg:py-14">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Private beta</p>
          <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_.9fr] lg:items-end">
            <div>
              <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.06em] sm:text-5xl">Bring a product. Leave with an ad plan you can actually make.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-white/58">Buffer Blaster is being opened to a small group while the production system finishes its release gauntlet.</p>
            </div>
            <div className="lg:flex lg:justify-end"><BetaWaitlist compact /></div>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>Buffer Blaster · AI Ad Factory</span>
          <div className="flex gap-5"><Link href="#proof">Proof</Link><Link href="/studio">Studio</Link><Link href="/blog">Notes</Link></div>
        </div>
      </footer>
    </main>
  );
}

function ProofStage() {
  return (
    <div className="relative mx-auto w-full max-w-[700px]">
      <div className="absolute -inset-4 rounded-[36px] bg-[#e7e5de]" />
      <div className="relative grid gap-4 rounded-[30px] border border-black/8 bg-white p-4 shadow-[0_30px_90px_rgba(0,0,0,.12)] sm:grid-cols-[1.22fr_.78fr] sm:p-5">
        <div className="overflow-hidden rounded-[22px] bg-[#11120f]">
          <video className="aspect-[16/11] h-full w-full object-cover" autoPlay muted loop playsInline preload="metadata" poster="/media/ugc-hero-poster.svg">
            <source src="/media/ugc-skincare.mp4" type="video/mp4" />
          </video>
        </div>
        <div className="flex flex-col justify-between rounded-[22px] bg-[#151613] p-5 text-white">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-white/45">Actual output</p>
            <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">UGC product ad</p>
            <p className="mt-3 text-sm leading-6 text-white/58">A working video output from the current Buffer Blaster creative pipeline.</p>
          </div>
          <a href="#proof" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-[#dfff67]">Watch the proof <ArrowRight className="h-4 w-4" /></a>
        </div>
      </div>
    </div>
  );
}

function ProofVideo({ src, title, body }: { src: string; title: string; body: string }) {
  return (
    <article className="overflow-hidden rounded-[22px] border border-white/10 bg-white/[.055]">
      <video className="aspect-[9/11] w-full object-cover" controls playsInline preload="metadata" poster="/media/ugc-hero-poster.svg">
        <source src={src} type="video/mp4" />
      </video>
      <div className="p-4"><p className="text-sm font-medium">{title}</p><p className="mt-1 text-xs text-white/48">{body}</p></div>
    </article>
  );
}

function ReceiptRow({ label, value }: { label: string; value: string }) {
  return <div className="grid grid-cols-[85px_1fr] gap-3 border-b border-white/8 pb-4 last:border-0 last:pb-0"><span className="text-white/42">{label}</span><span className="text-white/72">{value}</span></div>;
}

function TrustCard({ title, body }: { title: string; body: string }) {
  return <div className="rounded-xl bg-[#f5f5f2] p-4"><div className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#159653]" /><p className="text-xs font-medium">{title}</p></div><p className="mt-2 text-[11px] leading-5 text-black/58">{body}</p></div>;
}
