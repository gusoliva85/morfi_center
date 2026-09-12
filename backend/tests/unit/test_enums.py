"""Verifica que los enums de dominio existan con los valores esperados
(según `documentacion/02_Documento_Tecnico.md` §6 y §7)."""

from app.core import enums


def test_str_enum_behaviour():
    # Los miembros son strings iguales a su valor.
    assert enums.Role.ADMIN == "ADMIN"
    assert isinstance(enums.Role.ADMIN, str)
    assert str(enums.OrderStatus.DELIVERED) == "DELIVERED"
    assert enums.Role.values() == ["CUSTOMER", "ADMIN", "DELIVERY"]


EXPECTED = {
    "Role": ["CUSTOMER", "ADMIN", "DELIVERY"],
    "UserStatus": ["ACTIVE", "SUSPENDED", "INACTIVE"],
    "AuthProvider": ["local", "google"],
    "VehicleType": ["moto", "bici", "auto", "a_pie"],
    "DriverStatus": ["DISPONIBLE", "NO_DISPONIBLE", "EN_RUTA", "INACTIVO"],
    "ServiceType": ["BREAKFAST", "LUNCH", "DINNER"],
    "ShiftStatus": [
        "SCHEDULED",
        "OPEN",
        "CLOSED",
        "IN_PRODUCTION",
        "DISPATCHING",
        "FINISHED",
    ],
    "PromotionType": ["PROMO", "DAILY_SPECIAL"],
    "ReservationStatus": ["HELD", "COMMITTED", "RELEASED"],
    "OrderStatus": [
        "DRAFT",
        "PENDING_PAYMENT",
        "PAYMENT_UNDER_REVIEW",
        "PAYMENT_APPROVED",
        "PAYMENT_REJECTED",
        "CANCELLED",
        "IN_PREPARATION",
        "READY_FOR_PICKUP",
        "ASSIGNED_TO_DELIVERY",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "DELIVERY_INCIDENT",
    ],
    "PaymentMethod": ["transfer"],
    "PaymentStatus": ["PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED"],
    "BalanceTxnType": ["credit", "debit"],
    "BalanceOrigin": ["cancellation", "order_use", "admin_adjustment"],
    "ZoneType": ["neighborhood", "radius"],
    "CoverageMode": ["neighborhood", "radius", "neighborhood_and_radius", "off"],
    "ShippingMode": ["free", "flat", "by_distance", "off"],
    "AssignmentStatus": ["DRAFT", "ASSIGNED", "IN_PROGRESS", "COMPLETED"],
    "StopStatus": ["PENDING", "ARRIVED", "DELIVERED", "INCIDENT"],
    "SettingValueType": ["json", "string", "int", "bool"],
    "NotificationType": [
        "order_created",
        "proof_received",
        "payment_approved",
        "payment_rejected",
        "order_cancelled",
        "balance_credited",
        "order_in_preparation",
        "order_ready",
        "order_out_for_delivery",
        "order_delivered",
        "delivery_incident",
        "validation_critical",
    ],
}


def test_all_enums_present_with_expected_values():
    for name, values in EXPECTED.items():
        enum_cls = getattr(enums, name, None)
        assert enum_cls is not None, f"Falta el enum {name}"
        assert enum_cls.values() == values, f"{name}: {enum_cls.values()} != {values}"


def test_enum_names_are_unique_and_exported():
    for name in EXPECTED:
        assert name in enums.__all__, f"{name} no está en __all__"


def test_production_and_terminal_status_sets():
    assert enums.OrderStatus.CANCELLED in enums.TERMINAL_STATUSES
    assert enums.OrderStatus.DELIVERED in enums.TERMINAL_STATUSES
    assert enums.OrderStatus.PAYMENT_APPROVED in enums.PRODUCTION_STATUSES
    assert enums.OrderStatus.PENDING_PAYMENT not in enums.PRODUCTION_STATUSES
