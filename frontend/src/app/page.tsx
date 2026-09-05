import Link from "next/link";
import { ArrowRight, Bot, Check, FileSearch, Film, ReceiptText, ShieldCheck, Sparkles } from "lucide-react";
import { BetaWaitlist } from "@/components/BetaWaitlist";

const steps = [
  { title: "Learn", body: "Pull together product truth, customer pain, brand context, references, and the angles worth testing.", icon: FileSearch },
  { title: "Shape", body: "Turn the signal into scripts, concepts, and controlled variations your team can actually review.", icon: ShieldCheck },
  { title: "Make", body: "Route creative through the right generation path only after the plan, rights, and cost are clear.", icon: Film },
  { title: "Learn again", body: "Keep approvals, output, spend, and performance evidence attached so the next round gets smarter.", icon: ReceiptText },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#f4f3ef] text-[#151613]">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="text-lg font-semibold tracking-[-0.04em]">Buffer Blaster</Link>
        <nav className="hidden items-center gap-7 text-sm text-black/60 md:flex">
          <Link href="#system">System</Link><Link href="#control">Control</Link><Link href="#agents">Agents</Link><Link href="#beta">Beta</Link>
        </nav>
        <Link href="#beta" className="rounded-full bg-black px-4 py-2.5 text-sm font-medium text-white">Join the beta</Link>
      </header>

      <section className="mx-auto max-w-7xl px-5 pb-16 pt-12 sm:px-8 sm:pt-20 lg:pb-20">
        <div className="grid gap-12 lg:grid-cols-[.86fr_1.14fr] lg:items-center lg:gap-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-black/60"><Sparkles className="h-3.5 w-3.5 text-[#2357ff]" /> Private beta · coming soon</div>
            <h1 className="mt-6 max-w-3xl text-balance text-5xl font-semibold leading-[.92] tracking-[-0.075em] sm:text-7xl lg:text-[82px]">Find the angle.<br />Make the ad.<br /><span className="text-black/42">Learn what works.</span></h1>
            <p className="mt-7 max-w-2xl text-balance text-base leading-7 text-black/62 sm:text-lg">Buffer Blaster is private creative infrastructure for teams and agents that need to turn product truth into testable UGC, keep paid actions governed, and bring real evidence back into the next creative decision.</p>
            <div className="mt-8"><BetaWaitlist /></div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-black/55">
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Built for real client work</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />Human approval before paid actions</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#159653]" />UI, REST, MCP & CLI</span>
            </div>
            <Link href="#system" className="mt-7 inline-flex items-center gap-2 text-sm font-medium text-black/70 hover:text-black">See how it works <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <DeviceStage />
        </div>
      </section>

      <section className="border-y border-black/7 bg-[#e8e7e3] py-8"><div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-x-10 gap-y-4 px-5 text-[10px] font-semibold tracking-[0.14em] text-black/48"><span>ECOMMERCE</span><span>SHOPIFY</span><span>CLIENT TEAMS</span><span>AGENCIES</span><span>AI AGENTS</span></div></section>

      <section id="system" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-start">
          <div className="lg:sticky lg:top-12"><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">The creative loop</p><h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">One governed system from signal to evidence.</h2><p className="mt-5 max-w-lg text-base leading-7 text-black/60">Research, reference analysis, creative planning, provider routing, repurposing, approvals, Shopify context, distribution handoff, and performance evidence can share one operating model instead of becoming eight disconnected tools.</p></div>
          <div className="grid gap-x-6 gap-y-10 sm:grid-cols-2">{steps.map(({ title, body, icon: Icon }, index) => <article key={title} className="border-t border-black/15 pt-5"><div className="grid h-9 w-9 place-items-center rounded-xl bg-[#e9e9e5]"><Icon className="h-4 w-4" /></div><p className="mt-6 text-[10px] uppercase tracking-[.15em] text-black/44">Step {index + 1}</p><h3 className="mt-2 text-xl font-semibold tracking-tight">{title}</h3><p className="mt-3 text-sm leading-6 text-black/58">{body}</p></article>)}</div>
        </div>
      </section>

      <section id="control" className="bg-[#10110f] text-white"><div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-28">
        <div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/48">Control stays with the operator</p><h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Automation should remove busywork, not remove judgment.</h2><p className="mt-5 max-w-xl text-base leading-7 text-white/58">The system can research, draft, route, organize, and prepare the next move. Paid generation, publishing, and ad activation remain explicit decisions, with limits enforced on the server.</p><div className="mt-7 flex flex-wrap gap-2 text-[10px]"><span className="rounded-full bg-white/8 px-3 py-2">PLAN</span><span className="rounded-full bg-white/8 px-3 py-2">REVIEW</span><span className="rounded-full bg-white/8 px-3 py-2">APPROVE</span><span className="rounded-full bg-[#b9ff66] px-3 py-2 text-black">LEARN</span></div></div>
        <div className="rounded-[22px] border border-white/10 bg-white/[.055] p-6"><div className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-[#b9ff66]" /><p className="text-sm font-medium">Every consequential job keeps its evidence</p></div><div className="mt-6 space-y-4 text-xs"><ReceiptRow label="Plan" value="what we are testing" /><ReceiptRow label="Rights" value="what can be used commercially" /><ReceiptRow label="Approval" value="who cleared the action" /><ReceiptRow label="Cost" value="what the action may spend" /><ReceiptRow label="Result" value="what actually happened" /></div></div>
      </div></section>

      <section id="agents" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28"><div className="grid gap-10 lg:grid-cols-2 lg:items-center">
        <div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/48">Agent-native</p><h2 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.01] tracking-[-0.06em] sm:text-5xl">Use the Studio. Or let your agent call the same system.</h2><p className="mt-5 max-w-xl text-base leading-7 text-black/60">The browser is one doorway. REST, MCP, and CLI let approved agents use the same governed workflow without creating a second process or a second source of truth.</p><div className="mt-7 flex flex-wrap gap-2 text-[10px] font-medium"><span className="rounded-full border border-black/10 bg-white px-3 py-2">UI</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">MCP</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">REST</span><span className="rounded-full border border-black/10 bg-white px-3 py-2">CLI</span></div></div>
        <div className="rounded-[22px] border border-black/8 bg-white p-6 shadow-[0_22px_70px_rgba(0,0,0,.06)]"><div className="flex items-center gap-2 text-xs text-black/50"><Bot className="h-4 w-4 text-[#2357ff]" />Agent request</div><p className="mt-5 text-xl leading-7 tracking-[-0.03em]">Analyze this reference. Build three original angles. Show me the route, rights, estimated cost, and plan before anything paid happens.</p><div className="mt-6 grid gap-2 sm:grid-cols-2"><TrustCard title="Prepare" body="No-spend research and planning can run automatically." /><TrustCard title="Commit" body="Consequential actions remain governed and explicit." /></div></div>
      </div></section>

      <section id="beta" className="mx-auto max-w-6xl px-5 pb-24 sm:px-8"><div className="overflow-hidden rounded-[30px] bg-[#dfff67] px-6 py-12 sm:px-10 lg:px-12 lg:py-14">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/50">Private beta · coming soon</p>
        <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_.9fr] lg:items-end"><div><h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.06em] sm:text-5xl">We sell the outcome. Buffer Blaster is how we deliver it.</h2><p className="mt-4 max-w-2xl text-sm leading-6 text-black/62">We’re opening the system to a small group of teams first. Join the list for beta access, build notes, and the first public demos while the production system finishes its final release gauntlet.</p></div><div className="lg:flex lg:justify-end"><BetaWaitlist compact /></div></div>
      </div></section>

      <footer className="border-t border-black/7 px-5 py-8 text-xs text-black/50 sm:px-8"><div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><span>Buffer Blaster · Private creative infrastructure</span><div className="flex gap-5"><Link href="#beta">Beta</Link><Link href="/studio">Studio</Link><Link href="/blog">Notes</Link></div></div></footer>
    </main>
  );
}

