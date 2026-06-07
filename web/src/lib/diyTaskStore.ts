"use client";

import { useSyncExternalStore } from "react";
import { postDiyBountyGenerate } from "./api";
import { saveDiyBountyHistory } from "./historyStore";
import type { DiyBountyAnswers, DiyBountyGenerateResponse } from "./types";

type DiyTaskStatus = "idle" | "running" | "succeeded" | "failed";

export type DiyTaskSnapshot = {
  status: DiyTaskStatus;
  progress: number;
  stage: string;
  error: string | null;
  result: DiyBountyGenerateResponse | null;
};

type StartDiyTaskInput = {
  referenceImage: File;
  handImage?: File | null;
  answers: DiyBountyAnswers;
};

const LAST_DIY_RESULT_KEY = "nailai:last-diy-bounty-result";
const LAST_DIY_ANSWERS_KEY = "nailai:last-diy-bounty-answers";

const loadingStages = [
  { at: 0, progress: 10, label: "正在整理选择题答案" },
  { at: 1500, progress: 24, label: "正在分析参考图风格" },
  { at: 5000, progress: 42, label: "wan2.7-image-pro 正在生成美甲方案" },
  { at: 18000, progress: 66, label: "正在生成可报价方案" },
  { at: 36000, progress: 82, label: "正在写入生成历史" },
  { at: 60000, progress: 92, label: "快完成了，请再等一下" },
] as const;

const STORAGE_KEY = "nailai:diy-task-snapshot";

function saveTaskSnapshot(snap: DiyTaskSnapshot) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snap));
  } catch (e) {
    console.error("Failed to save diy task snapshot", e);
  }
}

function loadTaskSnapshot(): DiyTaskSnapshot {
  const fallback: DiyTaskSnapshot = {
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
      const parsed = JSON.parse(raw) as DiyTaskSnapshot;
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

let snapshot: DiyTaskSnapshot = loadTaskSnapshot();
let progressTimer: number | null = null;
const listeners = new Set<() => void>();

function emit(next: Partial<DiyTaskSnapshot>) {
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
    const currentStage = [...loadingStages].reverse().find((stage) => elapsed >= stage.at) ?? loadingStages[0];
    emit({
      progress: Math.max(snapshot.progress, Math.min(currentStage.progress, 94)),
      stage: currentStage.label,
    });
  }, 400);
}

function saveLatestDiyResult(result: DiyBountyGenerateResponse, answers: DiyBountyAnswers) {
  window.localStorage.setItem(LAST_DIY_RESULT_KEY, JSON.stringify(result));
  window.localStorage.setItem(LAST_DIY_ANSWERS_KEY, JSON.stringify(answers));
  saveDiyBountyHistory(result, answers);
}

export function subscribeDiyTask(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getDiyTaskSnapshot() {
  return snapshot;
}

export function useDiyTask() {
  return useSyncExternalStore(subscribeDiyTask, getDiyTaskSnapshot, getDiyTaskSnapshot);
}

export function dismissDiyTask() {
  if (snapshot.status === "running") return;
  emit({
    status: "idle",
    progress: 0,
    stage: "等待开始",
    error: null,
    result: null,
  });
}

export async function startDiyTask(input: StartDiyTaskInput) {
  if (snapshot.status === "running") return;

  emit({ status: "running", error: null, result: null });
  startProgressTimer();

  try {
    const result = await postDiyBountyGenerate({
      referenceImage: input.referenceImage,
      handImage: input.handImage,
      answers: input.answers,
      numVariants: 1,
    });
    saveLatestDiyResult(result, input.answers);
    stopProgressTimer();
    emit({
      status: "succeeded",
      progress: 100,
      stage: "WAN DIY 方案已生成，可去悬赏页查看",
      result,
    });
  } catch (error) {
    stopProgressTimer();
    emit({
      status: "failed",
      progress: 0,
      stage: "生成失败",
      error: error instanceof Error ? error.message : "DIY 方案生成失败，请稍后重试。",
    });
  }
}
