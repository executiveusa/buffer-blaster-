import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, Download, ShieldCheck, Sparkles } from "lucide-react";

const BENEFITS = [
  "Lifetime access to the founding creator tier",
  "Discover, adapt, save, and export creator workflows",
  "Portable ICM agent packs you can keep and inspect",
  "Early access to larger verified corpus batches",
  "Founding-member price locked at $29"
];

export default function FoundingPage() {
  const checkoutUrl = process.env.NEXT_PUBLIC_FOUNDING_CREATOR_CHECKOUT_URL?.trim();

  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text">
            <ArrowLeft className="h-4 w-4" aria-hidden /> Creator Studio
          </Link>
          <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-dim">First 100 creators</span>
        </div>
      </header>

      <section className="mx-auto grid max-w-5xl gap-10 px-6 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:py-24">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent-soft">Founding Creator</p>
          <h1 className="mt-5 max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">Own the workflow, not another subscription.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-text-muted">
            Join the first 100 creators for a one-time $29 founding price. Keep your recipes, your adapted prompts, and your exported agent packs portable.
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-border bg-bg-card p-5"><ShieldCheck className="h-5 w-5 text-success"/><p className="mt-3 text-sm text-text-muted"><span className="text-text">No lock-in.</span> Your exports remain usable outside this app.</p></div>
            <div className="rounded-2xl border border-border bg-bg-card p-5"><Download className="h-5 w-5 text-warning"/><p className="mt-3 text-sm text-text-muted"><span className="text-text">Portable by design.</span> Download inspectable ICM agent packs.</p></div>
            <div className="rounded-2xl border border-border bg-bg-card p-5"><Sparkles className="h-5 w-5 text-accent-soft"/><p className="mt-3 text-sm text-text-muted"><span className="text-text">Early access.</span> Get new verified corpus batches first.</p></div>
          </div>
        </div>

        <aside className="self-start rounded-3xl border border-border bg-bg-elevated p-7 sm:p-8">
          <p className="text-sm text-text-muted">Founding Creator</p>
          <div className="mt-3 flex items-end gap-2"><span className="text-5xl font-semibold">$29</span><span className="pb-1 text-sm text-text-dim">one time</span></div>
          <p className="mt-3 text-sm leading-relaxed text-text-muted">Limited to the first 100 founding creators during validation.</p>
          <ul className="mt-7 space-y-3">
            {BENEFITS.map((benefit) => <li key={benefit} className="flex gap-3 text-sm text-text-muted"><Check className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />{benefit}</li>)}
          </ul>

          {checkoutUrl ? (
            <a href={checkoutUrl} className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim">
              Become a Founding Creator <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
          ) : (
            <div className="mt-8 rounded-xl border border-border bg-bg-card p-4">
              <p className="text-sm text-text">Checkout connection pending.</p>
              <p className="mt-1 text-xs leading-relaxed text-text-dim">The purchase page is production-ready. A payment-link environment variable must be connected before money is accepted.</p>
              <Link href="/create" className="mt-4 inline-flex items-center gap-2 text-sm text-accent-soft hover:text-text">Use Creator Studio now <ArrowRight className="h-4 w-4" aria-hidden /></Link>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}
