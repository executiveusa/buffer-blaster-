import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/blog";

const SITE = "https://stavarai.example.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ["", "/blog", "/admin"].map((path) => ({
    url: `${SITE}${path}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: path === "" ? 1 : 0.7,
  }));

  const postRoutes = getAllPosts().map((p) => ({
    url: `${SITE}/blog/${p.slug}`,
    lastModified: new Date(p.date),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...postRoutes];
}
