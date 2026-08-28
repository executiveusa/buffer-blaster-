import type { MetadataRoute } from "next";

const SITE = "https://stavarai-platform.vercel.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/admin/*", "/studio", "/studio/*"] }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
