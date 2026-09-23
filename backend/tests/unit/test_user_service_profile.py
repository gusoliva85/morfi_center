import pytest

from app.services.user_service import update_profile


class FakeUser:
    """Sin base de datos: `update_profile` es lógica pura."""

    def __init__(self, first_name="Ana", last_name="Pérez", phone="1155551234"):
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone


def test_updates_the_phone():
    user = FakeUser()

    update_profile(user, {"phone": "1199998888"})

    assert user.phone == "1199998888"


def test_updates_names():
    user = FakeUser()

    update_profile(user, {"first_name": "Juan", "last_name": "Gómez"})

    assert (user.first_name, user.last_name) == ("Juan", "Gómez")


def test_a_field_that_was_not_sent_stays_untouched():
    """Lo importante del PATCH: editar el nombre no debe borrar el teléfono."""
    user = FakeUser()

    update_profile(user, {"first_name": "Juan"})

    assert user.first_name == "Juan"
    assert user.last_name == "Pérez"
    assert user.phone == "1155551234"


def test_an_empty_change_set_does_nothing():
    user = FakeUser()

    update_profile(user, {})

    assert (user.first_name, user.last_name, user.phone) == ("Ana", "Pérez", "1155551234")


def test_sending_phone_null_clears_it():
    """Distinto de no mandarlo: acá el usuario quiere borrar su teléfono."""
    user = FakeUser()

    update_profile(user, {"phone": None})

    assert user.phone is None


def test_an_empty_phone_is_stored_as_null_not_as_empty_string():
    user = FakeUser()

    update_profile(user, {"phone": "   "})

    assert user.phone is None


def test_names_and_phone_are_trimmed():
    user = FakeUser()

    update_profile(user, {"first_name": "  Juan ", "last_name": " Gómez  ", "phone": " 1122 "})

    assert (user.first_name, user.last_name, user.phone) == ("Juan", "Gómez", "1122")


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_a_blank_name_is_rejected(blank):
    user = FakeUser()

    with pytest.raises(ValueError):
        update_profile(user, {"first_name": blank})

    assert user.first_name == "Ana"  # no quedó a medias


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_a_blank_last_name_is_rejected(blank):
    user = FakeUser()

    with pytest.raises(ValueError):
        update_profile(user, {"last_name": blank})

    assert user.last_name == "Pérez"
