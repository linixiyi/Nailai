# NailAI Team Onboarding

This file is for teammates to run and deploy the current branch quickly.

## 1) Clone And Checkout

```bash
git clone https://github.com/linixiyi/MeiTuanHackathon.git
cd MeiTuanHackathon
git checkout feature/new-approach
```

## 2) Backend Setup (`ai-service`)

```bash
cd ai-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
```

Fill `ai-service/.env.local` with real keys (do not commit them):

- `QWEN_IMAGE_API_KEY`
- `DOUBAO_IMAGE_API_KEY`
- `GPT_IMAGE2_API_KEY`
- (optional but recommended) `VISION_ANALYZER_API_KEY`

Required key settings now:

- `VISION_ANALYZER_ENABLED=true`
- `VISION_ANALYZER_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `VISION_ANALYZER_MODEL=qwen3-vl-flash`

Run backend:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8008
```

Health check:

```bash
curl http://127.0.0.1:8008/health
```

## 3) Frontend Setup (`web`)

```bash
cd ../web
npm install
cp .env.local.example .env.local 2>/dev/null || true
```

Ensure frontend API target:

- `AI_SERVICE_URL=http://127.0.0.1:8008`
- `NEXT_PUBLIC_API_BASE_URL=`

Run frontend:

```bash
npm run dev -- --port 3003
```

Open:

- `http://localhost:3003/ai-tryon`
- `http://localhost:3003/test-dashboard`

## 4) QA Checklist

1. Upload hand image in `/ai-tryon`
2. Select style card (now shown upright in UI)
3. Choose generation channel (`hd` / `regular` / `fast`)
4. Generate result and verify on `/tryon-result`
5. Open `/test-dashboard` and verify:
   - channel/model
   - step timings
   - hand/style/result assets
   - prompt + structured payload

## 5) Server Deployment Notes

Use two services:

1. `web` (Next.js, Node runtime)
2. `ai-service` (FastAPI, Python runtime)

Production env recommendations:

- Backend CORS:
  - `CORS_ORIGINS=https://your-web-domain`
- Frontend API URL:
  - `NEXT_PUBLIC_API_BASE_URL=https://your-api-domain`

Never commit production API keys into repository history.
