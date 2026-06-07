"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  ClipboardList,
  ImagePlus,
  Loader2,
  Palette,
  RefreshCw,
  Send,
  Sparkles,
  Wand2,
} from "lucide-react";
import { fetchLatestDiyBountyGeneration, postDiyBountyPublish } from "@/lib/api";
import { loadDiyBountyHistory, type DiyBountyHistoryItem } from "@/lib/historyStore";
import { startDiyTask } from "@/lib/diyTaskStore";
import type {
  DiyBountyAnswers,
  DiyBountyGenerateResponse,
  DiyBountyPublishResponse,
  DiyBountyVariant,
} from "@/lib/types";
import { PhoneShell, PrimaryButton, SoftCard } from "./Shell";

const singleChoiceGroups = [
  { key: "occasion", title: "使用场景", options: ["通勤", "约会", "婚礼", "派对", "节日", "日常", "职场", "度假", "拍摄"] },
  { key: "nail_length", title: "甲片长度", options: ["超短甲", "短甲", "中短甲", "中长甲", "长甲", "超长甲"] },
  { key: "nail_shape", title: "甲型", options: ["方圆", "圆形", "椭圆", "杏仁", "尖形", "梯形", "芭蕾", "棺材型"] },
  { key: "style", title: "整体风格", options: ["简约", "甜美", "轻奢", "个性", "国风", "韩系", "日系", "法式", "Y2K", "暗黑"] },
  { key: "budget", title: "预算", options: ["¥50-100", "¥100-150", "¥150-250", "¥250-350", "¥350-500", "¥500+"] },
  { key: "change_policy", title: "改动范围", options: ["严格复刻", "可轻微改色", "可调整复杂度", "允许自由发挥"] },
] as const;

const multiChoiceGroups = [
  { key: "colors", title: "主色", options: ["奶茶", "裸粉", "酒红", "黑白", "蓝紫", "抹茶", "银色", "珊瑚橙", "雾霾蓝", "香芋紫", "焦糖棕", "蜜桃粉"] },
  { key: "decorations", title: "装饰工艺", options: ["细闪", "法式边", "贝壳片", "猫眼", "手绘", "立体饰品", "珍珠", "水钻", "金属线", "极光粉", "镜面", "蕾丝"] },
] as const;

const cases = [
  {
    title: "上传参考图",
    text: "把刚收藏的款式图或灵感图放进来，DIY 生成就从这一步开始。",
    image: "/diy-tutorial/tutorial-1.png",
  },
  {
    title: "选择偏好",
    text: "用选择题锁定场景、长度、甲型和预算，不需要自己写很长的提示词。",
    image: "/diy-tutorial/tutorial-2.png",
  },
  {
    title: "回来看结果",
    text: "查看 DIY 创意的效果图，如果您满意，请发布悬赏等待商家接单。",
    image: "/diy-tutorial/tutorial-3.png",
  },
];

const defaultAnswers: DiyBountyAnswers = {
  occasion: "通勤",
  nail_length: "短甲",
  nail_shape: "方圆",
  style: "简约",
  colors: ["奶茶"],
  decorations: ["细闪"],
  budget: "¥150-250",
  change_policy: "可轻微改色",
  user_prompt: "",
};

const LAST_DIY_RESULT_KEY = "nailai:last-diy-bounty-result";
const LAST_DIY_ANSWERS_KEY = "nailai:last-diy-bounty-answers";

function ChoiceButton({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-9 rounded-full border px-3 text-[12px] font-black transition ${
        selected ? "border-[#ff5c74] bg-[#ff5c74] text-white shadow-md shadow-[#ff5c74]/25" : "border-[#f4d8df] bg-white text-[#5d404a]"
      }`}
    >
      {label}
    </button>
  );
}

function SectionHeader({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[16px] bg-[#fff0f4] text-[#ff5c74]">{icon}</span>
      <div>
        <h2 className="text-base font-black">{title}</h2>
        <p className="mt-1 text-[11px] leading-4 text-[#9b7580]">{subtitle}</p>
      </div>
    </div>
  );
}

function VariantCard({
  variant,
  selected,
  onSelect,
}: {
  variant: DiyBountyVariant;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-[154px] shrink-0 rounded-[20px] border bg-white p-2 text-left shadow-sm ${
        selected ? "border-[#ff5c74]" : "border-[#f5dce3]"
      }`}
    >
      <div className="relative h-32 overflow-hidden rounded-[16px] bg-[#fff0f4]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={variant.image_url} alt={variant.title} className="h-full w-full object-cover" />
        {selected ? (
          <span className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-full bg-[#ff5c74] text-white">
            <Check size={14} />
          </span>
        ) : null}
      </div>
      <p className="mt-2 truncate text-xs font-black">{variant.title}</p>
      <p className="mt-1 truncate text-[10px] font-bold text-[#a88a93]">{variant.tags.join(" · ")}</p>
    </button>
  );
}

