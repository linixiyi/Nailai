"use client";

import { useState } from "react";
import Link from "next/link";
import { Camera, MapPin, Star } from "lucide-react";
import type { NailStyle } from "@/lib/types";
import type { PrototypeBounty, PrototypeShop, StoreTask } from "@/lib/prototypeData";
import { styleImageOrientationClass } from "@/lib/stylePresentation";

export function NailStyleThumb({ style, selected = false }: { style: NailStyle; selected?: boolean }) {
  return (
    <div className={`overflow-hidden rounded-[18px] border bg-white p-1 ${selected ? "border-[#ff5c74]" : "border-[#f5dce3]"}`}>
      <div className="relative h-[78px] w-full overflow-hidden rounded-[14px] bg-[#fff0f4] flex items-center justify-center">
        {style.image_url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={style.image_url} alt={style.name} className={`h-full w-full object-cover${styleImageOrientationClass(style)}`} />
        ) : null}
      </div>
      <div className="px-1 pb-1 pt-2">
        <p className="truncate text-xs font-black">{style.name}</p>
        <p className="mt-0.5 text-[10px] font-semibold text-[#a88a93]">{style.price_level} · {style.finish}</p>
      </div>
    </div>
  );
}

export function StyleGridCard({ style }: { style: NailStyle }) {
  return (
    <Link href={`/style-detail/${style.id}`} className="block">
      <NailStyleThumb style={style} />
    </Link>
  );
}

export function NailStyleLargeCard({ style }: { style: NailStyle }) {
  return (
    <div className="overflow-hidden rounded-[18px] bg-white shadow-sm">
      <div className="relative aspect-[1/1.18] overflow-hidden rounded-t-[18px] bg-[#fff0f4] flex items-center justify-center">
        <Link href={`/style-detail/${style.id}`} className="block h-full w-full">
          {style.image_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={style.image_url} alt={style.name} className={`h-full w-full object-cover${styleImageOrientationClass(style)}`} />
          ) : null}
        </Link>
        <Link
          href={`/ai-tryon?styleId=${style.id}`}
          className="absolute bottom-3 right-3 inline-flex h-8 items-center gap-1.5 rounded-full bg-black/35 px-3 text-xs font-black text-white backdrop-blur active:bg-[#ff5c74] transition-colors"
        >
          <Camera size={14} />
          试戴
        </Link>
      </div>
      <Link href={`/style-detail/${style.id}`} className="block px-3 py-3">
        <p className="line-clamp-2 min-h-9 text-[13px] font-black leading-[18px]">{style.name}</p>
        <p className="mt-1 text-[11px] font-semibold text-[#a88a93]">{style.price_level} · {style.finish}</p>
      </Link>
    </div>
  );
}

