"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronLeft, Home, MessageCircle, MoreHorizontal, Search, Sparkles, Trophy, User, X } from "lucide-react";

type PhoneShellProps = {
  title?: string;
  active?: "home" | "tryon" | "chat" | "bounty" | "mine";
  children: React.ReactNode;
  bottomPanel?: React.ReactNode;
};

const navItems = [
  { key: "home", label: "首页", href: "/", icon: Home, center: false },
  { key: "tryon", label: "换美甲", href: "/ai-tryon", icon: Sparkles, center: false },
  { key: "chat", label: "推荐", href: "/chat", icon: MessageCircle, center: true },
  { key: "bounty", label: "悬赏", href: "/diy-bounty", icon: Trophy, center: false },
  { key: "mine", label: "我的", href: "/me", icon: User, center: false },
] as const;

export function PhoneShell({ title, active = "home", children, bottomPanel }: PhoneShellProps) {
  return (
    <main className="h-dvh overflow-hidden bg-background text-foreground selection:bg-accent-pink/20 sm:bg-[radial-gradient(circle_at_top_left,rgba(255,20,147,0.10),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(197,160,89,0.16),transparent_30%),#f3efe7] sm:px-3 sm:py-6">
      <section className="relative mx-auto h-dvh w-full max-w-[440px] overflow-hidden bg-background sm:h-[812px] sm:rounded-[34px] sm:border sm:border-white/80 sm:shadow-2xl sm:shadow-black/10">
        <div className="relative flex h-full flex-col">
          <AppHeader title={title} brand={!title} back={Boolean(title)} />
          <div className={`min-h-0 flex-1 overflow-y-auto no-scrollbar ${bottomPanel ? "pb-4" : "pb-36"}`}>{children}</div>
          {bottomPanel ? (
            <div className="relative z-40 shrink-0 bg-[linear-gradient(180deg,rgba(253,252,249,0),#fdfcf9_18%)] px-4 pb-[98px] pt-3">
              {bottomPanel}
            </div>
          ) : null}
          <BottomNav active={active} />
        </div>
      </section>
    </main>
  );
}

