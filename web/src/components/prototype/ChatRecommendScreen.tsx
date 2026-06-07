"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Bot, Loader2, Sparkles, Send, Zap } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { NailStyleThumb } from "./Cards";
import { PhoneShell, SoftCard } from "./Shell";
import { fetchStyles, postChatStream, subscribeStyleCatalogUpdates } from "@/lib/api";
import { inventoryStyles } from "@/lib/styles";
import type { ChatResponse, NailStyle } from "@/lib/types";

type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  styles?: NailStyle[];
  loading?: boolean;
};

const starterPrompts = [
  "想要通勤又显白的款式",
  "帮我找短甲友好的款式",
  "想做更适合约会拍照的美甲",
  "我喜欢清透、干净、低饱和",
];

function buildFallbackReply(message: string, selectedStyleIds: string[], styles: NailStyle[]): ChatResponse {
  const matched = styles.filter((style) => selectedStyleIds.includes(style.id)).slice(0, 4);
  const fallbackStyles = matched.length ? matched : styles.slice(0, 4);
  return {
    reply: `我先按“${message}”帮你从库存里挑了几款更稳的方向，重点会优先考虑显白、上手快、和当前手型更兼容的版本。`,
    intent: "fallback-recommendation",
    recommended_styles: fallbackStyles,
    follow_up_questions: ["偏短甲还是中长甲？", "更想要通勤还是拍照出片？", "要不要我优先找库存现货款？"],
    channel: "local-fallback",
    model: null,
  };
}

function ToneChip({ children }: { children: React.ReactNode }) {
  return <span className="inline-flex items-center rounded-full bg-[#fff0f4] px-3 py-1 text-[11px] font-bold text-[#ff5c74]">{children}</span>;
}

