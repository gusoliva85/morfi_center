"""Verifica el middleware de request_id: header de respuesta + propagación al log
(`documentacion/02_Documento_Tecnico.md` §20.2)."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import RequestContextMiddleware, bind_user_id, get_request_id


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def _ping():
        return {"request_id": get_request_id()}

    @app.post("/do")
    async def _do():
        # en la app real lo llama la dependencia async get_current_user (Fase 1)
        bind_user_id(42)
        return {"ok": True}

    return TestClient(app)


def test_response_has_generated_request_id_header(client: TestClient):
    r = client.get("/ping")
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) == 32  # uuid4().hex
    # el mismo id es visible dentro del endpoint (ContextVar propagado)
    assert r.json()["request_id"] == rid


def test_incoming_request_id_is_preserved(client: TestClient):
    r = client.get("/ping", headers={"X-Request-Id": "trace-abc-123"})
    assert r.headers["x-request-id"] == "trace-abc-123"
    assert r.json()["request_id"] == "trace-abc-123"


def test_request_id_appears_in_access_log(client: TestClient, caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.DEBUG, logger="morfi.access"):
        r = client.get("/ping", headers={"X-Request-Id": "trace-log-xyz"})
    rid = r.headers["x-request-id"]
    records = [rec for rec in caplog.records if rec.name == "morfi.access"]
    assert records, "no se emitió ningún log de acceso"
    rec = records[-1]
    assert getattr(rec, "request_id", None) == rid == "trace-log-xyz"
    assert rec.status_code == 200
    assert rec.method == "GET"
    assert rec.path == "/ping"
    assert rec.duration_ms >= 0


def test_mutation_logs_at_info_and_binds_user(client: TestClient, caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.DEBUG, logger="morfi.access"):
        client.post("/do")
    rec = [r for r in caplog.records if r.name == "morfi.access"][-1]
    assert rec.levelno == logging.INFO  # POST es mutación
    assert rec.user_id == 42


def test_context_is_reset_between_requests(client: TestClient):
    client.get("/ping", headers={"X-Request-Id": "first"})
    # fuera de una request no hay request_id en contexto
    assert get_request_id() is None
