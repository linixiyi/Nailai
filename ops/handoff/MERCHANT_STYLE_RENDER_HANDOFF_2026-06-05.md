# Merchant Style Render Handoff

Date: 2026-06-05
Scope: 店主端“款式上架”预览/发布链路，重点是商家上传后的 AI 设计图渲染、队列、进度和 fallback 问题。

## Current Status

- 商家上传现在支持前端排队，不需要等上一张生成完成才能继续上传下一张。
- 页面已有进度条和任务列表，任务完成后可逐个确认上架。
- 后端商家预览链路已改成多 provider 顺序重试。
- 当前本地验证下，商家预览已经可以返回真实 AI 图，不再总是落到提纯底图。

最新实测结果：

- `POST /api/v1/store/styles/preview` 返回：
  - `render_status=ai_generated`
  - `render_channel=doubao-style-render`

## What Changed

### Frontend

1. 新增前端任务队列 store：
   - `web/src/lib/merchantStyleTaskStore.ts`
2. 扩展商家上传相关类型：
   - `web/src/lib/types.ts`
3. 店主端“款式上架”页面接入队列、进度条、任务切换、任务发布：
   - `web/src/components/prototype/ListScreens.tsx`

行为变化：

- 可以连续提交多张商家图。
- 一个任务运行时，后续任务进入队列。
- 页面显示 `queued / running / succeeded / failed` 状态。
- 用户可切换查看不同任务的预览结果。
- 发布动作从当前选中的成功任务发起。

### Backend

核心文件：

- `ai-service/app/routers/demo_data.py`

关键修复：

1. 商家预览渲染不再只试一个 provider。
2. provider 顺序调整为：
   - `jiekou light`
   - `doubao`
   - `highway`
3. 新增对 `GPT Image 2 Light 编辑` 请求体的适配：
   - `images: [{ image_url }]`
   - `prompt`
   - `size`
   - `background`
   - `moderation`
4. 保留对旧 `gpt-image-2-edit` 风格 payload 的兼容。
5. 修掉一个关键逻辑 bug：
   - 之前即使 AI 成功出图，只要分割提纯成功，也会被提纯图覆盖。
   - 现在改为 AI 成功优先，只有 AI 全部失败时才退回 `segmentation-isolated-design`。

### Env / Config

已切到 `Light 编辑` endpoint：

- `ai-service/.env`
- `ai-service/.env.local`
- `ai-service/.env.example`

当前配置方向：

- `IMAGE2_API_URL=https://api.jiekou.ai/v3/gpt-image-2-light-edit`
- `GPT_IMAGE2_API_URL=https://api.highwayapi.ai/v3/gpt-image-2-edit`
- `DOUBAO_IMAGE_API_URL=https://ark.cn-beijing.volces.com/api/v3/images/generations`

## Real Provider Findings

这次不是前端假象，是真实外部 provider 状态不同：

- `jiekou light`：
  - 返回 `403`
  - body: `INVALID_API_KEY`
- `highway edit`：
  - 当前会 `ReadTimeout`
- `doubao`：
  - 返回 `200`
  - 能给出图片 URL

因此当前可工作的真实 AI 渠道是 `doubao`。

## Why The User Kept Seeing Fallback Before

主要有两个原因叠加：

1. 首个 provider 失败后，后端直接停止，不会继续尝试其他可用 provider。
2. 即使 AI 已成功生成，旧逻辑仍会优先展示提纯分割图，导致页面看起来“永远是 fallback”。

这两点都已经修复。

## Validation Already Done

### Backend syntax

```bash
cd ai-service
./.venv/bin/python -m compileall app
```

### Health check

```bash
curl -sS http://localhost:8008/health
```

### Merchant preview harness

```bash
curl -sS -X POST http://localhost:8008/api/v1/store/styles/preview \
  -F 'name=测试冰透款' \
  -F 'price=158' \
  -F 'image=@/Users/Zhuanz/MeiTuanHackathon/web/public/style-images/library-20260514/library-20260514-003.png'
```

本次实测返回：

```json
{
  "status": "success",
  "render_status": "ai_generated",
  "render_channel": "doubao-style-render"
}
```

## Runtime State

当前本地服务状态：

- Web health previously normal
- API currently running on `8008`

当前 screen：

- `nailai-web`
- `nailai-api`

如果需要重启 API：

```bash
screen -S nailai-api -X quit
screen -dmS nailai-api zsh -lc 'cd /Users/Zhuanz/MeiTuanHackathon/ai-service && exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8008'
```

## Important Testing Note

用户如果还在页面里看旧的 fallback 结果，不一定代表现在代码还坏着。

原因：

- 旧任务/旧 draft 已经把当时的 fallback 图存下来了。
- 必须重新上传一张图，或重新生成一个新的 preview draft，才能看到修复后的真实 AI 结果。

## Open Risks

1. `jiekou light` key 当前不可用。
   - 代码已适配，但账号权限/密钥本身仍需要排查。
2. `highway` 当前超时。
   - 现在它被放到 `doubao` 后面，不会先阻塞商家预览，但它本身还是未修复状态。
3. 前端任务队列是浏览器侧 store，不是后端持久化任务系统。
   - 刷新页面后，未完成上传任务的 `File` 无法完整恢复。

## Suggested Next Steps

1. 让下一个 agent 先在浏览器里重新上传一张商家图，确认 UI 端看到的也是 `ai_generated`。
2. 如果要继续追根因，优先排查：
   - `jiekou light` API key 权限
   - `highway` timeout
3. 如果要把排队上传做完整：
   - 把前端队列升级为后端 job system
   - 支持刷新后继续追踪任务
4. 如果要继续统一文档：
   - 把商家预览这条 provider 策略和验证命令补进 `ops/manual/HARNESS_CHECKS.md` 或相关 README

## Files Touched In This Work

- `ai-service/app/routers/demo_data.py`
- `ai-service/.env`
- `ai-service/.env.local`
- `ai-service/.env.example`
- `web/src/lib/types.ts`
- `web/src/lib/merchantStyleTaskStore.ts`
- `web/src/components/prototype/ListScreens.tsx`
- `ops/issues/KNOWN_ISSUES.md`
