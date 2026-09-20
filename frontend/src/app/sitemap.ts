import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/blog";

const SITE = "https://bufferblaster.netlify.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ["", "/install", "/blog"].map((path) => ({
    url: `${SITE}${path}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: path === "" ? 1 : path === "/install" ? 0.9 : 0.7,
  }));
  const postRoutes = getAllPosts().map((post) => ({
    url: `${SITE}/blog/${post.slug}`,
    lastModified: new Date(post.date),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));
  return [...staticRoutes, ...postRoutes];
}
