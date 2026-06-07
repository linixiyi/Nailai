"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Bookmark, Loader2, RotateCcw, Store } from "lucide-react";
import { inventoryStyles } from "@/lib/styles";
import { styleImageOrientationClass } from "@/lib/stylePresentation";
import { resolveApiAssetUrl } from "@/lib/api";
import { loadTryOnResult, loadTryOnOriginalImage } from "@/lib/tryOnStore";
import { loadTryOnHistory, type TryOnHistoryItem } from "@/lib/historyStore";
import type { TryOnResponse } from "@/lib/types";
import { PhoneShell, PrimaryButton, SoftCard } from "./Shell";

export function ResultScreen() {
  const [result, setResult] = useState<TryOnResponse | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [history, setHistory] = useState<TryOnHistoryItem[]>([]);
  const fallback = inventoryStyles[0];

  const normalizeTryOnUrls = (item: TryOnResponse): TryOnResponse => ({
    ...item,
    result_image_url: resolveApiAssetUrl(item.result_image_url),
    mask_image_url: item.mask_image_url ? resolveApiAssetUrl(item.mask_image_url) : item.mask_image_url,
    style: {
      ...item.style,
      image_url: item.style.image_url ? resolveApiAssetUrl(item.style.image_url) : item.style.image_url,
    },
  });

  useEffect(() => {
    const latest = loadTryOnResult();
    setResult(latest ? normalizeTryOnUrls(latest) : null);
    setOriginalImage(loadTryOnOriginalImage());
    setHistory(loadTryOnHistory().map((h) => ({ ...h, result: normalizeTryOnUrls(h.result) })));
    setIsLoaded(true);
  }, []);

  const imageUrl = result?.result_image_url ?? fallback.image_url ?? "/style-images/custom/fixed-target-style.png";
  const displayUrl = showOriginal && originalImage ? originalImage : imageUrl;
  const style = result?.style ?? fallback;
  const isFallback = result?.channel === "mock-fallback";
  const fallbackReason = result?.provider_payload?.fallback_reason || "生成失败，使用了演示数据";
  const providerPayload = result?.provider_payload as { mode?: string; model?: string; mask_guided?: boolean } | undefined;

  return (
    <PhoneShell title="试戴结果" active="tryon">
      <div className="space-y-4 px-4 pt-3">
        {isFallback && (
          <div className="flex gap-2 rounded-[16px] bg-red-50 p-3 text-xs font-semibold leading-5 text-red-600">
            <AlertTriangle className="shrink-0" size={16} />
            <p>由于模型接口调用失败或超时，当前为您展示兜底演示效果。<br/><span className="font-normal opacity-80">原因：{String(fallbackReason)}</span></p>
          </div>
        )}

        <section className="overflow-hidden rounded-[26px] bg-[#2b0d1b] p-3 shadow-lg shadow-[#e2aab7]/30">
          <div className="relative h-[340px] overflow-hidden rounded-[22px] bg-black/20">
            {isLoaded ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={displayUrl} alt="AI 试戴结果" className="h-full w-full object-cover transition-opacity duration-200" />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-[#2b0d1b]">
                <Loader2 className="animate-spin text-[#ff5c74]" size={36} />
              </div>
            )}
            
            {isLoaded && originalImage && (
              <button
                type="button"
                className="absolute bottom-3 right-3 rounded-full bg-black/50 px-3 py-1.5 text-xs font-bold text-white backdrop-blur-md transition-colors active:bg-[#ff5c74]"
                onPointerDown={() => setShowOriginal(true)}
                onPointerUp={() => setShowOriginal(false)}
                onPointerLeave={() => setShowOriginal(false)}
                onContextMenu={(e) => e.preventDefault()}
              >
                按住对比原图
              </button>
            )}
          </div>
        </section>

        <SoftCard>
          <p className="text-[11px] font-bold text-[#ff5c74]">AI 换美甲结果</p>
          <h1 className="mt-1 text-2xl font-black">{style.name}</h1>
          <p className="mt-2 text-xs leading-5 text-[#8f6b75]">
            已根据你的手图与目标款式生成。
            {result
              ? `手图置信度 ${(result.hand_confidence * 100).toFixed(0)}%，识别指甲 ${result.nail_count ?? "-"} 个，通道 ${result.channel}，模型 ${providerPayload?.model ?? "-"}，模式 ${providerPayload?.mode ?? "-"}。`
              : "当前展示演示图，可回到换美甲页重新生成。"}
          </p>
          {providerPayload?.mask_guided ? (
            <p className="mt-2 rounded-[12px] bg-[#fff7f2] px-3 py-2 text-[11px] font-bold text-[#ff5c74]">
              已启用指甲分割 mask 控制，结果来自本次上传手图与当前选择款式。
            </p>
          ) : null}
        </SoftCard>

        <div className="grid grid-cols-2 gap-3">
          <PrimaryButton href="/ai-tryon">
            <RotateCcw size={16} />
            重拍
          </PrimaryButton>
          <PrimaryButton href="/shop-recommend">
            <Store size={16} />
            找店铺
          </PrimaryButton>
        </div>

        <button type="button" className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-[#f5dce3] bg-white text-sm font-black text-[#5a3a43]">
          <Bookmark size={16} />
          保存到我的方案
        </button>

        <SoftCard>
          <div className="flex gap-3">
            <div className="relative h-20 w-20 overflow-hidden rounded-[18px] bg-neutral-100 flex items-center justify-center">
              {style.image_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={style.image_url} alt={style.name} className={`h-full w-full object-contain p-1${styleImageOrientationClass(style)}`} />
              ) : null}
            </div>
            <div>
              <p className="text-sm font-black">目标款式</p>
              <p className="mt-1 text-xs font-semibold text-[#9b7580]">以左侧款式图片为准</p>
            </div>
          </div>
        </SoftCard>

        {history.length ? (
          <SoftCard>
            <p className="text-sm font-black">试戴历史</p>
            <p className="mt-1 text-[11px] font-bold text-[#9b7580]">保存在当前浏览器，点击可恢复查看。</p>
            <div className="mt-3 space-y-3">
              {history.slice(0, 5).map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setResult(normalizeTryOnUrls(item.result))}
                  className="flex w-full gap-3 rounded-[18px] bg-[#fff7f2] p-2 text-left"
                >
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-[14px] bg-[#fff0f4]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={item.result.result_image_url} alt={item.result.style.name} className="h-full w-full object-cover" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-black">{item.result.style.name}</p>
                    <p className="mt-1 text-[10px] font-bold text-[#9b7580]">{item.result.channel} · {new Date(item.created_at).toLocaleString()}</p>
                    <p className="mt-1 truncate text-[10px] text-[#a88a93]">{item.result.job_id}</p>
                  </div>
                </button>
              ))}
            </div>
          </SoftCard>
        ) : null}
        <div className="h-4" />
      </div>
    </PhoneShell>
  );
}
