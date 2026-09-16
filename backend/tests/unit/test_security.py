import pytest

from app.core.security import hash_password, verify_password


def test_verify_password_true_for_correct_password():
    hashed = hash_password("miPassword123")
    assert verify_password("miPassword123", hashed) is True


def test_verify_password_false_for_wrong_password():
    hashed = hash_password("miPassword123")
    assert verify_password("otraCosa456", hashed) is False


def test_hash_is_not_the_plaintext():
    password = "miPassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert password not in hashed


def test_hash_uses_cost_factor_12():
    hashed = hash_password("miPassword123")
    # formato bcrypt: $2b$<cost>$<22 chars de sal><31 chars de hash>
    cost = int(hashed.split("$")[2])
    assert cost == 12


def test_same_password_hashed_twice_gives_different_hashes():
    # bcrypt genera una sal distinta cada vez (gensalt) -> hashes distintos
    h1 = hash_password("miPassword123")
    h2 = hash_password("miPassword123")
    assert h1 != h2
    assert verify_password("miPassword123", h1) is True
    assert verify_password("miPassword123", h2) is True


def test_password_at_the_72_byte_limit_does_not_raise():
    password = "a1" * 36  # exactamente 72 bytes, el limite duro de bcrypt
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_password_over_72_bytes_is_silently_truncated_by_this_bcrypt_version():
    # Comportamiento real verificado con bcrypt==4.3.0 (nuestro pin es
    # >=4.1,<5.0): NO lanza error, trunca en silencio a 72 bytes -> dos
    # contraseñas que comparten el mismo prefijo de 72 bytes "verifican"
    # como iguales. bcrypt>=5.0 en cambio lanza ValueError para el mismo
    # caso (probado por separado). Por eso T-1.1.1 rechaza contraseñas de
    # más de 72 bytes ANTES de llegar acá: sin esa validación, esto sería
    # un problema silencioso hoy y un crash si algún día se saca el <5.0.
    long_password = "a" * 100
    hashed = hash_password(long_password)
    assert verify_password("a" * 72, hashed) is True
    assert verify_password("a" * 71 + "b", hashed) is False
