import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const aiServiceUrl = process.env.AI_SERVICE_URL ?? "http://127.0.0.1:8008";

/**
 * NailAI Next.js 配置
 *
 * 前后端通信链路：
 *   浏览器 → Next.js → /api/v1/[...path] Route Handler（src/app/api/v1/[...path]/route.ts）
 *          → 服务端 fetch → FastAPI (AI_SERVICE_URL)
 *
 *   /generated/* 静态资源走 revrite 直接代理
 *   客户端不直连 FastAPI，避免跨域和端口问题
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  output: "standalone",
  outputFileTracingRoot: root,
  poweredByHeader: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.supabase.co" },
      { protocol: "https", hostname: "dashscope.aliyuncs.com" },
      { protocol: "https", hostname: "ark-content.volces.com" },
      { protocol: "https", hostname: "www.gpt2api.com" },
      { protocol: "https", hostname: "gpt2api.com" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/generated/:path*",
        destination: `${aiServiceUrl}/generated/:path*`,
      },
    ];
  },
};

export default nextConfig;
