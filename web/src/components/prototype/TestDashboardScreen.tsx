"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, RefreshCw } from "lucide-react";
import { fetchTryOnAuditRun, fetchTryOnAuditRuns, resolveApiAssetUrl } from "@/lib/api";
import { appendTestDashboardPassword } from "@/lib/testDashboardAuth";
import type { TryOnAuditRun } from "@/lib/types";
import { TestDashboardPasswordGate } from "./TestDashboardPasswordGate";

function EvidenceImage({ title, src, empty }: { title: string; src?: string | null; empty?: string }) {
  return (
    <section className="overflow-hidden rounded-lg border border-black/10 bg-white">
      <div className="border-b border-black/10 px-3 py-2 text-xs font-bold text-[#5a3a43]">{title}</div>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={appendTestDashboardPassword(resolveApiAssetUrl(src))} alt={title} className="aspect-square w-full bg-[#f7f4f2] object-contain" />
      ) : (
        <div className="grid aspect-square place-items-center bg-[#f7f4f2] px-5 text-center text-xs text-[#9b7580]">{empty ?? "暂无图片"}</div>
      )}
    </section>
  );
}

function StatusBadge({ status }: { status: TryOnAuditRun["status"] }) {
  const styles = status === "succeeded" ? "bg-emerald-50 text-emerald-700" : status === "failed" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700";
  return <span className={`rounded-full px-2 py-1 text-[11px] font-bold ${styles}`}>{status}</span>;
}

