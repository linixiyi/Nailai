# NailAI Harness Checks

Harness engineering means keeping small proof loops close to the code. Use these checks to quickly prove the product still works.

## Service Health

```bash
curl -sS http://localhost:8008/health
```

Expected:

```json
{"status":"ok","service":"nailai-ai-service"}
```

## Demo Data APIs

```bash
curl -sS http://localhost:8008/api/v1/shops | head -c 300
curl -sS http://localhost:8008/api/v1/bounties | head -c 300
curl -sS http://localhost:8008/api/v1/store/tasks | head -c 300
```

Use these when list pages fail or render empty.

## Frontend Static Gates

```bash
cd web
npm run lint
npm run build
```

If `npm run build` fails while a dev server is running and `.next` looks corrupted, stop the dev server and run:

```bash
cd web
rm -rf .next
npm run build
```

## Backend Static Gate

```bash
cd ai-service
./.venv/bin/python -m compileall app
```

## Merchant Style Upload Preview/Publish

先验证两阶段接口都在线：

```bash
curl -sS http://localhost:8008/health
```

再用一张本地款式图做预览：

```bash
curl -sS -X POST http://localhost:8008/api/v1/store/styles/preview \
  -F 'name=测试蓝色星月' \
  -F 'price=198' \
  -F 'image=@/absolute/path/to/style-photo.png'
```

预期返回：

- `status: success`
- `draft_id`
- `source_image_url`
- `design_image_url`

然后用上一步的 `draft_id` 发布：

```bash
curl -sS -X POST http://localhost:8008/api/v1/store/styles/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "draft_id": "style-draft-xxxx",
    "name": "测试蓝色星月",
    "price": "198",
    "taxonomy": {
      "colors": ["蓝色系"],
      "techniques": ["手绘"],
      "shapes": ["方圆型"],
      "styles": ["梦幻"],
      "occasions": ["约会"],
      "lengths": ["长款"]
    },
    "custom_tags_by_dimension": {
      "colors": [],
      "techniques": ["星月"],
      "shapes": [],
      "styles": ["个性"],
      "occasions": [],
      "lengths": []
    }
  }'
```

预期返回：

- `status: success`
- `style_id`
- `style.taxonomy`
- `style.design_image_url`
- `style.nail_length`

## 375x812 Prototype Screenshots

```bash
mkdir -p /tmp/nailai-screens
cd web
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ /tmp/nailai-screens/home.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ai-tryon /tmp/nailai-screens/ai-tryon.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/tryon-result /tmp/nailai-screens/tryon-result.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/style-detail/aurora-holo /tmp/nailai-screens/style-detail.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/chat-recommend /tmp/nailai-screens/chat-recommend.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/diy-bounty /tmp/nailai-screens/diy-bounty.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/bounty-detail/bounty-aurora /tmp/nailai-screens/bounty-detail.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/shop-recommend /tmp/nailai-screens/shop-recommend.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/store-take-order /tmp/nailai-screens/store-take-order.png
```

Review the screenshots for:

- no blank pages
- no bottom CTA overlap
- selected images visible
- text inside buttons and cards
- route-specific page content

## AI Try-On Manual Flow

1. Open `http://localhost:3003/ai-tryon`.
2. Upload a hand photo.
3. Select the target nail style.
4. Confirm the photo quality checklist.
5. Click generate.
6. Verify redirect to `/tryon-result`.
7. Confirm the displayed image is the latest backend `result_image_url`.

Failure records from this flow belong in `ops/issues/KNOWN_ISSUES.md`.
