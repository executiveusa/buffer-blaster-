import Link from "next/link";
import { ArrowRight, Check, ServerCog, ShieldCheck } from "lucide-react";
import { InstallInquiry } from "@/components/InstallInquiry";

const included = [
  "Private Buffer Blaster deployment",
  "Studio + REST + MCP + CLI access",
  "Provider-neutral video gateway",
  "Model allowlist and generation-cost controls",
  "Human approval before paid generation or publishing",
  "Private database and asset-storage boundary",
  "Handoff documentation and rollback path",
];

const variable = [
  "Your server or hosting bill",
  "Model/provider generation usage",
  "Optional publishing, commerce, or paid-media accounts you connect",
];

export default function InstallPage() {
  return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
    <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
      <Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Buffer Blaster</Link>
      <div className="flex items-center gap-2"><Link href="/" className="hidden px-4 py-2 text-sm text-black/60 sm:block">Overview</Link><Link href="#request" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Request install</Link></div>
    </header>

    <section className="mx-auto max-w-7xl px-5 pb-20 pt-14 sm:px-8 sm:pt-24">
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/50">One-time private install</p>
        <h1 className="mt-5 text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">Install the factory once. <span className="text-black/45">Keep the workflow.</span></h1>
        <p className="mx-auto mt-6 max-w-3xl text-base leading-7 text-black/62">Buffer Blaster is installed for your team. Connect the provider accounts you want, keep the workflow under your control, and pay hosting or generation usage directly through those accounts.</p>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <article className="rounded-[26px] border border-black bg-[#10110f] p-7 text-white shadow-[0_30px_90px_rgba(0,0,0,.12)] sm:p-8">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/10"><ServerCog className="h-5 w-5"/></div>
          <p className="mt-6 text-[10px] uppercase tracking-[.14em] text-white/48">Buffer Blaster Private Install</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">One install. Yours to run.</h2>
          <p className="mt-5 text-sm leading-6 text-white/62">The one-time install covers the Buffer Blaster system and deployment work. Hosting and third-party model usage stay separate and transparent.</p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-2">{included.map(feature => <li key={feature} className="flex items-start gap-2 text-sm leading-5 text-white/74"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#b9ff66]"/>{feature}</li>)}</ul>
        </article>

        <aside className="rounded-[26px] border border-black/8 bg-white p-7 sm:p-8">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-[#ecece8]"><ShieldCheck className="h-5 w-5"/></div>
          <p className="mt-6 text-[10px] uppercase tracking-[.14em] text-black/48">What stays variable</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">Usage stays transparent.</h2>
          <ul className="mt-6 space-y-3">{variable.map(item => <li key={item} className="flex items-start gap-2 text-sm leading-5 text-black/68"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#159653]"/>{item}</li>)}</ul>
          <p className="mt-6 text-xs leading-5 text-black/48">No recurring Buffer Blaster SaaS plan is required for the installed product. Optional support or managed-service work would be a separate agreement.</p>
        </aside>
      </div>

      <div className="mx-auto mt-12 max-w-5xl border-t border-black/12 pt-10">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Why ownership</p>
        <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">The workflow should outlast the model vendor.</h2>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-black/62">Models and providers change quickly. Buffer Blaster keeps the creative process stable so your team can change generation routes without rebuilding the whole system around a new vendor.</p>
      </div>

      <div id="request" className="mx-auto mt-14 max-w-5xl rounded-[28px] bg-[#dfff67] p-7 sm:p-9">
        <div className="grid gap-7 lg:grid-cols-[1fr_.9fr] lg:items-end">
          <div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Request your install</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">Tell us where you want it installed.</h2><p className="mt-4 max-w-xl text-sm leading-6 text-black/62">The scope depends on your deployment target, provider accounts, storage, and integrations. This starts the install conversation; it does not create a subscription.</p></div>
          <InstallInquiry compact />
        </div>
      </div>

      <div className="mx-auto mt-10 max-w-5xl"><Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-black/65 hover:text-black">Back to proof and product <ArrowRight className="h-4 w-4"/></Link></div>
    </section>

    <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between"><span>Buffer Blaster · one-time private install</span><Link href="/">Overview</Link></div></footer>
  </main>;
}
