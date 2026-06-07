"""Basic health and routing tests for NailAI ai-service."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    """FastAPI 健康检查端点应返回 200 并包含 service 字段。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "nailai-ai-service"


@pytest.mark.anyio
async def test_styles_endpoint(client: AsyncClient):
    """款式列表端点应返回 200 且 styles 为列表。"""
    resp = await client.get("/api/v1/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert "styles" in data
    assert isinstance(data["styles"], list)


@pytest.mark.anyio
async def test_try_on_validation(client: AsyncClient):
    """试戴端点在缺少必填字段时应返回 422。"""
    resp = await client.post("/api/v1/nail/try-on")
    assert resp.status_code == 422  # FastAPI validation error


@pytest.mark.anyio
async def test_chat_validation(client: AsyncClient):
    """Chat 端点缺少 message 时应返回 422。"""
    resp = await client.post("/api/v1/chat", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_bounty_endpoint(client: AsyncClient):
    """悬赏列表端点应返回 200。"""
    resp = await client.get("/api/v1/bounties")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_shops_endpoint(client: AsyncClient):
    """店铺端点应返回 200。"""
    resp = await client.get("/api/v1/shops")
    assert resp.status_code == 200
