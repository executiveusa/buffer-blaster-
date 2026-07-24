export type CreatorCard = {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  subcategory: string;
  media_type: "image" | "video" | "text" | "workflow";
  prompt: string;
  tags: string[];
  model_hints: string[];
  preview_assets: string[];
  required_inputs: string[];
  requires_reference: boolean;
  quality_score: number;
  source: {
    attribution: string;
    license: string;
    license_verified: boolean;
    repo?: string;
    path?: string;
    author?: string;
    content_hash?: string;
  };
};

// Generated snapshot from provenance-verified upstream sources. These cards are
// intentionally small in Phase 8; the ingestion compiler can replace/expand this
// snapshot without changing the discovery or export contracts.
export const IMPORTED_CREATOR_CARDS: CreatorCard[] = [
  {
    id: "ym-nbp-wide-quote-card-001",
    slug: "wide-quote-card-portrait",
    title: "Wide Quote Card with Portrait",
    description: "Create a wide editorial quote card with a portrait, serif typography, and a reusable quote/author structure.",
    category: "Images",
    subcategory: "Social Media Post",
    media_type: "image",
    prompt: "A wide quote card featuring a famous person, with a brown background and a light-gold serif font for the quote: “{argument name=\"famous_quote\" default=\"Stay Hungry, Stay Foolish\"}” and smaller text: “—{argument name=\"author\" default=\"Steve Jobs\"}.” There is a large, subtle quotation mark before the text. The portrait of the person is on the left, the text on the right.\nThe text occupies two-thirds of the image and the portrait one-third, with a slight gradient transition effect on the portrait.",
    tags: ["quote", "portrait", "social", "editorial", "typography", "featured"],
    model_hints: ["image-generation"],
    preview_assets: [],
    required_inputs: ["famous_quote", "author", "portrait subject"],
    requires_reference: false,
    quality_score: 94,
    source: {
      attribution: "YouMind OpenLab · Nicolechan",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-nano-banana-pro-prompts",
      path: "README.md#no-1-wide-quote-card-with-portrait-and-chineseenglish-customization",
      author: "Nicolechan",
      content_hash: "da6b0f9d03d43f524f76f5fc05c5e8417767b689846a58bdf9353731cb4c03a8"
    }
  },
  {
    id: "ym-nbp-hand-drawn-header-003",
    slug: "hand-drawn-header-from-photo",
    title: "Hand-Drawn Header from a Photo",
    description: "Turn an uploaded person into a simple hand-drawn horizontal article header with controlled title text and gradient styling.",
    category: "Images",
    subcategory: "Article Header",
    media_type: "image",
    prompt: "Completely recreate the uploaded person. Make it a header image for a note article where that person introduces “Nano Banana Pro”. Aspect ratio: horizontal 16:9.\nStyle and colors: simple, hand-drawn style, italic, with a blue and green gradient. Title text: “In-depth explanation of Google’s new AI ‘Nano Banana Pro’”.",
    tags: ["header", "illustration", "photo-reference", "article", "hand-drawn", "16:9"],
    model_hints: ["image-generation", "image-editing"],
    preview_assets: [],
    required_inputs: ["person reference", "article title"],
    requires_reference: true,
    quality_score: 91,
    source: {
      attribution: "YouMind OpenLab · Akira Kudo",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-nano-banana-pro-prompts",
      path: "README.md#no-3-hand-drawn-style-header-image-prompt-from-photo",
      author: "Akira Kudo",
      content_hash: "e6e3818562beaeb1e738940e18054ec512bd556b20b500a7feb4fecb01d12dbc"
    }
  },
  {
    id: "ym-nbp-vintage-patent-006",
    slug: "vintage-patent-document",
    title: "Vintage Patent Document",
    description: "Generate an archival late-1800s patent-document aesthetic with technical diagrams, aged paper, annotations, seals, and period detail.",
    category: "Images",
    subcategory: "Poster / Flyer",
    media_type: "image",
    prompt: "A vintage patent document for {argument name=\"invention\" default=\"INVENTION\"}, styled after late 1800s United States Patent Office filings. The page features precise technical drawings with numbered callouts (Fig. 1, Fig. 2, Fig. 3) showing front, side, and exploded views.\nHandwritten annotations in fountain-pen ink describe mechanisms. The paper is aged ivory with foxing stains and soft fold creases. An official embossed seal and red wax stamp appear in the corner. A hand-signed inventor's name and date appear at the bottom. The entire image feels like a recovered archival document—authoritative, historic, and slightly mysterious.",
    tags: ["patent", "vintage", "technical", "poster", "archival", "invention"],
    model_hints: ["image-generation"],
    preview_assets: [],
    required_inputs: ["invention"],
    requires_reference: false,
    quality_score: 93,
    source: {
      attribution: "YouMind OpenLab · Alexandra Aisling",
      license: "CC-BY-4.0",
      license_verified: true,
      repo: "YouMind-OpenLab/awesome-nano-banana-pro-prompts",
      path: "README.md#no-6-vintage-patent-document-for-an-invention",
      author: "Alexandra Aisling",
      content_hash: "3fd5bb12a6cf320caa907caf4c78a588ae2bfb15df6aedf0d51af92332752c0b"
    }
  }
];

