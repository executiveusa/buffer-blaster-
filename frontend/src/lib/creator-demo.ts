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
  source: { attribution: string; license: string; license_verified: boolean };
};

export const CREATOR_DEMO_CARDS: CreatorCard[] = [
  {id:"bb-image-product-studio-001",slug:"clean-product-studio-shot",title:"Clean Product Studio Shot",description:"Turn a product reference into a polished studio-style hero image with controlled lighting and a clear commercial focal point.",category:"Images",subcategory:"Product Photography",media_type:"image",prompt:"Create a premium studio product photograph of {{product}} with {{background}} and {{lighting}}.",tags:["product","ecommerce","studio","photography","campaign","hero"],model_hints:["image-generation"],preview_assets:[],required_inputs:["product","background","lighting"],requires_reference:true,quality_score:90,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-video-launch-reel-001",slug:"cinematic-launch-reel",title:"Cinematic Launch Reel",description:"A short-form launch structure for turning one product or creative idea into a visually coherent vertical reel.",category:"Video",subcategory:"Short-form",media_type:"workflow",prompt:"Build a 15-30 second vertical launch reel for {{subject}} aimed at {{audience}}.",tags:["video","reel","launch","instagram","tiktok","cinematic","short-form"],model_hints:["video-generation","image-to-video"],preview_assets:[],required_inputs:["subject","audience","tone","platform"],requires_reference:false,quality_score:92,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-social-ugc-ad-001",slug:"ugc-problem-proof-offer",title:"UGC Problem → Proof → Offer",description:"A creator-first UGC ad recipe that starts with a real problem, demonstrates believable proof, and closes with one concrete action.",category:"Social",subcategory:"UGC",media_type:"workflow",prompt:"Create a natural UGC script for {{product}} for {{audience}} in {{voice}} voice.",tags:["ugc","ad","creator","social","script","offer","conversion"],model_hints:["text-generation","video-generation"],preview_assets:[],required_inputs:["product","audience","voice"],requires_reference:false,quality_score:89,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-brand-moodboard-001",slug:"brand-world-moodboard",title:"Brand World Moodboard",description:"Translate a brand idea into a coherent visual world before generating final campaign assets.",category:"Brand",subcategory:"Creative Direction",media_type:"image",prompt:"Create a visual moodboard for {{brand}} built around {{idea}}.",tags:["brand","moodboard","creative-direction","visual-identity","campaign"],model_hints:["image-generation","multimodal"],preview_assets:[],required_inputs:["brand","idea"],requires_reference:false,quality_score:87,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-writing-short-script-001",slug:"60-second-story-script",title:"60-Second Story Script",description:"A compact story structure for creators who need a clear beginning, tension, turn, and payoff without filler.",category:"Writing",subcategory:"Scripts",media_type:"text",prompt:"Write a spoken script under 60 seconds about {{topic}} for {{audience}} in {{voice}} voice.",tags:["writing","script","story","short-form","voiceover","creator"],model_hints:["text-generation"],preview_assets:[],required_inputs:["topic","audience","voice"],requires_reference:false,quality_score:88,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}},
  {id:"bb-workflow-launch-pack-001",slug:"one-idea-launch-pack",title:"One Idea → Launch Pack",description:"Turn one idea into a coordinated mini-launch: visual direction, hero asset, reel concept, caption, and reusable agent pack.",category:"Workflows",subcategory:"Launch",media_type:"workflow",prompt:"Transform {{idea}} into a compact launch pack for {{audience}} using {{brand_voice}}.",tags:["workflow","launch","campaign","image","video","social","icm"],model_hints:["multimodal","text-generation","image-generation","video-generation"],preview_assets:[],required_inputs:["idea","audience","brand_voice"],requires_reference:false,quality_score:95,source:{attribution:"Curated recipe",license:"proprietary",license_verified:true}}
];

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
  return [...CREATOR_DEMO_CARDS]
    .sort((a,b) => score(b)-score(a) || b.quality_score-a.quality_score || a.id.localeCompare(b.id))
    .slice(0, Math.max(1, Math.min(limit,12)));
}
