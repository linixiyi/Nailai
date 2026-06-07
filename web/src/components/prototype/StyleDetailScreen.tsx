"use client";
import { useEffect, useState } from "react";
import { Heart, MapPin, Sparkles, Star, AlertCircle } from "lucide-react";
import { prototypeShops } from "@/lib/prototypeData";
import type { PrototypeShop } from "@/lib/prototypeData";
import { styleImageOrientationClass } from "@/lib/stylePresentation";
import { findStyleExact } from "@/lib/styles";
import type { NailStyle } from "@/lib/types";
import { fetchShops, fetchStyles, reportStyleTelemetry } from "@/lib/api";
import { PhoneShell, PrimaryButton, SoftCard } from "./Shell";
import { ShopCard } from "./Cards";

export function StyleDetailScreen({ styleId }: { styleId?: string }) {
  const [style, setStyle] = useState<NailStyle | null>(null);
  const [shops, setShops] = useState<PrototypeShop[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [liked, setLiked] = useState(false);

  const handleLike = () => {
    const nextLiked = !liked;
    setLiked(nextLiked);
    if (nextLiked && style) {
      reportStyleTelemetry(style.id, "interest");
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchStyles(), fetchShops()])
      .then(([fetchedStyles, fetchedShops]) => {
        const found = fetchedStyles.find((s) => s.id === styleId) ?? findStyleExact(styleId) ?? null;
        setStyle(found);
        setNotFound(!found);
        setShops(fetchedShops);
        if (found) {
          reportStyleTelemetry(found.id, "view");
        }
      })
      .catch((err) => {
        console.error("Failed to load dynamic details", err);
        const fallback = findStyleExact(styleId) ?? null;
        setStyle(fallback);
        setNotFound(!fallback);
        setShops(prototypeShops);
        if (fallback) {
          reportStyleTelemetry(fallback.id, "view");
        }
      })
      .finally(() => setLoading(false));
  }, [styleId]);

  if (loading) {
    return (
      <PhoneShell title="款式详情" active="home">
        <div className="flex h-[80vh] items-center justify-center">
          <span className="h-8 w-8 animate-spin rounded-full border-4 border-[#ff5c74] border-t-transparent" />
        </div>
      </PhoneShell>
    );
  }

  if (notFound || !style) {
    return (
      <PhoneShell title="款式详情" active="home">
        <div className="flex min-h-[70vh] flex-col items-center justify-center px-8 text-center">
          <AlertCircle size={32} className="text-[#ff5c74]" />
          <h1 className="mt-4 text-lg font-black text-[#27101c]">没有找到这款美甲</h1>
          <p className="mt-2 text-xs font-bold leading-5 text-[#9b7580]">库存数据可能刚刚更新，请返回款式列表重新选择。</p>
          <div className="mt-5">
            <PrimaryButton href="/">返回款式列表</PrimaryButton>
          </div>
        </div>
      </PhoneShell>
    );
  }

  // Find shops that can do this style
  const matchedShops = shops.filter((shop) => shop.availableStyles.includes(style.id));
  const finalShops = matchedShops.length ? matchedShops : shops.slice(0, 2);
  const displayTags = style.taxonomy
    ? [
        style.taxonomy.colors[0],
        style.taxonomy.techniques[0],
        style.taxonomy.shapes[0],
        style.taxonomy.styles[0],
        style.taxonomy.occasions[0],
        style.taxonomy.lengths[0],
      ].filter((tag, index, tags): tag is string => Boolean(tag) && tags.indexOf(tag) === index)
    : style.tags.slice(0, 6);

  // Helper to resolve price based on style price level
  const getStylePriceText = (priceLevel?: string | null) => {
    if (priceLevel === "¥¥¥") return "¥258";
    if (priceLevel === "¥¥") return "¥158";
    return "¥98";
  };

  return (
    <PhoneShell title="款式详情" active="home">
      <div className="space-y-4 px-4 pt-3 pb-8">
        <div className="relative h-[330px] overflow-hidden rounded-[28px] bg-[#fff0f4]">
          {style.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={style.image_url}
              alt={style.name}
              className={`h-full w-full ${styleImageOrientationClass(style).trim()} object-contain p-3`}
            />
          ) : null}
          <button
            type="button"
            onClick={handleLike}
            className={`absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full bg-white/90 transition-colors ${
              liked ? "text-[#ff5c74]" : "text-neutral-400 hover:text-[#ff5c74]"
            }`}
          >
            <Heart size={18} fill={liked ? "#ff5c74" : "none"} />
          </button>
        </div>

        <SoftCard>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold text-[#ff5c74]">可预约款式 · 同款可做</p>
              <h1 className="mt-1 text-2xl font-black text-[#27101c]">{style.name}</h1>
              <div className="mt-2 flex items-center gap-2 text-xs font-bold text-[#9b7580]">
                <Star size={13} fill="#ffb600" className="text-[#ffb600]" />
                4.9
                <span>1.2k 收藏</span>
              </div>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xl font-black text-[#ff5c74]">
                {getStylePriceText(style.price_level)}
              </p>
              <p className="text-[9px] text-[#9b7580] font-bold mt-0.5">款式统一定制价</p>
            </div>
          </div>
          <p className="mt-4 text-xs leading-5 text-[#74515b]">
            这款设计融合了高光质感与细节图案，适合需要上镜、显白和强风格表达的场合。价格已公开透明化，到店后无任何隐形增项消费。
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {displayTags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-[#fff0f4] px-3 py-1 text-[11px] font-bold text-[#ff5c74]"
              >
                {tag}
              </span>
            ))}
          </div>
        </SoftCard>

        {/* Pricing & Scheduling transparency notice */}
        <div className="rounded-[20px] bg-emerald-50/50 border border-emerald-100 p-3 flex gap-2">
          <AlertCircle className="text-emerald-600 shrink-0 mt-0.5" size={16} />
          <div className="text-[10px] leading-relaxed text-emerald-800 font-bold">
            <p className="text-xs font-black text-emerald-900">免等预约 & 透明低价保障</p>
            <p className="mt-0.5">
              店家在此同步了其实时到店等待时间与今日排期。您在去之前即可确定价格并查看是否空闲，避免耗时排队。
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <PrimaryButton 
            href={`/ai-tryon?styleId=${style.id}`}
            onClick={() => reportStyleTelemetry(style.id, "booking")}
          >
            <Sparkles size={16} />
            试戴
          </PrimaryButton>
          <PrimaryButton 
            href="/shop-recommend"
            onClick={() => reportStyleTelemetry(style.id, "booking")}
          >
            <MapPin size={16} />
            可做店铺
          </PrimaryButton>
        </div>

        <section>
          <h2 className="mb-3 text-base font-black text-[#27101c]">附近可做店铺 (实时排期与价格)</h2>
          <div className="space-y-3">
            {finalShops.map((shop) => (
              <div key={shop.id} className="relative group">
                <ShopCard shop={shop} />
                {/* Transparent Price agreed Tag */}
                <div className="absolute right-3 bottom-3 flex items-center gap-1 text-[9px] bg-emerald-50 text-emerald-700 font-black px-2.5 py-0.5 rounded-full border border-emerald-100">
                  定制价: {getStylePriceText(style.price_level)}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </PhoneShell>
  );
}
