import type { NailStyle } from "./types";

export function shouldRotateStyleImage(style: NailStyle | null | undefined) {
  if (!style) return false;
  if (style.source_batch === "merchant-upload") return false;
  if (style.id.startsWith("custom-style-")) return false;
  return true;
}

export function styleImageOrientationClass(style: NailStyle | null | undefined) {
  return shouldRotateStyleImage(style) ? " rotate-180" : "";
}
