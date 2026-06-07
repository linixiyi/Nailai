"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Camera,
  Check,
  CheckCircle2,
  ChevronLeft,
  Hand,
  Heart,
  Home,
  ImageUp,
  Loader2,
  MapPin,
  MessageCircle,
  Menu,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  XCircle,
  User,
} from "lucide-react";
import { motion } from "framer-motion";
import { styleImageOrientationClass } from "@/lib/stylePresentation";
import { nailStyles, searchStyles } from "@/lib/styles";
import type { ChatResponse, NailStyle, TryOnResponse } from "@/lib/types";

type Tab = "try-on" | "chat" | "styles";
type UploadReviewStatus = "idle" | "checking" | "pass" | "warn";
type UploadCheck = {
  id: string;
  label: string;
  description: string;
  passed: boolean;
};
type UploadReview = {
  status: UploadReviewStatus;
  score: number;
  message: string;
  checks: UploadCheck[];
  metrics?: {
    width: number;
    height: number;
    brightness: number;
    contrast: number;
    sharpness: number;
  };
};

const emptyUploadReview: UploadReview = {
  status: "idle",
  score: 0,
  message: "上传后会自动检查基础画质。",
  checks: [],
};

const handPhotoRules = [
  {
    label: "单手入镜",
    description: "保证手掌和手指完整，避免多人同框",
    good: true,
    icon: Hand,
  },
  {
    label: "手部完整",
    description: "手掌和五指尽量都在画面内",
    good: false,
    icon: Hand,
  },
  {
    label: "指甲完整",
    description: "不要遮挡甲面，指尖不要出框",
    good: false,
    icon: ShieldCheck,
  },
  {
    label: "手势自然",
    description: "避免握拳、夸张美甲或多手重叠",
    good: false,
    icon: RotateCcw,
  },
];

function clsx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function StyleVisual({ style }: { style: NailStyle }) {
  const [first, second, third] = style.palette;
  if (style.image_url) {
    return (
      <div className="relative h-28 overflow-hidden rounded-md border border-black/10 bg-gradient-to-b from-neutral-100 to-neutral-200">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={style.image_url}
          alt={style.name}
          className={`h-full w-full object-contain p-1${styleImageOrientationClass(style)}`}
          loading="lazy"
        />
      </div>
    );
  }
  return (
    <div
      className="relative h-28 overflow-hidden rounded-md border border-black/10"
      style={{ background: `linear-gradient(135deg, ${second}, #ffffff 46%, ${first})` }}
    >
      <div className="absolute inset-x-4 bottom-4 flex items-end justify-between">
        {style.palette.concat(style.palette.slice(0, 2)).map((color, index) => (
          <span
            key={`${style.id}-${index}`}
            className="h-12 w-7 rounded-b-2xl rounded-t-full border border-white/80 shadow-sm"
            style={{ background: index % 2 ? color : third }}
          />
        ))}
      </div>
    </div>
  );
}

function StyleCard({
  style,
  selected,
  onSelect,
}: {
  style: NailStyle;
  selected: boolean;
  onSelect: (style: NailStyle) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(style)}
      className={clsx(
        "group rounded-lg border bg-white p-2 text-left transition hover:-translate-y-0.5 hover:border-neutral-900 hover:shadow-md",
        selected ? "border-neutral-900 shadow-md" : "border-neutral-200",
      )}
    >
      <StyleVisual style={style} />
      <div className="mt-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-950">{style.name}</p>
          <p className="mt-1 text-xs text-neutral-500">{style.color} · {style.finish}</p>
          {style.stock_total ? (
            <p className="mt-1 text-[11px] text-neutral-500">
              库存 {Math.max(style.stock_total - (style.stock_reserved ?? 0), 0)} / {style.stock_total}
            </p>
          ) : null}
        </div>
        {selected ? (
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-neutral-950 text-white">
            <Check size={14} />
          </span>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {style.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="rounded-full bg-neutral-100 px-2 py-1 text-[11px] text-neutral-600">
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
}

async function loadImage(file: File) {
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const nextImage = new Image();
      nextImage.onload = () => resolve(nextImage);
      nextImage.onerror = () => reject(new Error("图片读取失败，请换一张照片。"));
      nextImage.src = url;
    });
    return { image, url };
  } catch (error) {
    URL.revokeObjectURL(url);
    throw error;
  }
}

