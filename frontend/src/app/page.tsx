import Link from "next/link";
import { ArrowRight, Bot, Check, CirclePlay, FileSearch, Film, ReceiptText, ServerCog, ShieldCheck, Sparkles } from "lucide-react";
import { InstallInquiry } from "@/components/InstallInquiry";

const steps = [
  { title: "Bring the product", body: "Add the product, audience, offer, and brand context.", icon: FileSearch },
  { title: "Build the angle", body: "Turn customer pain and product truth into hooks, scripts, and creative directions worth testing.", icon: ShieldCheck },
  { title: "Choose the route", body: "Pick an approved model route and see the estimated cost before paid generation begins.", icon: Film },
  { title: "Review and repeat", body: "Keep the output, approval, cost, and result together so the next variation starts smarter.", icon: ReceiptText },
];

const ownership = [
  { title: "One install", body: "Buffer Blaster is installed for your team instead of rented as another recurring software account." },
  { title: "Your providers", body: "Connect compatible model gateways and provider accounts without rebuilding the campaign workflow." },
  { title: "Your workflow", body: "Keep briefs, approvals, cost limits, outputs, and learning together even when the model underneath changes." },
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
          <Link href="#proof">Proof</Link><Link href="#how">How it works</Link><Link href="#ownership">Ownership</Link><Link href="#models">Models</Link>
        </nav>
        <Link href="#install" className="rounded-full bg-black px-3.5 py-2.5 text-xs font-medium text-white sm:px-4 sm:text-sm">Request install</Link>
      </header>

      <section className="mx-auto max-w-7xl px-5 pb-14 pt-10 sm:px-8 sm:pt-16 lg:pb-20">
        <div className="grid gap-12 lg:grid-cols-[.92fr_1.08fr] lg:items-center lg:gap-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-black/60">
              <Sparkles className="h-3.5 w-3.5 text-[#2357ff]" /> AI video ad factory · private install
            </div>
            <h1 className="mt-6 max-w-3xl text-balance text-[44px] font-semibold leading-[.94] tracking-[-0.06em] min-[380px]:text-5xl sm:text-7xl sm:tracking-[-0.07em] lg:text-[82px]">
              Create AI ads. <span className="text-black/42">Own the factory.</span>
            </h1>
            <p className="mt-7 max-w-2xl text-balance text-base leading-7 text-black/62 sm:text-lg">
              Buffer Blaster turns one product brief into angles, scripts, and UGC-style video ads using the models you choose—all through a private system you control.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="#install" className="inline-flex items-center justify-center gap-2 rounded-full bg-black px-5 py-3 text-sm font-medium text-white">
                Request a private install <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="#proof" className="inline-flex items-center justify-center gap-2 rounded-full border border-black/12 bg-white px-5 py-3 text-sm font-medium text-black/75">
                <CirclePlay className="h-4 w-4" /> Watch real output
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-black/55">
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />No Buffer Blaster subscription</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Bring your provider accounts</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />UI, REST, MCP & CLI</span>
            </div>
          </div>
          <ProofStage />
        </div>
      </section>

      <section id="proof" className="border-y border-black/8 bg-[#11120f] text-white">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <div className="max-w-2xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Actual output</p>
            <h2 className="mt-4 text-4xl font-semibold leading-[.98] tracking-[-0.055em] sm:text-5xl">Watch what Buffer Blaster makes.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-white/58">Finished vertical product ads from the current creative pipeline. New work drops into the same proof wall as it is completed.</p>
          </div>
          <div className="mt-9 grid gap-4 md:grid-cols-3">
            <ProofVideo src="https://d2ol7oe51mr4n9.cloudfront.net/user_33irX78ICVwRYWpFZ5l6a5vZbf5/2e5d7ea7-6ba9-48cb-9a51-9193c8f1cf7f.mp4" title="Selva & Sea" body="15s product UGC · real-use demo" />
            <ProofVideo src="/media/ugc-streetwear.mp4" title="Streetwear" body="Creator product demo" />
            <ProofPlaceholder slot="UGC slot 03" />
          </div>
        </div>
      </section>

      <section id="ownership" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-start">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">One-time private install</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">The ad factory lives with you.</h2>
            <p className="mt-5 max-w-lg text-base leading-7 text-black/60">Install Buffer Blaster once, connect the provider accounts you want, and keep the creative workflow under your control.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {ownership.map((item) => <article key={item.title} className="rounded-[22px] border border-black/8 bg-white p-6"><h3 className="text-xl font-semibold tracking-[-0.03em]">{item.title}</h3><p className="mt-3 text-sm leading-6 text-black/58">{item.body}</p></article>)}
          </div>
        </div>
      </section>

      <section id="how" className="border-y border-black/7 bg-[#e8e7e3]">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
          <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-start">
            <div className="lg:sticky lg:top-12">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">From product to ad</p>
              <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">One product in. Testable ads out.</h2>
              <p className="mt-5 max-w-lg text-base leading-7 text-black/60">Keep the angle, script, model route, estimated cost, approval, output, and result in one loop.</p>
            </div>
            <div className="grid gap-x-6 gap-y-10 sm:grid-cols-2">
              {steps.map(({ title, body, icon: Icon }, index) => (
                <article key={title} className="border-t border-black/15 pt-5">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-white/65"><Icon className="h-4 w-4" /></div>
                  <p className="mt-6 text-[10px] uppercase tracking-[.15em] text-black/44">Step {index + 1}</p>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-black/58">{body}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="models" className="bg-[#10110f] text-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-24">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Choose your model</p>
            <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Change models without changing the workflow.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-white/58">Connect compatible approved gateways for Seedance, Kling, Veo, Wan, MiniMax, Fal, and other model families. Exact access and pricing depend on the provider accounts you connect.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-[10px] font-medium">
              {["SEEDANCE", "KLING", "VEO", "WAN", "MINIMAX", "FAL / GATEWAYS"].map((label) => <span key={label} className="rounded-full border border-white/12 bg-white/[.06] px-3 py-2 text-white/72">{label}</span>)}
            </div>
          </div>
          <div className="rounded-[22px] border border-white/10 bg-white/[.055] p-6">
            <div className="flex items-center gap-2"><ServerCog className="h-4 w-4 text-[#dfff67]" /><p className="text-sm font-medium">The model can change. The workflow stays.</p></div>
            <div className="mt-6 space-y-4 text-xs"><ReceiptRow label="Brief" value="stays in Buffer Blaster" /><ReceiptRow label="Model" value="selected from approved routes" /><ReceiptRow label="Cost" value="estimated before paid generation" /><ReceiptRow label="Approval" value="required before spend" /><ReceiptRow label="Receipt" value="kept with the output" /></div>
          </div>
        </div>
      </section>

      <section id="control" className="bg-[#dfff67] text-[#151613]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-24">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Cost control</p>
            <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Know the cost before you render.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/62">See the selected route and estimated spend before paid generation starts. Approval stays explicit.</p>
          </div>
          <div className="rounded-[22px] border border-black/10 bg-black p-6 text-white">
            <div className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-[#dfff67]" /><p className="text-sm font-medium">Every job keeps a receipt</p></div>
            <div className="mt-6 space-y-4 text-xs"><ReceiptRow label="Angle" value="what we are testing" /><ReceiptRow label="Rights" value="what can be used" /><ReceiptRow label="Approval" value="who cleared the action" /><ReceiptRow label="Cost" value="what the action may spend" /><ReceiptRow label="Result" value="what actually happened" /></div>
          </div>
        </div>
      </section>

      <section id="agents" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Agent access</p>
            <h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Run it yourself—or through your agents.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-black/60">Use the Studio in your browser or let approved agents call the same workflow through REST, MCP, or CLI.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-[10px] font-medium"><span className="rounded-full border border-black/10 bg-white px-3 py-2">UI</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">MCP</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">REST</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">CLI</span></div>
          </div>
          <div className="rounded-[22px] border border-black/8 bg-white p-6 shadow-[0_22px_70px_rgba(0,0,0,.06)]">
            <div className="flex items-center gap-2 text-xs text-black/50"><Bot className="h-4 w-4 text-[#2357ff]" />Example request</div>
            <p className="mt-5 text-xl leading-7 tracking-[-0.03em]">“Use this product and reference. Give me three original angles, the scripts, the generation route, and the estimated cost before rendering.”</p>
            <div className="mt-6 grid gap-2 sm:grid-cols-2"><TrustCard title="Plan first" body="Research and creative planning do not need a paid render." /><TrustCard title="Approve spend" body="Paid generation remains an explicit operator decision." /></div>
          </div>
        </div>
      </section>

      <section id="install" className="mx-auto max-w-6xl px-5 pb-24 sm:px-8">
        <div className="overflow-hidden rounded-[30px] bg-black px-6 py-12 text-white sm:px-10 lg:px-12 lg:py-14">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">One-time private install</p>
          <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_.9fr] lg:items-end">
            <div>
              <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.06em] sm:text-5xl">Install the factory once. Bring your own providers.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-white/58">Buffer Blaster does not require a recurring software subscription. Hosting and model-generation usage remain with the infrastructure and provider accounts you choose.</p>
            </div>
            <div className="lg:flex lg:justify-end"><InstallInquiry compact inverse /></div>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>Buffer Blaster · AI Ad Factory · one-time private install</span>
          <div className="flex gap-5"><Link href="#proof">Proof</Link><Link href="/install">Install</Link><Link href="/studio">Studio</Link></div>
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
        <div className="grid place-items-center overflow-hidden rounded-[22px] bg-[#11120f] p-3 sm:p-4">
          <video
            className="aspect-[9/16] max-h-[560px] w-full max-w-[315px] rounded-[16px] bg-black object-cover"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            aria-label="Selva & Sea product UGC example"
          >
            <source src="https://d2ol7oe51mr4n9.cloudfront.net/user_33irX78ICVwRYWpFZ5l6a5vZbf5/2e5d7ea7-6ba9-48cb-9a51-9193c8f1cf7f.mp4" type="video/mp4" />
          </video>
        </div>
        <div className="flex flex-col justify-between rounded-[22px] bg-[#151613] p-5 text-white">
          <div><p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-white/45">Actual output</p><p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Selva & Sea</p><p className="mt-3 text-sm leading-6 text-white/58">15-second vertical product UGC with product handling and real-use shots.</p></div>
          <a href="#proof" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-[#dfff67]">Watch the proof <ArrowRight className="h-4 w-4" /></a>
        </div>
      </div>
    </div>
  );
}

function ProofVideo({ src, title, body }: { src: string; title: string; body: string }) {
  return <article className="overflow-hidden rounded-[22px] border border-white/10 bg-white/[.055]"><div className="grid place-items-center bg-black/35 p-3"><video className="aspect-[9/16] max-h-[620px] w-full max-w-[349px] rounded-[14px] bg-black object-cover" controls playsInline preload="metadata" aria-label={`${title} video example`}><source src={src} type="video/mp4" /></video></div><div className="p-4"><p className="text-sm font-medium">{title}</p><p className="mt-1 text-xs text-white/48">{body}</p></div></article>;
}

function ProofPlaceholder({ slot }: { slot: string }) {
  return (
    <article className="overflow-hidden rounded-[22px] border border-dashed border-white/18 bg-white/[.025]">
      <div className="grid aspect-[9/16] max-h-[620px] place-items-center p-6 text-center">
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-white/35">{slot}</p>
          <p className="mt-3 text-xl font-semibold tracking-[-0.035em] text-white/75">Next UGC ad</p>
          <p className="mx-auto mt-2 max-w-[210px] text-xs leading-5 text-white/38">Reserved for the next finished Buffer Blaster example.</p>
        </div>
      </div>
      <div className="border-t border-white/8 p-4">
        <p className="text-sm font-medium text-white/60">Coming later</p>
        <p className="mt-1 text-xs text-white/34">Placeholder only · not proof</p>
      </div>
    </article>
  );
}

function ReceiptRow({ label, value }: { label: string; value: string }) {
  return <div className="grid grid-cols-[85px_1fr] gap-3 border-b border-white/8 pb-4 last:border-0 last:pb-0"><span className="text-white/42">{label}</span><span className="text-white/72">{value}</span></div>;
}

function TrustCard({ title, body }: { title: string; body: string }) {
  return <div className="rounded-xl bg-[#f5f5f2] p-4"><div className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#159653]" /><p className="text-xs font-medium">{title}</p></div><p className="mt-2 text-[11px] leading-5 text-black/58">{body}</p></div>;
}
