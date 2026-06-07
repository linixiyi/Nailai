import type { TryOnResponse } from "./types";
import { saveTryOnHistory } from "./historyStore";

const STORAGE_KEY = "nailai.latestTryOn";
const ORIGINAL_IMAGE_KEY = "nailai.originalImage";

function safeSet(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // quota exceeded — silently ignore, sessionStorage fallback below
  }
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

export function saveTryOnResult(result: TryOnResponse) {
  if (typeof window === "undefined") return;
  safeSet(STORAGE_KEY, JSON.stringify(result));
  saveTryOnHistory(result);
}

export function clearLatestTryOnResult() {
  if (typeof window === "undefined") return;
  try { window.localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  try { window.sessionStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
}

export function loadTryOnResult(): TryOnResponse | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY) ?? window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TryOnResponse;
  } catch {
    return null;
  }
}

export function saveTryOnOriginalImage(dataUrl: string) {
  if (typeof window === "undefined") return;
  safeSet(ORIGINAL_IMAGE_KEY, dataUrl);
}

export function loadTryOnOriginalImage(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ORIGINAL_IMAGE_KEY) ?? window.sessionStorage.getItem(ORIGINAL_IMAGE_KEY);
}

