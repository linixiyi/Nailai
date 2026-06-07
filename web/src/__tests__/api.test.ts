import { describe, it, expect } from "vitest";
import { resolveApiAssetUrl } from "@/lib/api";

describe("api helpers", () => {
  describe("resolveApiAssetUrl", () => {
    it("returns empty string for falsy input", () => {
      expect(resolveApiAssetUrl(null)).toBe("");
      expect(resolveApiAssetUrl(undefined)).toBe("");
      expect(resolveApiAssetUrl("")).toBe("");
    });

    it("prepends base URL when path starts with /", () => {
      // NEXT_PUBLIC_API_BASE_URL is empty in test → base is ""
      const result = resolveApiAssetUrl("/generated/test.png");
      expect(result).toBe("/generated/test.png");
    });

    it("returns absolute URLs unchanged", () => {
      const result = resolveApiAssetUrl("https://example.com/img.png");
      expect(result).toBe("https://example.com/img.png");
    });
  });
});
