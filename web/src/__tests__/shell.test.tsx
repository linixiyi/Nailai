import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { PhoneShell, PrimaryButton, SoftCard } from "@/components/prototype/Shell";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ back: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href?: string } & AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

describe("Shell components", () => {
  describe("PhoneShell", () => {
    it("renders children content", () => {
      render(
        <PhoneShell title="测试" active="home">
          <p>Hello NailAI</p>
        </PhoneShell>,
      );
      expect(screen.getByText("Hello NailAI")).toBeTruthy();
    });

    it("renders brand mark when no title", () => {
      render(<PhoneShell active="home"><div /></PhoneShell>);
      expect(screen.getByText("NailAI")).toBeTruthy();
    });

    it("renders bottom navigation", () => {
      render(<PhoneShell active="home"><div /></PhoneShell>);
      expect(screen.getByText("首页")).toBeTruthy();
      expect(screen.getByText("换美甲")).toBeTruthy();
      expect(screen.getByText("推荐")).toBeTruthy();
      expect(screen.getByText("悬赏")).toBeTruthy();
      expect(screen.getByText("我的")).toBeTruthy();
    });
  });

  describe("PrimaryButton", () => {
    it("renders as a link when href is provided", () => {
      render(<PrimaryButton href="/test">前往</PrimaryButton>);
      const link = screen.getByRole("link");
      expect(link.getAttribute("href")).toBe("/test");
    });

    it("renders as a button when no href", () => {
      render(<PrimaryButton>点击</PrimaryButton>);
      expect(screen.getByRole("button")).toBeTruthy();
    });

    it("applies disabled state", () => {
      render(<PrimaryButton disabled>禁用</PrimaryButton>);
      expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
    });
  });

  describe("SoftCard", () => {
    it("renders children", () => {
      render(<SoftCard><span>card content</span></SoftCard>);
      expect(screen.getByText("card content")).toBeTruthy();
    });
  });
});
