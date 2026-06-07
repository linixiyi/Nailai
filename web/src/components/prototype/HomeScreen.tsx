"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, useCallback } from "react";
import { Heart, MessageCircle, Sparkles, Trophy, X } from "lucide-react";
import { fetchStyles } from "@/lib/api";
import { inventoryStyles } from "@/lib/styles";
import { styleImageOrientationClass } from "@/lib/stylePresentation";
import type { NailStyle } from "@/lib/types";
import { PhoneShell } from "./Shell";

/** Dimension display names */
const DIMENSION_LABELS: Record<string, string> = {
  colors: "颜色",
  techniques: "技法",
  shapes: "甲型",
  styles: "风格",
  occasions: "场合",
  lengths: "长度",
};

const toneClasses = [
  "bg-black/45 text-white backdrop-blur-sm",
  "bg-accent-pink text-white",
  "bg-accent-wine text-white",
  "bg-accent-gold text-white",
];

const FILTER_DIMENSIONS = ["styles", "occasions", "colors", "techniques", "shapes", "lengths"] as const;
const FILTER_WHITELISTS: Record<FilterDimension, string[]> = {
  colors: ["红色系", "粉色系", "蓝色系", "绿色系", "紫色系", "黑色系", "白色系", "灰色系", "裸色系", "大地色系", "金属色系", "金银色", "彩色", "多色", "冷色系"],
  techniques: ["亮片", "闪粉", "爆闪", "动物纹", "手绘", "花卉", "立体花", "法式", "法式变体", "渐变", "腮红", "冰透", "猫眼", "魔镜", "极光", "纯色", "跳色", "几何", "钻饰", "宝石", "珍珠"],
  shapes: ["尖型", "方圆型", "杏仁型", "梯型", "椭圆型"],
  styles: ["仙气", "温柔", "梦幻", "复古", "老钱", "莫兰迪", "奢华", "巴洛克", "千金", "日系", "清新", "可爱", "暗黑", "朋克", "酷感", "极简", "冷淡", "INS", "欧美", "辣妹", "Y2K", "高级感", "轻奢", "气质"],
  occasions: ["婚礼", "新娘", "宴会", "日常", "通勤", "百搭", "春夏", "度假", "清凉", "派对", "蹦迪", "晚宴", "秋冬", "约会", "节日", "新年", "圣诞"],
  lengths: ["短款", "中长款", "长款"],
};

type FilterDimension = (typeof FILTER_DIMENSIONS)[number];

type DisplayFilter = {
  label: string;
  dimension: FilterDimension;
  count: number;
};

function formatPrice(style: NailStyle) {
  const map: Record<string, string> = {
    "¥": "¥138",
    "¥¥": "¥198",
    "¥¥¥": "¥288",
    "¥¥¥¥": "¥368",
  };
  return map[style.price_level] ?? style.price_level ?? "¥198";
}

function canonicalizeFilterValue(dimension: FilterDimension, value: string | null | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized) return null;
  return FILTER_WHITELISTS[dimension].includes(normalized) ? normalized : null;
}

function getPrimaryDimensionValue(style: NailStyle, dimension: FilterDimension): string | null {
  const taxonomyValues = style.taxonomy?.[dimension];
  if (taxonomyValues?.length) {
    for (const value of taxonomyValues) {
      const canonical = canonicalizeFilterValue(dimension, value);
      if (canonical) return canonical;
    }
  }

  switch (dimension) {
    case "occasions":
      return canonicalizeFilterValue(dimension, style.occasion?.[0]);
    case "colors":
      return canonicalizeFilterValue(dimension, style.color?.split(" / ")[0]);
    case "techniques":
      return canonicalizeFilterValue(dimension, style.finish);
    case "lengths":
      if (style.nail_length === "long") return canonicalizeFilterValue(dimension, "长款");
      if (style.nail_length === "medium") return canonicalizeFilterValue(dimension, "中长款");
      if (style.nail_length === "natural") return canonicalizeFilterValue(dimension, "短款");
      return null;
    default:
      return null;
  }
}

function getStyleDimensionValues(style: NailStyle, dimension: FilterDimension): string[] {
  const taxonomyValues = style.taxonomy?.[dimension];
  if (taxonomyValues?.length) {
    const canonical = getPrimaryDimensionValue(style, dimension);
    return canonical ? [canonical] : [];
  }

  switch (dimension) {
    case "occasions":
      return style.occasion?.map((value) => canonicalizeFilterValue(dimension, value)).filter((value): value is string => Boolean(value)) ?? [];
    case "colors":
      return style.color ? [style.color.split(" / ")[0]].map((value) => canonicalizeFilterValue(dimension, value)).filter((value): value is string => Boolean(value)) : [];
    case "techniques":
      return style.finish ? [canonicalizeFilterValue(dimension, style.finish)].filter((value): value is string => Boolean(value)) : [];
    case "lengths":
      if (style.nail_length === "long") return ["长款"];
      if (style.nail_length === "medium") return ["中长款"];
      if (style.nail_length === "natural") return ["短款"];
      return [];
    default:
      return [];
  }
}

