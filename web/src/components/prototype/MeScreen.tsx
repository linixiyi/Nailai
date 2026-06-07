"use client";

import { useEffect, useState } from "react";
import { PhoneShell, SoftCard } from "./Shell";
import {
  loadTryOnHistory,
  loadDiyBountyHistory,
  type TryOnHistoryItem,
  type DiyBountyHistoryItem,
} from "@/lib/historyStore";
import { resolveApiAssetUrl } from "@/lib/api";
import {
  Clock,
  Sparkles,
  X,
  Palette,
} from "lucide-react";

export function MeScreen() {
  const [tryOnHistory, setTryOnHistory] = useState<TryOnHistoryItem[]>([]);
  const [diyHistory, setDiyHistory] = useState<DiyBountyHistoryItem[]>([]);
  const [activeTab, setActiveTab] = useState<"tryon" | "diy">("tryon");
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  useEffect(() => {
    // Load try-on history and normalize URLs
    const rawTryOn = loadTryOnHistory();
    const normalizedTryOn = rawTryOn.map((item) => ({
      ...item,
      result: {
        ...item.result,
        result_image_url: resolveApiAssetUrl(item.result.result_image_url),
        style: {
          ...item.result.style,
          image_url: item.result.style.image_url
            ? resolveApiAssetUrl(item.result.style.image_url)
            : item.result.style.image_url,
        },
      },
    }));
    setTryOnHistory(normalizedTryOn);

    // Load DIY history and normalize variant URLs
    const rawDiy = loadDiyBountyHistory();
    const normalizedDiy = rawDiy.map((item) => ({
      ...item,
      result: {
        ...item.result,
        variants: item.result.variants.map((v) => ({
          ...v,
          image_url: resolveApiAssetUrl(v.image_url),
        })),
      },
    }));
    setDiyHistory(normalizedDiy);
  }, []);

  return (
    <PhoneShell title="我的" active="mine">
      <div className="space-y-4 px-4 pt-3 pb-6">
        {/* User Card */}
        <SoftCard className="bg-[linear-gradient(135deg,#fff0f4,#ffebe3)]">
          <div className="flex items-center gap-4">
            <div className="grid h-16 w-16 place-items-center rounded-full bg-white text-lg font-black text-[#ff5c74] shadow-md shadow-[#ff5c74]/10">
              Nail
            </div>
            <div>
              <h2 className="text-lg font-black text-[#2b0d1b]">NailAI 体验官</h2>
              <p className="mt-1 text-xs text-[#8f6b75] font-semibold">
                欢迎来到你的美甲灵感专属空间
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 divide-x divide-[#ffb8c7]/20 border-t border-[#ffb8c7]/15 pt-3 text-center">
            <div>
              <p className="text-lg font-black text-[#ff5c74]">{tryOnHistory.length}</p>
              <p className="text-[10px] text-[#9b7580] font-black">AI 试戴记录</p>
            </div>
            <div>
              <p className="text-lg font-black text-[#ff5c74]">{diyHistory.length}</p>
              <p className="text-[10px] text-[#9b7580] font-black">DIY 方案记录</p>
            </div>
          </div>
        </SoftCard>

        {/* Tab Selection */}
        <div className="flex rounded-full bg-[#f4ecef] p-1">
          <button
            type="button"
            onClick={() => setActiveTab("tryon")}
            className={`flex-1 rounded-full py-2 text-xs font-black transition-all ${
              activeTab === "tryon"
                ? "bg-[#ff5c74] text-white shadow-sm shadow-[#ff5c74]/20"
                : "text-[#8f6b75]"
            }`}
          >
            美甲试戴 ({tryOnHistory.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("diy")}
            className={`flex-1 rounded-full py-2 text-xs font-black transition-all ${
              activeTab === "diy"
                ? "bg-[#ff5c74] text-white shadow-sm shadow-[#ff5c74]/20"
                : "text-[#8f6b75]"
            }`}
          >
            DIY 方案 ({diyHistory.length})
          </button>
        </div>

        {/* Active List */}
        {activeTab === "tryon" ? (
          <div className="space-y-3">
            {tryOnHistory.length ? (
              tryOnHistory.map((item) => (
                <SoftCard key={item.id} className="relative">
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate text-sm font-black text-[#2b0d1b]">
                          {item.result.style.name}
                        </h3>
                        <p className="mt-1 flex items-center gap-1 text-[10px] font-bold text-[#9b7580]">
                          <Sparkles size={11} className="text-[#ff5c74]" />
                          生成通道: {item.result.channel}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 text-[9px] text-[#a88a93] font-bold shrink-0">
                        <Clock size={9} />
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    
                    {/* Horizontal image row */}
                    <div className="flex gap-2.5 overflow-x-auto pb-1">
                      {item.result.style.image_url ? (
                        <div 
                          onClick={() => setLightboxImage(item.result.style.image_url!)}
                          className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={item.result.style.image_url} alt="设计款式" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                          <span className="absolute bottom-0.5 right-0.5 rounded bg-black/60 px-1 py-0.5 text-[8px] font-black text-white">款式</span>
                        </div>
                      ) : null}

                      {item.hand_image ? (
                        <div 
                          onClick={() => setLightboxImage(item.hand_image!)}
                          className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={item.hand_image} alt="上传原图" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                          <span className="absolute bottom-0.5 right-0.5 rounded bg-black/60 px-1 py-0.5 text-[8px] font-black text-white">原图</span>
                        </div>
                      ) : null}

                      <div 
                        onClick={() => setLightboxImage(item.result.result_image_url)}
                        className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={item.result.result_image_url} alt="试戴效果" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                        <span className="absolute bottom-0.5 right-0.5 rounded bg-[#ff5c74] px-1 py-0.5 text-[8px] font-black text-white">效果</span>
                      </div>
                    </div>
                  </div>
                </SoftCard>
              ))
            ) : (
              <div className="rounded-[24px] bg-white border border-dashed border-[#e6dee1] py-12 text-center text-xs text-[#9b7580] font-bold">
                暂无试戴历史。快去“换美甲”页体验一下吧！
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {diyHistory.length ? (
              diyHistory.map((item) => {
                const cover = item.result.variants[0];
                const payloadAssets = (item.result.provider_payload as { assets?: { reference_image_url?: string; hand_image_url?: string } } | undefined)?.assets;
                const refImgUrl = payloadAssets?.reference_image_url;
                const handImgUrl = payloadAssets?.hand_image_url;

                return (
                  <SoftCard key={item.id}>
                    <div className="flex flex-col gap-3">
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate text-sm font-black text-[#2b0d1b]">
                            {item.answers.style} · {item.answers.nail_length}
                          </h3>
                          <div className="mt-1 flex flex-wrap gap-1">
                            <span className="rounded-full bg-[#fdeef2] px-2 py-0.5 text-[9px] font-black text-[#ff5c74]">
                              {item.answers.occasion}
                            </span>
                            <span className="rounded-full bg-[#fff6ec] px-2 py-0.5 text-[9px] font-black text-[#ff8e29]">
                              {item.answers.nail_shape}
                            </span>
                          </div>
                          {item.answers.user_prompt ? (
                            <p className="mt-1.5 line-clamp-1 text-[10px] font-bold text-[#7a5561] flex items-center gap-1">
                              <Palette size={10} className="text-[#ff5c74]" />
                              补充: {item.answers.user_prompt}
                            </p>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-1 text-[9px] text-[#a88a93] font-bold shrink-0">
                          <Clock size={9} />
                          {new Date(item.created_at).toLocaleString()}
                        </div>
                      </div>

                      {/* Horizontal image row */}
                      <div className="flex gap-2.5 overflow-x-auto pb-1">
                        {refImgUrl ? (
                          <div 
                            onClick={() => setLightboxImage(resolveApiAssetUrl(refImgUrl))}
                            className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={resolveApiAssetUrl(refImgUrl)} alt="参考图" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                            <span className="absolute bottom-0.5 right-0.5 rounded bg-black/60 px-1 py-0.5 text-[8px] font-black text-white">参考图</span>
                          </div>
                        ) : null}

                        {handImgUrl ? (
                          <div 
                            onClick={() => setLightboxImage(resolveApiAssetUrl(handImgUrl))}
                            className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={resolveApiAssetUrl(handImgUrl)} alt="手部图" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                            <span className="absolute bottom-0.5 right-0.5 rounded bg-black/60 px-1 py-0.5 text-[8px] font-black text-white">手图</span>
                          </div>
                        ) : null}

                        {cover ? (
                          <div 
                            onClick={() => setLightboxImage(cover.image_url)}
                            className="group relative h-16 w-16 shrink-0 cursor-zoom-in overflow-hidden rounded-xl border border-black/5 bg-neutral-100"
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={cover.image_url} alt="方案图" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                            <span className="absolute bottom-0.5 right-0.5 rounded bg-[#ff5c74] px-1 py-0.5 text-[8px] font-black text-white">方案</span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </SoftCard>
                );
              })
            ) : (
              <div className="rounded-[24px] bg-white border border-dashed border-[#e6dee1] py-12 text-center text-xs text-[#9b7580] font-bold">
                暂无 DIY 方案。快去“悬赏”页定制专属美甲吧！
              </div>
            )}
          </div>
        )}

        {/* Lightbox / Zoomed image Modal */}
        {lightboxImage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 animate-fade-in"
            onClick={() => setLightboxImage(null)}
          >
            <button
              type="button"
              onClick={() => setLightboxImage(null)}
              className="absolute right-4 top-4 rounded-full bg-white/20 p-2 text-white hover:bg-white/30 transition-colors"
            >
              <X size={20} />
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={lightboxImage}
              alt="放大图预览"
              className="max-h-[85dvh] max-w-full rounded-lg object-contain shadow-2xl"
            />
          </div>
        )}
      </div>
    </PhoneShell>
  );
}