async function reviewHandPhoto(file: File): Promise<{ review: UploadReview; previewUrl: string }> {
  if (!file.type.startsWith("image/")) {
    throw new Error("请上传 JPG、PNG 或 HEIC 等图片文件。");
  }
  if (file.size > 12 * 1024 * 1024) {
    throw new Error("图片超过 12MB，请压缩后再上传。");
  }

  const { image, url } = await loadImage(file);
  const width = image.naturalWidth;
  const height = image.naturalHeight;
  const ratio = width / height;
  const sampleSize = 96;
  const canvas = document.createElement("canvas");
  canvas.width = sampleSize;
  canvas.height = sampleSize;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("浏览器暂时无法分析图片，请换个浏览器或重试。");
  context.drawImage(image, 0, 0, sampleSize, sampleSize);
  const data = context.getImageData(0, 0, sampleSize, sampleSize).data;
  const grayscale: number[] = [];
  let brightness = 0;
  for (let index = 0; index < data.length; index += 4) {
    const value = 0.299 * data[index] + 0.587 * data[index + 1] + 0.114 * data[index + 2];
    grayscale.push(value);
    brightness += value;
  }
  brightness /= grayscale.length;
  const contrast = Math.sqrt(
    grayscale.reduce((total, value) => total + (value - brightness) ** 2, 0) / grayscale.length,
  );
  const checks: UploadCheck[] = [
    {
      id: "resolution",
      label: "分辨率足够",
      description: `${width} x ${height}，建议短边不低于 480px`,
      passed: Math.min(width, height) >= 480,
    },
    {
      id: "crop",
      label: "画面不易裁切手部",
      description: "照片比例自然，适合保留完整单手",
      passed: ratio >= 0.55 && ratio <= 1.9,
    },
    {
      id: "exposure",
      label: "曝光正常",
      description: "允许轻微偏暗，避免极暗/极曝即可",
      passed: brightness >= 40 && brightness <= 235 && contrast >= 12,
    },
  ];
  const passedCount = checks.filter((check) => check.passed).length;
  const score = Math.round((passedCount / checks.length) * 100);
  const status: UploadReviewStatus = passedCount === checks.length ? "pass" : "warn";
  const message =
    status === "pass"
      ? "图片基础检查通过，请再确认单手完整、指甲可见、手势自然。"
      : "图片可继续尝试，但效果可能受影响；有空可换更清晰照片。";

  return {
    previewUrl: url,
    review: {
      status,
      score,
      message,
      checks,
      metrics: {
        width,
        height,
        brightness: Math.round(brightness),
        contrast: Math.round(contrast),
        sharpness: 0,
      },
    },
  };
}