function buildDisplayFilters(styles: NailStyle[]): DisplayFilter[] {
  const counters = new Map<FilterDimension, Map<string, number>>();
  FILTER_DIMENSIONS.forEach((dimension) => counters.set(dimension, new Map()));

  for (const style of styles) {
    for (const dimension of FILTER_DIMENSIONS) {
      const value = getPrimaryDimensionValue(style, dimension);
      const normalized = value?.trim();
      if (!normalized) continue;
      const bucket = counters.get(dimension);
      if (!bucket) continue;
      bucket.set(normalized, (bucket.get(normalized) ?? 0) + 1);
    }
  }

  const guaranteed = FILTER_DIMENSIONS.flatMap((dimension) => {
    const bucket = counters.get(dimension);
    if (!bucket?.size) return [];
    const ranked = [...bucket.entries()]
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1]);
    if (!ranked.length) return [];
    const [label, count] = ranked[0];
    return [{ label, dimension, count }];
  });
  return guaranteed;
}

function StyleCard({ style, index }: { style: NailStyle; index: number }) {
  const tag = style.tags[0] ?? style.finish ?? "REAL";
  const offset = index % 4 === 1;
  const pull = index % 5 === 2;

  return (
    <div className={`flex flex-col gap-2 ${offset ? "pt-8" : ""} ${pull ? "-mt-4" : ""}`}>
      <div className="group relative overflow-hidden rounded-2xl bg-muted ring-1 ring-black/5">
        <Link href={`/style-detail/${style.id}`} className="block">
          {style.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={style.image_url} alt={style.name} loading="lazy" className={`aspect-[4/5] w-full object-cover transition-transform duration-700 group-hover:scale-105${styleImageOrientationClass(style)}`} />
          ) : (
            <div className="aspect-[4/5] w-full bg-gradient-to-br from-accent-pink/10 to-accent-gold/20" />
          )}
        </Link>
        <span className={`absolute left-2 top-2 rounded-full px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-tighter ${toneClasses[index % toneClasses.length]}`}>
          {tag}
        </span>
        <Link href={`/ai-tryon?styleId=${style.id}`} className="absolute bottom-2 right-2 grid size-9 place-items-center rounded-full bg-white/90 text-accent-pink shadow-lg backdrop-blur transition-transform active:scale-95">
          <Sparkles className="size-4" />
        </Link>
      </div>
      <div className="px-1">
        <h3 className="text-xs font-bold leading-tight">{style.name}</h3>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="text-[10px] font-bold text-accent-wine">{formatPrice(style)}</span>
          <span className="inline-flex items-center gap-1 text-[9px] text-foreground/40">
            <Heart className="size-3" />
            {900 + index * 73} 喜欢
          </span>
        </div>
      </div>
    </div>
  );
}

