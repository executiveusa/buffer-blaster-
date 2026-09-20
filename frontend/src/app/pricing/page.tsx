import Link from "next/link";
import { ArrowLeft, Bot, Check, Route, ServerCog, ShieldCheck } from "lucide-react";
import { InstallInterestForm } from "@/components/InstallInterestForm";

const included = [
  "Dedicated deployment in infrastructure you control",
  "Buffer Blaster Studio + REST + MCP + CLI",
  "Multi-gateway video model routing",
  "Operator-owned provider credentials",
  "Approval and generation-cost controls",
  "Private asset storage and evidence receipts",
  "Install documentation and rollback path",
  "Handoff for your team or agents",
];

export default function AccessPage() {
  return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
    <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
      <Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Buffer Blaster</Link>
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-black/60"><ArrowLeft className="h-4 w-4"/>Overview</Link>
    </header>

    <section className="mx-auto max-w-7xl px-5 pb-20 pt-14 sm:px-8 sm:pt-24">
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/50">One-time private install</p>
        <h1 className="mt-5 text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">Buy the install once. <span className="text-black/45">Keep the system.</span></h1>
        <p className="mx-auto mt-6 max-w-3xl text-base leading-7 text-black/62">Buffer Blaster is sold as a dedicated installation, not a recurring software seat. Your model, API, and hosting accounts stay separate and under your control.</p>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-5 lg:grid-cols-[1.08fr_.92fr]">
        <article className="rounded-[28px] bg-[#10110f] p-7 text-white shadow-[0_30px_90px_rgba(0,0,0,.12)] sm:p-9">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/48"><ServerCog className="h-4 w-4 text-[#dfff67]"/>Private Install</div>
          <h2 className="mt-5 text-4xl font-semibold tracking-[-0.05em]">Your ad factory, on your stack.</h2>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-white/62">One implementation scope. One dedicated deployment. No monthly Buffer Blaster subscription after handoff.</p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-2">{included.map(item => <li key={item} className="flex items-start gap-2 text-sm leading-5 text-white/76"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#dfff67]"/>{item}</li>)}</ul>
        </article>

        <aside className="rounded-[28px] border border-black/8 bg-white p-7 sm:p-9">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">What stays yours</p>
          <div className="mt-6 space-y-5">
            <ValueRow icon={Route} title="Provider choice" body="Connect the gateways and model accounts you approve." />
            <ValueRow icon={ShieldCheck} title="Spend authority" body="Generation stays behind your budget and approval rules." />
            <ValueRow icon={Bot} title="Agent access" body="Your approved agents can use the same backend through MCP, REST, or CLI." />
          </div>
          <div className="mt-8 border-t border-black/10 pt-6">
            <p className="text-xs leading-5 text-black/52">Installation scope and final one-time price depend on deployment, integrations, and handoff requirements. Ongoing cloud and model-provider usage are not included.</p>
          </div>
        </aside>
      </div>

      <div className="mx-auto mt-8 max-w-5xl rounded-[28px] bg-[#dfff67] p-7 sm:p-9">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Request the install</p>
        <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">Tell us where you want Buffer Blaster to live.</h2>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-black/62">We’ll scope the deployment, provider connections, and agent surfaces before any installation work starts.</p>
        <div className="mt-6"><InstallInterestForm compact /></div>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-4 lg:grid-cols-3">
        <TrustCard title="No subscription lock-in" body="The public offer is the one-time install, not a monthly Buffer Blaster seat plan." />
        <TrustCard title="Provider-neutral by design" body="The backend can route across configured model gateways instead of tying the workflow to one vendor." />
        <TrustCard title="Built for handoff" body="Deployment, operating boundaries, documentation, and rollback are part of the install contract." />
      </div>
    </section>

    <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between"><span>Buffer Blaster · one-time private install</span><Link href="/">Overview</Link></div></footer>
  </main>;
}

function ValueRow({ icon: Icon, title, body }: { icon: typeof Route; title: string; body: string }) {
  return <div className="flex gap-3"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#ecece8]"><Icon className="h-4 w-4"/></div><div><p className="text-sm font-semibold">{title}</p><p className="mt-1 text-xs leading-5 text-black/55">{body}</p></div></div>;
}

function TrustCard({ title, body }: { title: string; body: string }) {
  return <article className="border-t border-black/15 pt-5"><h2 className="text-lg font-semibold tracking-tight">{title}</h2><p className="mt-2 text-sm leading-6 text-black/60">{body}</p></article>;
}
