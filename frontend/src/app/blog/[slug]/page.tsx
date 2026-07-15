import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { remark } from "remark";
import html from "remark-html";
import { ArrowLeft } from "lucide-react";
import { getAllPosts, getPost, CATEGORY_LABEL } from "@/lib/blog";

export async function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
      authors: [post.author],
    },
  };
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  const processed = await remark().use(html).process(post.content);
  const htmlContent = processed.toString();

  // JSON-LD for SEO.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.date,
    author: { "@type": "Organization", name: post.author },
  };

  return (
    <main className="flex-1">
      <article className="mx-auto max-w-2xl px-6 py-20">
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-xs text-text-dim transition hover:text-text"
        >
          <ArrowLeft className="h-3 w-3" />
          All posts
        </Link>

        <div className="mt-8 flex items-center gap-3 text-xs">
          <span className="rounded bg-accent/10 px-2 py-0.5 font-medium text-accent-soft">
            {CATEGORY_LABEL(post.category)}
          </span>
          <span className="text-text-dim">{formatDate(post.date)}</span>
          <span className="text-text-dim">·</span>
          <span className="text-text-dim">{post.readingTime} min read</span>
        </div>

        <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          {post.title}
        </h1>
        <p className="mt-4 text-text-muted">By {post.author}</p>

        <div
          className="prose-stavarai mt-10"
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        />

        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </article>
    </main>
  );
}
