import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function AdminBlogPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Blog</h1>
      <p className="mt-1 text-sm text-text-muted">
        Posts live as MDX in <code className="text-text">content/blog/</code>.
        The draft editor activates on the VPS.
      </p>
      <Link
        href="/blog"
        className="mt-6 inline-flex items-center gap-2 text-sm text-accent-soft hover:underline"
      >
        View published posts
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
