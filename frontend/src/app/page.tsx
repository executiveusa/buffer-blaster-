import Link from "next/link";
import { ArrowRight, Bot, Check, CirclePlay, FileSearch, Film, ReceiptText, Route, ServerCog, ShieldCheck, Sparkles } from "lucide-react";
import { InstallInterestForm } from "@/components/InstallInterestForm";

const steps = [
  { title: "Bring the product", body: "Add the product, audience, offer, brand context, and a reference ad when you have one.", icon: FileSearch },
  { title: "Find the angle", body: "Turn customer pain and reference mechanics into hooks, scripts, and original directions worth testing.", icon: ShieldCheck },
  { title: "Choose the route", body: "Select the approved provider and model for the shot, with cost visible before paid generation.", icon: Route },
  { title: "Make and keep the evidence", body: "Generate, review, store the output, and keep the approval, spend, and result attached.", icon: ReceiptText },
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
          <Link href="#proof">Proof</Link><Link href="#how">How it works</Link><Link href="#models">Models</Link><Link href="#install">Install</Link>
        </nav>
        <Link href="#install" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Get the install</Link>
      </header>

      <section className="mx-auto max-w-7xl px-5 pb-14 pt-10 sm:px-8 sm:pt-16 lg:pb-20">
        <div className="grid gap-12 lg:grid-cols-[.92fr_1.08fr] lg:items-center lg:gap-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-black/60">
              <Sparkles className="h-3.5 w-3.5 text-[#2357ff]" /> AI ad factory · one-time private install
            </div>
            <h1 className="mt-6 max-w-3xl text-balance text-5xl font-semibold leading-[.92] tracking-[-0.075em] sm:text-7xl lg:text-[82px]">
              Own the system that turns products into ads.
            </h1>
            <p className="mt-7 max-w-2xl text-balance text-base leading-7 text-black/62 sm:text-lg">
              Buffer Blaster installs on infrastructure you control. Bring your product, brand context, and approved model accounts. It finds angles, routes video generation, keeps cost visible before spend, and gives your team and agents one place to make and review ads.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="#install" className="inline-flex items-center justify-center gap-2 rounded-full bg-black px-5 py-3 text-sm font-medium text-white">
                Get a private install <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="#proof" className="inline-flex items-center justify-center gap-2 rounded-full border border-black/12 bg-white px-5 py-3 text-sm font-medium text-black/75">
                <CirclePlay className="h-4 w-4" /> Watch real output
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-black/55">
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />No monthly Buffer Blaster subscription</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Your provider accounts</span>
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
              <p className="mt-5 max-w-lg text-base leading-7 text-white/58">Current Buffer Blaster video outputs are playable here. More finished client-style examples can be added without changing the page structure.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <ProofVideo src="/media/ugc-skincare.mp4" title="Skincare" body="Problem-led product UGC" />
              <ProofVideo src="/media/ugc-streetwear.mp4" title="Streetwear" body="Creator product demo" />
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-start">
          <div className="lg:sticky lg:top-12">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">From product to testable creative</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">The model is replaceable. The workflow is yours.</h2>
            <p className="mt-5 max-w-lg text-base leading-7 text-black/60">Buffer Blaster keeps the brief, angle, provider route, cost estimate, approval, output, and evidence in one system so changing generation models does not mean rebuilding your creative operation.</p>
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

      <section id="models" className="bg-[#dfff67] text-[#151613]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-24">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Provider-neutral generation</p>
            <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Call the model that fits the shot.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/62">Connect the gateways and provider accounts you approve. Buffer Blaster can route allowlisted models such as Seedance, Kling, Veo, Wan, MiniMax, Fal-backed models, and compatible self-hosted gateways when those providers are configured.</p>
          </div>
          <div className="rounded-[22px] border border-black/10 bg-black p-6 text-white">
            <div className="flex items-center gap-2"><Film className="h-4 w-4 text-[#dfff67]" /><p className="text-sm font-medium">One governed route</p></div>
            <div className="mt-6 space-y-4 text-xs">
              <ReceiptRow label="Model" value="allowlisted per install" />
              <ReceiptRow label="Cost" value="checked before wallet reservation" />
              <ReceiptRow label="Rights" value="commercial status stays explicit" />
              <ReceiptRow label="Approval" value="paid generation remains gated" />
              <ReceiptRow label="Fallback" value="switch providers without changing the product" />
            </div>
          </div>
        </div>
      </section>

      <section id="install" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-[.9fr_1.1fr] lg:items-start">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">One-time private install</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Pay for the install. Keep the system.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/60">Buffer Blaster is sold as a dedicated installation, not a monthly seat subscription. Your cloud, model, and API usage stay in accounts you control.</p>
            <div className="mt-7"><InstallInterestForm /></div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <InstallCard icon={ServerCog} title="Your infrastructure" body="Dedicated deployment, database boundary, documentation, and rollback path." />
            <InstallCard icon={Route} title="Your model accounts" body="Connect approved gateways and keep provider credentials under operator control." />
            <InstallCard icon={Bot} title="Agent-ready" body="The same system is available through the Studio, REST, MCP, and CLI." />
            <InstallCard icon={ShieldCheck} title="Spend stays governed" body="Planning can run first; paid generation and publishing remain explicit decisions." />
          </div>
        </div>
      </section>

      <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>Buffer Blaster · one-time private AI ad factory install</span>
          <div className="flex gap-5"><Link href="#proof">Proof</Link><Link href="/pricing">Install</Link><Link href="/studio">Studio</Link></div>
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
            <p className="mt-3 text-sm leading-6 text-white/58">Working video output from the Buffer Blaster creative pipeline.</p>
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

function InstallCard({ icon: Icon, title, body }: { icon: typeof ServerCog; title: string; body: string }) {
  return <article className="rounded-[22px] border border-black/8 bg-white p-5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#ecece8]"><Icon className="h-5 w-5" /></div><h3 className="mt-5 text-lg font-semibold tracking-tight">{title}</h3><p className="mt-2 text-sm leading-6 text-black/60">{body}</p></article>;
}
