"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Palette, X } from "lucide-react";
import { dismissDiyTask, useDiyTask } from "@/lib/diyTaskStore";

export function DiyTaskWindow() {
  const task = useDiyTask();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const progress = Math.min(100, Math.max(0, task.progress));
  const thumbWidth = 50;
  const thumbHalf = thumbWidth / 2;

  if (!mounted) return null;
  if (task.status === "idle") return null;

  // Hide the window if the user is already on the audit page or creation details page
  if (pathname === "/diy-audit" || pathname === "/diy-bounty/create") return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 left-1/2 z-[91] h-dvh w-full max-w-[440px] -translate-x-1/2">
      <aside className="animate-task-window-pop pointer-events-auto absolute bottom-[86px] left-4 right-4 overflow-hidden rounded-[18px] border border-[#ffd4df] bg-white/96 px-3 py-2 shadow-[0_12px_30px_rgba(85,35,53,0.18)] backdrop-blur">
        <div className="flex items-start gap-2">
          <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#fff0f4] text-[#ff5c74]">
            {task.status === "running" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : task.status === "succeeded" ? (
              <CheckCircle2 size={15} />
            ) : (
              <AlertTriangle size={15} />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-black text-[#4b2532]">
                {task.status === "running"
                  ? "DIY 方案后台生成中"
                  : task.status === "succeeded"
                    ? "DIY 方案已生成"
                    : "本次 DIY 生成失败"}
              </p>
              {task.status !== "running" ? (
                <button
                  type="button"
                  onClick={dismissDiyTask}
                  className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[#a88a93] hover:bg-[#fff0f4]"
                  aria-label="关闭提示"
                >
                  <X size={14} />
                </button>
              ) : null}
            </div>

            {task.status === "running" ? (
              <>
                <div className="mt-1 flex items-center justify-between gap-2 text-[10px] font-bold text-[#9b7580]">
                  <span className="truncate">{task.stage}</span>
                  <span className="shrink-0 text-[#ff5c74]">{progress}%</span>
                </div>
                <div className="relative mt-4 mb-2">
                  <div className="h-[10px] rounded-full bg-[#f6d8e0] p-[2px] shadow-inner">
                    <div
                      className="h-full rounded-full bg-[linear-gradient(90deg,#ff5c74,#ff9a73,#ffd66d)] shadow-[0_0_8px_rgba(255,92,116,0.45)] transition-[width] duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div
                    className="pointer-events-none absolute top-[-2px] transition-[left] duration-500"
                    style={{
                      left: `clamp(${thumbHalf}px, ${progress}%, calc(100% - ${thumbHalf}px))`,
                      transform: "translateX(-50%)",
                    }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/progress/anime-manicure-hand.png"
                      alt=""
                      aria-hidden="true"
                      className="h-[42px] w-[50px] max-w-none select-none object-contain drop-shadow-[0_6px_8px_rgba(139,64,84,0.2)]"
                    />
                  </div>
                </div>
                <div className="mt-2 flex gap-2">
                  <Link
                    href="/"
                    className="flex h-8 flex-1 items-center justify-center rounded-full bg-[#ff5c74] text-[11px] font-black text-white"
                  >
                    回首页继续浏览
                  </Link>
                  <Link
                    href="/diy-audit"
                    className="flex h-8 flex-1 items-center justify-center rounded-full border border-[#f5dce3] text-[11px] font-black text-[#5d404a]"
                  >
                    看过程
                  </Link>
                </div>
              </>
            ) : task.status === "succeeded" ? (
              <div className="mt-2 grid grid-cols-2 gap-2">
                <Link
                  href="/diy-bounty/create#result-hero"
                  className="flex h-8 items-center justify-center gap-1.5 rounded-full bg-[#ff5c74] text-[11px] font-black text-white"
                >
                  <Palette size={14} />
                  查看大图
                </Link>
                <Link
                  href="/diy-audit"
                  className="flex h-8 items-center justify-center rounded-full border border-[#f5dce3] text-[11px] font-black text-[#5d404a]"
                >
                  看过程
                </Link>
              </div>
            ) : (
              <p className="mt-1.5 text-[10px] font-bold leading-4 text-red-600">{task.error}</p>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
