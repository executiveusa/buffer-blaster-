import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import readingTime from "reading-time";

export interface BlogPostMeta {
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  date: string; // ISO
  readingTime: number; // minutes
  author: string;
}

export interface BlogPost extends BlogPostMeta {
  content: string; // markdown body (rendered client-side or via MDX)
}

// content/blog/ lives at the repo root, one level above frontend/.
const POSTS_DIR = path.join(process.cwd(), "..", "content", "blog");

const CATEGORIES = [
  "shopify-growth",
  "ai-content",
  "social-strategy",
  "behind-results",
  "tools",
] as const;

export function CATEGORY_LABEL(c: string): string {
  const map: Record<string, string> = {
    "shopify-growth": "Shopify Growth",
    "ai-content": "AI & Content",
    "social-strategy": "Social Strategy",
    "behind-results": "Behind the Results",
    tools: "Tools",
  };
  return map[c] ?? c;
}

export function getAllPosts(): BlogPostMeta[] {
  if (!fs.existsSync(POSTS_DIR)) return [];
  const files = fs.readdirSync(POSTS_DIR).filter((f) => f.endsWith(".mdx"));
  const posts = files.map((file) => {
    const slug = file.replace(/\.mdx$/, "");
    const raw = fs.readFileSync(path.join(POSTS_DIR, file), "utf-8");
    const { data, content } = matter(raw);
    const stats = readingTime(content);
    return {
      slug,
      title: data.title ?? slug,
      excerpt: data.excerpt ?? "",
      category: data.category ?? "uncategorized",
      date: data.date ?? new Date().toISOString(),
      readingTime: Math.max(1, Math.round(stats.minutes)),
      author: data.author ?? "The Team",
    } satisfies BlogPostMeta;
  });
  return posts.sort((a, b) => (a.date < b.date ? 1 : -1));
}

export function getPost(slug: string): BlogPost | null {
  const file = path.join(POSTS_DIR, `${slug}.mdx`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf-8");
  const { data, content } = matter(raw);
  const stats = readingTime(content);
  return {
    slug,
    title: data.title ?? slug,
    excerpt: data.excerpt ?? "",
    category: data.category ?? "uncategorized",
    date: data.date ?? new Date().toISOString(),
    readingTime: Math.max(1, Math.round(stats.minutes)),
    author: data.author ?? "The Team",
    content,
  };
}

export function getAllCategories(): string[] {
  return [...CATEGORIES];
}
