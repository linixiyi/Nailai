# NailAI Known Issues And Fix Records

Use this file for problems actually encountered during development. Keep each entry short and operational.

## 2026-05-17: Frontend Shows Spinner But No Try-On Result

- Symptom: user clicks generate on the web page, frontend keeps spinning or shows no correct try-on result.
- Cause: frontend flow can become disconnected from FastAPI, or result page can display an old fixed preview instead of backend response.
- Fix: new pages call FastAPI through `web/src/lib/api.ts`; AI try-on sends `image`, `style_image`, `style_id`, and `style_payload`; result is saved to session storage and `/tryon-result` reads `result_image_url`.
- Prevention harness: run the AI try-on manual flow in `ops/manual/HARNESS_CHECKS.md` and confirm the result image changes with backend response.

## 2026-05-17: Generated Image Did Not Match Selected Style

- Symptom: generated result looked like the same old image and did not reflect the selected hand/style pair.
- Cause: frontend and backend did not reliably pass the selected style image and payload through the generation request.
- Fix: include `style_image` blob and structured style payload in multipart requests.
- Prevention harness: inspect browser request payload or backend logs when testing a new style; verify selected style id and style image filename/path are present.

## 2026-05-17: Next Build Corrupted While Dev Server Was Running

- Symptom: dev server started returning 500 and reported missing `.next/routes-manifest.json` after running production build concurrently.
- Cause: `npm run build` and `npm run dev` touched `.next` at the same time.
- Fix: stop dev server, delete `.next`, then run `npm run build` alone.
- Prevention harness:

```bash
cd web
rm -rf .next
npm run build
```

## 2026-05-17: Uploaded Hand Photo Needs Guardrails

- Symptom: poor hand pose or incomplete fingers can make nail replacement unreliable.
- Cause: AI try-on quality depends on clear, complete single-hand input and visible nails.
- Fix: UI includes a photo quality checklist and guidance before generation.
- Prevention harness: use the AI try-on manual flow and verify the upload panel blocks generation until a hand image is selected and quality confirmation is visible.

## 2026-05-17: Style Images Displayed Cropped Or Incomplete

- Symptom: nail style images were not visually complete enough for users to recognize the selected design.
- Cause: card image sizing over-prioritized uniform cropping.
- Fix: prototype components use image presentation patterns that preserve recognizable style content.
- Prevention harness: check 375x812 screenshots for the home, AI try-on, and style detail pages.

## 2026-06-04: Imported Library Has Unmatched Extra Images

- Symptom: `library-20260514-006` and `library-20260514-032` do not map cleanly to the six-dimensional taxonomy source and can confuse public filtering.
- Cause: the image set contains extra files outside the curated `美甲01.png` to `美甲30.png` source range.
- Fix: keep these ids out of the public catalog and regenerate taxonomy from the six-dimensional directory.
- Prevention harness: run `python3 scripts/generate_nail_taxonomy_from_dir.py "<六维分类目录>"` and confirm the unmatched ids stay hidden.

## 2026-06-04: Chat Recommendation Waited On Remote Model Before Showing Results

- Symptom: the chat recommendation page kept spinning after submission and felt disconnected from the UI.
- Cause: the chat service was waiting on a remote LLM path before emitting a recommendation, even when the user only needed a quick nail-shape-first suggestion.
- Fix: switch the default chat path to deterministic local shape-first ranking, then let the response explain why the selected styles fit that nail shape.
- Prevention harness: call `GET /health` and `POST /api/v1/chat` with a short request and confirm the response returns in about 1-2 seconds with shape-locked recommendations.

## 2026-06-04: DIY Generation Locked Users On The Create Page

- Symptom: the DIY create page showed a large inline progress card and kept the user waiting in place while generation was running.
- Cause: the flow used page-local loading state instead of the shared background task window already available in the app shell.
- Fix: start DIY generation through `diyTaskStore`, redirect the user back to the home feed, and show progress in the global floating task window.
- Prevention harness: open `/diy-bounty/create`, trigger generation, and confirm the app navigates away while the background task window continues updating.

## 2026-06-04: Six-Dimensional Style Tags Drifted From Database

