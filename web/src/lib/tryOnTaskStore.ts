"use client";

import { useSyncExternalStore } from "react";
import { postTryOn } from "./api";
import { clearLatestTryOnResult, saveTryOnResult } from "./tryOnStore";
import type { NailStyle, TryOnResponse } from "./types";

type TryOnTaskStatus = "idle" | "running" | "succeeded" | "failed";

export type TryOnTaskSnapshot = {
  status: TryOnTaskStatus;
  progress: number;
  stage: string;
  error: string | null;
  result: TryOnResponse | null;
};

type StartTryOnTaskInput = {
  image: File;
  style: NailStyle;
  styleImage?: Blob;
  generationMode: "hd" | "regular" | "fast";
};

const loadingStages = [
  { at: 0, progress: 12, label: "正在检查手图和款式图" },
  { at: 1800, progress: 28, label: "正在上传图片到生图模型" },
  { at: 8000, progress: 46, label: "模型正在生成试戴效果" },
  { at: 22000, progress: 68, label: "正在校正美甲边缘与长度" },
  { at: 45000, progress: 84, label: "正在整理最终结果" },
  { at: 70000, progress: 92, label: "快完成了，请再等一下" },
] as const;

const STORAGE_KEY = "nailai:tryon-task-snapshot";

function saveTaskSnapshot(snap: TryOnTaskSnapshot) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snap));
  } catch (e) {
    console.error("Failed to save tryon task snapshot", e);
  }
}

function loadTaskSnapshot(): TryOnTaskSnapshot {
  const fallback: TryOnTaskSnapshot = {
    status: "idle",
    progress: 0,
    stage: "等待开始",
    error: null,
    result: null,
  };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as TryOnTaskSnapshot;
      if (parsed.status === "running") {
        return fallback;
      }
      return parsed;
    }
  } catch {
    // ignore
  }
  return fallback;
}

let snapshot: TryOnTaskSnapshot = loadTaskSnapshot();
let progressTimer: number | null = null;
const listeners = new Set<() => void>();

function emit(next: Partial<TryOnTaskSnapshot>) {
  snapshot = { ...snapshot, ...next };
  saveTaskSnapshot(snapshot);
  listeners.forEach((listener) => listener());
}

function stopProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function startProgressTimer() {
  stopProgressTimer();
  const startedAt = Date.now();
  emit({ progress: loadingStages[0].progress, stage: loadingStages[0].label });
  progressTimer = window.setInterval(() => {
    const elapsed = Date.now() - startedAt;
    const currentStage =
      [...loadingStages].reverse().find((stage) => elapsed >= stage.at) ?? loadingStages[0];
    emit({
      progress: Math.max(snapshot.progress, Math.min(currentStage.progress, 94)),
      stage: currentStage.label,
    });
  }, 400);
}

export function subscribeTryOnTask(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getTryOnTaskSnapshot() {
  return snapshot;
}

export function useTryOnTask() {
  return useSyncExternalStore(subscribeTryOnTask, getTryOnTaskSnapshot, getTryOnTaskSnapshot);
}

export function dismissTryOnTask() {
  if (snapshot.status === "running") return;
  emit({
    status: "idle",
    progress: 0,
    stage: "等待开始",
    error: null,
    result: null,
  });
}

export async function startTryOnTask(input: StartTryOnTaskInput) {
  if (snapshot.status === "running") return;

  clearLatestTryOnResult();
  emit({ status: "running", error: null, result: null });
  startProgressTimer();

  try {
    const result = await postTryOn(input);
    saveTryOnResult(result);
    stopProgressTimer();
    emit({
      status: "succeeded",
      progress: 100,
      stage: "试戴生成完成，可以查看效果",
      result,
    });
  } catch (error) {
    stopProgressTimer();
    emit({
      status: "failed",
      progress: 0,
      stage: "生成失败",
      error: error instanceof Error ? error.message : "生成失败，请稍后重试。",
    });
  }
}
