import type {
  ChatResponse,
  DiyBountyAnswers,
  DiyBountyGenerateResponse,
  DiyBountyPublishResponse,
  DiyBountyAuditRun,
  NailStyle,
  MerchantStyleWithAnalytics,
  StyleUploadPreviewResponse,
  StyleUploadPublishResponse,
  TryOnAuditRun,
  TryOnResponse,
} from "./types";
import { prototypeBounties, prototypeShops, prototypeStyles, storeTasks } from "./prototypeData";
import { getClientUserId } from "./historyStore";
import { buildTestDashboardHeaders } from "./testDashboardAuth";

const DEFAULT_SERVER_API_BASE_URL = "http://127.0.0.1:8008";

function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.AI_SERVICE_URL || DEFAULT_SERVER_API_BASE_URL;
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "";
}

export function resolveApiAssetUrl(path?: string | null) {
  if (!path) return "";
  if (path.startsWith("/style-images/") || path.startsWith("/modao-assets/")) {
    return path;
  }
  return path.startsWith("/") ? `${getApiBaseUrl()}${path}` : path;
}

function normalizeStyleAssetUrls(style: NailStyle): NailStyle {
  return {
    ...style,
    image_url: style.image_url ? resolveApiAssetUrl(style.image_url) : style.image_url,
    source_image_url: style.source_image_url ? resolveApiAssetUrl(style.source_image_url) : style.source_image_url,
    design_image_url: style.design_image_url ? resolveApiAssetUrl(style.design_image_url) : style.design_image_url,
  };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    let detail: string | undefined;
    try {
      const data = JSON.parse(text) as { detail?: string };
      detail = data.detail;
    } catch {
      detail = undefined;
    }
    throw new Error(detail || text || `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStyles(): Promise<NailStyle[]> {
  try {
    const data = await readJson<{ styles: NailStyle[] }>(await fetch(`${getApiBaseUrl()}/api/v1/styles`));
    return data.styles.length ? data.styles.map(normalizeStyleAssetUrls) : prototypeStyles;
  } catch {
    return prototypeStyles;
  }
}

export function subscribeStyleCatalogUpdates(onUpdate: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleFocus = () => onUpdate();
  const handleVisibilityChange = () => {
    if (!document.hidden) {
      onUpdate();
    }
  };

  const intervalId = window.setInterval(() => {
    onUpdate();
  }, 30_000);

  window.addEventListener("focus", handleFocus);
  document.addEventListener("visibilitychange", handleVisibilityChange);

  return () => {
    window.clearInterval(intervalId);
    window.removeEventListener("focus", handleFocus);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  };
}

export async function fetchTaxonomyFilters(): Promise<Record<string, string[]>> {
  try {
    const data = await readJson<{ filters: Record<string, string[]> }>(
      await fetch(`${getApiBaseUrl()}/api/v1/taxonomy-filters`),
    );
    return data.filters;
  } catch {
    return {};
  }
}

export type ShopInfo = {
  name?: string;
  address?: string;
  active_score?: number;
  wait_time?: string;
  schedule?: string;
  facilities?: { wifi?: boolean; parking?: boolean; tea?: boolean; private_room?: boolean };
};

export async function fetchShopInfo(): Promise<ShopInfo | null> {
  try {
    const data = await readJson<ShopInfo>(
      await fetch(`${getApiBaseUrl()}/api/v1/store/shop-info`),
    );
    return data || null;
  } catch {
    // Return default shop info on failure
    return {
      name: "Coco 美甲工作室",
      address: "福田区福华三路88号",
      active_score: 0.95,
      wait_time: "无需等待",
      schedule: "排期充裕",
      facilities: { wifi: true, parking: true, tea: true, private_room: true },
    };
  }
}

export async function fetchShops() {
  try {
    const data = await readJson<{ shops: typeof prototypeShops }>(await fetch(`${getApiBaseUrl()}/api/v1/shops`));
    return data.shops;
  } catch {
    return prototypeShops;
  }
}

export async function fetchBounties() {
  try {
    const data = await readJson<{ bounties: typeof prototypeBounties }>(await fetch(`${getApiBaseUrl()}/api/v1/bounties`));
    return data.bounties;
  } catch {
    return prototypeBounties;
  }
}

export async function fetchStoreTasks() {
  try {
    const data = await readJson<{ tasks: typeof storeTasks }>(await fetch(`${getApiBaseUrl()}/api/v1/store/tasks`));
    return data.tasks;
  } catch {
    return storeTasks;
  }
}

export async function postChat(message: string, selectedStyleIds: string[]): Promise<ChatResponse> {
  const response = await readJson<ChatResponse>(
    await fetch(`${getApiBaseUrl()}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, selected_style_ids: selectedStyleIds }),
    }),
  );
  return {
    ...response,
    recommended_styles: response.recommended_styles.map(normalizeStyleAssetUrls),
  };
}

