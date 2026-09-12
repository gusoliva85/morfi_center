"""Verifica que los handlers globales devuelvan el formato único de error
(`documentacion/02_Documento_Tecnico.md` §20)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    NotFoundError,
    OutOfStockError,
    register_error_handlers,
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom/notfound")
    def _nf():
        raise NotFoundError("El pedido no existe.", details={"order_id": 999})

    @app.get("/boom/stock")
    def _stock():
        raise OutOfStockError(details={"product_id": 3, "available": 1, "requested": 5})

    @app.get("/boom/unhandled")
    def _unhandled():
        raise RuntimeError("detalle interno secreto")

    @app.get("/items/{item_id}")
    def _item(item_id: int):
        return {"item_id": item_id}

    return TestClient(app, raise_server_exceptions=False)


def test_not_found_error_shape_and_status(client: TestClient):
    r = client.get("/boom/notfound")
    assert r.status_code == 404
    assert r.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "El pedido no existe.",
            "details": {"order_id": 999},
        }
    }


def test_domain_error_uses_default_message(client: TestClient):
    r = client.get("/boom/stock")
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "OUT_OF_STOCK"
    assert err["message"]  # mensaje por defecto de la clase
    assert err["details"] == {"product_id": 3, "available": 1, "requested": 5}


def test_pydantic_validation_error_shape(client: TestClient):
    r = client.get("/items/no-es-numero")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert isinstance(err["details"]["fields"], list)
    assert err["details"]["fields"], "debe listar el/los campos con error"


def test_unhandled_exception_is_generic(client: TestClient):
    r = client.get("/boom/unhandled")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "INTERNAL_ERROR"
    assert err["details"] == {}
    assert "secreto" not in err["message"]  # no filtra el detalle interno


def test_route_not_found_is_wrapped(client: TestClient):
    r = client.get("/ruta-inexistente")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_method_not_allowed_is_wrapped(client: TestClient):
    r = client.post("/boom/notfound")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
