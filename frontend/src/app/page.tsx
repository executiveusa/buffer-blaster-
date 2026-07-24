import Link from "next/link";
import { ArrowRight, Download, Search, ShieldCheck, Sparkles } from "lucide-react";

const STEPS = [
  ["01", "Describe the outcome", "Tell the studio what you want to make in normal language."],
  ["02", "Choose from three", "Get a small set of relevant, provenance-aware recipes instead of a wall of prompts."],
  ["03", "Adapt and own it", "Fill the required inputs, save locally, and export a portable agent pack you can inspect and reuse."],
];

export default function LandingPage() {
  return (
    <main className="flex-1">
      <section className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 hero-grid" aria-hidden />
        <div className="absolute inset-0 glow" aria-hidden />
        <div className="relative mx-auto max-w-5xl px-6 py-24 sm:py-36">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-text-dim">Sovereign creator workspace</p>
          <h1 className="mt-6 max-w-4xl text-balance text-5xl font-semibold leading-[1.02] tracking-tight sm:text-7xl">
            Your ideas. Your files. <span className="text-accent-soft">Your AI.</span>
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-relaxed text-text-muted">
            Discover useful creative workflows, adapt them to your project, keep your work locally, and export portable agent packs without surrendering your prompts or process.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Link href="/create" className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-dim">
              Open Creator Studio <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link href="/founding" className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-6 py-3 text-sm font-medium text-text transition hover:bg-bg-elevated">
              Founding Creator · $29
            </Link>
          </div>
          <p className="mt-6 text-xs text-text-dim">Bring your own AI. Keep your prompts. Keep your audience.</p>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-5xl px-6 py-20 sm:py-24">
        <div className="grid gap-6 sm:grid-cols-3">
          {STEPS.map(([n, title, body]) => (
            <article key={n} className="rounded-2xl border border-border bg-bg-card p-7">
              <span className="font-mono text-xs text-text-dim">{n}</span>
              <h2 className="mt-4 text-xl font-medium">{title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-text-muted">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-border bg-bg-elevated">
        <div className="mx-auto grid max-w-5xl gap-8 px-6 py-16 sm:grid-cols-3 sm:py-20">
          <div className="flex gap-3"><Search className="h-5 w-5 shrink-0 text-accent-soft"/><p className="text-sm text-text-muted"><span className="text-text">Find less, choose better.</span> Discovery returns the strongest few matches instead of thousands of raw prompts.</p></div>
          <div className="flex gap-3"><ShieldCheck className="h-5 w-5 shrink-0 text-success"/><p className="text-sm text-text-muted"><span className="text-text">Provenance stays attached.</span> Verified source and license metadata travel with exported recipes.</p></div>
          <div className="flex gap-3"><Download className="h-5 w-5 shrink-0 text-warning"/><p className="text-sm text-text-muted"><span className="text-text">Your work stays portable.</span> Export inspectable files and agent context instead of locking your process into one model.</p></div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-20 text-center sm:py-24">
        <Sparkles className="mx-auto h-6 w-6 text-accent-soft"/>
        <h2 className="mt-6 text-3xl font-semibold tracking-tight">Start with one idea.</h2>
        <p className="mx-auto mt-4 max-w-xl text-text-muted">Describe what you want to make. Choose a useful recipe. Adapt it. Keep it.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/create" className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-dim">
            Start creating <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link href="/founding" className="inline-flex items-center justify-center rounded-xl border border-border px-6 py-3 text-sm font-medium text-text transition hover:bg-bg-elevated">
            See Founding Creator
          </Link>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 py-10 text-xs text-text-dim sm:flex-row">
          <span>© {new Date().getFullYear()} Creator Studio</span>
          <div className="flex gap-5"><Link href="/create" className="transition hover:text-text">Creator workspace</Link><Link href="/founding" className="transition hover:text-text">Founding Creator</Link></div>
        </div>
      </footer>
    </main>
  );
}
