"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  GripVertical,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { dismissTryOnTask, useTryOnTask } from "@/lib/tryOnTaskStore";

// Panel dimensions (px) — must match the rendered size so clamp is accurate
const PANEL_W = 236;
const PANEL_H_EXPANDED = 102;
const PANEL_H_COLLAPSED = 40;
// Gap from bottom nav bar
const BOTTOM_OFFSET = 94;
const PHONE_CANVAS_MAX_W = 440;
const PHONE_OUTER_GAP = 12;
const THUMB_W = 42;
const THUMB_HALF = THUMB_W / 2;

export function TryOnTaskWindow() {
  const task = useTryOnTask();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Position: x = distance from left edge of viewport, y = distance from top
  // We'll compute relative to the phone-shell container if possible.
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{
    active: boolean;
    startPx: number;
    startPy: number;
    startX: number;
    startY: number;
  }>({ active: false, startPx: 0, startPy: 0, startX: 0, startY: 0 });

  useEffect(() => {
    setMounted(true);
  }, []);

  // Reset collapse when a new task starts
  useEffect(() => {
    if (task.status === "running") setCollapsed(false);
  }, [task.status]);

  // Compute initial default position once we're mounted
  useEffect(() => {
    if (!mounted || pos !== null) return;
    // Place the panel in the bottom-right, above the bottom nav
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const shellWidth = Math.min(PHONE_CANVAS_MAX_W, Math.max(0, vw - PHONE_OUTER_GAP * 2));
    const shellLeft = shellWidth >= PHONE_CANVAS_MAX_W ? (vw - PHONE_CANVAS_MAX_W) / 2 : PHONE_OUTER_GAP;
    const shellRight = shellLeft + shellWidth;
    const panelH = collapsed ? PANEL_H_COLLAPSED : PANEL_H_EXPANDED;
    const minX = shellLeft + 8;
    const maxX = Math.max(minX, shellRight - PANEL_W - 8);
    setPos({
      x: Math.max(minX, Math.min(maxX, vw - PANEL_W - 12)),
      y: Math.max(8, vh - panelH - BOTTOM_OFFSET),
    });
  }, [mounted, pos, collapsed]);

  function getClampedPos(x: number, y: number): { x: number; y: number } {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const shellWidth = Math.min(PHONE_CANVAS_MAX_W, Math.max(0, vw - PHONE_OUTER_GAP * 2));
    const shellLeft = shellWidth >= PHONE_CANVAS_MAX_W ? (vw - PHONE_CANVAS_MAX_W) / 2 : PHONE_OUTER_GAP;
    const shellRight = shellLeft + shellWidth;
    const panelH = collapsed ? PANEL_H_COLLAPSED : PANEL_H_EXPANDED;
    const minX = shellLeft + 8;
    const maxX = Math.max(minX, shellRight - PANEL_W - 8);
    return {
      x: Math.max(minX, Math.min(maxX, x)),
      y: Math.max(8, Math.min(vh - panelH - 8, y)),
    };
  }

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (!pos) return;
    dragState.current = {
      active: true,
      startPx: e.clientX,
      startPy: e.clientY,
      startX: pos.x,
      startY: pos.y,
    };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    e.preventDefault();
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragState.current.active) return;
    const dx = e.clientX - dragState.current.startPx;
    const dy = e.clientY - dragState.current.startPy;
    setPos(getClampedPos(dragState.current.startX + dx, dragState.current.startY + dy));
    e.preventDefault();
  }

  function onPointerUp() {
    dragState.current.active = false;
  }

  if (!mounted) return null;
  if (task.status === "idle") return null;
  if (pathname === "/tryon-result") return null;
  if (pos === null) return null;

  const isRunning = task.status === "running";
  const isSuccess = task.status === "succeeded";

  return (
    <div
      ref={panelRef}
      style={{
        position: "fixed",
        left: pos.x,
        top: pos.y,
        width: PANEL_W,
        zIndex: 95,
        touchAction: "none",
        userSelect: "none",
      }}
      className="animate-task-window-pop"
    >
      {/* ── Header / drag handle ── */}
      <div
        className="flex cursor-grab items-center gap-1.5 rounded-t-[16px] border border-[#ffd4df] bg-white px-2 py-1.5 shadow-lg active:cursor-grabbing"
        style={{ borderBottomWidth: collapsed ? 1 : 0, borderBottomColor: collapsed ? "#ffd4df" : undefined, borderBottomLeftRadius: collapsed ? 16 : 0, borderBottomRightRadius: collapsed ? 16 : 0 }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <GripVertical size={13} className="shrink-0 select-none text-[#c9a0b0]" />

        {/* Status icon */}
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#fff0f4] text-[#ff5c74]">
          {isRunning ? (
            <Loader2 size={12} className="animate-spin" />
          ) : isSuccess ? (
            <CheckCircle2 size={12} />
          ) : (
            <AlertTriangle size={12} />
          )}
        </span>

        {/* Label */}
        <p className="min-w-0 flex-1 truncate text-[11px] font-black text-[#4b2532]">
          {isRunning
            ? `AI 生成中 ${task.progress}%`
            : isSuccess
              ? "试戴完成 ✨"
              : "生成失败"}
        </p>

        {/* Collapse toggle — not draggable */}
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => setCollapsed((c) => !c)}
          className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[#a88a93] hover:bg-[#fff0f4]"
          aria-label={collapsed ? "展开" : "折叠"}
        >
          {collapsed ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {/* Close (only when not running) */}
        {!isRunning && (
          <button
            type="button"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={dismissTryOnTask}
            className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[#a88a93] hover:bg-[#fff0f4]"
            aria-label="关闭"
          >
            <X size={12} />
          </button>
        )}
      </div>

      {/* ── Expanded body ── */}
      {!collapsed && (
        <div className="rounded-b-[16px] border border-t-0 border-[#ffd4df] bg-white/96 px-3 py-2 shadow-lg backdrop-blur">
          {isRunning ? (
            <>
              <p className="truncate text-[10px] font-bold text-[#9b7580]">{task.stage}</p>

              {/* Progress bar */}
              <div className="relative mt-2 mb-1 select-none">
                <div className="h-[8px] rounded-full bg-[#f6d8e0] p-[1.5px] shadow-inner">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,#ff5c74,#ff9a73,#ffd66d)] shadow-[0_0_6px_rgba(255,92,116,0.4)] transition-[width] duration-500"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                {/* Emoji thumb */}
                <div
                  className="pointer-events-none absolute top-[-12px] transition-[left] duration-500"
                  style={{
                    left: `clamp(${THUMB_HALF}px, ${task.progress}%, calc(100% - ${THUMB_HALF}px))`,
                    transform: "translateX(-50%)",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/progress/anime-manicure-hand.png"
                    alt=""
                    aria-hidden="true"
                    className="h-[34px] w-[42px] max-w-none select-none object-contain drop-shadow-[0_4px_6px_rgba(139,64,84,0.2)]"
                  />
                </div>
              </div>

              <div className="flex justify-between text-[9px] font-bold text-[#c9a0b0]">
                <span>0%</span>
                <span className="text-[#ff5c74]">{task.progress}%</span>
                <span>100%</span>
              </div>
            </>
          ) : isSuccess ? (
            <Link
              href="/tryon-result"
              className="mt-1.5 flex h-8 items-center justify-center gap-1.5 rounded-full bg-[#ff5c74] text-[11px] font-black text-white shadow-sm"
            >
              <Sparkles size={13} />
              查看试戴效果
            </Link>
          ) : (
            <p className="mt-1 text-[10px] font-bold leading-4 text-red-600 line-clamp-3">
              {task.error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
