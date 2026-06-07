"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { CheckCircle2, Filter, Loader2, MapPin, Plus, Sparkles, Star, Store, Trophy, Upload, X } from "lucide-react";
import {
  fetchBounties,
  fetchShops,
  fetchStoreTasks,
  fetchShopInfo,
  fetchTaxonomyFilters,
  updateShopInfo,
  acceptDiyBounty,
  fetchMerchantStyles,
  toggleStyleActive,
} from "@/lib/api";
import { emptyMerchantTaxonomy, merchantTaxonomyChoices, merchantTaxonomyLabels } from "@/lib/merchantTaxonomy";
import { getPrototypeBounty, prototypeBounties, prototypeShops, storeTasks } from "@/lib/prototypeData";
import type { PrototypeBounty, PrototypeShop, StoreTask } from "@/lib/prototypeData";
import type { MerchantStyleUploadTask, NailTaxonomy, MerchantStyleWithAnalytics } from "@/lib/types";
import {
  dismissMerchantStyleTask,
  enqueueMerchantStyleTask,
  publishMerchantStyleTask,
  setActiveMerchantStyleTask,
  useMerchantStyleTasks,
} from "@/lib/merchantStyleTaskStore";
import { BountyCard, ShopCard, StoreTaskCard } from "./Cards";
import { PhoneShell, PrimaryButton, SoftCard } from "./Shell";

type TaxonomyKey = keyof NailTaxonomy;

const taxonomyDimensionOrder: TaxonomyKey[] = ["colors", "techniques", "shapes", "styles", "occasions", "lengths"];

const emptyTaxonomyInputs = (): Record<TaxonomyKey, string> => ({
  colors: "",
  techniques: "",
  shapes: "",
  styles: "",
  occasions: "",
  lengths: "",
});

function mergeTaxonomyChoices(filters: Record<string, string[]>) {
  return taxonomyDimensionOrder.reduce<Record<TaxonomyKey, string[]>>((acc, key) => {
    const merged = [...merchantTaxonomyChoices[key], ...(filters[key] ?? [])];
    acc[key] = merged.filter((value, index, values) => Boolean(value) && values.indexOf(value) === index);
    return acc;
  }, { ...merchantTaxonomyChoices });
}

export function DiyBountyScreen() {
  const [bounties, setBounties] = useState<PrototypeBounty[]>(prototypeBounties);

  useEffect(() => {
    fetchBounties().then(setBounties).catch(() => setBounties(prototypeBounties));
  }, []);

  return (
    <PhoneShell title="DIY 悬赏" active="bounty">
      <div className="space-y-4 px-4 pt-3">
        <SoftCard className="bg-[linear-gradient(145deg,#ffd0c5,#f3a4c7)]">
          <Trophy className="text-[#ff5c74]" size={24} />
          <h1 className="mt-4 text-2xl font-black">发布款式悬赏</h1>
          <p className="mt-2 text-xs leading-5 text-[#7b4c5b]">上传想复刻的美甲图，让附近店铺报价接单。</p>
          <PrimaryButton href="/diy-bounty/create">
            <Plus size={16} />
            创建悬赏
          </PrimaryButton>
        </SoftCard>
        <div className="space-y-3">
          {bounties.map((bounty) => (
            <BountyCard key={bounty.id} bounty={bounty} />
          ))}
        </div>
      </div>
    </PhoneShell>
  );
}

