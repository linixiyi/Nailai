import type { Metadata } from "next";
import { Cormorant_Garamond, JetBrains_Mono, Karla } from "next/font/google";
import Script from "next/script";
import { DiyTaskWindow } from "@/components/prototype/DiyTaskWindow";
import { TryOnTaskWindow } from "@/components/prototype/TryOnTaskWindow";
import "./globals.css";

const display = Cormorant_Garamond({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const sans = Karla({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "NailAI · 指尖上的高级时装周",
  description: "瀑布流款式墙、AI 智能试戴、Chat 推荐与 DIY 悬赏。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cryptoRandomUuidPolyfill = `(() => {
    const scope = typeof globalThis !== "undefined" ? globalThis : window;
    const webCrypto = scope?.crypto;
    if (!webCrypto || typeof webCrypto.randomUUID === "function" || typeof webCrypto.getRandomValues !== "function") {
      return;
    }

    const createUuid = () => {
      const bytes = new Uint8Array(16);
      webCrypto.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
      return [
        hex.slice(0, 4).join(""),
        hex.slice(4, 6).join(""),
        hex.slice(6, 8).join(""),
        hex.slice(8, 10).join(""),
        hex.slice(10, 16).join(""),
      ].join("-");
    };

    try {
      Object.defineProperty(webCrypto, "randomUUID", {
        configurable: true,
        value: createUuid,
      });
    } catch (error) {
      try {
        webCrypto.randomUUID = createUuid;
      } catch (_assignError) {
        console.warn("Failed to install crypto.randomUUID polyfill", error);
      }
    }
  })();`;

  return (
    <html lang="zh-CN" className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <Script id="crypto-randomuuid-polyfill" strategy="beforeInteractive">
          {cryptoRandomUuidPolyfill}
        </Script>
        {children}
        <TryOnTaskWindow />
        <DiyTaskWindow />
      </body>
    </html>
  );
}