export const CREATOR_DEMO_CARDS: CreatorCard[] = [
  {id:"bb-image-product-studio-001",slug:"clean-product-studio-shot",title:"Clean Product Studio Shot",description:"Turn a product reference into a polished studio-style hero image with controlled lighting and a clear commercial focal point.",category:"Images",subcategory:"Product Photography",media_type:"image",prompt:"Create a premium studio product photograph of {{product}} with {{background}} and {{lighting}}.",tags:["product","ecommerce","studio","photography","campaign","hero"],model_hints:["image-generation"],preview_assets:[],required_inputs:["product","background","lighting"],requires_reference:true,quality_score:90,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-video-launch-reel-001",slug:"cinematic-launch-reel",title:"Cinematic Launch Reel",description:"A short-form launch structure for turning one product or creative idea into a visually coherent vertical reel.",category:"Video",subcategory:"Short-form",media_type:"workflow",prompt:"Build a 15-30 second vertical launch reel for {{subject}} aimed at {{audience}}.",tags:["video","reel","launch","instagram","tiktok","cinematic","short-form"],model_hints:["video-generation","image-to-video"],preview_assets:[],required_inputs:["subject","audience","tone","platform"],requires_reference:false,quality_score:92,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-social-ugc-ad-001",slug:"ugc-problem-proof-offer",title:"UGC Problem → Proof → Offer",description:"A creator-first UGC ad recipe that starts with a real problem, demonstrates believable proof, and closes with one concrete action.",category:"Social",subcategory:"UGC",media_type:"workflow",prompt:"Create a natural UGC script for {{product}} for {{audience}} in {{voice}} voice.",tags:["ugc","ad","creator","social","script","offer","conversion"],model_hints:["text-generation","video-generation"],preview_assets:[],required_inputs:["product","audience","voice"],requires_reference:false,quality_score:89,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-brand-moodboard-001",slug:"brand-world-moodboard",title:"Brand World Moodboard",description:"Translate a brand idea into a coherent visual world before generating final campaign assets.",category:"Brand",subcategory:"Creative Direction",media_type:"image",prompt:"Create a visual moodboard for {{brand}} built around {{idea}}.",tags:["brand","moodboard","creative-direction","visual-identity","campaign"],model_hints:["image-generation","multimodal"],preview_assets:[],required_inputs:["brand","idea"],requires_reference:false,quality_score:87,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-writing-short-script-001",slug:"60-second-story-script",title:"60-Second Story Script",description:"A compact story structure for creators who need a clear beginning, tension, turn, and payoff without filler.",category:"Writing",subcategory:"Scripts",media_type:"text",prompt:"Write a spoken script under 60 seconds about {{topic}} for {{audience}} in {{voice}} voice.",tags:["writing","script","story","short-form","voiceover","creator"],model_hints:["text-generation"],preview_assets:[],required_inputs:["topic","audience","voice"],requires_reference:false,quality_score:88,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-workflow-launch-pack-001",slug:"one-idea-launch-pack",title:"One Idea → Launch Pack",description:"Turn one idea into a coordinated mini-launch: visual direction, hero asset, reel concept, caption, and reusable agent pack.",category:"Workflows",subcategory:"Launch",media_type:"workflow",prompt:"Transform {{idea}} into a compact launch pack for {{audience}} using {{brand_voice}}.",tags:["workflow","launch","campaign","image","video","social","icm"],model_hints:["multimodal","text-generation","image-generation","video-generation"],preview_assets:[],required_inputs:["idea","audience","brand_voice"],requires_reference:false,quality_score:95,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}}
];

export const CREATOR_CARDS: CreatorCard[] = [...IMPORTED_CREATOR_CARDS, ...CREATOR_DEMO_CARDS];

const tokens = (value: string) => new Set((value.toLowerCase().match(/[a-z0-9]+/g) ?? []));

export function discoverDemoCards(intent: string, limit = 3): CreatorCard[] {
  const intentTokens = tokens(intent);
  const score = (card: CreatorCard) => {
    const title = tokens(card.title);
    const description = tokens(card.description);
    const category = tokens(`${card.category} ${card.subcategory}`);
    const tags = new Set(card.tags.map((tag) => tag.toLowerCase()));
    const overlap = (set: Set<string>, weight: number) => [...intentTokens].filter((token) => set.has(token)).length * weight;
    return overlap(title,8)+overlap(tags,5)+overlap(category,3)+overlap(description,2)+Math.floor(card.quality_score/10);
  };
  return [...CREATOR_CARDS]
    .sort((a,b) => score(b)-score(a) || b.quality_score-a.quality_score || a.id.localeCompare(b.id))
    .slice(0, Math.max(1, Math.min(limit,12)));
}
