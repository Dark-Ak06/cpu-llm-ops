"""Pytest fixtures and test environment configuration."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated settings configured for mock inference."""
    return Settings(
        app_name="cpu-llm-ops-test",
        app_version="0.1.0-test",
        environment="development",
        mock_inference=True,
        max_concurrent_requests=2,
        max_queue_depth=2,
        request_timeout_seconds=2.0,
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Instantiate fresh application instance for tests with loaded engine."""
    application = create_app(test_settings)
    application.state.engine.load_model()
    return application


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client bound to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
