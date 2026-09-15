import Link from "next/link";
import { Check, ServerCog, ShieldCheck } from "lucide-react";

const options = [
  { name: "Managed", body: "We run Buffer Blaster for your team.", features: ["UGC ad planning and production", "Approval before spend", "Receipts for finished ads"], icon: ShieldCheck },
  { name: "Private install", body: "Your team runs its own instance.", features: ["Dedicated deployment", "Studio, REST, MCP, and CLI", "Your provider accounts and limits"], icon: ServerCog },
] as const;

export default function AccessPage() {
  return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
    <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8"><Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Buffer Blaster</Link><Link href="/studio/create" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Create an ad</Link></header>
    <section className="mx-auto max-w-6xl px-5 pb-20 pt-14 sm:px-8 sm:pt-24">
      <div className="max-w-3xl"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/50">Access</p><h1 className="mt-5 text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">Choose how you want to work.</h1><p className="mt-6 max-w-2xl text-base leading-7 text-black/62">Use our team or run a private install. Contact us for scope and price.</p></div>
      <div className="mt-14 grid gap-4 lg:grid-cols-2">{options.map(({name,body,features,icon:Icon},index)=><article key={name} className={`rounded-[24px] border p-7 sm:p-8 ${index===0?"border-black bg-[#10110f] text-white":"border-black/8 bg-white"}`}><Icon className="h-5 w-5"/><h2 className="mt-6 text-3xl font-semibold tracking-[-0.04em]">{name}</h2><p className={`mt-3 text-sm ${index===0?"text-white/62":"text-black/60"}`}>{body}</p><ul className="mt-7 space-y-3">{features.map(feature=><li key={feature} className={`flex gap-2 text-sm ${index===0?"text-white/74":"text-black/68"}`}><Check className="h-4 w-4 shrink-0 text-[#7bcf5b]"/>{feature}</li>)}</ul></article>)}</div>
      <div className="mt-8 flex flex-wrap gap-3"><Link href="/studio/create" className="rounded-full bg-black px-6 py-3 text-sm font-medium text-white">Try the Studio</Link><Link href="/#beta" className="rounded-full border border-black/15 bg-white px-6 py-3 text-sm font-medium">Join the beta</Link></div>
    </section>
  </main>;
}
