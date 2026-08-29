import Link from "next/link";
import { ArrowRight, Check, FileSearch, ReceiptText, ShieldCheck } from "lucide-react";

const INCLUDED = [
  "3 vertical UGC ads",
  "3 distinct customer pains / creative angles",
  "9:16 review-ready files",
  "Approved scripts and production prompts retained",
  "One revision round",
  "Generation and QA receipts retained with the batch",
];

export default function PricingPage(){return <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
  <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8"><Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Social Studio</Link><div className="flex items-center gap-2"><Link href="/" className="hidden px-4 py-2 text-sm text-black/55 sm:block">Overview</Link><Link href="/studio/create" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Build a batch</Link></div></header>

  <section className="mx-auto max-w-6xl px-5 pb-20 pt-16 text-center sm:px-8 sm:pt-24"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/35">Founding pilot</p><h1 className="mx-auto mt-5 max-w-4xl text-balance text-5xl font-semibold leading-[.95] tracking-[-0.07em] sm:text-7xl">Start with three ads.<br/><span className="text-black/35">Not another subscription.</span></h1><p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-black/50">Use the real factory on a bounded batch. We learn whether the creative and workflow are useful before asking you to buy ongoing software.</p>

    <div className="mx-auto mt-14 grid max-w-5xl gap-4 text-left lg:grid-cols-[1.05fr_.95fr]">
      <article className="rounded-[28px] bg-[#10110f] p-7 text-white shadow-[0_30px_90px_rgba(0,0,0,.16)] sm:p-9"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs text-white/42">Founding Ad Batch</p><div className="mt-4 text-6xl font-semibold tracking-[-0.07em]">$249</div><p className="mt-2 text-xs text-white/35">one bounded creative batch</p></div><span className="rounded-full bg-[#b9ff66] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-black">Pilot offer</span></div><p className="mt-7 max-w-xl text-sm leading-6 text-white/50">Three review-ready UGC ads built around three different pain/angle hypotheses. The point is to produce real creative, preserve the reasoning and receipts, and give you something concrete to test.</p><ul className="mt-7 grid gap-3 sm:grid-cols-2">{INCLUDED.map(feature=><li key={feature} className="flex items-start gap-2 text-sm leading-5 text-white/72"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#b9ff66]"/>{feature}</li>)}</ul><Link href="/studio/create" className="mt-9 flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-medium text-black">Build the batch brief <ArrowRight className="h-4 w-4"/></Link></article>

      <div className="grid gap-4"><TrustCard icon={<FileSearch className="h-5 w-5"/>} title="Research before render" body="The brief starts with the customer pain and the product mechanism, not a blank video prompt."/><TrustCard icon={<ShieldCheck className="h-5 w-5"/>} title="Approval before spend" body="You can inspect the scripts and gate results before any paid generation call is approved."/><TrustCard icon={<ReceiptText className="h-5 w-5"/>} title="Receipts after the call" body="Provider request state and approval state stay attached to the work. A queued render is never labeled finished."/></div>
    </div>

    <div className="mx-auto mt-8 max-w-5xl rounded-2xl border border-black/7 bg-white p-5 text-left"><p className="text-xs font-medium">What this price does not promise</p><p className="mt-2 text-xs leading-5 text-black/45">No guaranteed ROAS, conversion lift, or “winning ad” claim. Performance becomes evidence only after the creative is run against real traffic. This pilot proves the production flow and gives you three concrete hypotheses to test.</p></div>
  </section>

  <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/38 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between"><span>Social Studio · Founding pilot</span><Link href="/">Overview</Link></div></footer>
</main>}

function TrustCard({icon,title,body}:{icon:React.ReactNode;title:string;body:string}){return <article className="rounded-[22px] border border-black/7 bg-white p-6"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f0f0ed] text-black/55">{icon}</div><h2 className="mt-5 text-lg font-semibold tracking-tight">{title}</h2><p className="mt-2 text-sm leading-6 text-black/45">{body}</p></article>}
