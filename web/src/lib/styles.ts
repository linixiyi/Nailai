import type { NailStyle } from "./types";
import { importedStyles } from "./importedStyles";
import { applyTaxonomyToStyle, taxonomyTokensForStyle } from "./nailTaxonomy";

export const nailStyles: NailStyle[] = importedStyles.map(applyTaxonomyToStyle);

const blockedKeywords = ["十字架黄黑", "回归测试", "夏日清凉奶黄包"];
const blockedIds = new Set([
  "cross-yellow-black-sexy",
  "regression-test-style",
  "library-20260514-006",
  "library-20260514-032",
]);

export function isPublicCatalogStyle(style: NailStyle) {
  if (!Boolean(style.image_url)) return false;
  if ((style.stock_total ?? 0) <= (style.stock_reserved ?? 0)) return false;
  return !blockedIds.has(style.id) && !blockedKeywords.some((kw) => style.name.includes(kw));
}

export const inventoryStyles: NailStyle[] = nailStyles.filter(
  isPublicCatalogStyle
);

export function findStyle(styleId?: string | null) {
  return inventoryStyles.find((style) => style.id === styleId) ?? inventoryStyles[0];
}

export function findStyleExact(styleId?: string | null) {
  if (!styleId) return null;
  return nailStyles.find((style) => style.id === styleId) ?? null;
}

export function searchStyles(query: string, limit = 5) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return inventoryStyles.slice(0, limit);
  const scored = inventoryStyles
    .map((style) => {
      const taxonomyTokens = taxonomyTokensForStyle(style);
      const haystack = [
        style.name,
        style.color,
        style.finish,
        ...style.occasion,
        ...style.tags,
        ...taxonomyTokens,
      ].join(" ").toLowerCase();
      const score = normalized
        .replace(/[，,]/g, " ")
        .split(/\s+/)
        .filter(Boolean)
        .reduce((total, token) => total + (haystack.includes(token) ? 2 : 0), 0);
      const direct = [style.color, style.finish, ...style.occasion, ...style.tags, ...taxonomyTokens].reduce(
        (total, token) => total + (normalized.includes(token.toLowerCase()) ? 3 : 0),
        0,
      );
      return { style, score: score + direct };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((item) => item.style);
  return (scored.length ? scored : inventoryStyles).slice(0, limit);
}
