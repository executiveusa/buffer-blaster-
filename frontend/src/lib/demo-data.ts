/**
 * Seeded demo data — what the dashboard renders in demo mode
 * (NEXT_PUBLIC_DEMO_MODE=true, the default). Mirrors the API's
 * api/services/demo.py so the UI is identical with or without the backend.
 */

export type Niche = "food-beverage" | "beauty-skincare" | "apparel" | "home-lifestyle";

export interface Client {
  id: string;
  slug: string;
  name: string;
  niche: Niche;
  shopify_url: string;
  schema: string;
  created_at: string;
  status: "active" | "paused" | "onboarding";
  posts_scheduled: number;
  avg_score: number;
}

export interface ScoreBreakdown {
  hook_strength: number;
  platform_fit: number;
  niche_relevance: number;
  trend_alignment: number;
  visual_quality: number;
  audience_match: number;
}

export interface ContentUnit {
  id: string;
  client_slug: string;
  schema: string;
  platform: "tiktok" | "instagram" | "pinterest" | "youtube";
  hook: string;
  caption: string;
  raw_score: number;
  score_breakdown: ScoreBreakdown;
  status: "draft" | "pending" | "approved" | "rejected" | "published";
}

export const DEMO_CLIENTS: Client[] = [
  {
    id: "demo-cella",
    slug: "cella-coffee",
    name: "Cella Coffee Roasters",
    niche: "food-beverage",
    shopify_url: "https://cella-coffee.myshopify.com",
    schema: "schema_cella_coffee",
    created_at: "2026-06-14T09:00:00Z",
    status: "active",
    posts_scheduled: 47,
    avg_score: 84.2,
  },
  {
    id: "demo-lumen",
    slug: "lumen-skincare",
    name: "Lumen Skincare",
    niche: "beauty-skincare",
    shopify_url: "https://lumen-skincare.myshopify.com",
    schema: "schema_lumen_skincare",
    created_at: "2026-06-20T09:00:00Z",
    status: "active",
    posts_scheduled: 31,
    avg_score: 86.7,
  },
];

function unit(
  client_slug: string,
  platform: ContentUnit["platform"],
  hook: string,
  score: number,
  status: ContentUnit["status"],
): ContentUnit {
  return {
    id: `${client_slug}-${platform}-${score}`,
    client_slug,
    schema: `schema_${client_slug.replace(/-/g, "_")}`,
    platform,
    hook,
    caption: `${hook} — Swipe to see how we made it.`,
    raw_score: score,
    score_breakdown: {
      hook_strength: Math.round(score * 0.92),
      platform_fit: Math.round(score * 0.88),
      niche_relevance: Math.round(score * 0.95),
      trend_alignment: Math.round(score * 0.78),
      visual_quality: Math.round(score * 0.85),
      audience_match: Math.round(score * 0.90),
    },
    status,
  };
}

export const DEMO_CONTENT: ContentUnit[] = [
  unit("cella-coffee", "tiktok", "We roasted 1,000 beans and only 12 made the cut.", 91, "approved"),
  unit("cella-coffee", "instagram", "The pour that took our barista 4 years to nail.", 85, "approved"),
  unit("cella-coffee", "pinterest", "Morning ritual: 3 minutes, zero rush.", 78, "pending"),
  unit("lumen-skincare", "instagram", "She used our serum for 30 days. Here's day 14.", 88, "approved"),
  unit("lumen-skincare", "tiktok", "The ingredient dermatologists won't name on camera.", 93, "pending"),
  unit("lumen-skincare", "youtube", "Why your $80 cream isn't doing what you think.", 74, "rejected"),
];

export const DEMO_DASHBOARD = {
  greeting: "Welcome back, operator.",
  active_clients: DEMO_CLIENTS.length,
  posts_this_week: DEMO_CONTENT.filter((u) => u.status === "approved").length,
  pending_approvals: DEMO_CONTENT.filter((u) => u.status === "pending").length,
  pipeline_running: false,
};

export const NICHE_LABELS: Record<Niche, string> = {
  "food-beverage": "Food & Beverage",
  "beauty-skincare": "Beauty & Skincare",
  apparel: "Apparel & Accessories",
  "home-lifestyle": "Home & Lifestyle",
};