export function AppHeader({ title, back, brand }: { title?: string; back?: boolean; brand?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();

  const [isSearching, setIsSearching] = useState(false);
  const [searchVal, setSearchVal] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const search = params.get("search") || "";
      if (search) {
        setSearchVal(search);
        setIsSearching(true);
      } else {
        setSearchVal("");
        setIsSearching(false);
      }
    }
  }, [pathname]);

  const handleSearchSubmit = (val: string) => {
    setSearchVal(val);
    if (typeof window !== "undefined") {
      const url = val ? `/?search=${encodeURIComponent(val)}` : "/";
      router.push(url);
    }
  };

  const handleCloseSearch = () => {
    setIsSearching(false);
    setSearchVal("");
    if (typeof window !== "undefined") {
      router.push("/");
    }
  };

  const fallbackByPath: Array<[RegExp, string]> = [
    [/^\/tryon-result$/, "/ai-tryon"],
    [/^\/style-detail\/.+$/, "/"],
    [/^\/bounty-detail\/.+$/, "/diy-bounty"],
    [/^\/diy-bounty\/create$/, "/diy-bounty"],
    [/^\/chat$/, "/"],
    [/^\/chat-recommend$/, "/"],
    [/^\/shop-recommend$/, "/"],
    [/^\/store-take-order$/, "/"],
    [/^\/ai-tryon$/, "/"],
  ];

  const fallback =
    fallbackByPath.find(([matcher]) => matcher.test(pathname))?.[1] ?? "/";

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push(fallback);
  };

  if (isSearching) {
    return (
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-black/5 bg-background/80 px-4 backdrop-blur-md">
        <div className="flex flex-1 items-center gap-2">
          <input
            type="text"
            value={searchVal}
            onChange={(e) => handleSearchSubmit(e.target.value)}
            placeholder="搜索美甲款式..."
            autoFocus
            className="h-9 flex-1 rounded-full border border-black/5 bg-[#f6f2eb] px-4 text-xs font-bold text-foreground outline-none focus:border-accent-pink/30 focus:ring-1 focus:ring-accent-pink/30"
          />
          <button
            type="button"
            onClick={handleCloseSearch}
            className="grid size-9 shrink-0 place-items-center rounded-full border border-black/5 bg-white shadow-sm transition-transform active:scale-95"
            aria-label="关闭搜索"
          >
            <X className="size-4" />
          </button>
        </div>
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-black/5 bg-background/80 px-5 backdrop-blur-md">
      <div className="flex min-w-10 items-center gap-2">
        {back ? (
          <button
            type="button"
            onClick={handleBack}
            className="grid size-9 place-items-center rounded-full border border-black/5 bg-white shadow-sm transition-transform active:scale-95"
          >
            <ChevronLeft className="size-4" />
          </button>
        ) : brand ? (
          <Link href="/" className="font-display text-2xl font-semibold italic tracking-tight">
            NailAI
          </Link>
        ) : null}
      </div>
      {title ? (
        <h1 className="absolute left-1/2 -translate-x-1/2 font-display text-lg font-semibold tracking-tight">{title}</h1>
      ) : null}
      <div className="relative flex items-center gap-2">
        {!title ? (
          <button
            type="button"
            onClick={() => setIsSearching(true)}
            className="grid size-9 place-items-center rounded-full border border-black/5 bg-white shadow-sm transition-transform active:scale-95"
            aria-label="打开搜索"
          >
            <Search className="size-4" />
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          className="grid size-9 place-items-center rounded-full border border-black/5 bg-white shadow-sm transition-transform active:scale-95"
          aria-label="更多选项"
        >
          <MoreHorizontal className="size-4" />
        </button>

        {menuOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 top-11 z-50 w-40 rounded-2xl border border-black/5 bg-white p-1.5 shadow-xl ring-1 ring-black/5 animate-reveal">
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  router.push("/test-dashboard");
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-bold text-[#5a3a43] hover:bg-[#fff0f4] transition-colors"
              >
                查看测试看板
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  router.push("/store-take-order");
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-bold text-[#5a3a43] hover:bg-[#fff0f4] transition-colors"
              >
                商家接单中心
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  if (confirm("确定要清除试戴历史和本地缓存数据吗？")) {
                    localStorage.clear();
                    sessionStorage.clear();
                    alert("本地缓存已成功清除！");
                    window.location.reload();
                  }
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-bold text-red-500 hover:bg-red-50 transition-colors"
              >
                清除历史与缓存
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}

export function BottomNav({ active }: { active: PhoneShellProps["active"] }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-50">
      <div className="relative mx-4 mb-6 pointer-events-auto">
        <nav className="flex h-16 items-center justify-around rounded-3xl border border-black/5 bg-white/90 px-2 shadow-2xl shadow-black/10 backdrop-blur-xl">
          {navItems.map(({ key, label, href, icon: Icon, center }) => {
            const selected = key === active;
            if (center) {
              return (
                <Link key={key} href={href} className="-mt-8 flex flex-col items-center justify-center">
                  <div className="flex size-14 items-center justify-center rounded-full bg-foreground text-background shadow-lg shadow-black/30 ring-4 ring-background">
                    <Icon className="size-5" strokeWidth={2} />
                  </div>
                  <span className="mt-1 text-[10px] font-bold text-foreground">{label}</span>
                </Link>
              );
            }
            return (
              <Link key={key} href={href} className={`flex flex-col items-center gap-1 transition-opacity ${selected ? "opacity-100" : "opacity-40 hover:opacity-70"}`}>
                {selected ? <div className="size-1.5 rounded-full bg-accent-pink" /> : <Icon className="size-4" strokeWidth={1.75} />}
                <span className="text-[10px] font-bold text-foreground">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

export function BrandMark() {
  return <span className="font-display text-2xl font-semibold italic tracking-tight">NailAI</span>;
}

export function SectionTitle({ title, actionHref }: { title: string; actionHref?: string }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      {actionHref ? (
        <Link href={actionHref} className="text-xs font-semibold text-accent-pink">
          更多 →
        </Link>
      ) : null}
    </div>
  );
}

export function PrimaryButton({
  children,
  disabled,
  onClick,
  href,
}: {
  children: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  href?: string;
}) {
  const className =
    "flex h-14 items-center justify-center gap-2 rounded-full bg-gradient-to-r from-accent-wine via-accent-pink to-accent-purple px-5 text-sm font-bold text-white shadow-2xl shadow-accent-pink/30 transition-transform active:scale-[0.98] disabled:opacity-60";
  if (href) {
    return (
      <Link href={href} onClick={onClick} className={className}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" disabled={disabled} onClick={onClick} className={className}>
      {children}
    </button>
  );
}

type SoftCardProps = React.ComponentPropsWithoutRef<"section">;

export function SoftCard({ children, className = "", ...props }: SoftCardProps) {
  return <section className={`rounded-3xl border border-black/5 bg-white p-5 shadow-sm ${className}`} {...props}>{children}</section>;
}