export function ShopCard({ shop }: { shop: PrototypeShop }) {
  return (
    <Link href="/shop-recommend" className="flex gap-3 rounded-[20px] bg-white p-3 shadow-sm border border-neutral-100/50 hover:shadow-md transition-all">
      <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-[16px] bg-[#fff0f4] flex items-center justify-center border border-neutral-50">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={shop.image} alt={shop.name} className="h-full w-full object-cover" />
      </div>
      <div className="min-w-0 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-2">
            <p className="truncate text-sm font-black text-[#27101c]">{shop.name}</p>
            <span className="rounded-full bg-[#fff0f4] px-2 py-0.5 text-[10px] font-black text-[#ff5c74] shrink-0">{shop.price}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold text-[#9b7580]">
            <span className="flex items-center gap-0.5">
              <Star size={11} fill="#ffb600" className="text-[#ffb600]" />
              {shop.rating}
            </span>
            <span>·</span>
            <span className="flex items-center gap-0.5">
              <MapPin size={11} />
              {shop.distance}
            </span>
            {shop.wait_time && (
              <>
                <span>·</span>
                <span className={`px-1.5 py-0.2 rounded text-[9px] font-black ${
                  shop.wait_time === "无需等待" || shop.wait_time.includes("空闲")
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                    : "bg-amber-50 text-amber-600 border border-amber-100"
                }`}>
                  {shop.wait_time}
                </span>
              </>
            )}
            {shop.schedule && (
              <>
                <span>·</span>
                <span className="px-1.5 py-0.2 bg-indigo-50 text-indigo-700 border border-indigo-100 rounded text-[9px] font-black">
                  {shop.schedule}
                </span>
              </>
            )}
          </div>
          <p className="mt-1.5 truncate text-[10px] text-[#a88a93] font-medium">{shop.address}</p>
        </div>
        
        {/* Render facilities */}
        {shop.facilities && (
          <div className="mt-2 flex flex-wrap gap-1">
            {shop.facilities.tea && (
              <span className="bg-[#fff0f4] text-[#ff5c74] px-1.5 py-0.5 rounded-full border border-pink-100/50 text-[9px] font-black scale-95 origin-left">
                零食饮料
              </span>
            )}
            {shop.facilities.wifi && (
              <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full border border-blue-100/50 text-[9px] font-black scale-95 origin-left">
                免费WiFi
              </span>
            )}
            {shop.facilities.parking && (
              <span className="bg-gray-50 text-gray-600 px-1.5 py-0.5 rounded-full border border-gray-200 text-[9px] font-black scale-95 origin-left">
                免费停车
              </span>
            )}
            {shop.facilities.private_room && (
              <span className="bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded-full border border-purple-100/50 text-[9px] font-black scale-95 origin-left">
                独立包间
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}

export function BountyCard({ bounty }: { bounty: PrototypeBounty }) {
  return (
    <Link href={`/bounty-detail/${bounty.id}`} className="block rounded-[22px] bg-white p-3 shadow-sm">
      <div className="flex gap-3">
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-[18px] bg-[#fff0f4] flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={bounty.image} alt={bounty.title} className="h-full w-full object-cover" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="truncate text-sm font-black">{bounty.title}</h3>
            <span className="rounded-full bg-[#27101c] px-2 py-1 text-[10px] font-bold text-white">{bounty.status}</span>
          </div>
          <p className="mt-1 text-xs font-black text-[#ff5c74]">{bounty.budget}</p>
          <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-[#8f6b75]">{bounty.description}</p>
          <p className="mt-2 text-[10px] font-semibold text-[#b09199]">{bounty.participants} 家店铺参与 · {bounty.deadline}</p>
        </div>
      </div>
    </Link>
  );
}

export function StoreTaskCard({
  task,
  onAccept,
}: {
  task: StoreTask & { description?: string };
  onAccept?: (taskId: string) => Promise<void>;
}) {
  const isAvailable = task.status === "待抢单" || task.status === "可接单" || task.status === "待接单";
  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    if (!onAccept) return;
    setLoading(true);
    try {
      await onAccept(task.id);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-[20px] bg-white p-4 shadow-sm border border-neutral-100/60 hover:shadow-md transition-all duration-200">
      <div className="flex gap-3">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-[16px] bg-[#fff0f4] flex items-center justify-center border border-neutral-50">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={task.image} alt={task.styleName} className="h-full w-full object-cover" />
        </div>
        <div className="min-w-0 flex-1 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between">
              <p className="text-sm font-black text-[#27101c] truncate mr-2">{task.styleName}</p>
              <span className="text-sm font-black text-[#ff5c74] shrink-0">{task.price}</span>
            </div>
            <p className="mt-1 text-[11px] font-semibold text-[#9b7580]">
              {task.customer} · {task.distance}
            </p>
            {task.description && (
              <p className="mt-1.5 text-[10px] text-[#9b7580] line-clamp-2 italic leading-relaxed">
                “{task.description}”
              </p>
            )}
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() =>
                alert(
                  `需求详情\n顾客: ${task.customer}\n款式: ${task.styleName}\n报价/预算: ${task.price}\n说明: ${
                    task.description || "无"
                  }`
                )
              }
              className="h-8 flex-1 rounded-full border border-[#f5dce3] text-xs font-bold text-[#5a3a43] hover:bg-[#fff0f4] transition-colors"
            >
              查看详情
            </button>
            {isAvailable ? (
              <button
                type="button"
                onClick={handleAccept}
                disabled={loading}
                className="h-8 flex-1 rounded-full bg-[#27101c] text-xs font-bold text-white hover:bg-[#3d1a2d] active:scale-95 transition-all flex items-center justify-center gap-1.5"
              >
                {loading ? (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  "立即接单"
                )}
              </button>
            ) : (
              <button
                type="button"
                disabled
                className="h-8 flex-1 rounded-full bg-[#f8f5f6] text-xs font-bold text-[#bcaab0] cursor-not-allowed border border-neutral-100"
              >
                {task.status === "已接单" || task.status === "已确认" ? "已接单" : task.status}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
