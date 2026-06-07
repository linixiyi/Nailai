# NailAI 前后端对接文档

更新日期：2026-05-18

## 1. 对接原则

新版前端页面直接调用 FastAPI，不再以 Next API Routes 作为主业务链路。

前端 API Base URL：

```env
AI_SERVICE_URL=http://127.0.0.1:8008
NEXT_PUBLIC_API_BASE_URL=
```

前端统一调用入口：

- `web/src/lib/api.ts`

后端统一服务入口：

- `ai-service/app/main.py`

## 2. 本地服务地址

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| Next.js Web | `http://localhost:3003` | 用户端页面 |
| FastAPI | `http://localhost:8008` | AI 和数据接口 |
| FastAPI Health | `GET /health` | 健康检查 |

## 3. 数据类型

前端类型定义在：

- `web/src/lib/types.ts`

后端 Pydantic schema 定义在：

- `ai-service/app/schemas.py`

### NailStyle

```ts
type NailStyle = {
  id: string;
  name: string;
  color: string;
  finish: string;
  occasion: string[];
  tags: string[];
  palette: string[];
  prompt: string;
  difficulty: "easy" | "medium" | "hard";
  price_level: string;
  image_url?: string;
  stock_total?: number;
  stock_reserved?: number;
};
```

### TryOnResponse

```ts
type TryOnResponse = {
  job_id: string;
  status: string;
  channel: string;
  style: NailStyle;
  hand_confidence: number;
  quality_score: number;
  result_image_url: string;
  mask_image_url?: string | null;
  nail_count?: number | null;
  nail_confidence?: number | null;
};
```

### ChatResponse

```ts
type ChatResponse = {
  reply: string;
  intent: string;
  recommended_styles: NailStyle[];
  follow_up_questions: string[];
};
```

## 4. 接口清单

### 4.1 健康检查

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "service": "nailai-ai-service"
}
```

验证命令：

```bash
curl -sS http://localhost:8008/health
```

### 4.2 获取库存款式

```http
GET /api/v1/styles
```

用途：

- 首页推荐款式。
- AI 试戴款式选择。
- Chat 推荐候选。
- 款式详情页。

响应：

```json
{
  "styles": [
    {
      "id": "fixed-target-red-black-spider",
      "name": "指定款：红黑棋盘蜘蛛",
      "color": "红黑",
      "finish": "亮面",
      "occasion": ["派对", "万圣节", "个性写真"],
      "tags": ["指定款", "红黑棋盘", "蜘蛛", "高对比"],
      "palette": ["#cf1f2e", "#0f0f11", "#6d4f45"],
      "prompt": "red and black checkerboard manicure...",
      "difficulty": "hard",
      "price_level": "¥¥¥",
      "image_url": "/style-images/custom/fixed-target-style.png",
      "stock_total": 99,
      "stock_reserved": 0
    }
  ]
}
```

验证命令：

```bash
curl -sS http://localhost:8008/api/v1/styles | head -c 500
```

注意：

- `image_url` 是前端 public path，浏览器从 Next.js 静态目录加载。
- 当前后端 seed 和前端库存图路径需要保持一致。

### 4.3 AI 换甲

```http
POST /api/v1/nail/try-on
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `image` | File | 是 | 用户上传的手部照片 |
| `style_image` | File | 否，建议传 | 选中的库存款式图 |
| `style_id` | string | 否，建议传 | 选中的款式 id |
| `style_payload` | string JSON | 否，建议传 | 完整 NailStyle JSON |

前端调用位置：

- `web/src/lib/api.ts` 的 `postTryOn`
- `web/src/components/prototype/AiTryOnScreen.tsx`

后端处理位置：

- `ai-service/app/routers/nail_try_on.py`

后端处理流程：

1. 校验 `image.content_type` 必须是图片。
2. 读取手图 bytes。
3. 可选读取 `style_image` bytes。
4. 调用 `detect_hand` 做质量检测。
5. 调用 YOLOv8 指甲分割模型，尝试识别可编辑指甲区域，得到 `mask_image_url`、`nail_count`、`nail_confidence`。
6. 若分割模型可用但识别到的指甲数量或置信度低于门槛，返回 `422`，提示用户重拍。
7. 用 `style_payload` 或 `style_id` 解析目标款式。
8. 调用 `generate_try_on`，当前主链路走 `gpt_image2`：发送原手图 + 款式图给 GPT image2，款式设计只来自图片本身，不把库存文字描述作为款式输入。
9. 返回 `TryOnResponse`。

`gpt_image2` 说明：

- 第一张图：原始手图，是最终输出画布。
- 第二张图：目标美甲款式图，用来提取颜色、图案、亮片、饰品、甲型、长短和光泽。
- YOLOv8 指甲分割仍用于前置质量检测和结果元信息，不把 mask 当成拼图素材。
- 提示词只约束局部换甲、画面锁定、光影融合和输出限制，避免库存标题/颜色标签误导模型。
8. 返回 `TryOnResponse`。

成功响应：