export function HomeScreen() {
  const searchParams = useSearchParams();
  const search = searchParams?.get("search") || "";

  const [styles, setStyles] = useState<NailStyle[]>(inventoryStyles);
  const [displayFilters, setDisplayFilters] = useState<DisplayFilter[]>([]);
  const [activeFilter, setActiveFilter] = useState<DisplayFilter | null>(null);

  useEffect(() => {
    fetchStyles()
      .then((nextStyles) => {
        const stylesWithImages = nextStyles.filter((style) => Boolean(style.image_url));
        const catalogStyles = (stylesWithImages.length ? stylesWithImages : nextStyles).filter((style) => Boolean(style.image_url));
        setStyles(catalogStyles.length ? catalogStyles : inventoryStyles);
      })
      .catch(() => setStyles(inventoryStyles));
  }, []);

  useEffect(() => {
    setDisplayFilters(buildDisplayFilters(styles));
  }, [styles]);

  // Filter styles based on active filter tag and search query
  const visibleStyles = useMemo(() => {
    let withImages = styles.filter((style) => Boolean(style.image_url));

    if (search.trim()) {
      const q = search.toLowerCase();
      withImages = withImages.filter(
        (style) =>
          style.name.toLowerCase().includes(q) ||
          style.tags.some((tag) => tag.toLowerCase().includes(q)) ||
          (style.color && style.color.toLowerCase().includes(q)) ||
          (style.finish && style.finish.toLowerCase().includes(q))
      );
    }

    if (!activeFilter) return withImages;

    return withImages.filter((style) =>
      getStyleDimensionValues(style, activeFilter.dimension).includes(activeFilter.label),
    );
  }, [styles, activeFilter, search]);

  useEffect(() => {
    if (!activeFilter) return;
    const stillExists = displayFilters.some(
      (filter) => filter.dimension === activeFilter.dimension && filter.label === activeFilter.label,
    );
    if (!stillExists) {
      setActiveFilter(null);
    }
  }, [activeFilter, displayFilters]);

  const leftColumn = visibleStyles.filter((_, index) => index % 2 === 0);
  const rightColumn = visibleStyles.filter((_, index) => index % 2 === 1);

  const handleFilterClick = useCallback((filter: DisplayFilter) => {
    setActiveFilter((prev) =>
      prev?.label === filter.label && prev.dimension === filter.dimension ? null : filter,
    );
  }, []);

  return (
    <PhoneShell active="home">
      <header className="animate-reveal px-5 pb-6 pt-8">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.25em] text-foreground/40">第叁期 · 春夏甲面诗</p>
        <h1 className="text-balance mb-3 font-display text-[3.25rem] leading-[0.95]">
          十指<span className="italic text-accent-wine">流光</span>
          <br />
          一念<span className="italic text-accent-pink">倾城</span>
        </h1>
        <p className="font-display text-base italic leading-snug text-foreground/55">以釉色入诗，让指尖落款。</p>

        <div className="mt-6 grid grid-cols-3 gap-2">
          <Link href="/ai-tryon" className="flex flex-col items-center gap-2 rounded-2xl border border-accent-pink/10 bg-accent-pink/5 p-3 transition-transform active:scale-95">
            <div className="grid size-10 place-items-center rounded-full bg-accent-pink text-white shadow-lg shadow-accent-pink/30">
              <Sparkles className="size-4" />
            </div>
            <span className="text-[11px] font-bold tracking-tight">AI 试戴</span>
          </Link>
          <Link href="/chat" className="flex flex-col items-center gap-2 rounded-2xl border border-accent-purple/10 bg-accent-purple/5 p-3 transition-transform active:scale-95">
            <div className="grid size-10 place-items-center rounded-full bg-accent-purple text-white shadow-lg shadow-accent-purple/30">
              <MessageCircle className="size-4" />
            </div>
            <span className="text-[11px] font-bold tracking-tight">智能推荐</span>
          </Link>
          <Link href="/diy-bounty" className="flex flex-col items-center gap-2 rounded-2xl border border-accent-gold/20 bg-accent-gold/10 p-3 transition-transform active:scale-95">
            <div className="grid size-10 place-items-center rounded-full bg-accent-gold text-white shadow-lg shadow-accent-gold/30">
              <Trophy className="size-4" />
            </div>
            <span className="text-[11px] font-bold tracking-tight">悬赏定制</span>
          </Link>
        </div>
      </header>

      <div className="mb-4 flex gap-3 overflow-x-auto px-5 py-2 no-scrollbar">
        <button
          type="button"
          onClick={() => setActiveFilter(null)}
          className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-all ${
            !activeFilter
              ? "bg-foreground text-background font-bold shadow-sm"
              : "font-medium text-foreground/50 hover:text-foreground/80"
          }`}
        >
          全部
        </button>
        {displayFilters.map((filter) => (
          <button
            key={`${filter.dimension}-${filter.label}`}
            type="button"
            onClick={() => handleFilterClick(filter)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-all ${
              activeFilter?.label === filter.label && activeFilter.dimension === filter.dimension
                ? "bg-accent-pink text-white font-bold shadow-sm"
                : "font-medium text-foreground/50 hover:text-foreground/80 hover:bg-foreground/5"
            }`}
            aria-label={`${DIMENSION_LABELS[filter.dimension]}分类：${filter.label}`}
          >
            {DIMENSION_LABELS[filter.dimension]} · {filter.label}
          </button>
        ))}
      </div>
      {activeFilter ? (
        <div className="mb-2 flex items-center gap-2 px-5">
          <span className="text-[11px] font-bold text-foreground/50">
            {DIMENSION_LABELS[activeFilter.dimension]}:
            {" "}
            <span className="text-accent-pink">{activeFilter.label}</span>
            {" "}
            · {visibleStyles.length} 款
          </span>
          <button type="button" onClick={() => setActiveFilter(null)} className="rounded-full p-0.5 hover:bg-foreground/5">
            <X size={12} className="text-foreground/40" />
          </button>
        </div>
      ) : null}

      <section className="grid grid-cols-2 gap-4 px-4 pb-32">
        <div className="flex flex-col gap-4">
          {leftColumn.map((style, index) => (
            <div key={style.id} className="animate-reveal" style={{ animationDelay: `${100 + index * 80}ms` }}>
              <StyleCard style={style} index={index * 2} />
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-4">
          {rightColumn.map((style, index) => (
            <div key={style.id} className="animate-reveal" style={{ animationDelay: `${140 + index * 80}ms` }}>
              <StyleCard style={style} index={index * 2 + 1} />
            </div>
          ))}
        </div>
      </section>
    </PhoneShell>
  );
}
