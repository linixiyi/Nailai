export type NailTaxonomy = {
  colors: string[];
  techniques: string[];
  shapes: string[];
  styles: string[];
  occasions: string[];
  lengths: string[];
};

export type NailStyle = {
  id: string;
  name: string;
  color: string;
  finish: string;
  occasion: string[];
  tags: string[];
  palette: string[];
  prompt: string;
  difficulty: "easy" | "medium" | "hard";
  price_level: string;
  price?: string | null;
  image_url?: string | null;
  source_image_url?: string | null;
  design_image_url?: string | null;
  render_channel?: string | null;
  nail_length?: "natural" | "medium" | "long" | null;
  taxonomy?: NailTaxonomy;
  stock_total?: number | null;
  stock_reserved?: number | null;
  source_batch?: string | null;
  is_active?: boolean;
};

export type StyleAnalytics = {
  views: number;
  try_ons: number;
  interests: number;
  bookings: number;
};

export type MerchantStyleWithAnalytics = NailStyle & {
  analytics?: StyleAnalytics;
};

export type TryOnResponse = {
  job_id: string;
  status: string;
  channel: string;
  style: NailStyle;
  hand_confidence: number;
  quality_score: number;
  result_image_url: string;
  mask_image_url?: string | null;
  nail_count?: number | null;
  nail_confidence?: number | null;
  provider_payload?: Record<string, unknown>;
};

export type TryOnAuditRun = {
  id: string;
  created_at: string;
  completed_at?: string | null;
  status: "submitted" | "succeeded" | "failed";
  channel: string;
  endpoint: string;
  model?: string | null;
  result_image_url?: string | null;
  error?: string | null;
  prompt?: string;
  assets: {
    hand_image_url: string;
    style_image_url: string;
    mask_image_url?: string | null;
    prompt_url: string;
  };
  sent_to_model: {
    hand_image: boolean;
    style_image: boolean;
    mask_image: boolean;
    pixel_prompt: boolean;
  };
  pixel_control?: Record<string, unknown>;
  hand_analysis?: {
    analysis_source?: string;
    nail_count?: number;
    vision_error?: string;
    nails?: Array<Record<string, unknown>>;
  };
  timings_ms?: Record<string, number>;
  payload_summary?: Record<string, unknown>;
};

export type ChatResponse = {
  reply: string;
  intent: string;
  recommended_styles: NailStyle[];
  follow_up_questions: string[];
  channel?: string;
  model?: string | null;
};

export type DiyBountyAnswers = {
  occasion: string;
  nail_length: string;
  nail_shape: string;
  style: string;
  colors: string[];
  decorations: string[];
  budget: string;
  change_policy: string;
  user_prompt?: string;
};

export type DiyBountyVariant = {
  id: string;
  image_url: string;
  title: string;
  tags: string[];
  prompt: string;
};

export type DiyBountyGenerateResponse = {
  job_id: string;
  status: string;
  channel: string;
  prompt: string;
  variants: DiyBountyVariant[];
  provider_payload?: Record<string, unknown>;
};

export type DiyBountyAuditRun = {
  id: string;
  job_id: string;
  created_at: string;
  completed_at?: string | null;
  status: "submitted" | "succeeded" | "failed";
  channel: string;
  model?: string | null;
  prompt?: string;
  answers?: Partial<DiyBountyAnswers>;
  variants?: DiyBountyVariant[];
  error?: string | null;
  assets: {
    reference_image_url?: string | null;
    hand_image_url?: string | null;
    result_image_url?: string | null;
  };
  sent_to_model?: Record<string, unknown>;
  timings_ms?: Record<string, number>;
  payload_summary?: Record<string, unknown>;
  provider_payload?: Record<string, unknown>;
  publish?: {
    status?: string;
    bounty_id?: string;
    image?: string;
    merchant_visible?: boolean;
    store_visible?: boolean;
  };
};

export type DiyBountyPublishResponse = {
  id: string;
  title: string;
  budget: string;
  status: string;
  image: string;
  participants: number;
  deadline: string;
  description: string;
  selected_variant_id: string;
};

export type ShopInfo = {
  id: string;
  name: string;
  address: string;
  longitude?: number;
  latitude?: number;
  rating?: number;
  contact?: {
    phone: string;
    wechat: string;
  };
  facilities?: {
    wifi: boolean;
    parking: boolean;
    tea: boolean;
    private_room?: boolean;
  };
  active_score: number;
  wait_time?: string;
  schedule?: string;
};

export type StyleUploadPreviewResponse = {
  status: string;
  draft_id: string;
  source_image_url: string;
  design_image_url: string;
  render_status: string;
  render_channel: string;
  render_error?: string | null;
  extracted_taxonomy?: NailTaxonomy;
};

export type StyleUploadPublishResponse = {
  status: string;
  style_id: string;
  style: NailStyle;
};

export type MerchantStyleUploadTaskStatus = "queued" | "running" | "succeeded" | "failed";

export type MerchantStyleUploadTask = {
  id: string;
  status: MerchantStyleUploadTaskStatus;
  progress: number;
  stage: string;
  error: string | null;
  created_at: string;
  style_name: string;
  style_price: string;
  source_image_name: string;
  source_image_preview_url: string;
  taxonomy: NailTaxonomy;
  custom_tags_by_dimension: NailTaxonomy;
  preview_result: StyleUploadPreviewResponse | null;
  published_style: NailStyle | null;
};

// ── 原型/演示数据类型 ──────────────────────────────

export type PrototypeShop = {
  id: string;
  name: string;
  distance: string;
  rating: number;
  price: string;
  address: string;
  image: string;
  tags: string[];
  availableStyles: string[];
  wait_time?: string;
  schedule?: string;
  facilities?: {
    wifi: boolean;
    parking: boolean;
    tea: boolean;
    private_room?: boolean;
  };
};

export type PrototypeBounty = {
  id: string;
  title: string;
  budget: string;
  status: string;
  image: string;
  participants: number;
  deadline: string;
  description: string;
};

export type StoreTask = {
  id: string;
  customer: string;
  styleName: string;
  price: string;
  distance: string;
  status: string;
  image: string;
};