export async function postChatStream(
  message: string,
  selectedStyleIds: string[],
  onDelta: (payload: { text?: string; channel?: string; model?: string; intent?: string }) => void,
): Promise<ChatResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, selected_style_ids: selectedStyleIds }),
  });
  if (!response.ok || !response.body) {
    return postChat(message, selectedStyleIds);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: ChatResponse | null = null;
  let assembledText = "";
  let channel = "chat";
  let model: string | null | undefined = null;
  let intent = "chat-recommendation";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const lines = frame.split("\n");
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
      const dataLine = lines.find((line) => line.startsWith("data:"))?.slice(5).trim();
      if (!event || !dataLine) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataLine) as Record<string, unknown>;
      } catch {
        continue;
      }
      if (event === "meta") {
        channel = String(data.channel ?? channel);
        model = data.model as string | null | undefined;
        intent = String(data.intent ?? intent);
        onDelta({ channel, model: model ?? undefined, intent });
      } else if (event === "delta") {
        const text = String(data.text ?? "");
        assembledText += text;
        onDelta({ text });
      } else if (event === "done") {
        finalResponse = {
          reply: String(data.reply ?? assembledText),
          intent: String(data.intent ?? intent),
          recommended_styles: ((data.recommended_styles ?? []) as NailStyle[]).map(normalizeStyleAssetUrls),
          follow_up_questions: (data.follow_up_questions ?? []) as string[],
          channel: String(data.channel ?? channel),
          model: (data.model as string | null | undefined) ?? model ?? null,
        };
      }
    }
  }

  return (
    finalResponse ?? {
      reply: assembledText,
      intent,
      recommended_styles: [],
      follow_up_questions: [],
      channel,
      model,
    }
  );
}

export async function postTryOn(input: {
  image: File;
  style: NailStyle;
  styleImage?: Blob;
  generationMode?: "hd" | "regular" | "fast";
}): Promise<TryOnResponse> {
  const formData = new FormData();
  formData.append("image", input.image);
  formData.append("style_id", input.style.id);
  formData.append("style_payload", JSON.stringify(input.style));
  formData.append("generation_mode", input.generationMode ?? "hd");
  formData.append("user_id", getClientUserId());
  if (input.styleImage) formData.append("style_image", input.styleImage, `${input.style.id}.png`);

  try {
    return await readJson<TryOnResponse>(
      await fetch(`${getApiBaseUrl()}/api/v1/nail/try-on`, {
        method: "POST",
        body: formData,
      }),
    );
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("无法连接 AI 服务，请确认 FastAPI 后端正在运行并允许当前网页访问。");
    }
    throw error;
  }
}

export async function fetchTryOnAuditRuns(): Promise<TryOnAuditRun[]> {
  const data = await readJson<{ runs: TryOnAuditRun[] }>(
    await fetch(`${getApiBaseUrl()}/api/v1/test-dashboard/runs`, {
      cache: "no-store",
      headers: buildTestDashboardHeaders(),
    }),
  );
  return data.runs;
}

export async function fetchTryOnAuditRun(runId: string): Promise<TryOnAuditRun> {
  return readJson<TryOnAuditRun>(
    await fetch(`${getApiBaseUrl()}/api/v1/test-dashboard/runs/${runId}`, {
      cache: "no-store",
      headers: buildTestDashboardHeaders(),
    }),
  );
}

export async function fetchDiyAuditRuns(): Promise<DiyBountyAuditRun[]> {
  const data = await readJson<{ runs: DiyBountyAuditRun[] }>(
    await fetch(`${getApiBaseUrl()}/api/v1/test-dashboard/diy-runs`, {
      cache: "no-store",
      headers: buildTestDashboardHeaders(),
    }),
  );
  return data.runs;
}

export async function fetchDiyAuditRun(runId: string): Promise<DiyBountyAuditRun> {
  return readJson<DiyBountyAuditRun>(
    await fetch(`${getApiBaseUrl()}/api/v1/test-dashboard/diy-runs/${runId}`, {
      cache: "no-store",
      headers: buildTestDashboardHeaders(),
    }),
  );
}

