import type { MetadataRoute } from "next";

const SITE = "https://stavarai.example.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: ["/admin", "/admin/*"] },
    ],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