export default function NailAIApp() {
  const [tab, setTab] = useState<Tab>("try-on");
  const [query, setQuery] = useState("");
  const [chatInput, setChatInput] = useState("下周婚礼，想要显白但不要太夸张");
  const [chat, setChat] = useState<ChatResponse | null>(null);
  const [selectedStyle, setSelectedStyle] = useState<NailStyle>(nailStyles[0]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [tryOn, setTryOn] = useState<TryOnResponse | null>(null);
  const [loadingTryOn, setLoadingTryOn] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadReview, setUploadReview] = useState<UploadReview>(emptyUploadReview);
  const [manualPhotoConfirmed, setManualPhotoConfirmed] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const filteredStyles = useMemo(() => searchStyles(query, 12), [query]);

  async function handleFile(nextFile: File | null) {
    if (!nextFile) return;
    setUploadReview({ ...emptyUploadReview, status: "checking", message: "正在检查图片清晰度和基础构图..." });
    setManualPhotoConfirmed(false);
    setTryOn(null);
    setError(null);
    try {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const result = await reviewHandPhoto(nextFile);
      setFile(nextFile);
      setPreviewUrl(result.previewUrl);
      setUploadReview(result.review);
      if (result.review.status === "warn") {
        setError("图片质量一般，也可以继续试戴；想要更稳效果可换一张。");
      }
    } catch (err) {
      setFile(null);
      setPreviewUrl(null);
      setUploadReview(emptyUploadReview);
      setError(err instanceof Error ? err.message : "图片检查失败，请重试。");
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function submitTryOn() {
    if (!file) {
      setError("请先上传一张手部照片。");
      return;
    }
    if (uploadReview.status !== "pass" || !manualPhotoConfirmed) {
      setError("请上传清晰完整的单手照片，并确认手势符合要求后再生成试戴。");
      return;
    }
    setLoadingTryOn(true);
    setError(null);
    const formData = new FormData();
    formData.append("image", file);
    formData.append("style_id", selectedStyle.id);
    formData.append("style_payload", JSON.stringify(selectedStyle));
    if (selectedStyle.image_url) {
      try {
        const styleImageResponse = await fetch(selectedStyle.image_url);
        if (styleImageResponse.ok) {
          const styleBlob = await styleImageResponse.blob();
          formData.append("style_image", styleBlob, `${selectedStyle.id}.png`);
        }
      } catch {
        // Continue without style image fallback.
      }
    }
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120_000);
      const response = await fetch("/api/try-on", { method: "POST", body: formData, signal: controller.signal });
      clearTimeout(timeoutId);
      if (!response.ok) throw new Error(await response.text());
      setTryOn(await response.json());
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("生成超时（120秒），请重试一次。");
      } else {
        setError(err instanceof Error ? err.message : "生成失败，请稍后重试。");
      }
    } finally {
      setLoadingTryOn(false);
    }
  }

  async function submitChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoadingChat(true);
    setError(null);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: chatInput, selected_style_ids: [selectedStyle.id] }),
      });
      if (!response.ok) throw new Error(await response.text());
      const data: ChatResponse = await response.json();
      setChat(data);
      if (data.recommended_styles[0]) setSelectedStyle(data.recommended_styles[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "推荐失败，请稍后重试。");
    } finally {
      setLoadingChat(false);
    }
  }

  const canGenerateTryOn = Boolean(file && uploadReview.status === "pass" && manualPhotoConfirmed && !loadingTryOn);
  const qualityText = tryOn
    ? `置信度 ${(tryOn.hand_confidence * 100).toFixed(0)}% · ${tryOn.channel}`
    : uploadReview.status === "pass"
      ? "照片可用，确认后即可生成"
      : "上传手图后开始试戴";
  const previewImage = tryOn?.result_image_url ?? previewUrl;

  return (
    <main className="min-h-screen bg-[#f6f2ec] bg-[linear-gradient(#ebe4dc_1px,transparent_1px),linear-gradient(90deg,#ebe4dc_1px,transparent_1px)] bg-[size:28px_28px] px-4 py-6 text-[#25161b]">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[390px_minmax(0,1fr)]">
        <section className="hidden rounded-lg bg-[linear-gradient(145deg,#ffd0c5,#f4a9c9)] p-8 shadow-sm lg:block">
          <div className="flex items-center gap-2 text-2xl font-black">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-[#ff5c74] text-white shadow-sm">●</span>
            NailAI
          </div>
          <h1 className="mt-24 text-7xl font-black leading-[0.88] tracking-normal">Nail<br />AI</h1>
          <p className="mt-5 text-xl font-bold">指尖一秒，换上新美甲</p>
          <p className="mt-2 max-w-sm text-sm leading-6 text-[#6d4b56]">AI 试戴、智能推荐、DIY 悬赏，一站完成从灵感到到店的美甲体验。</p>
          <div className="mt-10 flex gap-3">
            {nailStyles.slice(0, 6).map((style) => (
              <button
                key={style.id}
                type="button"
                onClick={() => setSelectedStyle(style)}
                className="h-16 w-14 overflow-hidden rounded-lg bg-white/70 p-1 shadow-sm"
              >
                <StyleVisual style={style} />
              </button>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-[390px] overflow-hidden rounded-[34px] border border-white/80 bg-[#fff9f5] shadow-2xl shadow-[#e5b4bf]/40">
          <div className="relative min-h-[844px] pb-24">
            <div className="absolute left-1/2 top-3 z-20 h-7 w-32 -translate-x-1/2 rounded-full bg-black" />
            <header className="relative overflow-hidden bg-[linear-gradient(145deg,#ffd0c5,#f3a4c7)] px-5 pb-5 pt-12">
              <div className="flex items-center justify-between">
                <button type="button" className="grid h-9 w-9 place-items-center rounded-full bg-white/70 text-[#3a2029]">
                  <ChevronLeft size={18} />
                </button>
                <div className="flex items-center gap-1.5 text-sm font-black">
                  <span className="h-4 w-4 rounded-full bg-[#ff5c74]" />
                  NailAI
                </div>
                <button type="button" className="grid h-9 w-9 place-items-center rounded-full bg-white/70 text-[#3a2029]">
                  <Menu size={18} />
                </button>
              </div>

              {tab === "try-on" ? (
                <div className="mt-8">
                  <h1 className="text-4xl font-black leading-[0.95] tracking-normal">指尖一秒<br />换上新美甲</h1>
                  <p className="mt-3 text-xs font-medium text-[#7b4c5b]">上传手部照片，AI 复刻所选美甲款式。</p>
                  <div className="mt-5 flex h-11 items-center gap-2 rounded-full bg-white/85 px-4 shadow-sm">
                    <Search size={16} className="text-[#ff5c74]" />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="试试“红黑棋盘 蜘蛛”"
                      className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[#b88795]"
                    />
                    <button type="button" className="grid h-7 w-7 place-items-center rounded-full bg-[#ff5c74] text-white">
                      <Sparkles size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-8">
                  <h1 className="text-3xl font-black tracking-normal">{tab === "chat" ? "Nail 小助手" : "美甲款式库"}</h1>
                  <p className="mt-2 text-xs font-medium text-[#7b4c5b]">
                    {tab === "chat" ? "告诉我场合和偏好，我帮你挑款。" : "选择款式后回到首页生成试戴。"}
                  </p>
                </div>
              )}
            </header>

            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
            />

            <div className="-mt-4 space-y-4 px-4">
              {tab === "try-on" ? (
                <>
                  <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg bg-[#2b0d1b] p-4 text-white shadow-xl shadow-[#d68fa1]/30">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold text-[#d8bdd1]">P0 · AI 换美甲</p>
                        <h2 className="mt-1 text-xl font-black tracking-normal">{selectedStyle.name}</h2>
                        <p className="mt-1 text-xs text-[#d8bdd1]">{qualityText}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => fileRef.current?.click()}
                        className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white text-[#ff5c74]"
                      >
                        <ImageUp size={18} />
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => fileRef.current?.click()}
                      className="mt-4 grid h-72 w-full place-items-center overflow-hidden rounded-lg bg-[radial-gradient(circle_at_50%_20%,#4a1830,#180610_72%)]"
                    >
                      {previewImage ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={previewImage} alt={tryOn ? "AI try-on result" : "Uploaded hand preview"} className="h-full w-full object-contain" />
                      ) : (
                        <div className="flex flex-col items-center gap-3 text-center">
                          <span className="grid h-16 w-16 place-items-center rounded-full bg-white/10 text-white">
                            <Camera size={24} />
                          </span>
                          <span className="text-sm font-semibold">上传手部照片</span>
                          <span className="max-w-[220px] text-xs leading-5 text-[#d8bdd1]">单手完整入镜，指甲露出，试戴效果更稳。</span>
                        </div>
                      )}
                    </button>

                    <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
                      {[selectedStyle, ...filteredStyles.filter((style) => style.id !== selectedStyle.id).slice(0, 5)].map((style) => (
                        <button
                          key={style.id}
                          type="button"
                          onClick={() => {
                            setSelectedStyle(style);
                            setTryOn(null);
                          }}
                          className={clsx(
                            "h-16 w-16 shrink-0 overflow-hidden rounded-md border-2 bg-white/10 p-1",
                            style.id === selectedStyle.id ? "border-[#ffccdc]" : "border-transparent",
                          )}
                        >
                          <StyleVisual style={style} />
                        </button>
                      ))}
                    </div>
                  </motion.section>

                  <section className="rounded-lg bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h2 className="text-base font-black">选择要试戴的款式</h2>
                        <p className="mt-1 text-xs text-[#9b7580]">{selectedStyle.color} · {selectedStyle.finish} · {selectedStyle.price_level}</p>
                      </div>
                      <button type="button" onClick={() => setTab("styles")} className="text-xs font-bold text-[#ff5c74]">
                        更多
                      </button>
                    </div>
                    <div className="mt-3 flex gap-3 overflow-x-auto pb-1">
                      {filteredStyles.slice(0, 8).map((style) => (
                        <button
                          key={style.id}
                          type="button"
                          onClick={() => {
                            setSelectedStyle(style);
                            setTryOn(null);
                          }}
                          className={clsx("w-24 shrink-0 rounded-lg border p-1 text-left", style.id === selectedStyle.id ? "border-[#ff5c74] bg-[#fff0f4]" : "border-[#f4e2e7] bg-white")}
                        >
                          <StyleVisual style={style} />
                          <p className="mt-2 line-clamp-1 px-1 text-xs font-bold">{style.name}</p>
                          <p className="px-1 pb-1 text-[10px] text-[#9b7580]">已选 · {style.finish}</p>
                        </button>
                      ))}
                    </div>
                  </section>

                  <section className="rounded-lg bg-white p-4 shadow-sm">
                    <div className="flex items-start gap-3">
                      {uploadReview.status === "checking" ? (
                        <Loader2 className="mt-1 animate-spin text-[#ff5c74]" size={18} />
                      ) : uploadReview.status === "pass" ? (
                        <CheckCircle2 className="mt-1 text-emerald-500" size={18} />
                      ) : uploadReview.status === "warn" ? (
                        <AlertTriangle className="mt-1 text-amber-500" size={18} />
                      ) : (
                        <ShieldCheck className="mt-1 text-[#ff5c74]" size={18} />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h2 className="text-sm font-black">手部照片要求</h2>
                          <span className="text-xs font-bold text-[#9b7580]">{uploadReview.score ? `${uploadReview.score}分` : "待上传"}</span>
                        </div>
                        <p className="mt-1 text-xs leading-5 text-[#8f6b75]">{uploadReview.message}</p>
                        <div className="mt-3 grid grid-cols-2 gap-2">
                          {(uploadReview.checks.length ? uploadReview.checks : handPhotoRules.slice(0, 4).map((rule) => ({
                            id: rule.label,
                            label: rule.label,
                            description: rule.description,
                            passed: rule.good,
                          }))).map((check) => (
                            <div key={check.id} className="flex items-center gap-1.5 rounded-md bg-[#fff6f2] px-2 py-2">
                              {check.passed ? <CheckCircle2 size={13} className="text-[#ff5c74]" /> : <XCircle size={13} className="text-[#b8a4a9]" />}
                              <span className="truncate text-[11px] font-semibold text-[#5a3a43]">{check.label}</span>
                            </div>
                          ))}
                        </div>
                        <label className={clsx("mt-3 flex items-center gap-2 text-xs font-semibold text-[#5a3a43]", uploadReview.status !== "pass" && "opacity-50")}>
                          <input
                            type="checkbox"
                            checked={manualPhotoConfirmed}
                            disabled={uploadReview.status !== "pass"}
                            onChange={(event) => setManualPhotoConfirmed(event.target.checked)}
                            className="h-4 w-4 accent-[#ff5c74]"
                          />
                          确认手部和指甲完整可见
                        </label>
                      </div>
                    </div>
                  </section>

                  {error ? <p className="rounded-lg bg-red-50 p-3 text-xs font-semibold leading-5 text-red-600">{error}</p> : null}

                  <div className="sticky bottom-20 z-10">
                    <button
                      type="button"
                      onClick={submitTryOn}
                      disabled={!canGenerateTryOn}
                      className="flex h-14 w-full items-center justify-center gap-2 rounded-full bg-[#ff5c74] text-sm font-black text-white shadow-xl shadow-[#ff5c74]/35 disabled:bg-[#e9d5da]"
                    >
                      {loadingTryOn ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
                      {loadingTryOn ? "AI 正在换甲..." : "开始 AI 试戴 · 约 5 秒"}
                    </button>
                  </div>
                </>
              ) : null}

              {tab === "chat" ? (
                <section className="rounded-lg bg-white p-4 shadow-sm">
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg bg-[#27101c] p-4 text-white">
                    <p className="text-xs font-semibold text-[#ffb8c7]">Nail 小助手</p>
                    <p className="mt-2 text-sm leading-6">{chat?.reply ?? "告诉我场合、肤色偏好和风格，我帮你挑适合试戴的款式。"}</p>
                  </motion.div>
                  {chat ? (
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      {chat.recommended_styles.slice(0, 4).map((style) => (
                        <StyleCard key={style.id} style={style} selected={style.id === selectedStyle.id} onSelect={setSelectedStyle} />
                      ))}
                    </div>
                  ) : null}
                  <form onSubmit={submitChat} className="mt-4 flex gap-2">
                    <input
                      value={chatInput}
                      onChange={(event) => setChatInput(event.target.value)}
                      className="h-12 min-w-0 flex-1 rounded-full border border-[#f4d6de] px-4 text-sm outline-none focus:border-[#ff5c74]"
                    />
                    <button type="submit" disabled={loadingChat} className="grid h-12 w-12 place-items-center rounded-full bg-[#ff5c74] text-white disabled:opacity-60">
                      {loadingChat ? <Loader2 className="animate-spin" size={16} /> : <MessageCircle size={16} />}
                    </button>
                  </form>
                </section>
              ) : null}

              {tab === "styles" ? (
                <section className="space-y-3">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#bb8b98]" size={16} />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="搜索款式"
                      className="h-12 w-full rounded-full border border-[#f4d6de] bg-white pl-10 pr-4 text-sm outline-none focus:border-[#ff5c74]"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {filteredStyles.map((style) => (
                      <StyleCard key={style.id} style={style} selected={style.id === selectedStyle.id} onSelect={(nextStyle) => {
                        setSelectedStyle(nextStyle);
                        setTryOn(null);
                        setTab("try-on");
                      }} />
                    ))}
                  </div>
                </section>
              ) : null}
            </div>

            <nav className="absolute inset-x-0 bottom-0 z-20 border-t border-[#f5dbe2] bg-white/95 px-6 pb-5 pt-3 backdrop-blur">
              <div className="grid grid-cols-4 gap-2">
                {[
                  ["try-on", "首页", Home],
                  ["chat", "AI推荐", MessageCircle],
                  ["styles", "DIY悬赏", Heart],
                  ["styles", "我的", User],
                ].map(([value, label, Icon]) => {
                  const NavIcon = Icon as typeof Home;
                  const active = tab === value || (label === "我的" && false);
                  return (
                    <button
                      key={label as string}
                      type="button"
                      onClick={() => setTab(value as Tab)}
                      className={clsx("flex flex-col items-center gap-1 text-[10px] font-bold", active ? "text-[#ff5c74]" : "text-[#b69aa2]")}
                    >
                      <NavIcon size={18} />
                      {label as string}
                    </button>
                  );
                })}
              </div>
            </nav>
          </div>
        </section>

        <aside className="hidden lg:block">
          <div className="rounded-lg bg-[#fff9f5] p-6 shadow-sm">
            <h2 className="text-xl font-black">Design System</h2>
            <div className="mt-5 grid grid-cols-4 gap-3">
              {["#ff5c74", "#ff7b68", "#4a102c", "#1f1014", "#f7a8b8", "#f7dcc9", "#ffeec7", "#78b89a"].map((color) => (
                <span key={color} className="h-16 rounded-md border border-black/5" style={{ background: color }} />
              ))}
            </div>
            <h3 className="mt-8 text-sm font-black uppercase text-[#8d6872]">当前方案</h3>
            <div className="mt-3 rounded-lg bg-white p-4 shadow-sm">
              <StyleVisual style={selectedStyle} />
              <p className="mt-4 text-base font-black">{selectedStyle.name}</p>
              <p className="mt-1 text-sm text-[#8d6872]">{selectedStyle.occasion.join(" / ")} · {selectedStyle.price_level}</p>
              <div className="mt-3 flex items-center gap-1 text-[#ffb600]">
                {Array.from({ length: 5 }).map((_, index) => <Star key={index} size={14} fill="currentColor" />)}
              </div>
              <div className="mt-4 flex gap-2">
                <button type="button" className="flex h-10 flex-1 items-center justify-center gap-2 rounded-full bg-[#ff5c74] text-sm font-black text-white">
                  <MapPin size={15} />
                  找可做店铺
                </button>
                <button type="button" className="grid h-10 w-10 place-items-center rounded-full border border-[#f4d6de] text-[#ff5c74]">
                  <Save size={15} />
                </button>
              </div>
            </div>
            {error ? <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
          </div>
        </aside>
      </div>
    </main>
  );
}