export async function postDiyBountyGenerate(input: {
  referenceImage: File;
  handImage?: File | null;
  answers: DiyBountyAnswers;
  numVariants?: number;
}): Promise<DiyBountyGenerateResponse> {
  const formData = new FormData();
  formData.append("reference_image", input.referenceImage);
  if (input.handImage) {
    formData.append("hand_image", input.handImage);
  }
  formData.append("answers", JSON.stringify(input.answers));
  formData.append("num_variants", String(input.numVariants ?? 3));
  formData.append("user_id", getClientUserId());

  try {
    return await readJson<DiyBountyGenerateResponse>(
      await fetch(`${getApiBaseUrl()}/api/v1/bounty/generate`, {
        method: "POST",
        body: formData,
      }),
    );
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("无法连接 DIY 生成服务，请确认 FastAPI 后端正在运行。");
    }
    throw error;
  }
}

export async function fetchLatestDiyBountyGeneration(): Promise<DiyBountyGenerateResponse | null> {
  try {
    return await readJson<DiyBountyGenerateResponse>(await fetch(`${getApiBaseUrl()}/api/v1/bounty/latest`));
  } catch {
    return null;
  }
}

export async function postDiyBountyPublish(input: {
  title: string;
  description: string;
  budget: string;
  image: string;
  answers: DiyBountyAnswers;
  selectedVariantId: string;
}): Promise<DiyBountyPublishResponse> {
  return readJson<DiyBountyPublishResponse>(
    await fetch(`${getApiBaseUrl()}/api/v1/bounty/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: input.title,
        description: input.description,
        budget: input.budget,
        image: input.image,
        answers: input.answers,
        selected_variant_id: input.selectedVariantId,
      }),
      }),
  );
}

export async function acceptDiyBounty(bountyId: string, shopId = "library-nail-spa-futian") {
  return readJson<Record<string, unknown>>(
    await fetch(`${getApiBaseUrl()}/api/v1/store/bounties/${bountyId}/accept`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shop_id: shopId }),
    }),
  );
}

export async function previewNailStyleUpload(input: { name: string; price: string; image: File }): Promise<StyleUploadPreviewResponse> {
  const formData = new FormData();
  formData.append("name", input.name);
  formData.append("price", input.price);
  formData.append("image", input.image);

  const response = await readJson<StyleUploadPreviewResponse>(
    await fetch(`${getApiBaseUrl()}/api/v1/store/styles/preview`, {
      method: "POST",
      body: formData,
    }),
  );
  return {
    ...response,
    source_image_url: resolveApiAssetUrl(response.source_image_url),
    design_image_url: resolveApiAssetUrl(response.design_image_url),
  };
}

export async function publishNailStyle(input: {
  draftId: string;
  name: string;
  price: string;
  taxonomy: Record<string, string[]>;
  customTagsByDimension: Record<string, string[]>;
}): Promise<StyleUploadPublishResponse> {
  const response = await readJson<StyleUploadPublishResponse>(
    await fetch(`${getApiBaseUrl()}/api/v1/store/styles/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        draft_id: input.draftId,
        name: input.name,
        price: input.price,
        taxonomy: input.taxonomy,
        custom_tags_by_dimension: input.customTagsByDimension,
      }),
    }),
  );
  return {
    ...response,
    style: normalizeStyleAssetUrls(response.style),
  };
}

export async function updateShopInfo(
  name: string,
  address: string,
  activeScore: number,
  waitTime: string,
  schedule: string,
  facilities: { wifi: boolean; parking: boolean; tea: boolean; private_room: boolean },
) {
  return readJson<Record<string, unknown>>(
    await fetch(`${getApiBaseUrl()}/api/v1/store/shop-info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        address,
        active_score: activeScore,
        wait_time: waitTime,
        schedule,
        facilities,
      }),
    }),
  );
}

export async function fetchMerchantStyles(): Promise<MerchantStyleWithAnalytics[]> {
  try {
    const data = await readJson<{ styles: MerchantStyleWithAnalytics[] }>(
      await fetch(`${getApiBaseUrl()}/api/v1/store/styles`, { cache: "no-store" })
    );
    return (data.styles || []).map(normalizeStyleAssetUrls) as MerchantStyleWithAnalytics[];
  } catch (err) {
    console.error("fetchMerchantStyles failed:", err);
    return [];
  }
}

export async function toggleStyleActive(styleId: string, isActive: boolean): Promise<boolean> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/store/styles/${styleId}/toggle-active`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    const data = await response.json() as { status: string };
    return data.status === "success";
  } catch (err) {
    console.error("toggleStyleActive failed:", err);
    return false;
  }
}

export async function reportStyleTelemetry(styleId: string, eventType: "view" | "interest" | "booking"): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/api/v1/styles/${styleId}/telemetry?event_type=${eventType}`, {
      method: "POST",
    });
  } catch (err) {
    console.error("reportStyleTelemetry failed:", err);
  }
}
