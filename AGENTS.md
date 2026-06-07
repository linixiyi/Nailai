# NailAI Agent Operating Guide

This file is the first place every coding agent should read before changing the project. It is intentionally short, operational, and updated progressively as the team learns.

## Product North Star

NailAI is an AI manicure platform for the Hackathon MVP. The P0 demo must prove one closed loop:

1. Upload a clear hand photo.
2. Choose a nail style.
3. Generate an AI try-on result through the FastAPI image pipeline.
4. Show the result in the web UI.
5. Offer follow-up paths: style detail, chat recommendation, shop recommendation, DIY bounty.

Do not spend engineering time on non-P0 polish if this loop is broken.

## Current Architecture

- `web/`: Next.js App Router frontend. Browser calls should use `web/src/lib/api.ts`; by default it calls the Next.js same-origin proxy `/api/v1`, and Next connects to FastAPI through `AI_SERVICE_URL`.
- `ai-service/`: FastAPI service for image2 try-on, chat placeholder, style and demo data.
- `supabase/`: schema and seed migrations for future persistence.
- `ops/`: engineering operating manual, issue log, and templates.

The preferred runtime split is frontend and backend separated:

- Frontend: `http://localhost:3003`
- Backend: `http://localhost:8008`
- FastAPI health check: `GET /health`

## Harness Engineering Rules

Use a harness mindset: every important workflow needs a small, repeatable way to prove it still works.

Before editing, identify the workflow being touched:

- UI/prototype: screenshot at `375x812`.
- AI try-on: multipart request must include `image`, `style_image`, `style_id`, and `style_payload` when available.
- API/data: curl the FastAPI endpoint and verify JSON shape.
- Build/runtime: `npm run lint`, `npm run build`, and `/health`.

After editing, update or create the smallest harness that catches the failure next time. A harness can be a command, screenshot path, curl snippet, checklist, or automated test. Prefer simple repeatable proof over large test systems during the Hackathon.

## Development Protocol

1. Read `ops/manual/ENGINEERING_OPERATIONS.md` before making broad changes.
2. Check `ops/issues/KNOWN_ISSUES.md` before debugging a symptom.
3. Preserve the P0 flow first; treat UI, API, and image generation as one product path.
4. Keep generated or imported visual assets under `web/public/`.
5. Do not hardcode one fixed try-on result image in the main flow.
6. Do not leak API keys into committed files.
7. Keep old Next API routes only for compatibility; new user-facing pages should use FastAPI through `web/src/lib/api.ts`.

## Verification Gates

For frontend changes:

```bash
cd web
npm run lint
npm run build
```

For backend changes:

```bash
cd ai-service
./.venv/bin/python -m compileall app
curl -sS http://localhost:8008/health
```

For full demo flow:

```bash
curl -sS http://localhost:8008/health
curl -sS http://localhost:8008/api/v1/shops | head -c 300
cd web
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ /tmp/nailai-screens/home.png
```

## Progressive Updates

Update this file only when a rule changes how future agents should work. Keep details in `ops/`:

- New repeated failure: add it to `ops/issues/KNOWN_ISSUES.md`.
- New workflow or service operation: add it to `ops/manual/ENGINEERING_OPERATIONS.md`.
- New reusable debugging command: add it to `ops/manual/HARNESS_CHECKS.md`.
- New one-off note: do not put it here unless it changes future behavior.

When updating `AGENTS.md`, keep it under roughly 120 lines. It should remain a navigation map, not a project diary.


<claude-mem-context>
# Memory Context

# [MeiTuanHackathon] recent context, 2026-06-06 11:20am GMT+8

No previous sessions found.
</claude-mem-context>
