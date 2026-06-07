import type { DiyBountyAnswers, DiyBountyGenerateResponse, TryOnResponse } from "./types";

const USER_ID_KEY = "nailai:user-id";
const TRY_ON_HISTORY_KEY = "nailai:history:try-on";
const DIY_HISTORY_KEY = "nailai:history:diy-bounty";
const MAX_HISTORY_ITEMS = 60;

export type TryOnHistoryItem = {
  id: string;
  created_at: string;
  result: TryOnResponse;
  hand_image?: string;
};

export type DiyBountyHistoryItem = {
  id: string;
  created_at: string;
  answers: DiyBountyAnswers;
  result: DiyBountyGenerateResponse;
};

function canUseStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function readList<T>(key: string): T[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    return [];
  }
}

function safeSetItem(key: string, value: string): boolean {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function writeList<T extends { id: string }>(key: string, item: T) {
  if (!canUseStorage()) return;
  let list = [item, ...readList<T>(key).filter((current) => current.id !== item.id)].slice(0, MAX_HISTORY_ITEMS);

  // Try to write with progressively fewer items if quota is exceeded
  while (list.length > 0) {
    // Strip large base64 blobs from hand_image to save space before writing
    const trimmed = list.map((entry) => {
      if ("hand_image" in entry && typeof (entry as Record<string, unknown>).hand_image === "string") {
        const img = (entry as Record<string, unknown>).hand_image as string;
        // Keep only small thumbnails (< 50 KB of base64), drop the rest
        return img.length > 65536 ? { ...entry, hand_image: undefined } : entry;
      }
      return entry;
    });
    if (safeSetItem(key, JSON.stringify(trimmed))) return;
    // Still failing — drop the oldest item and retry
    list = list.slice(0, list.length - 1);
  }

  // Last resort: clear this key entirely so the app doesn't break
  try {
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function createLocalId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function getClientUserId() {
  if (!canUseStorage()) return "anonymous";
  const existing = window.localStorage.getItem(USER_ID_KEY);
  if (existing) return existing;
  const next = `local-${createLocalId()}`;
  window.localStorage.setItem(USER_ID_KEY, next);
  return next;
}

export function saveTryOnHistory(result: TryOnResponse) {
  let handImage: string | undefined = undefined;
  if (canUseStorage()) {
    const stored = window.localStorage.getItem("nailai.originalImage");
    if (stored) {
      handImage = stored;
    }
  }
  writeList<TryOnHistoryItem>(TRY_ON_HISTORY_KEY, {
    id: result.job_id,
    created_at: new Date().toISOString(),
    result,
    hand_image: handImage,
  });
}

export function loadTryOnHistory() {
  return readList<TryOnHistoryItem>(TRY_ON_HISTORY_KEY);
}

export function saveDiyBountyHistory(result: DiyBountyGenerateResponse, answers: DiyBountyAnswers) {
  writeList<DiyBountyHistoryItem>(DIY_HISTORY_KEY, {
    id: result.job_id,
    created_at: new Date().toISOString(),
    answers,
    result,
  });
}

export function loadDiyBountyHistory() {
  return readList<DiyBountyHistoryItem>(DIY_HISTORY_KEY);
}
