import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import errors

_EXCEPTIONS_BY_CODE = {
    "not_found": errors.NotFoundError,
    "forbidden": errors.ForbiddenError,
    "conflict": errors.ConflictError,
    "out_of_stock": errors.OutOfStockError,
    "shift_closed": errors.ShiftClosedError,
    "cancel_window_closed": errors.CancelWindowClosedError,
    "out_of_coverage": errors.OutOfCoverageError,
    "invalid_transition": errors.InvalidTransitionError,
}


def _build_test_app() -> FastAPI:
    app = FastAPI()
    errors.register_error_handlers(app)

    @app.get("/boom/{code}")
    def boom(code: str):
        raise _EXCEPTIONS_BY_CODE[code]("mensaje de prueba")

    @app.get("/producto")
    def get_producto():
        raise errors.NotFoundError("Producto no encontrado", details={"product_id": 14})

    @app.get("/sin-details")
    def sin_details():
        raise errors.ForbiddenError("no autorizado")

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_build_test_app())


def test_not_found_error_returns_json_envelope_with_details(client: TestClient):
    response = client.get("/producto")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Producto no encontrado",
            "details": {"product_id": 14},
        }
    }


def test_details_default_to_empty_dict(client: TestClient):
    response = client.get("/sin-details")
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {}


@pytest.mark.parametrize(
    "code,expected_status,expected_error_code",
    [
        ("not_found", 404, "NOT_FOUND"),
        ("forbidden", 403, "FORBIDDEN"),
        ("conflict", 409, "CONFLICT"),
        ("out_of_stock", 409, "OUT_OF_STOCK"),
        ("shift_closed", 409, "SHIFT_CLOSED"),
        ("cancel_window_closed", 409, "CANCEL_WINDOW_CLOSED"),
        ("out_of_coverage", 409, "OUT_OF_COVERAGE"),
        ("invalid_transition", 409, "INVALID_TRANSITION"),
    ],
)
def test_each_domain_error_maps_to_documented_status_and_code(
    client: TestClient, code, expected_status, expected_error_code
):
    response = client.get(f"/boom/{code}")
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_error_code
