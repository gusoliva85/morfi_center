"""App FastAPI: healthcheck, wiring de middleware/handlers, OpenAPI y CORS."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


def test_health_ok():
    with TestClient(create_app()) as client:  # ejecuta el lifespan
        r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["env"] == settings.app_env
    assert "version" in body


def test_request_id_header_present():
    client = TestClient(create_app())
    r = client.get("/api/v1/health")
    assert r.headers.get("x-request-id")


def test_unknown_route_uses_error_format():
    client = TestClient(create_app())
    r = client.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_openapi_and_docs_available():
    client = TestClient(create_app())
    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/health" in schema.json()["paths"]

    docs = client.get("/api/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]


def test_cors_preflight_allowed_for_frontend_origin():
    # settings.app_env == "development" -> cors_origins = [frontend_origin]
    client = TestClient(create_app())
    r = client.options(
        "/api/v1/health",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == settings.frontend_origin
    assert r.headers.get("access-control-allow-credentials") == "true"
