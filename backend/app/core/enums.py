from enum import Enum


class Role(str, Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    DELIVERY = "DELIVERY"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"


class OrderStatus(str, Enum):
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


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PromotionType(str, Enum):
    PROMO = "PROMO"
    DAILY_SPECIAL = "DAILY_SPECIAL"


class ReservationStatus(str, Enum):
    HELD = "HELD"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"


class ShiftStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    IN_PRODUCTION = "IN_PRODUCTION"
    DISPATCHING = "DISPATCHING"
    FINISHED = "FINISHED"


class VehicleType(str, Enum):
    """Transporte del repartidor. Estos valores ya existían como `CHECK` en
    `user_profiles` (§6.1) pero no estaban en el catálogo de enums de §7, igual
    que los tres que agregó T-0.2.2."""

    MOTO = "moto"
    BICI = "bici"
    AUTO = "auto"
    A_PIE = "a_pie"


class DriverStatus(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    NO_DISPONIBLE = "NO_DISPONIBLE"
    EN_RUTA = "EN_RUTA"
    INACTIVO = "INACTIVO"


class ZoneType(str, Enum):
    NEIGHBORHOOD = "neighborhood"
    RADIUS = "radius"


class ShippingMode(str, Enum):
    FREE = "free"
    FLAT = "flat"
    BY_DISTANCE = "by_distance"
    OFF = "off"


class CoverageMode(str, Enum):
    NEIGHBORHOOD = "neighborhood"
    RADIUS = "radius"
    NEIGHBORHOOD_AND_RADIUS = "neighborhood_and_radius"
    OFF = "off"


class BalanceTxnType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class BalanceOrigin(str, Enum):
    CANCELLATION = "cancellation"
    ORDER_USE = "order_use"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class NotificationType(str, Enum):
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


class AssignmentStatus(str, Enum):
    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class StopStatus(str, Enum):
    PENDING = "PENDING"
    ARRIVED = "ARRIVED"
    DELIVERED = "DELIVERED"
    INCIDENT = "INCIDENT"


class SettingValueType(str, Enum):
    JSON = "json"
    STRING = "string"
    INT = "int"
    BOOL = "bool"