function DeviceStage() {
  return <div className="relative mx-auto min-h-[500px] w-full max-w-[760px] sm:min-h-[600px] lg:min-h-[650px]" aria-label="Creative outputs inside Buffer Blaster">
    <div className="absolute inset-x-0 bottom-4 top-8 rounded-[40px] bg-[#e9e7e0]" />
    <div className="absolute left-[3%] right-[3%] top-[5%] aspect-[16/10] rounded-[24px] border-[8px] border-[#1b1c19] bg-[#11120f] shadow-[0_38px_90px_rgba(0,0,0,.18)] sm:border-[10px]"><div className="relative h-full w-full overflow-hidden rounded-[14px] bg-[#151713] sm:rounded-[16px]"><video className="h-full w-full object-cover" autoPlay muted loop playsInline preload="metadata" poster="/media/ugc-hero-poster.svg"><source src="/media/ugc-skincare.mp4" type="video/mp4" /></video><div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-black/5" /><div className="pointer-events-none absolute bottom-5 left-5 right-5 flex items-end justify-between text-white sm:bottom-7 sm:left-7 sm:right-7"><div><p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-white/65">Creative 01</p><p className="mt-1 text-base font-medium tracking-[-0.02em] sm:text-xl">Skincare · problem-led UGC</p></div><span className="hidden rounded-full border border-white/20 bg-black/25 px-3 py-1.5 text-[9px] font-medium backdrop-blur sm:block">GOVERNED OUTPUT</span></div></div><span className="absolute left-1/2 top-[-7px] h-1 w-12 -translate-x-1/2 rounded-full bg-black/70" /></div>
    <div className="absolute left-[7%] right-[7%] top-[58%] h-[16px] rounded-b-[80%] bg-[#c8c7c1] shadow-[0_16px_28px_rgba(0,0,0,.12)] sm:h-[20px]" />
    <div className="absolute bottom-[1%] right-[4%] w-[30%] min-w-[132px] max-w-[190px] rounded-[30px] border-[7px] border-[#151613] bg-[#151613] p-[3px] shadow-[0_32px_70px_rgba(0,0,0,.28)] sm:bottom-[2%] sm:right-[7%] sm:rounded-[38px] sm:border-[8px]"><div className="relative aspect-[9/18.8] overflow-hidden rounded-[20px] bg-[#11120f] sm:rounded-[27px]"><video className="h-full w-full object-cover" autoPlay muted loop playsInline preload="metadata" poster="/media/ugc-hero-poster.svg"><source src="/media/ugc-streetwear.mp4" type="video/mp4" /></video><div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/35 via-transparent to-black/10" /><div className="pointer-events-none absolute bottom-4 left-3 right-3 text-white"><p className="text-[7px] font-semibold uppercase tracking-[0.18em] text-white/60">Creative 02</p><p className="mt-1 text-[10px] font-medium leading-tight sm:text-xs">Streetwear · creator demo</p></div><span className="absolute left-1/2 top-2 h-4 w-14 -translate-x-1/2 rounded-full bg-black/75" /></div></div>
    <div className="absolute bottom-[8%] left-[4%] max-w-[250px] rounded-2xl border border-black/8 bg-white/88 p-4 shadow-[0_18px_50px_rgba(0,0,0,.1)] backdrop-blur sm:bottom-[11%] sm:left-[7%] sm:p-5"><p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-black/38">One system, multiple angles</p><p className="mt-2 text-sm font-medium leading-5 tracking-[-0.02em] sm:text-base">Signal → strategy → creative → evidence.</p></div>
  </div>;
}

function ReceiptRow({ label, value }: { label: string; value: string }) { return <div className="grid grid-cols-[85px_1fr] gap-3 border-b border-white/8 pb-4 last:border-0 last:pb-0"><span className="text-white/42">{label}</span><span className="text-white/72">{value}</span></div>; }
function TrustCard({ title, body }: { title: string; body: string }) { return <div className="rounded-xl bg-[#f5f5f2] p-4"><div className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#159653]" /><p className="text-xs font-medium">{title}</p></div><p className="mt-2 text-[11px] leading-5 text-black/58">{body}</p></div>; }