export function BountyDetailScreen({ bountyId }: { bountyId?: string }) {
  const bounty = getPrototypeBounty(bountyId);
  return (
    <PhoneShell title="悬赏详情" active="bounty">
      <div className="space-y-4 px-4 pt-3">
        <div className="relative h-64 overflow-hidden rounded-[26px] bg-[#fff0f4]">
          <Image src={bounty.image} alt={bounty.title} fill className="object-cover" sizes="343px" priority />
        </div>
        <SoftCard>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[11px] font-bold text-[#ff5c74]">{bounty.status}</p>
              <h1 className="mt-1 text-2xl font-black">{bounty.title}</h1>
            </div>
            <span className="text-lg font-black text-[#ff5c74]">{bounty.budget}</span>
          </div>
          <p className="mt-4 text-xs leading-5 text-[#74515b]">{bounty.description}</p>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-[16px] bg-[#fff7f2] p-3">
              <p className="text-lg font-black">{bounty.participants}</p>
              <p className="text-[10px] text-[#9b7580]">店铺报价</p>
            </div>
            <div className="rounded-[16px] bg-[#fff7f2] p-3">
              <p className="text-lg font-black">1.4h</p>
              <p className="text-[10px] text-[#9b7580]">平均响应</p>
            </div>
            <div className="rounded-[16px] bg-[#fff7f2] p-3">
              <p className="text-lg font-black">8</p>
              <p className="text-[10px] text-[#9b7580]">收藏</p>
            </div>
          </div>
        </SoftCard>
        <div className="space-y-3">
          {prototypeShops.map((shop) => (
            <ShopCard key={shop.id} shop={shop} />
          ))}
        </div>
      </div>
    </PhoneShell>
  );
}

export function ShopRecommendScreen() {
  const [shops, setShops] = useState<PrototypeShop[]>(prototypeShops);

  useEffect(() => {
    fetchShops().then(setShops).catch(() => setShops(prototypeShops));
  }, []);

  return (
    <PhoneShell title="可做店铺" active="home">
      <div className="space-y-4 px-4 pt-3">
        <div className="flex gap-2">
          {["距离最近", "3km内", "4.5+", "可预约"].map((filter) => (
            <span key={filter} className="flex h-8 items-center gap-1 rounded-full bg-white px-3 text-[11px] font-bold text-[#5a3a43] shadow-sm">
              <Filter size={12} />
              {filter}
            </span>
          ))}
        </div>
        <SoftCard className="bg-[#ffe8df]">
          <div className="h-28 rounded-[18px] bg-[radial-gradient(circle_at_25%_40%,#ff8ca0_0_10px,transparent_11px),radial-gradient(circle_at_70%_55%,#ff5c74_0_8px,transparent_9px),#f8d8ca]" />
        </SoftCard>
        <div className="space-y-3">
          {shops.map((shop) => (
            <ShopCard key={shop.id} shop={shop} />
          ))}
        </div>
      </div>
    </PhoneShell>
  );
}

export function StoreTakeOrderScreen() {
  const merchantTasks = useMerchantStyleTasks();
  const [activeTab, setActiveTab] = useState<"tasks" | "upload" | "manage" | "settings">("tasks");
  const [tasks, setTasks] = useState<(StoreTask & { description?: string })[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(false);

  const [merchantStyles, setMerchantStyles] = useState<MerchantStyleWithAnalytics[]>([]);
  const [loadingStyles, setLoadingStyles] = useState(false);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  const loadMerchantStyles = () => {
    setLoadingStyles(true);
    fetchMerchantStyles()
      .then((data) => {
        setMerchantStyles(data);
      })
      .catch((err) => {
        console.error("Failed to load merchant styles:", err);
      })
      .finally(() => {
        setLoadingStyles(false);
      });
  };

  const handleToggleStyleActive = async (styleId: string, currentActive: boolean) => {
    const nextActive = !currentActive;
    // Optimistic update
    setMerchantStyles((prev) =>
      prev.map((s) => (s.id === styleId ? { ...s, is_active: nextActive } : s))
    );
    try {
      const success = await toggleStyleActive(styleId, nextActive);
      if (!success) {
        throw new Error("API call failed");
      }
    } catch (err) {
      console.error("Failed to toggle style status:", err);
      // Revert
      setMerchantStyles((prev) =>
        prev.map((s) => (s.id === styleId ? { ...s, is_active: currentActive } : s))
      );
      alert("修改款式状态失败，请稍后重试");
    }
  };

  useEffect(() => {
    if (activeTab === "manage") {
      loadMerchantStyles();
    }
  }, [activeTab]);

  // Shop settings state
  const [shopName, setShopName] = useState("");
  const [shopAddress, setShopAddress] = useState("");
  const [shopActiveScore, setShopActiveScore] = useState(0.95);
  const [shopWaitTime, setShopWaitTime] = useState("无需等待");
  const [shopSchedule, setShopSchedule] = useState("排期充裕");
  const [facWifi, setFacWifi] = useState(true);
  const [facParking, setFacParking] = useState(true);
  const [facTea, setFacTea] = useState(true); // snacks & tea
  const [facPrivateRoom, setFacPrivateRoom] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // Style upload state
  const [styleName, setStyleName] = useState("");
  const [stylePrice, setStylePrice] = useState("158");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [publishingTaskId, setPublishingTaskId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [taxonomyOptions, setTaxonomyOptions] = useState<Record<TaxonomyKey, string[]>>(merchantTaxonomyChoices);
  const [selectedTaxonomy, setSelectedTaxonomy] = useState<NailTaxonomy>(emptyMerchantTaxonomy());
  const [customTaxonomy, setCustomTaxonomy] = useState<NailTaxonomy>(emptyMerchantTaxonomy());
  const [customTaxonomyInput, setCustomTaxonomyInput] = useState<Record<TaxonomyKey, string>>(emptyTaxonomyInputs());

  // Load initial tasks & shop info
  const loadTasks = () => {
    setLoadingTasks(true);
    fetchStoreTasks()
      .then((data) => setTasks(data as (StoreTask & { description?: string })[]))
      .catch((err: unknown) => {
        console.error(err);
        setTasks(storeTasks);
      })
      .finally(() => setLoadingTasks(false));
  };

  useEffect(() => {
    loadTasks();

    fetchShopInfo()
      .then((info) => {
        if (info) {
          setShopName(info.name || "");
          setShopAddress(info.address || "");
          setShopActiveScore(info.active_score !== undefined ? info.active_score : 0.95);
          setShopWaitTime(info.wait_time || "无需等待");
          setShopSchedule(info.schedule || "排期充裕");
          if (info.facilities) {
            setFacWifi(!!info.facilities.wifi);
            setFacParking(!!info.facilities.parking);
            setFacTea(!!info.facilities.tea);
            setFacPrivateRoom(!!info.facilities.private_room);
          }
        }
      })
      .catch((err) => console.error("Error fetching shop info:", err));

    fetchTaxonomyFilters()
      .then((filters) => setTaxonomyOptions(mergeTaxonomyChoices(filters)))
      .catch(() => setTaxonomyOptions(merchantTaxonomyChoices));
  }, []);

  const togglePresetTaxonomy = (dimension: TaxonomyKey, value: string) => {
    setSelectedTaxonomy((current) => {
      const nextValues = current[dimension].includes(value)
        ? current[dimension].filter((item) => item !== value)
        : [...current[dimension], value];
      return { ...current, [dimension]: nextValues };
    });
  };

  const addCustomTaxonomy = (dimension: TaxonomyKey) => {
    const nextValue = customTaxonomyInput[dimension].trim();
    if (!nextValue) return;
    setCustomTaxonomy((current) => ({
      ...current,
      [dimension]: current[dimension].includes(nextValue) ? current[dimension] : [...current[dimension], nextValue],
    }));
    setCustomTaxonomyInput((current) => ({ ...current, [dimension]: "" }));
  };

  const removeCustomTaxonomy = (dimension: TaxonomyKey, value: string) => {
    setCustomTaxonomy((current) => ({
      ...current,
      [dimension]: current[dimension].filter((item) => item !== value),
    }));
  };

  // Accept bounty handler
  const handleAcceptBounty = async (taskId: string) => {
    try {
      await acceptDiyBounty(taskId);
      // Reload tasks list to get updated status
      loadTasks();
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      alert(`接单失败：${errMsg || "请稍后再试"}`);
      throw err;
    }
  };

  // Upload style handler
  const handleUploadStyle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageFile) {
      alert("请先选择一款美甲款式图片！");
      return;
    }
    if (!styleName.trim()) {
      alert("请输入款式名称！");
      return;
    }
    const missingDimension = taxonomyDimensionOrder.find(
      (dimension) => selectedTaxonomy[dimension].length + customTaxonomy[dimension].length === 0,
    );
    if (missingDimension) {
      alert(`请先填写${merchantTaxonomyLabels[missingDimension]}标签，再生成款式图预览！`);
      return;
    }

    setUploadError(null);

    try {
      await enqueueMerchantStyleTask({
        image: imageFile,
        imagePreviewUrl: imagePreview ?? URL.createObjectURL(imageFile),
        styleName: styleName.trim(),
        stylePrice,
        taxonomy: selectedTaxonomy,
        customTagsByDimension: customTaxonomy,
      });
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setUploadError(errMsg || "款式图预览失败，请检查网络或重试。");
    }
  };

  const handlePublishStyle = async (taskId: string) => {
    setUploadError(null);
    setPublishingTaskId(taskId);
    try {
      const response = await publishMerchantStyleTask(taskId);
      if (response.status !== "success") {
        throw new Error("款式发布失败");
      }
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setUploadError(errMsg || "款式上架失败，请稍后重试。");
    } finally {
      setPublishingTaskId(null);
    }
  };

  // Update shop info handler
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopName.trim()) {
      alert("店铺名称不能为空！");
      return;
    }

    setSavingSettings(true);
    setSettingsSuccess(false);

    try {
      await updateShopInfo(
        shopName,
        shopAddress,
        shopActiveScore,
        shopWaitTime,
        shopSchedule,
        {
          wifi: facWifi,
          parking: facParking,
          tea: facTea,
          private_room: facPrivateRoom
        }
      );
      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      alert(`保存失败：${errMsg || "请稍后再试"}`);
    } finally {
      setSavingSettings(false);
    }
  };

  // Counts for active, accepted, revenue
  const pendingCount = tasks.filter(
    (t) => t.status === "待接单" || t.status === "待抢单" || t.status === "可接单"
  ).length;
  const acceptedCount = tasks.filter(
    (t) => t.status === "已接单" || t.status === "已确认"
  ).length;
  const activeUploadTask =
    merchantTasks.tasks.find((task) => task.id === merchantTasks.activeTaskId) ??
    merchantTasks.tasks.find((task) => task.status === "running") ??
    merchantTasks.tasks.find((task) => task.status === "succeeded") ??
    null;
  const activePreviewResult = activeUploadTask?.preview_result ?? null;
  const activePreviewIsAiGenerated = activePreviewResult?.render_status === "ai_generated";
  const pendingUploadCount = merchantTasks.tasks.filter((task) => task.status === "queued" || task.status === "running").length;
  const hasCompletedTaxonomy = taxonomyDimensionOrder.every(
    (dimension) => selectedTaxonomy[dimension].length + customTaxonomy[dimension].length > 0,
  );
  const isGeneratingPreview = merchantTasks.tasks.some((task) => task.status === "running");
  const queueButtonLabel = pendingUploadCount > 0 ? `继续排队上传 (${pendingUploadCount})` : "第三步：生成款式图预览";

  const renderTaskStatusPill = (task: MerchantStyleUploadTask) => {
    if (task.status === "running") {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-[#fff0f4] px-2 py-1 text-[10px] font-black text-[#ff5c74]">
          <Loader2 size={10} className="animate-spin" />
          生成中
        </span>
      );
    }
    if (task.status === "queued") {
      return <span className="rounded-full bg-[#fff7e8] px-2 py-1 text-[10px] font-black text-[#cc8400]">排队中</span>;
    }
    if (task.status === "failed") {
      return <span className="rounded-full bg-red-50 px-2 py-1 text-[10px] font-black text-red-600">失败</span>;
    }
    return <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-black text-emerald-700">已完成</span>;
  };

  return (
    <PhoneShell title="甲惠通·店主" active="mine">
      <div className="space-y-4 px-4 pt-3 pb-8">
        {/* Shop Profile Banner */}
        <SoftCard className="bg-[#511438] text-white">
          <div className="flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-full bg-[#ffb8c7] text-lg font-black text-[#511438]">
              {shopName ? shopName.slice(0, 1) : "店"}
            </span>
            <div className="min-w-0 flex-1">
              <h1 className="text-base font-black truncate">{shopName || "甲惠通美甲店"}</h1>
              <p className="mt-0.5 text-xs text-[#dec1d2] truncate">
                地址: {shopAddress || "未设置"}
              </p>
            </div>
          </div>
        </SoftCard>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-[18px] bg-white p-3 shadow-sm border border-neutral-100/60">
            <p className="text-lg font-black text-[#ff5c74]">{pendingCount}</p>
            <p className="text-[10px] text-[#9b7580]">待抢单</p>
          </div>
          <div className="rounded-[18px] bg-white p-3 shadow-sm border border-neutral-100/60">
            <p className="text-lg font-black text-[#10b981]">{acceptedCount}</p>
            <p className="text-[10px] text-[#9b7580]">已接单</p>
          </div>
          <div className="rounded-[18px] bg-white p-3 shadow-sm border border-neutral-100/60">
            <p className="text-lg font-black text-[#27101c]">95%</p>
            <p className="text-[10px] text-[#9b7580]">接单率</p>
          </div>
        </div>

        {/* Beautiful Custom Tab Navigation */}
        <div className="flex rounded-full bg-[#f6edef] p-1 shadow-inner">
          {[
            { id: "tasks", label: "接单中心" },
            { id: "upload", label: "款式上架" },
            { id: "manage", label: "款式管理" },
            { id: "settings", label: "店铺设置" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as "tasks" | "upload" | "manage" | "settings")}
              className={`flex-1 rounded-full py-2 text-[11px] font-bold transition-all duration-200 ${
                activeTab === tab.id
                  ? "bg-[#27101c] text-white shadow-sm"
                  : "text-[#7b515c] hover:text-[#27101c]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        {activeTab === "tasks" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-bold text-[#7b515c]">附近最新的DIY悬赏需求</span>
              <button
                onClick={loadTasks}
                disabled={loadingTasks}
                className="text-xs font-bold text-[#ff5c74] hover:underline flex items-center gap-1"
              >
                {loadingTasks ? "刷新中..." : "手动刷新"}
              </button>
            </div>
            {tasks.length === 0 ? (
              <div className="rounded-[20px] bg-white p-8 text-center border border-neutral-100">
                <p className="text-sm text-[#9b7580]">暂无待接单的DIY需求</p>
              </div>
            ) : (
              tasks.map((task) => (
                <StoreTaskCard
                  key={task.id}
                  task={task}
                  onAccept={handleAcceptBounty}
                />
              ))
            )}
          </div>
        )}

        {activeTab === "upload" && (
          <div className="space-y-4">
            <SoftCard className="bg-white border border-neutral-100">
              <h2 className="text-sm font-black text-[#27101c] mb-3">第一步：上传款式基础信息</h2>
              <form onSubmit={handleUploadStyle} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-[#7b515c] mb-1.5">
                    款式照片 (上传带手的美甲实拍图)
                  </label>
                  <div
                    onClick={() => {
                      const el = document.getElementById("style-image-input");
                      if (el) el.click();
                    }}
                    className={`border-2 border-dashed rounded-[20px] p-6 text-center cursor-pointer transition-all ${
                      imagePreview
                        ? "border-green-300 bg-green-50/20"
                        : "border-[#f5dce3] hover:border-[#ff5c74] hover:bg-[#fff7f8]"
                    }`}
                  >
                    <input
                      id="style-image-input"
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          setImageFile(file);
                          setImagePreview(URL.createObjectURL(file));
                        }
                      }}
                      className="hidden"
                    />
                    {imagePreview ? (
                      <div className="relative h-32 mx-auto w-32 rounded-[16px] overflow-hidden border border-neutral-200">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={imagePreview}
                          alt="款式预览"
                          className="h-full w-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="space-y-1.5 flex flex-col items-center">
                        <Upload className="text-[#ff5c74] mx-auto" size={24} />
                        <p className="text-xs font-bold text-[#27101c]">点击选择或拖入款式图片</p>
                        <p className="text-[10px] text-[#9b7580]">支持 PNG, JPG, JPEG 格式</p>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#7b515c] mb-1">款式名称</label>
                  <input
                    type="text"
                    value={styleName}
                    onChange={(e) => setStyleName(e.target.value)}
                    placeholder="例如: 冰透猫眼蝴蝶结款"
                    className="w-full h-10 px-4 rounded-full border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb]"
                  />
                </div>

                <div>
                  <div>
                    <label className="block text-xs font-bold text-[#7b515c] mb-1">参考价 (元)</label>
                    <input
                      type="number"
                      value={stylePrice}
                      onChange={(e) => setStylePrice(e.target.value)}
                      placeholder="158"
                      className="w-full h-10 px-4 rounded-full border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb]"
                    />
                  </div>
                </div>

                <div className="rounded-[18px] border border-[#f5dce3] bg-[#fff8fa] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-black text-[#27101c]">第二步：先填写六维标签</h2>
                      <p className="mt-1 text-[10px] leading-5 text-[#9b7580]">
                        每个维度至少选 1 个标签；先补齐标签，再生成上架款式图。
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[10px] font-black ${
                      hasCompletedTaxonomy ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : "bg-amber-50 text-amber-700 border border-amber-100"
                    }`}>
                      {hasCompletedTaxonomy ? "可出图" : "待补齐"}
                    </span>
                  </div>

                  <div className="mt-4 space-y-4">
                    {taxonomyDimensionOrder.map((dimension) => (
                      <div key={dimension} className="rounded-[18px] border border-[#f5dce3] bg-[#fdfafb] p-3">
                        <div className="flex items-center justify-between gap-2">
                          <label className="text-xs font-black text-[#5a3a43]">{merchantTaxonomyLabels[dimension]}</label>
                          <span className="text-[10px] font-bold text-[#9b7580]">
                            {(selectedTaxonomy[dimension].length + customTaxonomy[dimension].length) > 0 ? "已填写" : "必填"}
                          </span>
                        </div>

                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {taxonomyOptions[dimension].map((value) => {
                            const selected = selectedTaxonomy[dimension].includes(value);
                            return (
                              <button
                                key={`${dimension}-${value}`}
                                type="button"
                                onClick={() => togglePresetTaxonomy(dimension, value)}
                                className={`rounded-full px-2.5 py-1 text-[10px] font-bold transition-colors ${
                                  selected
                                    ? "bg-[#27101c] text-white"
                                    : "bg-white text-[#7b515c] border border-[#f5dce3]"
                                }`}
                              >
                                {value}
                              </button>
                            );
                          })}
                        </div>

                        {customTaxonomy[dimension].length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {customTaxonomy[dimension].map((value) => (
                              <button
                                key={`${dimension}-custom-${value}`}
                                type="button"
                                onClick={() => removeCustomTaxonomy(dimension, value)}
                                className="rounded-full border border-dashed border-[#ff5c74] bg-[#fff0f4] px-2.5 py-1 text-[10px] font-bold text-[#ff5c74]"
                              >
                                {value} ×
                              </button>
                            ))}
                          </div>
                        ) : null}

                        <div className="mt-2 flex gap-2">
                          <input
                            type="text"
                            value={customTaxonomyInput[dimension]}
                            onChange={(e) => setCustomTaxonomyInput((current) => ({ ...current, [dimension]: e.target.value }))}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                addCustomTaxonomy(dimension);
                              }
                            }}
                            placeholder={`补充${merchantTaxonomyLabels[dimension]}自定义标签`}
                            className="h-9 flex-1 rounded-full border border-[#f5dce3] bg-white px-3 text-[11px] font-medium focus:outline-none focus:border-[#ff5c74]"
                          />
                          <button
                            type="button"
                            onClick={() => addCustomTaxonomy(dimension)}
                            className="h-9 rounded-full border border-[#f5dce3] bg-white px-3 text-[11px] font-black text-[#5a3a43]"
                          >
                            添加
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                  <button
                    type="submit"
                    disabled={!hasCompletedTaxonomy}
                    className="w-full h-10 rounded-full bg-[#ff5c74] hover:bg-[#ff4560] disabled:bg-[#ffb7c3] disabled:cursor-not-allowed active:scale-98 transition-all text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-red-100"
                  >
                    {isGeneratingPreview ? (
                      <>
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        {queueButtonLabel}
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} />
                        {queueButtonLabel}
                      </>
                    )}
                  </button>

                  {activeUploadTask?.status === "running" ? (
                    <div className="rounded-[18px] border border-[#ffd4df] bg-[#fff8fa] px-3 py-3">
                      <div className="flex items-center justify-between gap-3 text-[11px] font-bold text-[#7b515c]">
                        <span className="truncate">{activeUploadTask.style_name} · {activeUploadTask.stage}</span>
                        <span className="shrink-0 text-[#ff5c74]">{activeUploadTask.progress}%</span>
                      </div>
                      <div className="mt-2 h-2 rounded-full bg-[#f7d8e1]">
                        <div
                          className="h-full rounded-full bg-[linear-gradient(90deg,#ff5c74,#ff9a73,#ffd66d)] transition-[width] duration-500"
                          style={{ width: `${activeUploadTask.progress}%` }}
                        />
                      </div>
                    </div>
                  ) : null}
                </form>
              </SoftCard>

            {uploadError && (
              <div className="rounded-[20px] bg-red-50 border border-red-200 p-4 text-xs font-medium text-red-600">
                {uploadError}
              </div>
            )}

            {merchantTasks.tasks.length > 0 ? (
              <SoftCard className="bg-white border border-neutral-100">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-black text-[#27101c]">上传队列</h3>
                    <p className="mt-1 text-[10px] text-[#9b7580]">生成中的任务不会锁住表单，新的款式可以继续加入队列。</p>
                  </div>
                  <span className="rounded-full bg-[#f6edef] px-2 py-1 text-[10px] font-black text-[#5a3a43]">
                    {merchantTasks.tasks.length} 个任务
                  </span>
                </div>
                <div className="mt-3 space-y-2">
                  {merchantTasks.tasks.map((task) => (
                    <button
                      key={task.id}
                      type="button"
                      onClick={() => setActiveMerchantStyleTask(task.id)}
                      className={`w-full rounded-[16px] border px-3 py-3 text-left transition-colors ${
                        merchantTasks.activeTaskId === task.id ? "border-[#ffb9c8] bg-[#fff7fa]" : "border-[#f2e7ea] bg-white"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="truncate text-xs font-black text-[#27101c]">{task.style_name}</p>
                            {renderTaskStatusPill(task)}
                          </div>
                          <p className="mt-1 text-[10px] font-semibold text-[#9b7580]">{task.source_image_name}</p>
                          <p className="mt-1 line-clamp-1 text-[10px] font-bold text-[#7b515c]">{task.stage}</p>
                          {task.status === "running" || task.status === "queued" ? (
                            <div className="mt-2 h-1.5 rounded-full bg-[#f7d8e1]">
                              <div
                                className="h-full rounded-full bg-[linear-gradient(90deg,#ff5c74,#ff9a73,#ffd66d)] transition-[width] duration-500"
                                style={{ width: `${Math.max(task.progress, task.status === "queued" ? 6 : 0)}%` }}
                              />
                            </div>
                          ) : null}
                          {task.error ? <p className="mt-1 text-[10px] font-semibold text-red-600">{task.error}</p> : null}
                        </div>
                        {task.status !== "running" ? (
                          <span
                            onClick={(event) => {
                              event.stopPropagation();
                              dismissMerchantStyleTask(task.id);
                            }}
                            className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[#a88a93] hover:bg-[#fff0f4]"
                          >
                            <X size={14} />
                          </span>
                        ) : null}
                      </div>
                    </button>
                  ))}
                </div>
              </SoftCard>
            ) : null}

            {activeUploadTask && activePreviewResult ? (
              <SoftCard className="bg-[linear-gradient(135deg,#fffbeb,#fff3f5)] border border-[#ffdee3] relative overflow-hidden">
                <div className="absolute top-2 right-2 flex items-center gap-0.5 bg-yellow-400/90 text-white text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider">
                  <Sparkles size={8} fill="white" />
                  预览已生成
                </div>
                <h3 className="text-xs font-black text-[#27101c] flex items-center gap-1">
                  第三步完成：确认款式图无误后即可上首页
                </h3>
                <p className="mt-1 text-[10px] text-[#9b7580]">
                  左侧是商家原图，右侧是用固定模板生成的上架款式图。
                </p>

                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <p className="text-[9px] font-bold text-[#9b7580]">原图</p>
                    <div className="relative h-16 w-full shrink-0 rounded-[12px] overflow-hidden border border-pink-100 bg-white">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={activePreviewResult.source_image_url}
                        alt="source"
                        className="h-full w-full object-cover"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[9px] font-bold text-[#9b7580]">设计图</p>
                    {activePreviewIsAiGenerated ? (
                      <div className="relative h-16 w-full shrink-0 rounded-[12px] overflow-hidden border border-pink-100 bg-white">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={activePreviewResult.design_image_url}
                          alt="design"
                          className="h-full w-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="flex h-16 w-full items-center justify-center rounded-[12px] border border-dashed border-[#f0c8d2] bg-[#fff8fa] px-2 text-center">
                        <span className="text-[9px] font-semibold leading-4 text-[#b87a88]">
                          AI 预览未生成，不展示兜底图
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex gap-3">
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-xs font-bold truncate text-[#27101c]">
                      {activeUploadTask.style_name}
                    </p>
                    <p className="text-[10px] text-[#ff5c74] font-black">
                      参考价: ¥{activeUploadTask.style_price} · 草稿编号: {activePreviewResult.draft_id}
                    </p>
                    <p className="text-[9px] font-bold text-[#7b515c]">
                      生成状态: {activePreviewResult.render_status || "unknown"} · 通道: {activePreviewResult.render_channel || "n/a"}
                    </p>
                    {!activePreviewIsAiGenerated ? (
                      <p className="text-[9px] font-semibold text-amber-700">
                        AI 生成失败，未展示兜底图，请重试后再确认上架。
                      </p>
                    ) : null}
                    {activePreviewResult.render_error ? <p className="text-[9px] font-semibold text-amber-700">生成提示: {activePreviewResult.render_error}</p> : null}
                    {activeUploadTask.published_style ? (
                      <p className="text-[9px] font-semibold text-emerald-700">已同步首页，可在款式墙中看到这张新图。</p>
                    ) : null}
                  </div>
                  {activePreviewIsAiGenerated ? (
                    <div className="relative h-16 w-16 shrink-0 rounded-[12px] overflow-hidden border border-pink-100 bg-white">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={activePreviewResult.design_image_url}
                        alt="uploaded"
                        className="h-full w-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-[12px] border border-dashed border-[#f0c8d2] bg-[#fff8fa] px-2 text-center">
                      <span className="text-[8px] font-semibold leading-4 text-[#b87a88]">未出图</span>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handlePublishStyle(activeUploadTask.id)}
                  disabled={publishingTaskId === activeUploadTask.id || Boolean(activeUploadTask.published_style) || !activePreviewIsAiGenerated}
                  className="mt-4 w-full h-10 rounded-full bg-[#27101c] hover:bg-[#3d1a2d] disabled:bg-[#d7c7cc] disabled:cursor-not-allowed transition-all text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-neutral-100"
                >
                  {publishingTaskId === activeUploadTask.id ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      正在确认上架...
                    </>
                  ) : !activePreviewIsAiGenerated ? (
                    <>
                      <X size={14} />
                      预览失败，无法上架
                    </>
                  ) : activeUploadTask.published_style ? (
                    <>
                      <CheckCircle2 size={14} />
                      已上架到首页
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      第四步：确认上架到首页
                    </>
                  )}
                </button>
              </SoftCard>
            ) : null}

            {hasCompletedTaxonomy && !activePreviewResult ? (
              <SoftCard className="bg-[#fff8fa] border border-[#ffdee3]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-black text-[#27101c]">下一步：生成款式图预览</h2>
                    <p className="mt-1 text-[10px] leading-5 text-[#9b7580]">
                      六维标签已经补齐，现在可以点击上方按钮生成上架预览图。
                    </p>
                  </div>
                  <span className="rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-1 text-[10px] font-black">
                    已可出图
                  </span>
                </div>
              </SoftCard>
            ) : null}
          </div>
        )}

        {activeTab === "manage" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
              <span className="text-[10px] font-bold text-[#7b515c]">
                管理你已上架的款式，查看实时流量和试戴数据
              </span>
              <button
                onClick={loadMerchantStyles}
                disabled={loadingStyles}
                className="text-[11px] font-black text-[#ff5c74] hover:underline"
              >
                {loadingStyles ? "刷新中..." : "刷新数据"}
              </button>
            </div>

            {loadingStyles && merchantStyles.length === 0 ? (
              <div className="rounded-[20px] bg-white p-8 text-center border border-neutral-100/60 flex flex-col items-center justify-center">
                <Loader2 className="animate-spin text-[#ff5c74] mb-2" size={24} />
                <p className="text-xs text-[#9b7580] font-bold">正在加载款式与分析数据...</p>
              </div>
            ) : merchantStyles.length === 0 ? (
              <div className="rounded-[20px] bg-white p-8 text-center border border-neutral-100">
                <p className="text-sm text-[#9b7580]">你还没有上架任何自定义美甲款式</p>
                <button
                  onClick={() => setActiveTab("upload")}
                  className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#ff5c74] hover:underline"
                >
                  <Plus size={14} /> 去款式上架
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {merchantStyles.map((style) => {
                  const analytics = style.analytics || { views: 0, try_ons: 0, interests: 0, bookings: 0 };
                  const isActive = style.is_active !== false;
                  const displayPrice = style.price?.trim()
                    ? style.price.replace(/^¥+/, "")
                    : style.price_level === "¥¥¥"
                      ? "258"
                      : style.price_level === "¥¥"
                        ? "158"
                        : "98";

                  return (
                    <SoftCard key={style.id} className="bg-white border border-neutral-100 p-4 relative overflow-hidden transition-all duration-200">
                      {/* Style Header */}
                      <div className="flex gap-3 items-start">
                        <div
                          onClick={() => {
                            if (style.image_url) setPreviewImageUrl(style.image_url);
                          }}
                          className="relative h-16 w-16 overflow-hidden rounded-xl bg-[#fff0f4] border border-neutral-100/60 shrink-0 cursor-pointer active:scale-95 transition-transform"
                        >
                          {style.image_url ? (
                            // Merchant uploads may point at third-party GPT result URLs.
                            // Use a plain img here so thumbnails do not depend on Next's optimizer fetch.
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={style.image_url}
                              alt={style.name}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <div className="h-full w-full bg-neutral-100" />
                          )}
                          {!isActive && (
                            <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px] grid place-items-center">
                              <span className="text-[10px] text-white font-black px-1.5 py-0.5 rounded-md bg-neutral-800/80">
                                已下架
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-sm font-black text-[#27101c] truncate">{style.name}</h3>
                            <span className={`text-[10px] font-black shrink-0 px-2 py-0.5 rounded-full ${
                              isActive 
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-100" 
                                : "bg-neutral-100 text-neutral-500 border border-neutral-200"
                            }`}>
                              {isActive ? "上架中" : "已下架"}
                            </span>
                          </div>
                          <p className="text-xs font-black text-[#ff5c74] mt-1">¥{displayPrice}</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {style.tags?.slice(0, 3).map((tag: string) => (
                              <span key={tag} className="text-[9px] bg-[#fdfafb] border border-[#fcecee] text-[#7b515c] px-1.5 py-0.5 rounded-md">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Divider */}
                      <div className="h-px bg-neutral-100 my-3" />

                      {/* Analytics Dashboard Grid */}
                      <div className="grid grid-cols-4 gap-2 text-center">
                        <div className="bg-[#fcf8fa] rounded-xl p-2 border border-[#f6eaed]/40">
                          <p className="text-xs font-black text-[#27101c]">{analytics.views}</p>
                          <p className="text-[9px] text-[#9b7580] mt-0.5">👁️ 浏览量</p>
                        </div>
                        <div className="bg-[#fcf8fa] rounded-xl p-2 border border-[#f6eaed]/40">
                          <p className="text-xs font-black text-[#ff5c74]">{analytics.try_ons}</p>
                          <p className="text-[9px] text-[#9b7580] mt-0.5">💅 试戴量</p>
                        </div>
                        <div className="bg-[#fcf8fa] rounded-xl p-2 border border-[#f6eaed]/40">
                          <p className="text-xs font-black text-[#ae4784]">{analytics.interests}</p>
                          <p className="text-[9px] text-[#9b7580] mt-0.5">❤️ 有意向</p>
                        </div>
                        <div className="bg-[#fcf8fa] rounded-xl p-2 border border-[#f6eaed]/40">
                          <p className="text-xs font-black text-[#10b981]">{analytics.bookings}</p>
                          <p className="text-[9px] text-[#9b7580] mt-0.5">📅 打算做</p>
                        </div>
                      </div>

                      {/* Footer Actions */}
                      <div className="mt-3 flex items-center justify-between bg-neutral-50/60 rounded-xl p-2 border border-neutral-100/40">
                        <span className="text-[9px] text-[#7b515c] font-black">
                          {isActive ? "款式在顾客首页正常展示" : "款式已被隐藏，顾客无法查看"}
                        </span>
                        
                        <button
                          onClick={() => handleToggleStyleActive(style.id, isActive)}
                          className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                            isActive
                              ? "bg-red-50 text-red-600 hover:bg-red-100/70"
                              : "bg-[#27101c] text-white hover:bg-neutral-800"
                          }`}
                        >
                          {isActive ? "下架款式" : "重新上架"}
                        </button>
                      </div>
                    </SoftCard>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "settings" && (
          <SoftCard className="bg-white border border-neutral-100">
            <h2 className="text-sm font-black text-[#27101c] mb-3">修改店铺基本资料</h2>
            <form onSubmit={handleSaveSettings} className="space-y-4">
              {/* Shop Name */}
              <div>
                <label className="block text-xs font-bold text-[#7b515c] mb-1">店铺名称</label>
                <input
                  type="text"
                  value={shopName}
                  onChange={(e) => setShopName(e.target.value)}
                  placeholder="例如: Library Nail Spa"
                  className="w-full h-10 px-4 rounded-full border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb]"
                />
              </div>

              {/* Address */}
              <div>
                <label className="block text-xs font-bold text-[#7b515c] mb-1">店铺地址</label>
                <textarea
                  value={shopAddress}
                  onChange={(e) => setShopAddress(e.target.value)}
                  placeholder="例如: 福田区福华三路星河COCO Park三楼"
                  rows={2}
                  className="w-full p-3 rounded-[16px] border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb] resize-none"
                />
              </div>

              {/* Waiting status & Schedule status */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#7b515c] mb-1">实时等待时间</label>
                  <select
                    value={shopWaitTime}
                    onChange={(e) => setShopWaitTime(e.target.value)}
                    className="w-full h-10 px-3 rounded-full border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb] appearance-none"
                  >
                    <option value="无需等待">空闲中 - 无需等待</option>
                    <option value="排队约15分钟">繁忙中 - 需等15分钟</option>
                    <option value="排队约30分钟">繁忙中 - 需等30分钟</option>
                    <option value="排队约60分钟+">极度繁忙 - 需等1小时+</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#7b515c] mb-1">今日可约状态</label>
                  <select
                    value={shopSchedule}
                    onChange={(e) => setShopSchedule(e.target.value)}
                    className="w-full h-10 px-3 rounded-full border border-[#f5dce3] text-xs font-medium focus:outline-none focus:border-[#ff5c74] bg-[#fdfafb] appearance-none"
                  >
                    <option value="排期充裕">排期充裕 (到店即做)</option>
                    <option value="今日可约">今日可约 (先约先得)</option>
                    <option value="可约晚间">仅剩晚间时段</option>
                    <option value="今日已约满">今日约满 (不可预约)</option>
                  </select>
                </div>
              </div>

              {/* Environment Amenities & Facilities */}
              <div>
                <label className="block text-xs font-bold text-[#7b515c] mb-2">店铺配套设施与特色</label>
                <div className="grid grid-cols-2 gap-2 bg-[#fdfafb] p-3 rounded-[16px] border border-[#f5dce3]">
                  <label className="flex items-center gap-2 text-xs font-semibold text-[#5a3a43] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={facTea}
                      onChange={(e) => setFacTea(e.target.checked)}
                      className="rounded text-[#ff5c74] focus:ring-[#ff5c74] h-4 w-4"
                    />
                    提供零食饮料
                  </label>
                  <label className="flex items-center gap-2 text-xs font-semibold text-[#5a3a43] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={facWifi}
                      onChange={(e) => setFacWifi(e.target.checked)}
                      className="rounded text-[#ff5c74] focus:ring-[#ff5c74] h-4 w-4"
                    />
                    免费高速WiFi
                  </label>
                  <label className="flex items-center gap-2 text-xs font-semibold text-[#5a3a43] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={facParking}
                      onChange={(e) => setFacParking(e.target.checked)}
                      className="rounded text-[#ff5c74] focus:ring-[#ff5c74] h-4 w-4"
                    />
                    免费专属停车
                  </label>
                  <label className="flex items-center gap-2 text-xs font-semibold text-[#5a3a43] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={facPrivateRoom}
                      onChange={(e) => setFacPrivateRoom(e.target.checked)}
                      className="rounded text-[#ff5c74] focus:ring-[#ff5c74] h-4 w-4"
                    />
                    独立私密包间
                  </label>
                </div>
              </div>

              {/* Active Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-[#7b515c]">店铺活跃度评分</label>
                  <span className="text-xs font-black text-[#ff5c74]">
                    {(shopActiveScore * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.01"
                  value={shopActiveScore}
                  onChange={(e) => setShopActiveScore(parseFloat(e.target.value))}
                  className="w-full accent-[#ff5c74]"
                />
                <p className="text-[9px] text-[#9b7580] mt-0.5 leading-normal">
                  高活跃度评分的店铺将在消费端获得更高的优先排序和搜索曝光率。
                </p>
              </div>

              {/* Success Notification */}
              {settingsSuccess && (
                <div className="rounded-[16px] bg-green-50 border border-green-200 p-3 text-xs font-bold text-green-600 text-center animate-pulse">
                  ✓ 店铺设置保存成功！
                </div>
              )}

              {/* Submit button */}
              <button
                type="submit"
                disabled={savingSettings}
                className="w-full h-10 rounded-full bg-[#27101c] hover:bg-[#3d1a2d] active:scale-98 transition-all text-white text-xs font-bold flex items-center justify-center gap-1 shadow-md shadow-neutral-100"
              >
                {savingSettings ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  "保存设置"
                )}
              </button>
            </form>
          </SoftCard>
        )}
      </div>
      {previewImageUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
          <div className="relative max-w-full max-h-[85vh] flex flex-col items-center">
            <button
              onClick={() => setPreviewImageUrl(null)}
              className="absolute -top-12 right-0 grid h-10 w-10 place-items-center rounded-full bg-white/20 text-white hover:bg-white/30 active:scale-95 transition-all"
            >
              <X size={20} />
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewImageUrl}
              alt="款式大图"
              className="max-w-full max-h-[75vh] object-contain rounded-2xl shadow-2xl border border-white/10 bg-black/20 p-1"
            />
          </div>
        </div>
      )}
    </PhoneShell>
  );
}

export function StorePlaceholder() {
  return (
    <PhoneShell title="门店详情" active="home">
      <div className="px-4 pt-3">
        <SoftCard>
          <Store className="text-[#ff5c74]" size={28} />
          <h1 className="mt-4 text-2xl font-black">附近门店</h1>
          <p className="mt-2 text-xs leading-5 text-[#8f6b75]">选择店铺后可查看报价、距离、评分和可预约时间。</p>
          <div className="mt-4 flex items-center gap-2 text-xs font-bold text-[#9b7580]">
            <MapPin size={14} />
            当前位置 3km 范围
            <Star size={14} fill="#ffb600" className="text-[#ffb600]" />
            优先高评分
          </div>
        </SoftCard>
      </div>
    </PhoneShell>
  );
}
