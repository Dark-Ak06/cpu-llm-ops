"""Integration tests for all REST and SSE API endpoints."""

import asyncio
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.llm import EngineSaturatedException
from app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Validate /health endpoint returns 200 with service version."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_ready_endpoint_loaded(async_client: AsyncClient) -> None:
    """Validate /ready endpoint returns 200 when model is loaded."""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["model_loaded"] is True
    assert "model_name" in data


@pytest.mark.asyncio
async def test_ready_endpoint_not_loaded(async_client: AsyncClient) -> None:
    """Validate /ready endpoint returns 503 when model engine is unloaded."""
    app = async_client._transport.app  # type: ignore[attr-defined]
    app.state.engine._is_loaded = False

    response = await async_client.get("/ready")
    assert response.status_code == 503
    assert "Model not ready" in response.json()["detail"]

    app.state.engine._is_loaded = True


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient) -> None:
    """Validate /metrics returns Prometheus formatted exposition."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "llm_requests_total" in text
    assert "llm_model_loaded" in text
    assert "llm_in_flight_requests" in text


@pytest.mark.asyncio
async def test_generate_endpoint_success(async_client: AsyncClient) -> None:
    """Validate successful text generation payload and schema."""
    payload = {
        "prompt": "Explain DevOps automation in one line.",
        "max_tokens": 32,
        "temperature": 0.5,
    }
    response = await async_client.post(
        "/generate",
        json=payload,
        headers={"X-Request-ID": "test-req-1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert data["tokens_generated"] > 0
    assert data["latency_ms"] >= 0.0
    assert data["request_id"] == "test-req-1234"
    assert response.headers["X-Request-ID"] == "test-req-1234"


@pytest.mark.asyncio
async def test_generate_input_validation(async_client: AsyncClient) -> None:
    """Validate rejection of invalid payloads with 422 Unprocessable Entity."""
    resp_empty = await async_client.post("/generate", json={"prompt": ""})
    assert resp_empty.status_code == 422

    resp_neg = await async_client.post(
        "/generate", json={"prompt": "valid prompt", "max_tokens": -5}
    )
    assert resp_neg.status_code == 422

    resp_temp = await async_client.post(
        "/generate", json={"prompt": "valid prompt", "temperature": 3.5}
    )
    assert resp_temp.status_code == 422


@pytest.mark.asyncio
async def test_generate_stream_endpoint(async_client: AsyncClient) -> None:
    """Validate Server-Sent Events token streaming endpoint."""
    payload = {
        "prompt": "Stream greetings",
        "max_tokens": 16,
    }
    response = await async_client.post("/generate/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "X-Request-ID" in response.headers

    body = response.text
    assert "data: " in body
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_generate_saturated_429(async_client: AsyncClient) -> None:
    """Validate 429 response with Retry-After when engine raises EngineSaturatedException."""
    app = async_client._transport.app  # type: ignore[attr-defined]
    with patch.object(
        app.state.engine, "generate", side_effect=EngineSaturatedException(retry_after=7)
    ):
        response = await async_client.post(
            "/generate",
            json={"prompt": "Heavy prompt", "max_tokens": 10},
        )
        assert response.status_code == 429
        assert response.headers["retry-after"] == "7"
        assert response.json()["error_code"] == "SATURATION_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_generate_timeout_504(async_client: AsyncClient) -> None:
    """Validate 504 Gateway Timeout when inference exceeds deadline."""
    app = async_client._transport.app  # type: ignore[attr-defined]

    async def slow_inference(*_args: object, **_kwargs: object) -> tuple[str, int, float]:
        await asyncio.sleep(5.0)
        return "slow response", 2, 5000.0

    with patch.object(app.state.engine, "generate", side_effect=slow_inference):
        app.state.settings.request_timeout_seconds = 0.05
        response = await async_client.post(
            "/generate",
            json={"prompt": "Timeout prompt", "max_tokens": 10},
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]


@pytest.mark.asyncio
async def test_lifespan_context() -> None:
    """Validate app startup and shutdown lifespan hooks."""
    app = create_app()
    with (
        patch.object(app.state.engine, "load_model") as mock_load,
        patch.object(app.state.engine, "unload_model") as mock_unload,
    ):
        async with app.router.lifespan_context(app):
            mock_load.assert_called_once()
        mock_unload.assert_called_once()
