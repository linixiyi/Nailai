# NailAI Web

Next.js App Router frontend for the NailAI P0 demo and 375x812 prototype pages.

```bash
npm install
npm run dev
```

Local URL: `http://localhost:3003`

The current product pages call the Next.js same-origin proxy by default:

```env
AI_SERVICE_URL=http://127.0.0.1:8008
NEXT_PUBLIC_API_BASE_URL=
```

Only set `NEXT_PUBLIC_API_BASE_URL` for split-domain deployment with a browser-reachable API domain. For same-server deployment, keep it empty so phones hit `/api/v1` on the web host instead of trying to connect to their own `localhost`.
