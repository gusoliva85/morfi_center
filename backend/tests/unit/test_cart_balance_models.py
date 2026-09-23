import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.enums import Role
from app.models import Cart, CustomerBalance, User


def make_customer(**overrides) -> User:
    data = {
        "first_name": "Ana",
        "last_name": "Pérez",
        "email": "ana@example.com",
        "role": Role.CUSTOMER,
    }
    data.update(overrides)
    user = User(**data)
    user.cart = Cart()
    user.balance = CustomerBalance()
    return user


def test_customer_is_created_with_empty_cart_and_zero_balance(session):
    session.add(make_customer())
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.cart is not None
    assert user.cart.user_id == user.id
    assert user.balance is not None
    assert user.balance.balance == 0


def test_cart_and_balance_timestamps_are_utc(session):
    session.add(make_customer())
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.cart.updated_at.utcoffset().total_seconds() == 0
    assert user.balance.updated_at.utcoffset().total_seconds() == 0


def test_a_user_cannot_have_two_carts(session):
    user = make_customer()
    session.add(user)
    session.commit()

    session.add(Cart(user_id=user.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_a_user_cannot_have_two_balances(session):
    # INSERT crudo a propósito: con el ORM, el identity map corta el duplicado
    # antes de llegar a la base y no se probaría la restricción de verdad.
    user = make_customer()
    session.add(user)
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(
            text("INSERT INTO customer_balances (user_id, balance, updated_at) VALUES (:u, 0, :t)"),
            {"u": user.id, "t": "2026-09-23 12:00:00"},
        )


def test_negative_balance_is_rejected(session):
    user = make_customer()
    session.add(user)
    session.commit()

    user.balance.balance = -100
    with pytest.raises(IntegrityError):
        session.commit()


def test_balance_can_be_credited(session):
    user = make_customer()
    session.add(user)
    session.commit()

    user.balance.balance = 150000  # $1.500 en centavos
    session.commit()
    session.expire_all()

    assert session.get(CustomerBalance, user.id).balance == 150000


def test_deleting_user_cascades_to_cart_and_balance(session):
    user = make_customer()
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    assert session.scalars(select(Cart)).all() == []
    assert session.scalars(select(CustomerBalance)).all() == []


def test_cart_and_balance_require_an_existing_user(session):
    session.add(Cart(user_id=999))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(CustomerBalance(user_id=999))
    with pytest.raises(IntegrityError):
        session.commit()


def test_balance_is_stored_as_integer_cents(session):
    user = make_customer()
    user.balance.balance = 31800
    session.add(user)
    session.commit()

    raw = session.execute(text("SELECT balance FROM customer_balances")).scalar_one()
    assert raw == 31800
    assert isinstance(raw, int)
