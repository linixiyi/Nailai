"use client";

import { useSyncExternalStore } from "react";
import { previewNailStyleUpload, publishNailStyle } from "./api";
import type {
  MerchantStyleUploadTask,
  NailTaxonomy,
  StyleUploadPublishResponse,
} from "./types";

type EnqueueMerchantStyleTaskInput = {
  image: File;
  imagePreviewUrl: string;
  styleName: string;
  stylePrice: string;
  taxonomy: NailTaxonomy;
  customTagsByDimension: NailTaxonomy;
};

type PendingMerchantStyleTaskInput = EnqueueMerchantStyleTaskInput & {
  taskId: string;
};

type MerchantStyleTaskSnapshot = {
  tasks: MerchantStyleUploadTask[];
  activeTaskId: string | null;
};

const STORAGE_KEY = "nailai:merchant-style-task-snapshot";

const loadingStages = [
  { at: 0, progress: 8, label: "已加入生成队列" },
  { at: 1200, progress: 18, label: "正在上传款式原图" },
  { at: 5000, progress: 34, label: "正在分析款式标签语义" },
  { at: 12000, progress: 56, label: "GPT Image 2 正在生成款式预览" },
  { at: 30000, progress: 76, label: "正在提取可上架设计图" },
  { at: 52000, progress: 90, label: "即将完成，请稍候" },
] as const;