function formatDuration(value?: number) {
  if (typeof value !== "number") return "待采集";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value.toFixed(1)} ms`;
}

export function TestDashboardScreen() {
  const [runs, setRuns] = useState<TryOnAuditRun[]>([]);
  const [selected, setSelected] = useState<TryOnAuditRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);

  const selectedIdRef = useRef<string | null>(null);
  selectedIdRef.current = selected?.id ?? null;

  async function reload(preferredId?: string, isSilent = false) {
    if (!isSilent) {
      setLoading(true);
      setError(null);
    }
    try {
      const nextRuns = await fetchTryOnAuditRuns();
      setRuns(nextRuns);
      const nextId = preferredId ?? selectedIdRef.current ?? nextRuns[0]?.id;
      if (nextId) {
        setSelected(await fetchTryOnAuditRun(nextId));
      } else {
        setSelected(null);
      }
      setAuthorized(true);
    } catch (err) {
      if (err instanceof Error && /401|密码|unauthorized/i.test(err.message)) {
        setAuthorized(false);
        setError("测试面板密码错误");
        return;
      }
      if (!isSilent) {
        setError(err instanceof Error ? err.message : "加载测试记录失败");
      }
    } finally {
      if (!isSilent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void reload(undefined, false);

    const interval = setInterval(() => {
      void reload(undefined, true);
    }, 3000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const coverage = useMemo(() => {
    if (!selected) return [];
    return [
      ["手图", selected.sent_to_model.hand_image],
      ["款式图", selected.sent_to_model.style_image],
      ["无 Mask 模式", !selected.sent_to_model.mask_image],
      ["像素提示词", selected.sent_to_model.pixel_prompt],
    ] as const;
  }, [selected]);

  const pipeline = useMemo(() => {
    const timings = selected?.timings_ms ?? {};
    const grounding = selected?.hand_analysis;
    return [
      { title: "输入校验", detail: "手图 + 款式图", time: undefined },
      { title: "手图指甲定位", detail: "YOLO / Qwen-VL bbox", time: timings.hand_nail_detection },
      {
        title: "视觉理解",
        detail: grounding?.vision_error
          ? `Qwen2.5-VL 失败：${grounding.vision_error.split(":")[0]}`
          : `${grounding?.analysis_source ?? "等待分析"} · ${grounding?.nail_count ?? 0} 个指甲`,
        time: timings.qwen_vl_grounding,
      },
      {
        title: "款式预处理",
        detail: `方向标准化 ${formatDuration(timings.style_orientation_normalize)} · 款式归一化 ${formatDuration(timings.style_image_normalize)}`,
        time: timings.style_reference_preprocess,
      },
      { title: "AI 换甲生成", detail: selected?.model ?? "图像编辑模型", time: timings.image_generation_api },
      { title: "结果返回", detail: selected?.status ?? "等待中", time: timings.provider_total },
    ];
  }, [selected]);

  if (!authorized) {
    return (
      <TestDashboardPasswordGate
        title="AI 换甲测试看板"
        description="输入测试面板密码后，才能查看试戴调试记录、提示词和测试图片。"
        error={error}
        onUnlock={async () => {
          setError(null);
          await reload(undefined, false);
        }}
      />
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f4f2] p-4 text-[#2b1820] md:p-6">
      <header className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-[#ff5c74]">NailAI QA</p>
          <h1 className="mt-1 text-2xl font-black">AI 换甲测试看板</h1>
          <p className="mt-1 text-sm text-[#7f6870]">查看每轮试戴的输入、视觉定位、提示词、模型、耗时与生成结果。</p>
        </div>
        <div className="flex gap-2">
          <Link href="/ai-tryon" className="rounded-lg border border-black/10 bg-white px-4 py-2 text-sm font-bold">返回试戴</Link>
          <button type="button" onClick={() => void reload()} className="flex items-center gap-2 rounded-lg bg-[#2b1820] px-4 py-2 text-sm font-bold text-white">
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />刷新
          </button>
        </div>
      </header>

      <div className="mx-auto mt-5 grid max-w-7xl gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="max-h-[calc(100vh-140px)] overflow-y-auto rounded-lg border border-black/10 bg-white">
          <div className="sticky top-0 border-b border-black/10 bg-white px-4 py-3 text-sm font-black">历史批次 ({runs.length})</div>
          {runs.length ? runs.map((run) => (
            <button key={run.id} type="button" onClick={() => void reload(run.id)} className={`block w-full border-b border-black/5 px-4 py-3 text-left ${selected?.id === run.id ? "bg-[#fff0f4]" : "hover:bg-[#faf7f6]"}`}>
              <div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-black">{run.channel}</span><StatusBadge status={run.status} /></div>
              <p className="mt-2 text-[11px] text-[#9b7580]">{new Date(run.created_at).toLocaleString()}</p>
              <p className="mt-1 truncate text-[11px] text-[#7f6870]">{run.model ?? "-"}</p>
            </button>
          )) : <p className="p-4 text-xs text-[#9b7580]">还没有测试记录。先在试戴页跑一轮。</p>}
        </aside>

        <section className="space-y-4">
          {error ? <p className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm font-bold text-red-700"><AlertTriangle size={16} />{error}</p> : null}
          {selected ? (
            <>
              <div className="rounded-lg border border-black/10 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div><p className="text-xs text-[#9b7580]">批次 {selected.id}</p><h2 className="mt-1 text-lg font-black">{selected.channel}</h2></div>
                  <StatusBadge status={selected.status} />
                </div>
                <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2 xl:grid-cols-4">
                  <p><b>模型：</b>{selected.model ?? "-"}</p><p><b>接口：</b><span className="break-all">{selected.endpoint}</span></p>
                  <p><b>创建：</b>{new Date(selected.created_at).toLocaleString()}</p><p><b>完成：</b>{selected.completed_at ? new Date(selected.completed_at).toLocaleString() : "等待中"}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {coverage.map(([label, ok]) => <span key={label} className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs font-bold ${ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{ok ? <CheckCircle2 size={13} /> : <Clock3 size={13} />}{label}</span>)}
                </div>
              </div>

              <section className="rounded-lg border border-black/10 bg-white p-4">
                <div className="flex flex-wrap items-end justify-between gap-2">
                  <div>
                    <p className="text-xs font-bold text-[#ff5c74]">PIPELINE TRACE</p>
                    <h3 className="mt-1 text-base font-black">AI 换甲处理链路</h3>
                  </div>
                  <p className="text-xs font-bold text-[#9b7580]">总耗时：{selected.completed_at ? formatDuration(new Date(selected.completed_at).getTime() - new Date(selected.created_at).getTime()) : "等待中"}</p>
                </div>
                <div className="mt-4 grid gap-2 md:grid-cols-[1fr_auto_1fr_auto_1fr] xl:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr]">
                  {pipeline.map((step, index) => (
                    <div key={step.title} className="contents">
                      <article className="rounded-lg border border-[#f3dce3] bg-[#fff9fb] p-3">
                        <p className="text-[10px] font-black text-[#ff5c74]">STEP {index + 1}</p>
                        <p className="mt-1 text-xs font-black">{step.title}</p>
                        <p className="mt-1 text-[10px] leading-4 text-[#9b7580]">{step.detail}</p>
                        <p className="mt-2 flex items-center gap-1 text-[11px] font-black text-[#6b4b55]"><Clock3 size={12} />{formatDuration(step.time)}</p>
                      </article>
                      {index < pipeline.length - 1 ? <ArrowRight className="mx-auto hidden self-center text-[#ff8da0] md:block" size={16} /> : null}
                    </div>
                  ))}
                </div>
              </section>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <EvidenceImage title="1. 输入手图" src={selected.assets.hand_image_url} />
                <EvidenceImage title="2. 已正向化款式图" src={selected.assets.style_image_url} />
                <EvidenceImage title="3. Mask 状态" src={selected.assets.mask_image_url} empty="当前为无 Mask 模式：使用指甲 bbox 与视觉理解提示词控制编辑。" />
                <EvidenceImage title="4. 生成结果" src={selected.result_image_url} empty={selected.error ?? "等待模型返回"} />
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-lg border border-black/10 bg-white p-4"><h3 className="text-sm font-black">实际提示词</h3><pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-[#22161a] p-4 text-xs leading-5 text-[#ffe9ef]">{selected.prompt || "暂无提示词"}</pre></section>
                <section className="rounded-lg border border-black/10 bg-white p-4"><h3 className="text-sm font-black">结构化控制参数</h3><pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-[#f7f4f2] p-4 text-xs leading-5">{JSON.stringify({ sent_to_model: selected.sent_to_model, payload_summary: selected.payload_summary, timings_ms: selected.timings_ms, hand_analysis: selected.hand_analysis, pixel_control: selected.pixel_control, error: selected.error }, null, 2)}</pre></section>
              </div>
            </>
          ) : <div className="rounded-lg border border-dashed border-black/15 bg-white p-10 text-center text-sm text-[#9b7580]">等待第一条试戴测试记录</div>}
        </section>
      </div>
    </main>
  );
}
