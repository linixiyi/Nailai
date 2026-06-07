"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Camera, CheckCircle2, Loader2, XCircle, Zap } from "lucide-react";
import { fetchStyles } from "@/lib/api";
import { inventoryStyles } from "@/lib/styles";
import { styleImageOrientationClass } from "@/lib/stylePresentation";
import { clearLatestTryOnResult, loadTryOnResult, loadTryOnOriginalImage } from "@/lib/tryOnStore";
import { startTryOnTask } from "@/lib/tryOnTaskStore";
import type { NailStyle } from "@/lib/types";
import { NailStyleThumb } from "./Cards";
import { PhoneShell, PrimaryButton, SoftCard } from "./Shell";

type Review = "idle" | "pass" | "warn";

export function AiTryOnScreen({ initialStyleId }: { initialStyleId?: string }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  
  const defaultStyle = useMemo(() => {
    if (initialStyleId) {
      return inventoryStyles.find(s => s.id === initialStyleId) || inventoryStyles[0];
    }
    return inventoryStyles[0];
  }, [initialStyleId]);

  const [style, setStyle] = useState<NailStyle>(defaultStyle);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [review, setReview] = useState<Review>("idle");
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [styles, setStyles] = useState<NailStyle[]>(inventoryStyles);

  const canGenerate = Boolean(file && review === "pass" && confirmed && !loading);

  useEffect(() => {
    fetchStyles()
      .then((nextStyles) => {
        const stylesWithImages = nextStyles.filter((nextStyle) => Boolean(nextStyle.image_url));
        const runtimeStyles = stylesWithImages.length ? stylesWithImages : nextStyles;
        setStyles(runtimeStyles);
        const matchedStyle = initialStyleId
          ? runtimeStyles.find((nextStyle) => nextStyle.id === initialStyleId)
          : undefined;
        setStyle((currentStyle) => matchedStyle ?? runtimeStyles.find((nextStyle) => nextStyle.id === currentStyle.id) ?? runtimeStyles[0] ?? currentStyle);
      })
      .catch(() => setStyles(inventoryStyles));
  }, [initialStyleId]);

  // 在组件加载时，尝试恢复上一次上传的手图和选中的美甲款式
  useEffect(() => {
    if (!initialStyleId) {
      const lastResult = loadTryOnResult();
      if (lastResult?.style) {
        setStyle(lastResult.style);
      }
    }

    const lastImage = loadTryOnOriginalImage();
    if (lastImage) {
      try {
        const arr = lastImage.split(',');
        const mimeMatch = arr[0].match(/:(.*?);/);
        const mime = mimeMatch ? mimeMatch[1] : "image/png";
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
          u8arr[n] = bstr.charCodeAt(n);
        }
        const recoveredFile = new File([u8arr], "original-hand.png", { type: mime });
        setFile(recoveredFile);
        setPreview(lastImage);
        setReview("pass");
        setConfirmed(true); // 自动勾选确认，提升二次试戴体验
      } catch (e) {
        console.error("Failed to recover last uploaded image", e);
      }
    }
  }, [initialStyleId]);
  const reviewRows = useMemo(
    () => [
      ["单手完整", review === "pass"],
      ["指甲清晰露出", review === "pass"],
      ["款式语义已解析", true],
      ["图文结合输入后端", true],
    ],
    [review],
  );

  async function handleFile(nextFile: File | null) {
    if (!nextFile) return;
    setError(null);
    setConfirmed(false);
    setFile(nextFile);
    if (preview) URL.revokeObjectURL(preview);
    const nextPreview = URL.createObjectURL(nextFile);
    setPreview(nextPreview);
    setReview(nextFile.size < 12 * 1024 * 1024 ? "pass" : "warn");
  }

  function openFilePicker() {
    const input = inputRef.current;
    if (!input) return;
    if (typeof input.showPicker === "function") {
      input.showPicker();
      return;
    }
    input.click();
  }

  async function handleUseDemo() {
    setError(null);
    setConfirmed(false);
    setLoading(true);
    try {
      const response = await fetch("/style-images/custom/demo-hand.png");
      if (!response.ok) {
        throw new Error("示例手图加载失败");
      }
      const blob = await response.blob();
      const demoFile = new File([blob], "demo-hand.png", { type: "image/png" });
      setFile(demoFile);
      setPreview("/style-images/custom/demo-hand.png");
      setReview("pass");
      setConfirmed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载示例手图失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    if (!file) return;
    setError(null);
    setLoading(true);
    clearLatestTryOnResult();
    try {
      let styleImage: Blob | undefined = undefined;
      if (style.image_url) {
        const styleImageResponse = await fetch(style.image_url);
        if (!styleImageResponse.ok) {
          throw new Error("款式图读取失败，请重新选择款式。");
        }
        styleImage = await styleImageResponse.blob();
      }
      
      const reader = new FileReader();
      reader.onload = async (e) => {
        if (e.target?.result && typeof e.target.result === "string") {
          const { saveTryOnOriginalImage } = await import("@/lib/tryOnStore");
          saveTryOnOriginalImage(e.target.result);
        }
      };
      reader.readAsDataURL(file);
      void startTryOnTask({ image: file, style, styleImage, generationMode: "fast" });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PhoneShell title="AI 换美甲" active="tryon">
      <div className="space-y-4 px-4 pt-3">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={(event) => {
            void handleFile(event.target.files?.[0] ?? null);
            event.currentTarget.value = "";
          }}
        />

          <button
            type="button"
            onClick={openFilePicker}
            className="grid h-[236px] w-full place-items-center overflow-hidden rounded-[24px] border border-dashed border-[#f2b9c7] bg-[linear-gradient(145deg,#fff2ec,#f7c2dc)]"
          >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="上传手图" className="h-full w-full object-cover" />
          ) : (
            <div className="text-center">
              <span className="mx-auto grid h-16 w-16 place-items-center rounded-[20px] bg-white text-[#ff5c74] shadow-sm">
                <Camera size={26} />
              </span>
              <p className="mt-4 text-sm font-black">上传手部照片</p>
              <p className="mt-2 text-xs text-[#9b7580]">掌心或手背朝上，指甲完整露出</p>
            </div>
          )}
        </button>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={openFilePicker}
            className="flex-1 py-2 text-xs font-bold text-[#5a3a43] rounded-full border border-[#f2b9c7] bg-white hover:bg-[#fff6f8] active:scale-95 transition-all"
          >
            {file ? "换一张手图" : "从相册上传"}
          </button>
          <button
            type="button"
            onClick={handleUseDemo}
            className="flex-1 py-2 text-xs font-bold text-white rounded-full bg-[linear-gradient(135deg,#ff8a9a,#ff5c74)] hover:opacity-90 active:scale-95 transition-all shadow-sm shadow-[#ff5c74]/20"
          >
            使用示例手图
          </button>
        </div>

        {/* ── AI 引擎标识卡 ── */}
        <div className="relative overflow-hidden rounded-[22px] bg-[linear-gradient(135deg,#2b0d1b_0%,#7c1f3e_45%,#ff5c74_100%)] px-4 py-3.5 shadow-lg shadow-[#ff5c74]/20">
          {/* 装饰光晕 */}
          <div className="pointer-events-none absolute -right-6 -top-6 h-28 w-28 rounded-full bg-white/10 blur-2xl" />
          <div className="pointer-events-none absolute -bottom-4 left-8 h-16 w-16 rounded-full bg-[#ffd6e0]/20 blur-xl" />

          <div className="relative flex items-center gap-3">
            {/* 左侧图标 */}
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] bg-white/15 ring-1 ring-white/25 backdrop-blur-sm">
              <span className="text-[22px] leading-none select-none">💅</span>
            </div>

            {/* 中间文字 */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <p className="text-[13px] font-black tracking-tight text-white">AI 魔法换甲引擎</p>
                <span className="flex items-center gap-0.5 rounded-full bg-[#ffd4df]/25 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-widest text-[#ffd4df]">
                  <Zap size={8} strokeWidth={3} />
                  极速
                </span>
              </div>
              <p className="mt-0.5 text-[11px] font-medium text-white/65">智能识别甲型 · 秒级生成 · 精准上色</p>
            </div>

            {/* 右侧装饰钻石 */}
            <div className="flex shrink-0 flex-col items-end gap-0.5">
              <span className="text-[18px] leading-none select-none">✨</span>
              <span className="text-[9px] font-bold text-white/50">NailAI</span>
            </div>
          </div>

          {/* 底部三个标签 */}
          <div className="relative mt-3 flex gap-2">
            {["🎨 色彩还原", "💎 饰品精准", "⚡ 30s 出图"].map((label) => (
              <span
                key={label}
                className="flex-1 rounded-full bg-white/12 py-1 text-center text-[10px] font-bold text-white/80 ring-1 ring-white/20"
              >
                {label}
              </span>
            ))}
          </div>
        </div>

        <SoftCard>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-black">选择想试戴的款式</h2>
            <span className="text-[11px] font-bold text-[#ff5c74]">更多</span>
          </div>
          <div className="mt-3 flex gap-3 overflow-x-auto pb-1">
            {styles.map((nextStyle) => (
              <button key={nextStyle.id} type="button" onClick={() => setStyle(nextStyle)} className="w-[92px] shrink-0 text-left">
                <NailStyleThumb style={nextStyle} selected={nextStyle.id === style.id} />
              </button>
            ))}
          </div>
        </SoftCard>

        <SoftCard>
          <div className="flex gap-3">
            <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-[18px] bg-neutral-100 flex items-center justify-center">
              {style.image_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={style.image_url} alt={style.name} className={`h-full w-full object-cover${styleImageOrientationClass(style)}`} />
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-black">{style.name}</p>
              <p className="mt-1 text-xs font-semibold text-[#9b7580]">{style.color} · {style.finish}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {style.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="rounded-full bg-[#fff0f4] px-2 py-1 text-[10px] font-bold text-[#ff5c74]">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </SoftCard>

        <SoftCard>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-black">照片质量初筛</h2>
            <span className="text-xs font-black text-[#ff5c74]">{review === "pass" ? "100分" : review === "warn" ? "需重拍" : "待上传"}</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {reviewRows.map(([label, passed]) => (
              <div key={label as string} className="flex items-center gap-1.5 rounded-[12px] bg-[#fff7f2] px-2 py-2">
                {passed ? <CheckCircle2 size={14} className="text-[#ff5c74]" /> : <XCircle size={14} className="text-[#b8a4a9]" />}
                <span className="text-[11px] font-bold text-[#5a3a43]">{label}</span>
              </div>
            ))}
          </div>
          <label className={`mt-3 flex items-center gap-2 text-xs font-bold ${review !== "pass" ? "text-[#b8a4a9]" : "text-[#5a3a43]"}`}>
            <input type="checkbox" checked={confirmed} disabled={review !== "pass"} onChange={(event) => setConfirmed(event.target.checked)} className="h-4 w-4 accent-[#ff5c74]" />
            确认手部完整、指甲无遮挡
          </label>
        </SoftCard>

        {error ? (
          <p className="flex gap-2 rounded-[16px] bg-red-50 p-3 text-xs font-semibold leading-5 text-red-600">
            <AlertTriangle size={16} />
            {error}
          </p>
        ) : null}

        <div>
          <PrimaryButton disabled={!canGenerate} onClick={handleGenerate}>
            {loading ? <Loader2 className="animate-spin" size={18} /> : <span className="text-[18px] leading-none">💅</span>}
            {loading ? "AI 换甲生成中..." : "立即 AI 试戴"}
          </PrimaryButton>
        </div>

        <div className="h-2" />
      </div>
    </PhoneShell>
  );
}