- Symptom: homepage filters, style detail chips, chat recommendation, and try-on prompts showed stale or bloated tags such as `seed`, `imported`, and old library labels.
- Cause: `importedStyles.ts` and Supabase rows were not regenerated from the six-dimensional taxonomy source; the live database also had unapplied catalog columns such as `taxonomy` and `nail_length`.
- Fix: regenerate the frontend/backend catalog from the six-dimensional directory, sync canonical rows with `scripts/sync_nail_taxonomy_catalog_to_supabase.py`, and hide stale library rows.
- Prevention harness: run `python3 scripts/generate_nail_taxonomy_from_dir.py "<六维分类目录>"`, then run `python3 scripts/sync_nail_taxonomy_catalog_to_supabase.py "<六维分类目录>"` and confirm `library-20260514-006` / `032` are unmatched while `暗黑星芒辣妹甲` maps to `library-20260514-007`.

## 2026-06-05: Merchant Style Upload Frontend Switched To Preview/Publish Before Backend Did

- Symptom: 店主端“款式上架”点击生成预览或最终发布时失败，前端调用 `/api/v1/store/styles/preview` 和 `/publish`，但 FastAPI 只有老的 `/store/styles/upload`。
- Cause: 前端已经拆成“先预览纯甲片设计图，再补六维标签发布”的两阶段流程，后端仍停留在旧的一步式上传接口。
- Fix: 在 `ai-service/app/routers/demo_data.py` 中补齐 `/store/styles/preview` 和 `/store/styles/publish`，共用旧上传链路的图片分析、纯甲片提纯和落库逻辑；同时保留 `/store/styles/upload` 做兼容。
- Prevention harness: 先 `POST /api/v1/store/styles/preview` 拿到 `draft_id`，再 `POST /api/v1/store/styles/publish` 带完整六维 taxonomy，确认两步都返回 `status=success` 且最终 style 带上 `taxonomy`、`design_image_url`、`nail_length`。

## 2026-06-05: Phone Browser Hit Fallback Because API Base Used Localhost

- Symptom: 服务器部署后，电脑端打开页面时前后端看起来联通，但手机端 AI 相关接口失败，页面全部回到本地 fallback 数据或兜底流程。
- Cause: 客户端环境变量把 `NEXT_PUBLIC_API_BASE_URL` 配成 `http://localhost:8008`。手机浏览器里的 `localhost` 指向手机本机，不是服务器；同时部分代理和文档仍写着旧端口 `3000/8000`。
- Fix: 浏览器默认走 Next.js 同源代理 `/api/v1`，`NEXT_PUBLIC_API_BASE_URL` 保持空值；Next 服务端用 `AI_SERVICE_URL=http://127.0.0.1:8008` 转发到 FastAPI；前端固定 `3003`，后端固定 `8008`。
- Prevention harness: 运行 `./ops/check-connectivity.sh`，并在手机浏览器访问 `http://<服务器IP>:3003/api/v1/styles`，确认返回真实 `styles` JSON 而不是前端 fallback。

## 2026-06-05: Merchant Style Preview Fell Back Even When A Backup AI Provider Was Available

- Symptom: 店主端“款式上架”预览经常显示提纯兜底图，页面会把 fallback 图当成最终设计图展示，影响商家观感。
- Cause: 商家预览链路过去会在 AI 失败后自动回填 `segmentation-isolated-design`，而且优先级里还混入了豆包通道；后续又发现 `wan2.7` 返回的图没有被正确解析，导致看起来像一直在 fallback。
- Fix: 商家预览现在只走 `wan2.7`，不再展示提纯兜底图；AI 失败时直接返回失败态，前端也只显示失败提示，不再渲染备用设计图。
- Prevention harness: 执行 `curl -sS -X POST http://localhost:8008/api/v1/store/styles/preview -F 'name=测试冰透款' -F 'price=158' -F 'image=@web/public/style-images/library-20260514/library-20260514-003.png'`，确认响应包含 `render_status=ai_generated` 且 `render_channel=qwen-wan2.7-style-render`。

## 2026-06-06: Merchant Upload Broke On WebViews Without `crypto.randomUUID`

- Symptom: 线上店主端“第三步：生成款式图预览”点击后立刻报错 `crypto.randomUUID is not a function`，无法进入预览生成队列。
- Cause: `web/src/lib/merchantStyleTaskStore.ts` 直接调用了 `crypto.randomUUID()`；部分手机浏览器、嵌入式 WebView 或较老运行环境只提供 `crypto`，但没有 `randomUUID`。
- Fix: 任务 id 改为先判断 `crypto.randomUUID` 是否可用，不可用时退回 `timestamp + Math.random()` 的本地唯一 id 方案。
- Prevention harness: 在浏览器控制台临时执行 `crypto.randomUUID = undefined`，然后走 `/store-take-order` 的“款式上架 -> 生成款式图预览”流程，确认任务仍能进入队列并继续请求 `/api/v1/store/styles/preview`。
