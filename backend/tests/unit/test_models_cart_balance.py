"""Modelos `Cart` y `CustomerBalance` — vacíos, para el alta (`03_Roadmap.md` T-1.2.2)."""

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.balance import CustomerBalance
from app.models.cart import Cart
from app.models.user import User


def _make_customer(session, email="cliente@morficenter.test") -> User:
    user = User(first_name="Gustavo", last_name="Pérez", email=email)
    session.add(user)
    session.commit()
    return user


def test_customer_gets_a_cart_and_a_zero_balance(session):
    # Simula lo que hará AuthService.register (Tema 1.3) al dar de alta un CUSTOMER.
    user = _make_customer(session)
    session.add(Cart(user_id=user.id))
    session.add(CustomerBalance(user_id=user.id))
    session.commit()

    session.refresh(user)
    assert user.cart is not None
    assert user.balance is not None
    assert user.balance.balance == 0


def test_cart_and_balance_relationships_are_bidirectional(session):
    user = _make_customer(session)
    cart = Cart(user_id=user.id)
    balance = CustomerBalance(user_id=user.id)
    session.add_all([cart, balance])
    session.commit()

    assert cart.user is user
    assert balance.user is user


def test_cart_and_balance_have_utc_timestamps(session):
    user = _make_customer(session)
    session.add(Cart(user_id=user.id))
    session.add(CustomerBalance(user_id=user.id))
    session.commit()

    session.refresh(user)
    assert user.cart.updated_at.tzinfo is dt.UTC
    assert user.balance.updated_at.tzinfo is dt.UTC


def test_a_user_can_only_have_one_cart(session):
    user = _make_customer(session)
    session.add(Cart(user_id=user.id))
    session.commit()

    session.add(Cart(user_id=user.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_a_user_can_only_have_one_balance_by_primary_key(session):
    user = _make_customer(session)
    session.add(CustomerBalance(user_id=user.id))
    session.commit()

    session.add(CustomerBalance(user_id=user.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_balance_cannot_go_negative(session):
    user = _make_customer(session)
    session.add(CustomerBalance(user_id=user.id, balance=500))
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(
            text("UPDATE customer_balances SET balance = -1 WHERE user_id = :uid"),
            {"uid": user.id},
        )
    session.rollback()


def test_deleting_user_cascades_to_cart_and_balance(session):
    user = _make_customer(session)
    session.add(Cart(user_id=user.id))
    session.add(CustomerBalance(user_id=user.id))
    session.commit()

    session.delete(user)
    session.commit()

    assert session.query(Cart).filter_by(user_id=user.id).count() == 0
    assert session.get(CustomerBalance, user.id) is None
