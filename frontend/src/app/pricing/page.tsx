import Link from "next/link";
import { Check, CircleDollarSign, FileSearch, ReceiptText, ShieldCheck } from "lucide-react";
import { CheckoutButton } from "@/components/checkout-button";

const offers = [
  {
    id: "trial-7",
    eyebrow: "Lowest-risk start",
    name: "7-Day Test Drive",
    price: "$19",
    cadence: "one-time",
    credits: "3 Ad Credits",
    badge: "Start here",
    body: "A small paid pass to test the real workflow without committing to a subscription.",
    features: ["7 days of access", "3 included Ad Credits", "No watermark", "Scripts + production receipts", "Exact credit cost shown before generation"],
    cta: "Start the 7-day test",
  },
  {
    id: "trial-30",
    eyebrow: "More room to learn",
    name: "30-Day Launch Pass",
    price: "$49",
    cadence: "one-time",
    credits: "8 Ad Credits",
    badge: "Best trial value",
    body: "Run more angles across a month and learn the workflow before choosing a recurring plan.",
    features: ["30 days of access", "8 included Ad Credits", "No watermark", "Full UGC factory + final asset receipts", "Credits expire with the pass"],
    cta: "Start the 30-day pass",
  },
  {
    id: "starter-monthly",
    eyebrow: "Consistent testing",
    name: "Starter",
    price: "$99",
    cadence: "per month",
    credits: "20 Ad Credits",
    badge: "Most popular",
    body: "For a brand that wants a steady creative testing cadence without an agency production bill.",
    features: ["20 Ad Credits / month", "Campaign planning", "UGC factory", "Asset library + receipts", "Human approval before paid generation"],
    cta: "Choose Starter",
  },
  {
    id: "pro-monthly",
    eyebrow: "Higher-volume operator",
    name: "Pro",
    price: "$199",
    cadence: "per month",
    credits: "50 Ad Credits",
    badge: "Best unit value",
    body: "For teams and agents that need more testing volume plus programmatic control surfaces.",
    features: ["50 Ad Credits / month", "REST + MCP + CLI", "Higher-volume creative testing", "Canonical job receipts", "Approval and spend guards stay on"],
    cta: "Choose Pro",
  },
] as const;

export default function PricingPage() {
  return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
    <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
      <Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Social Studio</Link>
      <div className="flex items-center gap-2"><Link href="/" className="hidden px-4 py-2 text-sm text-black/55 sm:block">Overview</Link><Link href="/studio/create" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Open studio</Link></div>
    </header>

    <section className="mx-auto max-w-7xl px-5 pb-20 pt-16 sm:px-8 sm:pt-24">
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/35">Paid test before subscription</p>
        <h1 className="mt-5 text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">Pay a little. Make real ads. <span className="text-black/35">Then decide.</span></h1>
        <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-black/50">Start with a bounded paid pass instead of handing over a large monthly fee before you know the workflow fits. Your pass includes Ad Credits, and the studio shows the credit requirement before any paid generation starts.</p>
      </div>

      <div className="mt-14 grid gap-4 lg:grid-cols-4">
        {offers.map((offer, index) => <article key={offer.id} className={`relative flex flex-col rounded-[26px] border p-6 ${index === 1 ? "border-black bg-[#10110f] text-white shadow-[0_30px_90px_rgba(0,0,0,.14)]" : "border-black/7 bg-white"}`}>
          <div className="flex items-start justify-between gap-3"><div><p className={`text-[10px] uppercase tracking-[.14em] ${index === 1 ? "text-white/38" : "text-black/35"}`}>{offer.eyebrow}</p><h2 className="mt-2 text-xl font-semibold tracking-tight">{offer.name}</h2></div><span className={`rounded-full px-2.5 py-1 text-[9px] font-semibold ${index === 1 ? "bg-[#b9ff66] text-black" : "bg-[#f0f0ed] text-black/55"}`}>{offer.badge}</span></div>
          <div className="mt-7"><span className="text-5xl font-semibold tracking-[-0.07em]">{offer.price}</span><span className={`ml-2 text-xs ${index === 1 ? "text-white/38" : "text-black/35"}`}>{offer.cadence}</span></div>
          <p className={`mt-2 text-xs font-medium ${index === 1 ? "text-[#b9ff66]" : "text-[#2357ff]"}`}>{offer.credits}</p>
          <p className={`mt-5 min-h-20 text-sm leading-6 ${index === 1 ? "text-white/50" : "text-black/48"}`}>{offer.body}</p>
          <ul className="mt-5 flex-1 space-y-3">{offer.features.map((feature) => <li key={feature} className={`flex items-start gap-2 text-xs leading-5 ${index === 1 ? "text-white/68" : "text-black/58"}`}><Check className={`mt-0.5 h-4 w-4 shrink-0 ${index === 1 ? "text-[#b9ff66]" : "text-[#159653]"}`} />{feature}</li>)}</ul>
          <CheckoutButton offer={offer.id} label={offer.cta} className={`mt-7 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${index === 1 ? "bg-white text-black" : "bg-black text-white"}`} />
        </article>)}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <TrustCard icon={<CircleDollarSign className="h-5 w-5"/>} title="One credit has a cost ceiling" body="A standard generation estimated under $1 uses one Ad Credit. More expensive models, longer outputs, or retries can require more credits. You see that before approval." />
        <TrustCard icon={<ShieldCheck className="h-5 w-5"/>} title="No surprise provider spend" body="The server reserves both your Ad Credits and the internal generation-cost allowance before calling a media provider. If the allowance cannot cover the request, the render is blocked." />
        <TrustCard icon={<ReceiptText className="h-5 w-5"/>} title="The receipt stays with the asset" body="Plan version, scripts, approval, provider requests, QA state, and final asset state are retained together. Queued work is never labeled finished." />
      </div>

      <div className="mt-6 grid gap-4 rounded-[24px] border border-black/7 bg-white p-6 lg:grid-cols-[1fr_1fr]">
        <div><div className="flex items-center gap-2"><FileSearch className="h-4 w-4 text-black/45"/><p className="text-sm font-medium">What an Ad Credit means</p></div><p className="mt-3 text-xs leading-5 text-black/48">An Ad Credit is our customer-facing usage unit, not an opaque provider token. When a finished-ad attempt fits under the standard $1 generation-cost ceiling, one credit covers it. If the estimated provider cost is $1.60, the studio requires two credits before it can run.</p></div>
        <div><p className="text-sm font-medium">What we do not promise</p><p className="mt-3 text-xs leading-5 text-black/48">No guaranteed ROAS, conversion lift, or automatic “winning ad” claim. Trial credits are usage allowance, not cash, and unused trial credits expire with the pass. Performance becomes evidence only after real traffic produces real results.</p></div>
      </div>
    </section>

    <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/38 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between"><span>Social Studio · paid test before subscription</span><Link href="/">Overview</Link></div></footer>
  </main>;
}

function TrustCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return <article className="rounded-[22px] border border-black/7 bg-white p-6"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f0f0ed] text-black/55">{icon}</div><h2 className="mt-5 text-lg font-semibold tracking-tight">{title}</h2><p className="mt-2 text-sm leading-6 text-black/45">{body}</p></article>;
}
