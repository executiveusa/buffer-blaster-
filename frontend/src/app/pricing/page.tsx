import Link from "next/link";
import { ArrowRight, Bot, Check, ServerCog, ShieldCheck } from "lucide-react";

const accessModels = [
  {
    eyebrow: "Managed",
    name: "Creative Engine",
    badge: "Most common",
    body: "We operate Buffer Blaster as part of the client engagement. Your team gets the output, approvals, visibility, and learning loop without managing another software stack.",
    features: [
      "Research, concepts, and UGC-style production",
      "Human review before consequential actions",
      "Client workspace and evidence trail",
      "Usage and generation-cost controls",
      "Optional Shopify and paid-media connections per account",
    ],
    icon: ShieldCheck,
  },
  {
    eyebrow: "Dedicated",
    name: "Private Install",
    badge: "For internal teams",
    body: "For teams that need their own infrastructure, Buffer Blaster can run as a dedicated deployment with the same governed workflow available to people and approved agents.",
    features: [
      "Dedicated deployment and database boundary",
      "Studio + REST + MCP + CLI access",
      "Workspace-level approval and budget limits",
      "Operator-owned provider credentials",
      "Handoff, documentation, and rollback path",
    ],
    icon: ServerCog,
  },
] as const;

export default function AccessPage() {
  return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
    <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
      <Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Buffer Blaster</Link>
      <div className="flex items-center gap-2"><Link href="/" className="hidden px-4 py-2 text-sm text-black/60 sm:block">Overview</Link><Link href="/studio" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Open Studio</Link></div>
    </header>

    <section className="mx-auto max-w-7xl px-5 pb-20 pt-14 sm:px-8 sm:pt-24">
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/50">Private client access</p>
        <h1 className="mt-5 text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">The software is not the offer. <span className="text-black/45">The output is.</span></h1>
        <p className="mx-auto mt-6 max-w-3xl text-base leading-7 text-black/62">Buffer Blaster is built to remove subscriptions, handoffs, and repetitive creative operations from client work. We either run it for the engagement or deploy a dedicated instance when ownership matters.</p>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-4 lg:grid-cols-2">
        {accessModels.map(({eyebrow,name,badge,body,features,icon:Icon}, index) => <article key={name} className={`relative flex flex-col rounded-[24px] border p-7 sm:p-8 ${index === 0 ? "border-black bg-[#10110f] text-white shadow-[0_30px_90px_rgba(0,0,0,.12)]" : "border-black/8 bg-white"}`}>
          <div className="flex items-start justify-between gap-3"><div><div className={`grid h-10 w-10 place-items-center rounded-xl ${index===0?"bg-white/10":"bg-[#ecece8]"}`}><Icon className="h-5 w-5"/></div><p className={`mt-6 text-[10px] uppercase tracking-[.14em] ${index===0?"text-white/52":"text-black/48"}`}>{eyebrow}</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">{name}</h2></div><span className={`rounded-full px-2.5 py-1 text-[9px] font-semibold ${index===0?"bg-[#b9ff66] text-black":"bg-[#ecece8] text-black/65"}`}>{badge}</span></div>
          <p className={`mt-5 text-sm leading-6 ${index===0?"text-white/62":"text-black/60"}`}>{body}</p>
          <ul className="mt-7 space-y-3">{features.map(feature => <li key={feature} className={`flex items-start gap-2 text-sm leading-5 ${index===0?"text-white/74":"text-black/68"}`}><Check className={`mt-0.5 h-4 w-4 shrink-0 ${index===0?"text-[#b9ff66]":"text-[#159653]"}`}/>{feature}</li>)}</ul>
        </article>)}
      </div>

      <div className="mx-auto mt-6 max-w-5xl border-t border-black/12 pt-8">
        <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end"><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Why no public $20 plan?</p><h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">Because another login is not leverage.</h2><p className="mt-4 max-w-3xl text-sm leading-6 text-black/62">The value is a working creative system connected to the way the client already operates: brand context, approvals, generation, agents, store data, and the evidence that informs the next round. Access and operating scope are set per engagement instead of forcing every client into the same token plan.</p></div><Link href="/studio" className="inline-flex items-center justify-center gap-2 rounded-full bg-black px-6 py-3 text-sm font-medium text-white">View the Studio <ArrowRight className="h-4 w-4"/></Link></div>
      </div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-4 lg:grid-cols-3">
        <TrustCard title="People stay in control" body="The system can prepare work automatically; spend, publishing, and other consequential transitions remain approval-gated." />
        <TrustCard title="Agents use the same rules" body="Approved agents can enter through MCP, REST, or CLI instead of creating a shadow workflow outside the Studio." />
        <TrustCard title="Connections are client-scoped" body="Shopify and paid-media adapters are enabled per client account. Credentials and provider activation are never assumed." />
      </div>

      <div className="mx-auto mt-14 max-w-5xl rounded-[22px] bg-[#dfff67] p-7 sm:p-9"><div className="flex items-start gap-3"><Bot className="mt-1 h-5 w-5 shrink-0"/><div><p className="text-sm font-semibold">Built to become part of the operating system</p><p className="mt-2 max-w-3xl text-sm leading-6 text-black/62">Buffer Blaster is most valuable when it is not another destination a client has to remember. The goal is to let the client, operator, or agent call the creative system from wherever the work already starts.</p></div></div></div>
    </section>

    <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between"><span>Buffer Blaster · private access</span><Link href="/">Overview</Link></div></footer>
  </main>;
}

function TrustCard({ title, body }: { title: string; body: string }) {
  return <article className="border-t border-black/15 pt-5"><h2 className="text-lg font-semibold tracking-tight">{title}</h2><p className="mt-2 text-sm leading-6 text-black/60">{body}</p></article>;
}
