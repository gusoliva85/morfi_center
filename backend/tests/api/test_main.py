from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get(f"{settings.api_prefix}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": settings.app_env}


def test_health_endpoint_returns_request_id_header():
    response = client.get(f"{settings.api_prefix}/health")
    assert "X-Request-Id" in response.headers


def test_swagger_docs_available():
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_openapi_schema_available():
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == settings.app_name
