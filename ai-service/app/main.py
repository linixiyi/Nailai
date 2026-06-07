from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routers import bounty, chat, demo_data, nail_try_on, test_dashboard
from app.services.style_catalog import list_styles, get_taxonomy_filters

app = FastAPI(
    title="NailAI Service",
    version="0.1.0",
    description="AI try-on and recommendation service for the NailAI MVP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PROTECTED_TEST_PATH_PREFIXES = (
    "/api/v1/test-dashboard",
    "/generated/tryon-audit",
    "/generated/diy-audit",
)


def _is_test_dashboard_authorized(request: Request) -> bool:
    expected = (settings.test_dashboard_password or "").strip()
    if not expected:
        return True
    provided = (
        request.headers.get("x-test-dashboard-password")
        or request.query_params.get("test_dashboard_password")
        or ""
    ).strip()
    return provided == expected


@app.middleware("http")
async def protect_test_dashboard(request: Request, call_next):
    if request.url.path.startswith(_PROTECTED_TEST_PATH_PREFIXES):
        if not _is_test_dashboard_authorized(request):
            return JSONResponse({"detail": "测试面板密码错误"}, status_code=401)
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nailai-ai-service"}


@app.get("/api/v1/styles")
async def styles():
    return {"styles": list_styles()}


@app.get("/api/v1/taxonomy-filters")
async def taxonomy_filters():
    return {"filters": get_taxonomy_filters()}


app.include_router(nail_try_on.router, prefix="/api/v1/nail", tags=["nail-try-on"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(bounty.router, prefix="/api/v1/bounty", tags=["bounty"])
app.include_router(demo_data.router, prefix="/api/v1", tags=["demo-data"])
app.include_router(test_dashboard.router, prefix="/api/v1/test-dashboard", tags=["test-dashboard"])
app.mount("/generated", StaticFiles(directory="generated", check_dir=False), name="generated")