export function DiyBountyCreateScreen() {
  const router = useRouter();
  const [answers, setAnswers] = useState<DiyBountyAnswers>(defaultAnswers);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<DiyBountyGenerateResponse | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [published, setPublished] = useState<DiyBountyPublishResponse | null>(null);
  const [history, setHistory] = useState<DiyBountyHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const referenceInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    function restoreLocalResult() {
      const cachedResult = window.localStorage.getItem(LAST_DIY_RESULT_KEY);
      if (cachedResult) {
        const parsed = JSON.parse(cachedResult) as DiyBountyGenerateResponse;
        // 只恢复 qwen-wan-diy 的缓存结果
        if (parsed.channel === "qwen-wan-diy" || parsed.channel === "mock-diy-bounty") {
          setResult(parsed);
          setSelectedVariantId(parsed.variants[0]?.id ?? null);
        } else {
          window.localStorage.removeItem(LAST_DIY_RESULT_KEY);
        }
      }

      const cachedAnswers = window.localStorage.getItem(LAST_DIY_ANSWERS_KEY);
      if (cachedAnswers) {
        setAnswers(JSON.parse(cachedAnswers) as DiyBountyAnswers);
      }
    }

    try {
      restoreLocalResult();
      setHistory(loadDiyBountyHistory());
    } catch {
      window.localStorage.removeItem(LAST_DIY_RESULT_KEY);
      window.localStorage.removeItem(LAST_DIY_ANSWERS_KEY);
    }

    fetchLatestDiyBountyGeneration().then((latest) => {
      if (cancelled || !latest) return;
      // 只显示 qwen-wan-diy 的结果，过滤旧的 doubao/qwen-image2 记录
      if (latest.channel !== "qwen-wan-diy" && latest.channel !== "mock-diy-bounty") return;
      setResult((current) => current ?? latest);
      setSelectedVariantId((current) => current ?? latest.variants[0]?.id ?? null);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedVariant = useMemo(
    () => result?.variants.find((variant) => variant.id === selectedVariantId) ?? result?.variants[0],
    [result, selectedVariantId],
  );

  function setSingle(key: keyof DiyBountyAnswers, value: string) {
    setAnswers((current) => ({ ...current, [key]: value }));
  }

  function toggleMulti(key: "colors" | "decorations", value: string) {
    setAnswers((current) => {
      const values = current[key];
      const next = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
      return { ...current, [key]: next.length ? next : [value] };
    });
  }

  function handleFile(nextFile: File | null) {
    setFile(nextFile);
    setResult(null);
    setSelectedVariantId(null);
    setPublished(null);
    setError(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(nextFile ? URL.createObjectURL(nextFile) : null);
  }

  function openReferencePicker() {
    const input = referenceInputRef.current;
    if (!input) return;
    if (typeof input.showPicker === "function") {
      try {
        input.showPicker();
        return;
      } catch {
        // Fallback to click() below.
      }
    }
    input.click();
  }

  async function handleGenerate() {
    if (!file) {
      setError("请先上传一张美甲或灵感参考图。");
      return;
    }
    setLoading(true);
    setError(null);
    setPublished(null);
    void startDiyTask({ referenceImage: file, answers });
    router.push("/");
  }

  async function handlePublish() {
    if (!selectedVariant) return;
    setPublishing(true);
    setError(null);
    try {
      const response = await postDiyBountyPublish({
        title: `${answers.style}${answers.nail_length} DIY 悬赏`,
        description: `${answers.occasion}场景，${answers.nail_shape}，${answers.colors.join("、")}，${answers.decorations.join("、")}。${answers.change_policy}。`,
        budget: answers.budget,
        image: selectedVariant.image_url,
        answers,
        selectedVariantId: selectedVariant.id,
      });
      setPublished(response);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "发布悬赏失败，请稍后重试。");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <PhoneShell title="创建 DIY 悬赏" active="bounty">
      <div className="space-y-4 px-4 pb-6 pt-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-black">操作案例</h2>
            <span className="rounded-full bg-[#fff0f4] px-3 py-1 text-[11px] font-black text-[#ff5c74]">单方案</span>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {cases.map((item, index) => (
              <div key={item.title} className="w-[150px] shrink-0 rounded-[20px] bg-white p-2 shadow-sm">
                <div className="relative h-24 overflow-hidden rounded-[16px] bg-[#fff0f4]">
                  <Image src={item.image} alt={item.title} fill sizes="150px" className="object-cover" />
                  <span className="absolute left-2 top-2 grid h-6 w-6 place-items-center rounded-full bg-white/90 text-[11px] font-black text-[#ff5c74]">
                    {index + 1}
                  </span>
                </div>
                <p className="mt-2 text-xs font-black">{item.title}</p>
                <p className="mt-1 text-[10px] leading-4 text-[#9b7580]">{item.text}</p>
              </div>
            ))}
          </div>
        </div>

        <SoftCard className="bg-[linear-gradient(145deg,#fff0f4,#fff7ec)]">
          <SectionHeader
            icon={<Wand2 size={18} />}
            title="用选择题生成美甲方案"
            subtitle="上传灵感图后，NailAI 会把你的选择整理成专业美甲方案图，方便店铺报价。"
          />
        </SoftCard>

        {selectedVariant ? (
          <SoftCard id="result-hero" className="border border-[#ffd4df] bg-[linear-gradient(180deg,#fff7fa,#ffffff)]">
            <SectionHeader
              icon={<Sparkles size={18} />}
              title="最新 DIY 结果"
              subtitle="回到这页时，第一屏直接看结果大图，不用再往下滑找方案。"
            />
            <div className="mt-4 overflow-hidden rounded-[24px] bg-[#fff0f4]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={selectedVariant.image_url} alt={selectedVariant.title} className="h-[320px] w-full object-cover" />
            </div>
            <div className="mt-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-black">{selectedVariant.title}</p>
                <p className="mt-1 text-[11px] font-bold text-[#a88a93]">{selectedVariant.tags.join(" · ")}</p>
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={loading || !file}
                className="shrink-0 rounded-full border border-[#f5dce3] px-3 py-2 text-[11px] font-black text-[#5d404a] disabled:opacity-50"
              >
                重新生成
              </button>
            </div>
          </SoftCard>
        ) : null}

        <SoftCard>
          <SectionHeader icon={<ImagePlus size={18} />} title="上传参考图" subtitle="支持美甲图、灵感图、甲片图；这不是手部试戴入口。" />
          <div className="relative mt-4">
            <button
              type="button"
              onClick={openReferencePicker}
              className="block w-full overflow-hidden rounded-[20px] border border-dashed border-[#ffb8c7] bg-[#fff7f9] text-left outline-none transition hover:border-[#ff94ac] focus-visible:ring-2 focus-visible:ring-[#ff5c74]/30"
            >
              <div className="grid min-h-[168px] place-items-center">
                {preview ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={preview} alt="参考图预览" className="h-full max-h-[220px] w-full object-contain p-2" />
                ) : (
                  <div className="px-6 text-center">
                    <ImagePlus className="mx-auto text-[#ff5c74]" size={28} />
                    <p className="mt-3 text-sm font-black">点击上传参考图</p>
                    <p className="mt-1 text-[11px] text-[#a88a93]">建议使用清晰的美甲近景或款式图</p>
                  </div>
                )}
              </div>
            </button>
            <input
              ref={referenceInputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(event) => {
                handleFile(event.target.files?.[0] ?? null);
                event.currentTarget.value = "";
              }}
            />
          </div>
        </SoftCard>

        <SoftCard>
          <SectionHeader icon={<ClipboardList size={18} />} title="选择题" subtitle="把需求拆成选择题，减少用户写 prompt 的负担。" />
          <div className="mt-4 space-y-4">
            {singleChoiceGroups.map((group) => (
              <div key={group.key}>
                <p className="mb-2 text-xs font-black text-[#5d404a]">{group.title}</p>
                <div className="flex flex-wrap gap-2">
                  {group.options.map((option) => (
                    <ChoiceButton
                      key={option}
                      label={option}
                      selected={answers[group.key] === option}
                      onClick={() => setSingle(group.key, option)}
                    />
                  ))}
                </div>
              </div>
            ))}
            {multiChoiceGroups.map((group) => (
              <div key={group.key}>
                <p className="mb-2 text-xs font-black text-[#5d404a]">{group.title}</p>
                <div className="flex flex-wrap gap-2">
                  {group.options.map((option) => (
                    <ChoiceButton
                      key={option}
                      label={option}
                      selected={answers[group.key].includes(option)}
                      onClick={() => toggleMulti(group.key, option)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SoftCard>

        <SoftCard>
          <SectionHeader icon={<Wand2 size={18} />} title="补充要求（可选）" subtitle="输入具体的提示词以补充偏好（例如：想要显白、贴个小星星等）。" />
          <textarea
            value={answers.user_prompt || ""}
            onChange={(e) => setSingle("user_prompt", e.target.value)}
            placeholder="例如：指甲边缘希望有金丝；或者是想要更偏向粉嫩一些..."
            rows={3}
            className="mt-4 w-full rounded-[16px] border border-[#f4d8df] bg-white p-3 text-xs font-bold text-[#5d404a] placeholder-[#c4b1b6] focus:border-[#ff5c74] focus:outline-none resize-none transition"
          />
        </SoftCard>

        <SoftCard className="border border-[#f5dce3]">
          <SectionHeader icon={<Palette size={18} />} title="需求摘要" subtitle="生成前可以快速确认方案方向。" />
          <div className="mt-4 rounded-[18px] bg-[#fff7f2] p-3 text-[12px] font-bold leading-6 text-[#6d4b56]">
            {answers.occasion} · {answers.nail_length} · {answers.nail_shape} · {answers.style}
            <br />
            {answers.colors.join(" / ")} · {answers.decorations.join(" / ")}
            <br />
            {answers.budget} · {answers.change_policy}
            {answers.user_prompt ? (
              <>
                <br />
                <span className="text-[#ff5c74]">补充：{answers.user_prompt}</span>
              </>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-full bg-[#ff5c74] text-sm font-black text-white shadow-lg shadow-[#ff5c74]/30 disabled:bg-[#eccdd5]"
          >
            {loading ? <Loader2 size={17} className="animate-spin" /> : <Sparkles size={17} />}
            {loading ? "正在生成 DIY 方案" : "生成 1 个 DIY 方案"}
          </button>
          {error ? <p className="mt-3 rounded-[16px] bg-[#fff0f4] px-3 py-3 text-xs font-bold text-red-600">{error}</p> : null}
        </SoftCard>

        {result ? (
          <SoftCard>
            <SectionHeader
              icon={<Sparkles size={18} />}
              title="生成结果"
              subtitle="下面保留方案卡片，方便你切换或确认要发布的那一张。"
            />
            <div className="mt-4 flex gap-3 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {result.variants.map((variant) => (
                <VariantCard
                  key={variant.id}
                  variant={variant}
                  selected={(selectedVariant?.id ?? selectedVariantId) === variant.id}
                  onSelect={() => setSelectedVariantId(variant.id)}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading || !file}
              className="mt-4 flex h-10 w-full items-center justify-center gap-2 rounded-full border border-[#f5dce3] text-xs font-black text-[#5d404a]"
            >
              <RefreshCw size={14} />
              重新生成
            </button>
          </SoftCard>
        ) : null}

        {selectedVariant ? (
          <SoftCard className="border border-[#ffd4df]">
            <SectionHeader icon={<Send size={18} />} title="悬赏预览" subtitle="确认后会生成一个待报价悬赏。" />
            <div className="mt-4 flex gap-3">
              <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-[18px] bg-[#fff0f4]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={selectedVariant.image_url} alt={selectedVariant.title} className="h-full w-full object-cover" />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-black">{answers.style}{answers.nail_length} DIY 悬赏</h3>
                <p className="mt-1 text-xs font-black text-[#ff5c74]">{answers.budget}</p>
                <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-[#8f6b75]">
                  {answers.occasion}场景，{answers.nail_shape}，{answers.colors.join("、")}，{answers.decorations.join("、")}。
                </p>
              </div>
            </div>
            <PrimaryButton onClick={handlePublish} disabled={publishing}>
              {publishing ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              确认发布悬赏
            </PrimaryButton>
            {published ? (
              <div className="mt-3 rounded-[18px] bg-[#f0fff7] p-3 text-xs font-bold leading-5 text-[#26734d]">
                已创建：{published.title} · {published.status} · {published.deadline}
              </div>
            ) : null}
          </SoftCard>
        ) : null}

        {history.length ? (
          <SoftCard>
            <SectionHeader icon={<RefreshCw size={18} />} title="生成历史" subtitle="保存在当前浏览器，本机刷新后仍可找回。" />
            <div className="mt-4 space-y-3">
              {history.filter((item) => item.result.channel === "qwen-wan-diy" || item.result.channel === "mock-diy-bounty").slice(0, 5).map((item) => {
                const cover = item.result.variants[0];
                return (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => {
                      setAnswers(item.answers);
                      setResult(item.result);
                      setSelectedVariantId(item.result.variants[0]?.id ?? null);
                    }}
                    className="flex w-full gap-3 rounded-[18px] bg-[#fff7f2] p-2 text-left"
                  >
                    <div className="h-16 w-16 shrink-0 overflow-hidden rounded-[14px] bg-[#fff0f4]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={cover?.image_url} alt={cover?.title ?? "DIY 方案"} className="h-full w-full object-cover" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-black">{item.answers.style} · {item.answers.nail_length} · {item.answers.colors.join("/")}</p>
                      <p className="mt-1 text-[10px] font-bold text-[#9b7580]">{item.result.variants.length} 张方案 · {new Date(item.created_at).toLocaleString()}</p>
                      <p className="mt-1 truncate text-[10px] text-[#a88a93]">{item.result.job_id}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </SoftCard>
        ) : null}
      </div>
    </PhoneShell>
  );
}
