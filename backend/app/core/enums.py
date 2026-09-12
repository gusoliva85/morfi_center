"""Enumeraciones de dominio de Morfi Center.

Se reutilizan en modelos SQLAlchemy, schemas Pydantic y validaciones/CHECK de la
base de datos. Todos los miembros son ``str`` (su valor coincide con lo que se
guarda en la DB).

Referencia: ``documentacion/02_Documento_Tecnico.md`` §6 (DDL) y §7 (catálogo de enums).
"""

from __future__ import annotations

from enum import StrEnum


class _StrEnum(StrEnum):
    """Base: enum cuyos miembros son ``str`` iguales a su valor
    (``StrEnum`` ya provee ``__str__`` -> valor e igualdad con strings)."""

    @classmethod
    def values(cls) -> list[str]:
        """Lista de valores (útil para construir CHECK constraints y tests)."""
        return [member.value for member in cls]


# ── Identidad y acceso ──────────────────────────────────


class Role(_StrEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    DELIVERY = "DELIVERY"


class UserStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class AuthProvider(_StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


class VehicleType(_StrEnum):
    MOTO = "moto"
    BICI = "bici"
    AUTO = "auto"
    A_PIE = "a_pie"


class DriverStatus(_StrEnum):
    DISPONIBLE = "DISPONIBLE"
    NO_DISPONIBLE = "NO_DISPONIBLE"
    EN_RUTA = "EN_RUTA"
    INACTIVO = "INACTIVO"


# ── Turnos ──────────────────────────────────────────────


class ServiceType(_StrEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class ShiftStatus(_StrEnum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    IN_PRODUCTION = "IN_PRODUCTION"
    DISPATCHING = "DISPATCHING"
    FINISHED = "FINISHED"


# ── Catálogo, stock y promociones ───────────────────────


class PromotionType(_StrEnum):
    PROMO = "PROMO"
    DAILY_SPECIAL = "DAILY_SPECIAL"


class ReservationStatus(_StrEnum):
    HELD = "HELD"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"


# ── Pedidos ─────────────────────────────────────────────


class OrderStatus(_StrEnum):
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAYMENT_UNDER_REVIEW = "PAYMENT_UNDER_REVIEW"
    PAYMENT_APPROVED = "PAYMENT_APPROVED"
    PAYMENT_REJECTED = "PAYMENT_REJECTED"
    CANCELLED = "CANCELLED"
    IN_PREPARATION = "IN_PREPARATION"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    ASSIGNED_TO_DELIVERY = "ASSIGNED_TO_DELIVERY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELIVERY_INCIDENT = "DELIVERY_INCIDENT"


# Estados en los que el pedido cuenta para la producción consolidada.
PRODUCTION_STATUSES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.PAYMENT_APPROVED,
        OrderStatus.IN_PREPARATION,
        OrderStatus.READY_FOR_PICKUP,
        OrderStatus.ASSIGNED_TO_DELIVERY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    }
)

# Estados terminales (no admiten más transiciones).
TERMINAL_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.DELIVERED, OrderStatus.CANCELLED}
)


# ── Pagos ───────────────────────────────────────────────


class PaymentMethod(_StrEnum):
    TRANSFER = "transfer"


class PaymentStatus(_StrEnum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Saldo a favor ───────────────────────────────────────


class BalanceTxnType(_StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class BalanceOrigin(_StrEnum):
    CANCELLATION = "cancellation"
    ORDER_USE = "order_use"
    ADMIN_ADJUSTMENT = "admin_adjustment"


# ── Cobertura y envío ───────────────────────────────────


class ZoneType(_StrEnum):
    NEIGHBORHOOD = "neighborhood"
    RADIUS = "radius"


class CoverageMode(_StrEnum):
    NEIGHBORHOOD = "neighborhood"
    RADIUS = "radius"
    NEIGHBORHOOD_AND_RADIUS = "neighborhood_and_radius"
    OFF = "off"


class ShippingMode(_StrEnum):
    FREE = "free"
    FLAT = "flat"
    BY_DISTANCE = "by_distance"
    OFF = "off"


# ── Logística ───────────────────────────────────────────


class AssignmentStatus(_StrEnum):
    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class StopStatus(_StrEnum):
    PENDING = "PENDING"
    ARRIVED = "ARRIVED"
    DELIVERED = "DELIVERED"
    INCIDENT = "INCIDENT"


# ── Configuración y notificaciones ──────────────────────


class SettingValueType(_StrEnum):
    JSON = "json"
    STRING = "string"
    INT = "int"
    BOOL = "bool"


class NotificationType(_StrEnum):
    ORDER_CREATED = "order_created"
    PROOF_RECEIVED = "proof_received"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_REJECTED = "payment_rejected"
    ORDER_CANCELLED = "order_cancelled"
    BALANCE_CREDITED = "balance_credited"
    ORDER_IN_PREPARATION = "order_in_preparation"
    ORDER_READY = "order_ready"
    ORDER_OUT_FOR_DELIVERY = "order_out_for_delivery"
    ORDER_DELIVERED = "order_delivered"
    DELIVERY_INCIDENT = "delivery_incident"
    VALIDATION_CRITICAL = "validation_critical"


__all__ = [
    "Role",
    "UserStatus",
    "AuthProvider",
    "VehicleType",
    "DriverStatus",
    "ServiceType",
    "ShiftStatus",
    "PromotionType",
    "ReservationStatus",
    "OrderStatus",
    "PRODUCTION_STATUSES",
    "TERMINAL_STATUSES",
    "PaymentMethod",
    "PaymentStatus",
    "BalanceTxnType",
    "BalanceOrigin",
    "ZoneType",
    "CoverageMode",
    "ShippingMode",
    "AssignmentStatus",
    "StopStatus",
    "SettingValueType",
    "NotificationType",
]