```json
{
  "job_id": "uuid",
  "status": "succeeded",
  "channel": "mock-image2",
  "style": {
    "id": "fixed-target-red-black-spider",
    "name": "指定款：红黑棋盘蜘蛛"
  },
  "hand_confidence": 0.9,
  "quality_score": 0.84,
  "result_image_url": "data:image/png;base64,...",
  "mask_image_url": "data:image/png;base64,...",
  "nail_count": 5,
  "nail_confidence": 0.86,
  "provider_payload": {
    "cache_key": "...",
    "mode": "mask-guided-edit",
    "mask_guided": true,
    "nail_segmentation": {
      "available": true,
      "nail_count": 5,
      "confidence": 0.86,
      "message": "nail-segmentation-pass",
      "boxes": []
    }
  }
}
```

错误响应：

- `400`：上传文件不是图片。
- `422`：手部检测置信度不足。
- `5xx`：生图 provider 调用失败或超时。

### 4.4 Chat 推荐

```http
POST /api/v1/chat
Content-Type: application/json
```

请求：

```json
{
  "message": "下周约会，想要显白但不要太夸张",
  "history": [],
  "selected_style_ids": ["fixed-target-red-black-spider"]
}
```

响应：

```json
{
  "reply": "推荐说明文本",
  "intent": "recommendation",
  "recommended_styles": [],
  "follow_up_questions": []
}
```

当前状态：

- 目前是规则推荐/占位能力。
- 后续可替换为 LLM + 库存款式 RAG。

### 4.5 店铺列表

```http
GET /api/v1/shops
```

响应：

```json
{
  "shops": []
}
```

当前用途：

- `/shop-recommend`
- 首页“附近可做店铺”
- 款式详情页“附近可做”

### 4.6 悬赏列表

```http
GET /api/v1/bounties
```

响应：

```json
{
  "bounties": []
}
```

当前用途：

- `/diy-bounty`
- `/bounty-detail/[id]`

### 4.7 商家任务

```http
GET /api/v1/store/tasks
```

响应：

```json
{
  "tasks": []
}
```

当前用途：

- `/store-take-order`

## 5. 前端状态流

AI 试戴成功后，前端会把 `TryOnResponse` 写入 sessionStorage：

- key：`nailai.latestTryOn`
- 写入：`saveTryOnResult`
- 读取：`loadTryOnResult`
- 文件：`web/src/lib/tryOnStore.ts`

结果页 `/tryon-result` 读取该状态并展示：

- `result_image_url`
- `style`
- `hand_confidence`
- `channel`

如果 sessionStorage 没有结果，则展示库存款式 fallback。

## 6. image2 / GPT image2 配置

后端配置文件：

- `ai-service/app/config.py`

环境变量：

```env
ENABLE_MOCK_AI=false
IMAGE2_PROVIDER=gpt_image2
IMAGE2_API_URL=https://api.jiekou.ai/v3/gpt-image-2-edit
IMAGE2_MODEL=gpt-image-2
GPT_IMAGE2_API_URL=https://api.jiekou.ai/v3/gpt-image-2-edit
GPT_IMAGE2_API_KEY=your_api_key
GPT_IMAGE2_MODEL=gpt-image-2
IMAGE2_TIMEOUT_SECONDS=45
CORS_ORIGINS=http://localhost:3003
```

注意：

- 不要提交真实 API Key。
- `ai-service/.env.local` 会覆盖 `ai-service/.env`，推荐把真实密钥放在 `.env.local`。
- 当前 GPT adapter 调用 `/v3/gpt-image-2-edit`，`image` 传 `[手图, 款式图]`，`mask` 传透明区域为指甲的 PNG。
- 如果 provider 只支持别的图片字段，需要改 `image2_client.py` 的 provider adapter，而不要改前端调用契约。

## 7. 联调检查清单

启动后端：

```bash
cd ai-service
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8008
```

启动前端：

```bash
cd web
npm run dev -- --port 3003
```

检查接口：

```bash
curl -sS http://localhost:8008/health
curl -sS http://localhost:8008/api/v1/styles | head -c 500
```

检查页面：

```bash
cd web
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ /tmp/nailai-screens/home.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ai-tryon /tmp/nailai-screens/ai-tryon.png
```

手动闭环：

1. 打开 `/ai-tryon`。
2. 上传手图。
3. 选择库存款式。
4. 确认照片质量。
5. 点击生成。
6. 跳转 `/tryon-result`。
7. 确认结果图不是固定旧 mock 图，而是本次接口返回的 `result_image_url`。

## 8. 常见问题

### 页面一直转圈

排查：

```bash
curl -sS http://localhost:8008/health
lsof -iTCP:8008 -sTCP:LISTEN -n -P
```

常见原因：

- FastAPI 未启动。
- `NEXT_PUBLIC_API_BASE_URL` 配错。
- image2 provider 超时。

### 结果图不匹配所选款式

排查：

- 检查 multipart 是否包含 `style_image`。
- 检查 `style_payload` 中的 `id` 和 `image_url` 是否为当前选择款式。
- 检查后端日志中解析出的 `style.id`。

### Next dev 出现 `.next` 缓存错误

处理：

```bash
cd web
rm -rf .next
npm run build
npm run dev -- --port 3003
```
