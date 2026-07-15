/**
 * Buffer Blaster — Per-Client Content Pipeline
 * Sandcastle workflow script (mattpocock/sandcastle)
 * 
 * Runs the full pipeline for a single client.
 * Called by the per-client orchestrator after interview completes.
 * 
 * Usage: hermes run scripts/client_pipeline.ts --client-slug=client-a
 */

import { agent, parallel, pipeline } from "sandcastle";
import { createClient } from "@supabase/supabase-js";
import Absurd from "absurd"; // earendil-works/absurd

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

const absurd = new Absurd({ retries: 3, backoff: 30_000 });

export default pipeline("client-content-pipeline", async (ctx) => {
  const { clientSlug } = ctx.params;

  // Load client brief from Supabase
  const { data: client } = await supabase
    .from("clients")
    .select("*, interviews(*)")
    .eq("slug", clientSlug)
    .single();

  if (!client?.interviews?.length) {
    throw new Error(`No completed interview found for ${clientSlug}. Run grill-me first.`);
  }

  const brief = client.interviews[0].brief_yaml;

  // Phase 1: Research (parallel scraping)
  const research = await parallel("research", [
    agent("competitor-scrape", {
      goal: `Scrape top competitor accounts for ${client.niche} niche on Instagram, TikTok, YouTube.
             Identify outliers (engagement > mean + 2σ). Extract hook patterns.
             Write results to research/outliers.json for client ${clientSlug}.`,
      toolsets: ["web_search", "terminal"],
    }),
    agent("trend-check", {
      goal: `Cross-reference Google Trends for ${client.niche} in ${client.shopify_url} market.
             Use as signal only — not primary driver. Flag any pre-trend indicators.
             Compare against outlier data from competitor scrape.`,
      toolsets: ["web_search"],
    }),
    agent("customer-analysis", {
      goal: `Analyze Shopify customer CSV for ${clientSlug}.
             Identify top 20% LTV segment. Find purchase patterns, combos, timing.
             Write segments to research/customer_segments.json.`,
      toolsets: ["terminal", "read_file"],
    }),
  ]);

  // Bead checkpoint after research
  await writeBead("research-complete", clientSlug);

  // Phase 2: Content ideation (sequential, uses research output)
  const ideas = await agent("content-ideation", {
    goal: `Using research results for ${clientSlug}, generate 15 content ideas.
           Each idea: hook (one line, stop-slop filtered), platform, format, 3 caption variants.
           Niche: ${client.niche}. Brand voice: ${brief.brand_voice}.
           Never use adverbs. Never use passive voice. Write like a person, not a brand.
           Save to Supabase content_units with status=draft.`,
    context: { research, brief },
    toolsets: ["terminal", "web_search"],
  });

  // Bead checkpoint after ideation
  await writeBead("ideation-complete", clientSlug);

  // Phase 3: Video prompt generation + Higgsfield (parallel by content unit)
  const videoUnits = ideas.filter((i: any) => i.format === "video");

  const videos = await parallel(
    "video-generation",
    videoUnits.map((unit: any) =>
      agent(`video-${unit.id}`, {
        goal: `Generate Seedance 2.0 video prompt for content unit ${unit.id}.
               Niche: ${client.niche}. Hook: "${unit.hook}".
               Use ${client.niche === "food-beverage" ? "food-beverage SKILL" : "ugc-video SKILL"}.
               Call Higgsfield MCP to generate video.
               On failure: log to Supabase, retry via absurd (3x, 30s backoff).
               Save video URL to content_units.video_url.`,
        toolsets: ["mcp_higgsfield"],
      })
    )
  );

  // Bead checkpoint after video gen
  await writeBead("video-generation-complete", clientSlug);

  // Phase 4: Scoring (all content units)
  const scored = await agent("scorer", {
    goal: `Score all content units for ${clientSlug} (0-100).
           Dimensions: hook_strength(25%), platform_fit(20%), niche_relevance(20%),
           trend_alignment(15%), visual_quality(10%), audience_match(10%).
           Show reasoning for each dimension. Save breakdown to score_breakdown_json.
           Sort by total score. Flag top 3 per platform for approval queue.`,
    context: { ideas, videos, research },
    toolsets: ["terminal"],
  });

  // Phase 5: Build approval queue
  const topContent = scored.filter((s: any) => s.raw_score >= 80);
  
  const { data: queue } = await supabase
    .from("approval_queues")
    .insert({
      client_id: client.id,
      content_unit_ids: topContent.map((c: any) => c.id),
      sent_at: new Date().toISOString(),
    })
    .select()
    .single();

  // Bead checkpoint before human notification
  await writeBead("approval-queue-ready", clientSlug);

  // Phase 6: Send approval email
  await agent("notifier", {
    goal: `Send approval email for client ${clientSlug}.
           Queue ID: ${queue!.id}. Top content: ${topContent.length} posts.
           Dashboard URL: ${process.env.VERCEL_URL}/review/${clientSlug}/${queue!.id}.
           Email format: ranked list, score, hook preview, thumbnail, approve button.
           Subject: "${client.name} — ${topContent.length} posts ready for review"
           NO enthusiasm. NO exclamation points. Just the facts and the ranked list.`,
    toolsets: ["send_message"],
  });

  return {
    status: "approval-pending",
    client: clientSlug,
    queueId: queue!.id,
    postsQueued: topContent.length,
  };
});

/**
 * Write a reversible bead checkpoint
 */
async function writeBead(action: string, clientSlug: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const beadPath = `.beads/${timestamp}_${action}_${clientSlug}.bead`;
  
  await supabase.from("beads").insert({
    timestamp: new Date().toISOString(),
    action,
    file_path: beadPath,
    reversible: true,
    notes: `Pipeline checkpoint: ${action} for ${clientSlug}`,
  });
}
