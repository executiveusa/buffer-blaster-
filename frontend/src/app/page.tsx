import Link from "next/link";
import { ArrowRight, Clock, Eye, ShieldCheck, TrendingUp } from "lucide-react";

const PAIN_POINTS = [
  {
    stat: "11pm",
    label: "and the content still isn’t scheduled.",
    body: "Every social media manager knows the 11pm draft. The one written between the meetings that ran long and the DMs that didn’t stop. We built this so nobody on our team writes that draft again.",
  },
  {
    stat: "3×",
    label: "more content than one human can make.",
    body: "A Shopify brand needs TikToks, Reels, Pinterest, captions, hooks, and carousels — across four platforms, every week. One person can’t make it. A team of five can’t make it well. We automated the making.",
  },
  {
    stat: "$0",
    label: "of your ad spend, wasted on slop.",
    body: "Most AI content reads like AI content. Customers scroll past it. Ours doesn’t, because we score every post against a viral rubric before it ever sees your feed — and we train the rubric on what actually worked for brands like yours.",
  },
  {
    stat: "14 days",
    label: "with zero manual content intervention.",
    body: "That’s the bar we hold ourselves to. Two straight weeks where the only thing you touch is the Approve button. If we can’t get there, we don’t take the client.",
  },
];

const HOW_IT_WORKS = [
  {
    n: "01",
    title: "We learn your brand",
    body: "A 30-minute intake. Your best customers, your flops, the three posts you wish you’d made. We turn it into a brief the system reads every time it writes.",
  },
  {
    n: "02",
    title: "The system makes the content",
    body: "Research, hooks, captions, video prompts — built for the platforms that matter to your niche. Scored, ranked, and queued. You see the top three, not the bottom thirty.",
  },
  {
    n: "03",
    title: "You approve. It ships.",
    body: "One email. One Approve button. Scheduled for the hours your audience is actually scrolling. We track what worked and feed it back into the next batch.",
  },
];

const RESULTS = [
  { value: "47", label: "posts shipped / client / month" },
  { value: "84", label: "average content score (of 100)" },
  { value: "4", label: "platforms, one workflow" },
  { value: "2", label: "active brands in production" },
];

export default function LandingPage() {
  return (
    <main className="flex-1">
      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 hero-grid" aria-hidden />
        <div className="absolute inset-0 glow" aria-hidden />
        <div className="relative mx-auto max-w-5xl px-6 pt-32 pb-24 sm:pt-40 sm:pb-32">
          <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-text-dim">
            Content operations for Shopify brands
          </p>
          <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl sm:leading-[1.02]">
            Your social feed,
            <br />
            <span className="text-accent-soft">actually full.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-text-muted">
            We research, write, and schedule the posts your team keeps meaning
            to make. TikTok, Reels, Pinterest — scored against a viral rubric,
            ready for your one-click approval.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href="#how"
              className="group inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-dim"
            >
              See how it works
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/blog"
              className="inline-flex items-center gap-2 rounded-lg border border-border px-6 py-3 text-sm font-medium text-text transition hover:border-border-strong hover:bg-bg-elevated"
            >
              Read the blog
            </Link>
          </div>
          <p className="mt-6 text-xs text-text-dim">
            Trusted by brands in food, beauty, apparel, and home.
          </p>
        </div>
      </section>

      {/* ── Pain points ──────────────────────────────────── */}
      <section className="border-t border-border bg-bg-elevated">
        <div className="mx-auto max-w-5xl px-6 py-24">
          <div className="grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2">
            {PAIN_POINTS.map((p) => (
              <div key={p.stat} className="bg-bg-card p-8 sm:p-10">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-semibold text-accent-soft">
                    {p.stat}
                  </span>
                  <span className="text-sm text-text">{p.label}</span>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-text-muted">
                  {p.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────── */}
      <section id="how" className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-24">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            How it works
          </h2>
          <p className="mt-3 max-w-lg text-text-muted">
            Three steps. The middle one is the part your team used to do at 11pm.
          </p>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            {HOW_IT_WORKS.map((s) => (
              <div key={s.n} className="group">
                <span className="font-mono text-sm text-text-dim">{s.n}</span>
                <h3 className="mt-3 text-lg font-medium">{s.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-text-muted">
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Results ──────────────────────────────────────── */}
      <section className="border-t border-border bg-bg-elevated">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {RESULTS.map((r) => (
              <div key={r.label}>
                <div className="font-mono text-4xl font-semibold text-text">
                  {r.value}
                </div>
                <div className="mt-2 text-xs leading-relaxed text-text-dim">
                  {r.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Trust strip ──────────────────────────────────── */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <div className="grid gap-8 sm:grid-cols-3">
            <div className="flex gap-3">
              <ShieldCheck className="h-5 w-5 shrink-0 text-success" />
              <p className="text-sm text-text-muted">
                <span className="text-text">Client data stays isolated.</span>{" "}
                Each brand gets its own encrypted schema. Never mixed, never
                leaked.
              </p>
            </div>
            <div className="flex gap-3">
              <Eye className="h-5 w-5 shrink-0 text-accent-soft" />
              <p className="text-sm text-text-muted">
                <span className="text-text">You always see it first.</span>{" "}
                Nothing publishes without your approval. One button, one email.
              </p>
            </div>
            <div className="flex gap-3">
              <Clock className="h-5 w-5 shrink-0 text-warning" />
              <p className="text-sm text-text-muted">
                <span className="text-text">Scheduled when it matters.</span>{" "}
                Per-niche time windows — when your audience is actually scrolling.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Closing CTA ──────────────────────────────────── */}
      <section className="border-t border-border bg-bg-elevated">
        <div className="mx-auto max-w-3xl px-6 py-24 text-center">
          <TrendingUp className="mx-auto h-6 w-6 text-accent-soft" />
          <h2 className="mt-6 text-2xl font-semibold tracking-tight sm:text-3xl">
            Stop writing the 11pm draft.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-text-muted">
            We take on a small number of Shopify brands at a time. If you’re
            spending more time planning content than running your business,
            let’s talk.
          </p>
          <Link
            href="mailto:hello@stavarai.example.com"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-dim"
          >
            Get in touch
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
          <p className="text-xs text-text-dim">
            © {new Date().getFullYear()} Stavarai. Content operations.
          </p>
          <div className="flex items-center gap-6">
            <Link href="/blog" className="text-xs text-text-dim transition hover:text-text">
              Blog
            </Link>
            <Link href="/admin" className="text-xs text-text-dim transition hover:text-text">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