function QuickChip({
  children,
  onClick,
  selected = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  selected?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-2 text-[12px] font-bold transition-colors ${
        selected ? "border-[#ff5c74] bg-[#ff5c74] text-white" : "border-[#f1d6de] bg-white text-[#5d404a] active:bg-[#fff0f4]"
      }`}
    >
      {children}
    </button>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";
  return (
    <div className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
      <div className={`max-w-[84%] rounded-[22px] px-4 py-3 shadow-sm ${isAssistant ? "bg-white text-[#2a1921]" : "bg-[#ff5c74] text-white"}`}>
        <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] opacity-70">
          {isAssistant ? <Bot size={11} /> : null}
          {isAssistant ? "NailAI 推荐助手" : "你"}
        </div>
        <p className="whitespace-pre-line text-[13px] leading-5">{message.content}</p>
        {isAssistant && message.styles?.length ? (
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {message.styles.slice(0, 5).map((style) => (
              <Link
                key={style.id}
                href={`/ai-tryon?styleId=${style.id}`}
                className="min-w-[126px] max-w-[126px] shrink-0 rounded-[14px] border border-[#f0d9e0] bg-[#fff7fa] p-2"
              >
                <div className="h-20 overflow-hidden rounded-[10px] bg-white">
                  <NailStyleThumb style={style} />
                </div>
                <p className="mt-1 truncate text-[11px] font-bold text-[#5d404a]">{style.name}</p>
              </Link>
            ))}
          </div>
        ) : null}
        {message.loading ? (
          <div className="mt-3 flex items-center gap-2 text-[11px] font-semibold text-[#a88a93]">
            <Loader2 size={14} className="animate-spin" />
            正在按甲型和库存整理适合你的方向...
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PromptSummary({ style }: { style?: NailStyle }) {
  if (!style) return null;

  return (
    <SoftCard className="border border-[#f8d8df] bg-[linear-gradient(135deg,#fff7f9,#fff1e8)] p-4">
      <div className="flex items-start gap-3">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-[16px] bg-white shadow-sm">
          <Sparkles className="text-[#ff5c74]" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-[11px] font-bold text-[#ff5c74]">当前围绕的款式</p>
              <h2 className="truncate text-sm font-black">{style.name}</h2>
            </div>
            <ToneChip>{style.finish}</ToneChip>
          </div>
          <p className="mt-1 line-clamp-2 text-[12px] leading-5 text-[#8f6b75]">
            {style.color} · {style.price_level} · {style.tags.slice(0, 3).join(" / ")}
          </p>
          <div className="mt-3 flex items-center gap-2">
            {style.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-[#a06f7d] shadow-sm">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </SoftCard>
  );
}

export function ChatRecommendScreen() {
  const searchParams = useSearchParams();
  const styleId = searchParams.get("styleId");
  const [styles, setStyles] = useState<NailStyle[]>(inventoryStyles);
  const defaultStyle = useMemo(
    () => styles.find((style) => !style.id.startsWith("fixed-target")) ?? styles[0] ?? inventoryStyles[0],
    [styles],
  );
  const focusedStyle = useMemo(() => styles.find((style) => style.id === styleId) ?? defaultStyle, [defaultStyle, styleId, styles]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "assistant-welcome",
      role: "assistant",
      content:
        "你好，我可以帮你按手型、场景、长度和库存现货来缩小范围。你可以直接告诉我“通勤、显白、短甲”这类需求，我会把结果拆成可试戴的款式。",
    },
  ]);
  const [followUps, setFollowUps] = useState<string[]>(["想先看通勤款还是约会款？", "要不要优先短甲友好？"]);
  const [lastIntent, setLastIntent] = useState("库存推荐");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = () => {
      fetchStyles()
        .then((nextStyles) => {
          if (!active) return;
          const stylesWithImages = nextStyles.filter((style) => Boolean(style.image_url));
          const runtimeStyles = stylesWithImages.length ? stylesWithImages : nextStyles;
          setStyles(runtimeStyles);
        })
        .catch(() => {
          if (active) setStyles(inventoryStyles);
        });
    };
    refresh();
    const unsubscribe = subscribeStyleCatalogUpdates(refresh);
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (messages.length <= 2) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, followUps, isSending]);

  useEffect(() => {
    if (focusedStyle) {
      setMessages((current) => {
        if (current.length > 1) return current;
        return [
          ...current,
          {
            id: "assistant-context",
            role: "assistant",
            content: `我已经看到你当前聚焦的是「${focusedStyle.name}」。如果你愿意，我可以围绕它继续帮你找“短甲版 / 长甲版 / 更显白版”。`,
          },
        ];
      });
    }
  }, [focusedStyle, styles]);

  async function submitChat(message: string) {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    setInput("");
    setIsSending(true);
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    const loadingMessageId = `assistant-loading-${Date.now()}`;

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: loadingMessageId,
        role: "assistant",
        content: "我在帮你筛库存和偏好，稍等一下。",
        loading: true,
      },
    ]);

    try {
      const response = await postChatStream(trimmed, [focusedStyle?.id ?? styles[0]?.id ?? inventoryStyles[0].id], (delta) => {
        setMessages((current) =>
          current.map((item) => {
            if (item.id !== loadingMessageId) return item;
            return {
              ...item,
              loading: true,
              content: `${item.content}${delta.text ?? ""}`,
            };
          }),
        );
        if (delta.channel || delta.intent) {
          setLastIntent(`${delta.channel ?? "chat"} · ${delta.intent ?? "chat-recommendation"}`);
        }
      });
      const nextStyles = response.recommended_styles.length ? response.recommended_styles : styles.slice(0, 4);
      setFollowUps(response.follow_up_questions.length ? response.follow_up_questions : ["还有没有更偏短甲的版本？", "可以再帮我找一组显白款吗？"]);
      setLastIntent(`${response.channel ?? "chat"} · ${response.intent || "chat-recommendation"}`);
      setMessages((current) =>
        current.flatMap((item) =>
          item.id === loadingMessageId
            ? [
                {
                  ...item,
                  loading: false,
                  content: response.reply || item.content,
                  styles: nextStyles,
                },
              ]
            : [item],
        ),
      );
    } catch {
      const fallback = buildFallbackReply(trimmed, [focusedStyle?.id ?? styles[0]?.id ?? inventoryStyles[0].id], styles);
      setFollowUps(fallback.follow_up_questions);
      setLastIntent("fallback-recommendation");
      setMessages((current) =>
        current.flatMap((item) =>
          item.id === loadingMessageId
            ? [
                {
                  ...item,
                  loading: false,
                  content: fallback.reply,
                  styles: fallback.recommended_styles,
                },
              ]
            : [item],
        ),
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <PhoneShell
      title="Chat 推荐"
      active="chat"
      bottomPanel={
        <div className="rounded-[24px] border border-[#eadde1] bg-white p-2 shadow-xl shadow-[#dba3b4]/15">
          <div className="flex items-end gap-2">
            <label className="flex min-h-12 flex-1 items-end gap-2 rounded-[18px] bg-[#faf6f7] px-3 py-3">
              <Sparkles size={16} className="mb-0.5 shrink-0 text-[#d1aab5]" />
              <textarea
                rows={1}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void submitChat(input);
                  }
                }}
                placeholder="告诉我你想要的款式..."
                className="max-h-24 min-h-5 w-full resize-none bg-transparent text-[13px] font-medium leading-5 outline-none placeholder:text-[#b898a2]"
              />
            </label>
            <button
              type="button"
              aria-label="发送消息"
              onClick={() => submitChat(input)}
              disabled={!input.trim() || isSending}
              className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#ff5c74] text-white shadow-lg shadow-[#ff5c74]/30 disabled:bg-[#eccdd5]"
            >
              {isSending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      }
    >
      <div className="space-y-4 px-4 py-4">
        <div className="flex items-center gap-3 rounded-[22px] bg-[linear-gradient(135deg,#2b0d1b,#ff7c94)] px-4 py-3 text-white shadow-lg shadow-[#ff5c74]/15">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-[16px] bg-white/15">
            <Bot size={22} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[10px] font-bold tracking-[0.16em] text-white/75">
              <Zap size={11} />
              智能推荐助手
            </div>
            <p className="mt-1 text-[12px] leading-5 text-white/90">先确认甲型，再从库存中筛选更适合的可试戴款式。</p>
          </div>
        </div>

        <PromptSummary style={focusedStyle} />

        <div className="space-y-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="flex flex-wrap gap-2">
          {(messages.length <= 2 ? starterPrompts : followUps).map((item) => (
            <QuickChip key={item} onClick={() => submitChat(item)} selected={input === item}>
              {item}
            </QuickChip>
          ))}
        </div>

        <div className="flex items-center justify-center gap-2 pb-2 text-[10px] font-semibold text-[#b4939d]">
          <Sparkles size={12} />
          {lastIntent}
        </div>
      </div>
    </PhoneShell>
  );
}