function createTaskId() {
  const webCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (webCrypto && typeof webCrypto.randomUUID === "function") {
    return `merchant-style-${webCrypto.randomUUID()}`;
  }
  return `merchant-style-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function cloneTaxonomy(taxonomy: NailTaxonomy): NailTaxonomy {
  return {
    colors: [...taxonomy.colors],
    techniques: [...taxonomy.techniques],
    shapes: [...taxonomy.shapes],
    styles: [...taxonomy.styles],
    occasions: [...taxonomy.occasions],
    lengths: [...taxonomy.lengths],
  };
}

function saveSnapshot(next: MerchantStyleTaskSnapshot) {
  if (typeof window === "undefined") return;
  try {
    const serializable = {
      ...next,
      tasks: next.tasks.map((task) => ({
        ...task,
        source_image_preview_url:
          task.status === "running" || task.status === "queued" ? "" : task.source_image_preview_url,
      })),
    };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
  } catch (error) {
    console.error("Failed to save merchant style task snapshot", error);
  }
}

function loadSnapshot(): MerchantStyleTaskSnapshot {
  const fallback: MerchantStyleTaskSnapshot = { tasks: [], activeTaskId: null };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as MerchantStyleTaskSnapshot;
    return {
      tasks: Array.isArray(parsed.tasks)
        ? parsed.tasks.filter((task) => task.status === "succeeded" || task.status === "failed")
        : [],
      activeTaskId: parsed.activeTaskId ?? null,
    };
  } catch {
    return fallback;
  }
}

let snapshot: MerchantStyleTaskSnapshot = loadSnapshot();
let queue: PendingMerchantStyleTaskInput[] = [];
let runningTaskId: string | null = null;
let progressTimer: number | null = null;
let progressStartedAt = 0;
const listeners = new Set<() => void>();

function emit(next: Partial<MerchantStyleTaskSnapshot>) {
  snapshot = { ...snapshot, ...next };
  saveSnapshot(snapshot);
  listeners.forEach((listener) => listener());
}

function updateTask(taskId: string, updater: (task: MerchantStyleUploadTask) => MerchantStyleUploadTask) {
  emit({
    tasks: snapshot.tasks.map((task) => (task.id === taskId ? updater(task) : task)),
  });
}

function stopProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function startProgressTimer(taskId: string) {
  stopProgressTimer();
  progressStartedAt = Date.now();
  updateTask(taskId, (task) => ({
    ...task,
    progress: loadingStages[0].progress,
    stage: loadingStages[0].label,
  }));
  progressTimer = window.setInterval(() => {
    const elapsed = Date.now() - progressStartedAt;
    const currentStage = [...loadingStages].reverse().find((stage) => elapsed >= stage.at) ?? loadingStages[0];
    updateTask(taskId, (task) => ({
      ...task,
      progress: Math.max(task.progress, Math.min(currentStage.progress, 94)),
      stage: currentStage.label,
    }));
  }, 400);
}

function nextQueuedTask() {
  return snapshot.tasks.find((task) => task.status === "queued");
}

async function pumpQueue() {
  if (runningTaskId || typeof window === "undefined") return;
  const nextTask = nextQueuedTask();
  if (!nextTask) return;

  const pendingInput = queue.find((item) => item.taskId === nextTask.id);
  if (!pendingInput) {
    updateTask(nextTask.id, (task) => ({
      ...task,
      status: "failed",
      progress: 0,
      stage: "任务数据已失效",
      error: "页面刷新后，未开始的上传任务文件引用丢失，请重新提交。",
    }));
    return pumpQueue();
  }

  runningTaskId = nextTask.id;
  updateTask(nextTask.id, (task) => ({
    ...task,
    status: "running",
    progress: 0,
    stage: "准备生成款式图预览",
    error: null,
  }));
  startProgressTimer(nextTask.id);

  try {
    const response = await previewNailStyleUpload({
      name: pendingInput.styleName,
      price: pendingInput.stylePrice,
      image: pendingInput.image,
    });

    updateTask(nextTask.id, (task) => ({
      ...task,
      status: "succeeded",
      progress: 100,
      stage: "款式图预览已生成",
      error: null,
      preview_result: response,
    }));
    emit({ activeTaskId: nextTask.id });
  } catch (error) {
    updateTask(nextTask.id, (task) => ({
      ...task,
      status: "failed",
      progress: 0,
      stage: "款式图预览生成失败",
      error: error instanceof Error ? error.message : "款式图预览生成失败，请稍后重试。",
    }));
  } finally {
    queue = queue.filter((item) => item.taskId !== pendingInput.taskId);
    runningTaskId = null;
    stopProgressTimer();
    void pumpQueue();
  }
}

export function subscribeMerchantStyleTask(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getMerchantStyleTaskSnapshot() {
  return snapshot;
}

export function useMerchantStyleTasks() {
  return useSyncExternalStore(subscribeMerchantStyleTask, getMerchantStyleTaskSnapshot, getMerchantStyleTaskSnapshot);
}

export function dismissMerchantStyleTask(taskId: string) {
  if (runningTaskId === taskId) return;
  const nextTasks = snapshot.tasks.filter((task) => task.id !== taskId);
  const nextActive = snapshot.activeTaskId === taskId ? nextTasks.find((task) => task.status === "succeeded")?.id ?? null : snapshot.activeTaskId;
  emit({ tasks: nextTasks, activeTaskId: nextActive });
}

export function setActiveMerchantStyleTask(taskId: string) {
  emit({ activeTaskId: taskId });
}

export async function enqueueMerchantStyleTask(input: EnqueueMerchantStyleTaskInput) {
  const taskId = createTaskId();
  const task: MerchantStyleUploadTask = {
    id: taskId,
    status: "queued",
    progress: 0,
    stage: "等待进入生成队列",
    error: null,
    created_at: new Date().toISOString(),
    style_name: input.styleName,
    style_price: input.stylePrice,
    source_image_name: input.image.name,
    source_image_preview_url: input.imagePreviewUrl,
    taxonomy: cloneTaxonomy(input.taxonomy),
    custom_tags_by_dimension: cloneTaxonomy(input.customTagsByDimension),
    preview_result: null,
    published_style: null,
  };

  queue.push({ ...input, taskId });
  emit({
    tasks: [task, ...snapshot.tasks],
    activeTaskId: snapshot.activeTaskId ?? taskId,
  });
  void pumpQueue();
  return taskId;
}

export async function publishMerchantStyleTask(taskId: string): Promise<StyleUploadPublishResponse> {
  const task = snapshot.tasks.find((item) => item.id === taskId);
  if (!task?.preview_result?.draft_id) {
    throw new Error("请先等待款式图预览生成完成。");
  }

  updateTask(taskId, (current) => ({
    ...current,
    stage: "正在确认上架到首页",
    error: null,
  }));

  try {
    const response = await publishNailStyle({
      draftId: task.preview_result.draft_id,
      name: task.style_name,
      price: task.style_price,
      taxonomy: task.taxonomy,
      customTagsByDimension: task.custom_tags_by_dimension,
    });

    updateTask(taskId, (current) => ({
      ...current,
      published_style: response.style,
      stage: "已上架到首页",
    }));
    return response;
  } catch (error) {
    updateTask(taskId, (current) => ({
      ...current,
      error: error instanceof Error ? error.message : "上架失败，请稍后重试。",
      stage: "上架失败",
    }));
    throw error;
  }
}

export function retryMerchantStyleTask(taskId: string) {
  const task = snapshot.tasks.find((item) => item.id === taskId);
  if (!task || task.status === "running") return;
  updateTask(taskId, (current) => ({
    ...current,
    status: "failed",
    stage: "刷新页面后请重新提交该任务",
    error: current.error || "原始图片文件已释放，无法直接重试，请重新选择图片。",
  }));
}
