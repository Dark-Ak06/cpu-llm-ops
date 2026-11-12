"""Unit tests for ModelEngine concurrency, lifecycle, and backpressure."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.llm import EngineSaturatedException, ModelEngine


@pytest.mark.asyncio
async def test_engine_lifecycle(test_settings: Settings) -> None:
    """Validate loading and unloading states of the engine."""
    engine = ModelEngine(test_settings)
    assert not engine.is_loaded

    engine.load_model()
    assert engine.is_loaded

    engine.unload_model()
    assert not engine.is_loaded


@pytest.mark.asyncio
async def test_engine_generate_unloaded(test_settings: Settings) -> None:
    """Validate generate call raises RuntimeError if model is unloaded."""
    engine = ModelEngine(test_settings)
    with pytest.raises(RuntimeError, match="Model is not loaded"):
        await engine.generate("test prompt", 16, 0.7)


@pytest.mark.asyncio
async def test_engine_stream_unloaded(test_settings: Settings) -> None:
    """Validate stream generation raises RuntimeError if model is unloaded."""
    engine = ModelEngine(test_settings)
    with pytest.raises(RuntimeError, match="Model is not loaded"):
        async for _ in engine.generate_stream("test prompt", 16, 0.7):
            pass


@pytest.mark.asyncio
async def test_engine_concurrency_saturation() -> None:
    """Validate that exceeding queue depth raises EngineSaturatedException."""
    # Settings: max_concurrent_requests=1, max_queue_depth=1
    custom_settings = Settings(
        mock_inference=True,
        max_concurrent_requests=1,
        max_queue_depth=1,
    )
    engine = ModelEngine(custom_settings)
    engine.load_model()

    # Artificially fill the queue depth
    engine._waiting_in_queue = 1

    with pytest.raises(EngineSaturatedException):
        await engine.generate("saturation test", 16, 0.7)


@pytest.mark.asyncio
async def test_engine_llama_cpp_loader(tmp_path: pytest.TempPathFactory) -> None:
    """Validate GGUF Llama loader branch using a mocked Llama class."""
    fake_model_file = tmp_path / "fake_model.gguf"  # type: ignore[operator]
    fake_model_file.write_text("fake gguf content")

    settings = Settings(
        model_path=str(fake_model_file),
        mock_inference=False,
    )
    engine = ModelEngine(settings)

    mock_llama_instance = MagicMock()
    mock_llama_instance.return_value = {
        "choices": [{"text": " Real llama response"}],
        "usage": {"completion_tokens": 4},
    }

    with patch.dict(
        "sys.modules", {"llama_cpp": MagicMock(Llama=MagicMock(return_value=mock_llama_instance))}
    ):
        engine.load_model()
        assert engine.is_loaded

        text, tokens, latency = await engine.generate("hello llama", 10, 0.2)
        assert text == " Real llama response"
        assert tokens == 4
        assert latency >= 0.0
