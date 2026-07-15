import Link from "next/link";
import type { Metadata } from "next";
import { ArrowLeft } from "lucide-react";
import { getAllPosts, CATEGORY_LABEL } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Field notes on Shopify growth, social strategy, and what actually converts.",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function BlogIndex() {
  const posts = getAllPosts();
  const [featured, ...rest] = posts;

  return (
    <main className="flex-1">
      <div className="mx-auto max-w-3xl px-6 py-20">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-text-dim transition hover:text-text"
        >
          <ArrowLeft className="h-3 w-3" />
          Back home
        </Link>

        <h1 className="mt-8 text-3xl font-semibold tracking-tight sm:text-4xl">
          Field notes
        </h1>
        <p className="mt-3 max-w-xl text-text-muted">
          What we’re learning about Shopify growth, social strategy, and the
          content that actually converts. Written by the team, not a robot.
        </p>

        {posts.length === 0 && (
          <p className="mt-12 text-sm text-text-dim">
            No posts yet. Check back soon.
          </p>
        )}

        {/* Featured */}
        {featured && (
          <Link
            href={`/blog/${featured.slug}`}
            className="mt-12 block rounded-xl border border-border bg-bg-card p-8 transition hover:border-border-strong"
          >
            <div className="flex items-center gap-3 text-xs">
              <span className="rounded bg-accent/10 px-2 py-0.5 font-medium text-accent-soft">
                {CATEGORY_LABEL(featured.category)}
              </span>
              <span className="text-text-dim">{formatDate(featured.date)}</span>
              <span className="text-text-dim">·</span>
              <span className="text-text-dim">{featured.readingTime} min read</span>
            </div>
            <h2 className="mt-4 text-2xl font-semibold tracking-tight">
              {featured.title}
            </h2>
            <p className="mt-3 text-text-muted">{featured.excerpt}</p>
          </Link>
        )}

        {/* Rest */}
        <div className="mt-8 divide-y divide-border border-t border-border">
          {rest.map((p) => (
            <Link
              key={p.slug}
              href={`/blog/${p.slug}`}
              className="block py-6 transition hover:bg-bg-elevated/40"
            >
              <div className="flex items-center gap-3 text-xs">
                <span className="text-text-dim">{CATEGORY_LABEL(p.category)}</span>
                <span className="text-text-dim">{formatDate(p.date)}</span>
              </div>
              <h3 className="mt-2 font-medium">{p.title}</h3>
              <p className="mt-1 text-sm text-text-muted">{p.excerpt}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
