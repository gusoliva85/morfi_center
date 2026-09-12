import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import (
    JsonFormatter,
    RequestContextFilter,
    RequestIdMiddleware,
    configure_logging,
    request_id_var,
)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_middleware_adds_request_id_header_when_absent():
    client = TestClient(_build_test_app())
    response = client.get("/ping")
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    assert len(response.headers["X-Request-Id"]) > 0


def test_middleware_reuses_incoming_request_id_header():
    client = TestClient(_build_test_app())
    response = client.get("/ping", headers={"X-Request-Id": "mi-request-id-123"})
    assert response.headers["X-Request-Id"] == "mi-request-id-123"


def test_request_context_filter_attaches_request_id_to_log_record():
    token = request_id_var.set("req-abc")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hola",
            args=(),
            exc_info=None,
        )
        RequestContextFilter().filter(record)
        assert record.request_id == "req-abc"
    finally:
        request_id_var.reset(token)


def test_json_formatter_produces_valid_json_with_request_id():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hola mundo",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-xyz"
    record.user_id = None
    data = json.loads(JsonFormatter().format(record))
    assert data["msg"] == "hola mundo"
    assert data["request_id"] == "req-xyz"
    assert data["level"] == "INFO"
    assert data["logger"] == "test"


def test_configure_logging_uses_json_formatter_in_production():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    try:
        configure_logging("production")
        assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
    finally:
        root.handlers[:] = original_handlers


def test_configure_logging_uses_plain_formatter_in_development():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    try:
        configure_logging("development")
        assert not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
    finally:
        root.handlers[:] = original_handlers
