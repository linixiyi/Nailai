# NailAI 标准化工程交接文档

更新日期：2026-05-18

## 1. 交接目标

本文档用于让后续开发者、队友或 agent 快速接手 NailAI 项目，明确：

- 当前代码放在哪里。
- 如何启动和验证。
- 修改功能时应该遵守什么工程标准。
- 遇到问题应该记录到哪里。
- 如何避免破坏 P0 AI 换甲闭环。

## 2. 必读文件顺序

新接手者建议按以下顺序阅读：

1. `README.md`：项目概览和启动方式。
2. `AGENTS.md`：agent/开发协作规则。
3. `ARCHITECTURE.md`：架构和核心接口。
4. `ops/handoff/PROJECT_REPORT.md`：阶段汇报和当前状态。
5. `ops/handoff/FRONTEND_BACKEND_INTEGRATION.md`：前后端接口契约。
6. `ops/manual/HARNESS_CHECKS.md`：验证命令。
7. `ops/issues/KNOWN_ISSUES.md`：已知问题与解决记录。

## 3. 工程目录规范

```text
.
├── AGENTS.md
├── ARCHITECTURE.md
├── README.md
├── ai-service/
│   └── app/
│       ├── routers/
│       ├── services/
│       ├── config.py
│       ├── main.py
│       └── schemas.py
├── ops/
│   ├── handoff/
│   ├── issues/
│   ├── manual/
│   └── templates/
├── supabase/
│   └── migrations/
└── web/
    ├── public/
    └── src/
        ├── app/
        ├── components/
        └── lib/
```

### 前端规范

- 页面放在 `web/src/app/`。
- 375x812 原型组件放在 `web/src/components/prototype/`。
- API 调用统一放在 `web/src/lib/api.ts`。
- 类型统一放在 `web/src/lib/types.ts`。
- 库存款式逻辑放在 `web/src/lib/styles.ts`。
- 静态图片放在 `web/public/`。

### 后端规范

- 路由放在 `ai-service/app/routers/`。
- Provider 或业务服务放在 `ai-service/app/services/`。
- API schema 放在 `ai-service/app/schemas.py`。
- 环境变量读取放在 `ai-service/app/config.py`。
- 路由注册放在 `ai-service/app/main.py`。

## 4. 分支与提交规范

建议分支命名：

```text
feature/tryon-flow
feature/style-inventory
fix/image2-timeout
docs/handoff-manual
```

提交信息建议：

```text
feat(web): connect inventory styles to try-on flow
fix(ai): pass style reference image to image2 adapter
docs(ops): add frontend backend integration handoff
```

提交前必须执行：

```bash
git status --short
cd web && npm run lint && npm run build
cd ../ai-service && ./.venv/bin/python -m compileall app
```

## 5. 环境变量规范

前端：

```env
AI_SERVICE_URL=http://127.0.0.1:8008
NEXT_PUBLIC_API_BASE_URL=
```

后端：

```env
ENABLE_MOCK_AI=true
IMAGE2_PROVIDER=generic
IMAGE2_API_URL=
IMAGE2_API_KEY=
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=gpt-image-2
CORS_ORIGINS=http://localhost:3003
```

规则：

- `.env`、`.env.local` 不提交。
- 真实 API Key 只保存在本地或部署平台环境变量。
- 任何文档中不得写真实 key。

## 6. 开发流程标准

### 6.1 接需求

先判断需求属于哪类：

- P0 AI 换甲闭环。
- UI 原型还原。
- 库存款式和数据。
- Chat 推荐。
- 店铺/悬赏/商家端。
- 工程文档和交接。

涉及 P0 闭环时，优先保证：

- 上传手图可用。
- 款式选择来自库存。
- 请求传递正确款式图。
- 后端返回结果。
- 结果页展示本次返回图。

### 6.2 写代码

前端改动：

1. 修改页面或组件。
2. 如涉及接口，统一改 `web/src/lib/api.ts`。
3. 如涉及类型，同步改 `web/src/lib/types.ts` 和 `ai-service/app/schemas.py`。
4. 用 375x812 截图检查视觉。

后端改动：

1. 修改 schema。
2. 修改 router。
3. 修改 service/provider adapter。
4. 用 curl 验证接口。

### 6.3 验证

基础验证：

```bash
cd web
npm run lint
npm run build

cd ../ai-service
./.venv/bin/python -m compileall app
curl -sS http://localhost:8008/health
```

页面截图：

```bash
cd web
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ /tmp/nailai-screens/home.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/ai-tryon /tmp/nailai-screens/ai-tryon.png
npx playwright screenshot --viewport-size=375,812 http://localhost:3003/tryon-result /tmp/nailai-screens/tryon-result.png
```

### 6.4 记录问题

真实遇到的问题写入：

- `ops/issues/KNOWN_ISSUES.md`

格式参考：

- `ops/templates/ISSUE_RECORD.md`

必须记录：

- symptom
- cause
- fix
- prevention harness

## 7. Harness Engineering 规则

项目采用轻量 Harness Engineering 思路：每条关键链路都要有可重复的验证方式。

当前核心 harness：

- 服务健康：`curl /health`
- 库存接口：`curl /api/v1/styles`
- 前端质量：`npm run lint`
- 构建质量：`npm run build`
- 后端语法：`python -m compileall app`
- UI 验收：375x812 Playwright screenshot
- P0 闭环：手动上传手图并生成试戴结果

新增功能时，要同步回答：

1. 这个功能坏了会怎么被发现？
2. 最小验证命令是什么？
3. 是否需要记录到 `HARNESS_CHECKS.md`？

## 8. 代码质量红线

不要做：

- 不要把真实 API Key 写入代码或文档。
- 不要在主链路硬编码固定结果图。
- 不要让首页推荐图和 AI 试戴实际款式图来自两套不同数据。
- 不要把全页截图当作真实 UI。
- 不要绕过 `web/src/lib/api.ts` 散落写 fetch。
- 不要在没有验证的情况下改 image2 请求格式。

必须做：

- 类型前后端同步。
- 生图请求必须带上当前选择的款式信息。
- 修改 P0 链路后必须跑一次手动闭环。
- 遇到重复问题必须补到问题库。

## 9. 当前优先级建议

P0 优先：

1. 稳定真实 image2 生图。
2. 加强手图质量检测。
3. 结果图持久化。
4. 库存款式和店铺可做能力绑定。

P1 后续：

1. Chat LLM + RAG。
2. Supabase 数据持久化。
3. 店铺预约流程。
4. DIY 悬赏接单流程。

## 10. 交接检查清单

交接前确认：

- `README.md` 可启动项目。
- `AGENTS.md` 规则最新。
- `PROJECT_REPORT.md` 反映当前阶段。
- `FRONTEND_BACKEND_INTEGRATION.md` 接口与代码一致。
- `KNOWN_ISSUES.md` 记录了本阶段主要问题。
- `npm run lint` 通过。
- `npm run build` 通过。
- FastAPI `/health` 正常。
- 首页和 AI 试戴页打开正常。
