"""Unit tests for metrics and logging formatting."""

import json
import logging

from app.config import Settings
from app.logging import JSONFormatter, setup_logging
from app.metrics import get_metrics_content_type, get_metrics_snapshot


def test_metrics_content_type() -> None:
    """Validate Prometheus metrics content type string."""
    ct = get_metrics_content_type()
    assert "text/plain" in ct or "version=0.0.4" in ct


def test_metrics_snapshot() -> None:
    """Validate metrics export bytes contain standard output."""
    snapshot = get_metrics_snapshot()
    assert isinstance(snapshot, bytes)
    assert len(snapshot) > 0


def test_json_formatter() -> None:
    """Validate JSONFormatter serializes fields correctly."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-abc-123"
    record.extra_fields = {"user": "admin", "status": "ok"}

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Test log message"
    assert data["request_id"] == "req-abc-123"
    assert data["user"] == "admin"
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_setup_logging() -> None:
    """Validate setup_logging configures root logger without error."""
    logger = setup_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG
    assert logger.name == "cpu_llm_ops"


def test_settings_defaults() -> None:
    """Validate Settings default parameters."""
    settings = Settings()
    assert settings.app_name == "cpu-llm-ops"
    assert settings.port == 8000
    assert settings.n_threads >= 1
    assert settings.max_concurrent_requests >= 1
