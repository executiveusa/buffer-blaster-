import type { CreatorCard } from "./creator-demo";

// Small transformed batch derived from CC-BY-4.0 upstream examples.
// Prompts are normalized for this product's adaptation contract rather than copied verbatim.
export const GROWTH_CREATOR_CARDS: CreatorCard[] = [
  {
    id: "ym-gpt2-explainer-slide-003",
    slug: "high-density-explainer-slide",
    title: "High-Density Explainer Slide",
    description: "Build a friendly illustrated explainer that still carries the information density of a professional briefing slide.",
    category: "Images",
    subcategory: "Infographic / Edu Visual",
    media_type: "image",
    prompt: "Create a {{format}} explainer about {{theme}}. Use approachable hand-drawn illustration, dense but clearly grouped information, strong hierarchy, labeled callouts, and a presentation-ready composition. Keep the visual friendly while making the information feel rigorous and complete.",
    tags: ["infographic", "explainer", "slide", "education", "diagram", "briefing"],
    model_hints: ["image-generation"],
    preview_assets: [],
    required_inputs: ["format", "theme"],
    requires_reference: false,
    quality_score: 92,
    source: {
      attribution: "Adapted from YouMind OpenLab · やまもん",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-gpt-image-2",
      path: "README.md#no-3-momotaro-explainer-slide-in-hybrid-style",
      author: "やまもん"
    }
  },
  {
    id: "ym-gpt2-lifestyle-selfie-001",
    slug: "travel-lifestyle-selfie",
    title: "Travel Lifestyle Selfie",
    description: "Create a polished travel portrait with controlled wardrobe, environment, foreground perspective, and editorial lighting.",
    category: "Images",
    subcategory: "Profile / Avatar",
    media_type: "image",
    prompt: "Create a photorealistic wide-angle travel selfie of {{subject}} at {{location}} during {{time_of_day}}. Use natural foreground arm perspective, a clearly readable landmark in soft focus, believable lifestyle props, realistic skin and fabric texture, shallow depth of field, and an editorial vertical 4:5 composition. Avoid text, watermarks, and unrelated people.",
    tags: ["portrait", "selfie", "travel", "lifestyle", "photography", "editorial"],
    model_hints: ["image-generation"],
    preview_assets: [],
    required_inputs: ["subject", "location", "time_of_day"],
    requires_reference: false,
    quality_score: 91,
    source: {
      attribution: "Adapted from YouMind OpenLab · Camille_1982_fr",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-gpt-image-2",
      path: "README.md#no-1-profile-avatar---paris-balcony-selfie",
      author: "Camille_1982_fr"
    }
  },
  {
    id: "ym-gpt2-staircase-infographic-006",
    slug: "milestone-staircase-infographic",
    title: "3D Milestone Staircase Infographic",
    description: "Turn a flat sequence into a realistic stepped timeline with milestones, labels, side panels, and a strong educational centerpiece.",
    category: "Images",
    subcategory: "Infographic / Edu Visual",
    media_type: "image",
    prompt: "Transform {{topic}} into a 3D milestone staircase infographic. Use {{material}} for the steps, {{background_style}} for the backdrop, realistic subject renders on major milestones, a compact legend, concise side labels, and a final speculative step showing {{future_concept}}. Keep the path visually readable from first milestone to last.",
    tags: ["infographic", "education", "3d", "timeline", "milestones", "diagram"],
    model_hints: ["image-generation"],
    preview_assets: [],
    required_inputs: ["topic", "material", "background_style", "future_concept"],
    requires_reference: false,
    quality_score: 90,
    source: {
      attribution: "Adapted from YouMind OpenLab · 知识猫图解",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-gpt-image-2",
      path: "README.md#no-6-3d-stone-staircase-evolution-infographic",
      author: "知识猫图解"
    }
  }
];
