# NailAI Agent Handoff

This document is the fastest on-ramp for another agent to continue the project without re-discovering the current state.

## Project Snapshot

- Repo: `/Users/Zhuanz/MeiTuanHackathon`
- Branch: `feature/new-approach`
- Frontend app: Next.js App Router in `web/`
- Backend app: FastAPI in `ai-service/`
- Current local ports used by the working setup:
  - Frontend: `http://localhost:3003`
  - Backend: `http://localhost:8008`

## Core Product Areas

1. `AI 换美甲`
   - Hand image + style image input
   - Strict local edit path for hand preservation
   - High quality path: `gpt-image-2`
   - Fast path: `wan2.7-image`
   - Regular path: `doubao-seedream-5-0-260128`

2. `Chat 推荐`
   - Uses `qwen-plus`
   - Recommendation should be filtered by taxonomy first, then explained by AI
   - Goal: choose nail shape / length first, then style

3. `DIY 悬赏`
   - Current generation model: `wan2.7-image`
   - Single output variant now
   - Supports user hand image + inspiration image + structured choices
   - Prompt is strongly constrained to avoid remaking the full hand

4. `悬赏 / 店铺 / 主页`
   - Home should not surface test data
   - DIY bounty page should use clean real/seeded demo data only

## What the Current State Intends

- Home page filters out obvious test assets and test catalog entries.
- DIY bounty creation is reduced to a single generated方案 image.
- The floating search bubble outside the phone frame was removed.
- Bounty demo images were replaced with:
  - `bounty-010.png`
  - `bounty-011.png`
  - `bounty-013.png`
- Old fake/ugly cache assets were cleaned from `web/public/modao-assets/`.

## Important Runtime Dependencies

### Frontend

- `web/.env.local` should point at the backend:
  - `AI_SERVICE_URL=http://127.0.0.1:8008`
  - `NEXT_PUBLIC_API_BASE_URL=`
- If the frontend shows stale content, hard refresh the browser.
- The frontend is sensitive to stale local browser cache because it uses a lot of local demo state.

### Backend

- `ai-service/.env.local` contains the live API credentials and provider routing.
- The backend must run on `8008` for the current frontend config.
- If the frontend cannot fetch, first check `AI_SERVICE_URL` and backend health.

## Model Map

| Area | Endpoint | Current Model |
|---|---|---|
| Chat recommendation | `POST /api/v1/chat` | `qwen-plus` |
| Chat streaming | `POST /api/v1/chat/stream` | `qwen-plus` |
| High quality try-on | `POST /api/v1/nail/try-on` with `generation_mode=hd` | `gpt-image-2` |
| Regular try-on | `POST /api/v1/nail/try-on` with `generation_mode=regular` | `doubao-seedream-5-0-260128` |
| Fast try-on | `POST /api/v1/nail/try-on` with `generation_mode=fast` | `wan2.7-image` |
| DIY bounty generation | `POST /api/v1/bounty/generate` | `wan2.7-image` |
| Style image cleanup / conversion | `POST /api/v1/store/styles/upload` | Mostly `doubao-seedream-5-0-260128`, fallback `gpt-image-2` |
| Vision grounding / nail localization | internal analysis layer | `qwen3-vl-flash` |

## Key Files

### Frontend

- `/Users/Zhuanz/MeiTuanHackathon/web/src/components/prototype/HomeScreen.tsx`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/components/prototype/DiyBountyCreateScreen.tsx`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/components/prototype/Shell.tsx`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/lib/api.ts`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/lib/prototypeData.ts`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/lib/types.ts`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/lib/historyStore.ts`
- `/Users/Zhuanz/MeiTuanHackathon/web/src/lib/diyTaskStore.ts`

### Backend

- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/main.py`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/routers/bounty.py`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/services/bounty_generator.py`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/services/style_catalog.py`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/services/supabase_db.py`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/app/routers/demo_data.py`

### Static assets and generated data

- `/Users/Zhuanz/MeiTuanHackathon/web/public/modao-assets/`
- `/Users/Zhuanz/MeiTuanHackathon/ai-service/generated/`

## Known Constraints / Watchouts

- Do not let the DIY hand-image flow drift into full image generation.
  - If a hand image is uploaded, the prompt must behave like a local edit task.
  - The hand pose, skin tone, background, and lighting should be preserved.
  - Only the nail region should be modified.
- DIY should stay at **one generated result** now, not three.
- Home page should avoid visible test assets / test labels / cache-like items.
- If the frontend and backend disagree on port, the site will appear broken even if the code is fine.
- Current browser state often needs a hard refresh after UI or asset changes.

## Recommended Validation Loop

Run these after changes:

```bash
cd /Users/Zhuanz/MeiTuanHackathon/web && npm run lint && npm run build
cd /Users/Zhuanz/MeiTuanHackathon/ai-service && ./.venv/bin/python -m compileall app
curl http://127.0.0.1:8008/health
```

Then spot-check:

- `http://localhost:3003/`
- `http://localhost:3003/diy-bounty`
- `http://localhost:3003/diy-bounty/create`
- `http://localhost:3003/chat-recommend`
- `http://localhost:3003/ai-tryon`

## Current Clean-up Direction

If continuing from here, the safest next steps are:

1. Keep removing any homepage test material that still leaks in from catalog fallback data.
2. Keep DIY output at a single image and preserve the hand as much as possible.
3. Make sure the backend and frontend ports stay aligned at `8008` / `3003`.
4. Keep the audit / history screens working so generation steps remain visible.

## Useful Git Reminder

Before changing the UX again, sync the repo state first:

```bash
git -C /Users/Zhuanz/MeiTuanHackathon fetch --all --prune
git -C /Users/Zhuanz/MeiTuanHackathon status --short --branch
```

That avoids mixing a local browser state with a stale code state.
