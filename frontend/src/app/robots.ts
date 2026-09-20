import type { MetadataRoute } from "next";

const SITE = "https://bufferblaster.netlify.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/admin/*", "/studio", "/studio/*"] }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
