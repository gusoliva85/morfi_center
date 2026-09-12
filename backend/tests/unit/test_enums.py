from app.core import enums


def test_role_values():
    assert [r.value for r in enums.Role] == ["CUSTOMER", "ADMIN", "DELIVERY"]


def test_user_status_values():
    assert [s.value for s in enums.UserStatus] == ["ACTIVE", "SUSPENDED", "INACTIVE"]


def test_auth_provider_is_lowercase():
    assert enums.AuthProvider.LOCAL.value == "local"
    assert enums.AuthProvider.GOOGLE.value == "google"


def test_order_status_has_all_12_states_in_order():
    assert [s.value for s in enums.OrderStatus] == [
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
    ]


def test_shift_status_values():
    assert [s.value for s in enums.ShiftStatus] == [
        "SCHEDULED",
        "OPEN",
        "CLOSED",
        "IN_PRODUCTION",
        "DISPATCHING",
        "FINISHED",
    ]


def test_driver_status_values():
    assert [s.value for s in enums.DriverStatus] == [
        "DISPONIBLE",
        "NO_DISPONIBLE",
        "EN_RUTA",
        "INACTIVO",
    ]


def test_coverage_mode_values():
    assert [m.value for m in enums.CoverageMode] == [
        "neighborhood",
        "radius",
        "neighborhood_and_radius",
        "off",
    ]


def test_notification_type_has_all_12_events():
    assert len(list(enums.NotificationType)) == 12


def test_assignment_status_matches_delivery_assignments_check():
    assert [s.value for s in enums.AssignmentStatus] == [
        "DRAFT",
        "ASSIGNED",
        "IN_PROGRESS",
        "COMPLETED",
    ]


def test_stop_status_matches_delivery_stops_check():
    assert [s.value for s in enums.StopStatus] == ["PENDING", "ARRIVED", "DELIVERED", "INCIDENT"]


def test_setting_value_type_matches_system_settings_check():
    assert [t.value for t in enums.SettingValueType] == ["json", "string", "int", "bool"]


def test_all_enums_are_str_enum():
    enum_classes = [
        enums.Role,
        enums.UserStatus,
        enums.AuthProvider,
        enums.OrderStatus,
        enums.PaymentStatus,
        enums.PromotionType,
        enums.ReservationStatus,
        enums.ShiftStatus,
        enums.DriverStatus,
        enums.ZoneType,
        enums.ShippingMode,
        enums.CoverageMode,
        enums.BalanceTxnType,
        enums.BalanceOrigin,
        enums.NotificationType,
        enums.AssignmentStatus,
        enums.StopStatus,
        enums.SettingValueType,
    ]
    assert len(enum_classes) == 18
    for enum_cls in enum_classes:
        for member in enum_cls:
            assert isinstance(member, str)
            assert isinstance(member.value, str)
