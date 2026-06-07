# NailAI Engineering Operations Manual

## 1. Product Requirement Fit

NailAI's MVP is not a generic gallery app. Every engineering decision should support the P0 user story:

1. User opens the mobile-first NailAI web app.
2. User enters AI try-on.
3. User uploads a hand photo with guardrails for usable hand posture.
4. User selects a nail style.
5. Frontend sends both the hand image and selected style image to FastAPI.
6. FastAPI calls the image2-compatible generation layer.
7. Frontend displays the returned `result_image_url`.
8. User can retry, view style detail, or find matching shops.

P1 pages such as shop recommendation, DIY bounty, and store order intake should be real navigable pages, but may use seed data until Supabase persistence is ready.

## 2. Repository Map

```text
.
├── AGENTS.md                 # Agent rules and progressive management entry
├── ARCHITECTURE.md           # High-level architecture and API contract
├── README.md                 # Project overview and quick start
├── ai-service/               # FastAPI AI and seed data service
├── ops/                      # Engineering ops manual and issue records
├── supabase/                 # Database migrations
└── web/                      # Next.js frontend
```

Important frontend paths:

- `web/src/app/`: App Router pages.
- `web/src/components/prototype/`: 375x812 prototype UI components.
- `web/src/lib/api.ts`: frontend-to-FastAPI client.
- `web/src/lib/prototypeData.ts`: local fallback seed data.
- `web/public/modao-assets/`: Modao-exported visual assets.
- `web/public/style-images/`: imported nail style inventory images.

Important backend paths:

- `ai-service/app/main.py`: FastAPI app registration.
- `ai-service/app/routers/nail_try_on.py`: AI try-on endpoint.
- `ai-service/app/routers/chat.py`: chat endpoint.
- `ai-service/app/routers/demo_data.py`: demo shops, bounties, and store tasks.
- `ai-service/app/services/image2_client.py`: image2-compatible provider adapter.
- `ai-service/app/services/style_catalog.py`: style catalog service.

## 3. Runtime Setup

Backend:

```bash
cd ai-service
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8008
```

Frontend:

```bash
cd web
npm install
npm run dev
```

Environment:

```bash
cp web/.env.example web/.env.local
cp ai-service/.env.example ai-service/.env
```

Use:

```env
AI_SERVICE_URL=http://127.0.0.1:8008
NEXT_PUBLIC_API_BASE_URL=
IMAGE2_API_URL=
IMAGE2_API_KEY=
ENABLE_MOCK_AI=false
```

Never commit real API keys.

## 4. Frontend Implementation Standards

The prototype acceptance baseline is `375x812`. Desktop only needs to center the mobile canvas.

Required UI behavior:

- Keep the first screen focused on actual product use, not a marketing landing page.
- Use real components rather than full-page screenshot backgrounds.
- Show selected style images fully enough for recognition.
- Keep bottom navigation, top status area, rounded cards, pink-purple visual language, and iPhone-like proportions.
- The AI try-on page must send the chosen style, not a default or stale mock style.
- The result page must render `result_image_url` from backend/session state, not a hardcoded preview.

When adding a page, add it to App Router and make sure it has a 375x812 screenshot check.

## 5. Backend Implementation Standards

FastAPI is the source of AI and demo data APIs for the new pages.

Required endpoints:

- `GET /health`
- `GET /api/v1/styles`
- `POST /api/v1/nail/try-on`
- `POST /api/v1/chat`
- `GET /api/v1/shops`
- `GET /api/v1/bounties`
- `GET /api/v1/store/tasks`

Try-on multipart contract:

- `image`: uploaded hand photo.
- `style_image`: selected nail style image when available.
- `style_id`: selected style id.
- `style_payload`: JSON details for the selected style.

The image provider adapter should be isolated behind `image2_client.py` so the UI and routers do not depend on vendor-specific request shapes.

## 6. Data Strategy

Hackathon MVP priority:

1. Code seed data and static assets for speed.
2. FastAPI seed endpoints for frontend/backend separation.
3. Supabase migrations for later persistence.

Do not block P0 demo on Supabase unless the user explicitly asks for persistence work.

## 7. Branch And Sync Workflow

Common commands:

```bash
git status --short
git branch --show-current
git fetch origin
git switch main
git pull --ff-only origin main
```

View teammate branch:

```bash
git fetch origin
git switch <branch-name>
cd web && npm install && npm run dev
```

Return to main:

```bash
git switch main
git pull --ff-only origin main
```

Before pushing:

```bash
git status --short
cd web && npm run lint && npm run build
cd ../ai-service && ./.venv/bin/python -m compileall app
```

## 8. Definition Of Done

A change is done when:

- It supports the product flow described in section 1.
- The relevant harness checks pass.
- The UI opens at `http://localhost:3003`.
- FastAPI is healthy at `http://localhost:8008/health`.
- Any new problem or workaround is recorded in `ops/issues/KNOWN_ISSUES.md`.
