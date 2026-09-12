"""`UserRepository` (`03_Roadmap.md` T-1.2.4)."""

from app.core.enums import AuthProvider, Role, UserStatus
from app.repositories.user_repository import UserRepository


def _repo(session) -> UserRepository:
    return UserRepository(session)


def _new_user(repo, n: int, **overrides):
    defaults = {
        "first_name": f"Nombre{n}",
        "last_name": "Apellido",
        "email": f"user{n}@morficenter.test",
    }
    return repo.create(**{**defaults, **overrides})


# ── create / get_by_id / get_by_email ───────────────────
def test_create_returns_persisted_user_with_id(session):
    repo = _repo(session)
    user = repo.create(first_name="Gustavo", last_name="Pérez", email="gustavo@morficenter.test")
    assert user.id is not None
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE


def test_get_by_id_found_and_not_found(session):
    repo = _repo(session)
    user = _new_user(repo, 1)
    assert repo.get_by_id(user.id) is user
    assert repo.get_by_id(999999) is None


def test_get_by_email_found_and_not_found(session):
    repo = _repo(session)
    _new_user(repo, 1, email="ana@morficenter.test")
    assert repo.get_by_email("ana@morficenter.test").email == "ana@morficenter.test"
    assert repo.get_by_email("no-existe@morficenter.test") is None


def test_create_does_not_commit_only_flushes(session):
    repo = _repo(session)
    user = repo.create(first_name="Temp", last_name="User", email="temp@morficenter.test")
    user_id = user.id
    assert user_id is not None  # el flush ya le asignó id

    session.rollback()  # nadie hizo commit todavía
    assert repo.get_by_id(user_id) is None  # se deshizo


# ── list (paginación y filtro por rol) ──────────────────
def test_list_paginates_and_orders_by_id(session):
    repo = _repo(session)
    for n in range(1, 6):
        _new_user(repo, n)

    page1 = repo.list(page=1, page_size=2)
    assert [u.id for u in page1.items] == sorted(u.id for u in page1.items)
    assert len(page1.items) == 2
    assert page1.total == 5
    assert page1.pages == 3

    page3 = repo.list(page=3, page_size=2)
    assert len(page3.items) == 1  # 5 usuarios, página 3 de a 2 -> 1 resto


def test_list_defaults_when_page_args_missing_or_invalid(session):
    repo = _repo(session)
    for n in range(1, 3):
        _new_user(repo, n)

    page = repo.list(page=0, page_size=-5)  # se corrigen a valores válidos
    assert page.page == 1
    assert page.page_size >= 1
    assert page.total == 2


def test_list_filters_by_role(session):
    repo = _repo(session)
    _new_user(repo, 1, role=Role.ADMIN)
    _new_user(repo, 2, role=Role.CUSTOMER)
    _new_user(repo, 3, role=Role.DELIVERY)

    admins = repo.list(role=Role.ADMIN)
    assert admins.total == 1
    assert admins.items[0].role == Role.ADMIN

    everyone = repo.list()
    assert everyone.total == 3


# ── get_provider / link_provider ────────────────────────
def test_link_provider_and_get_provider_round_trip(session):
    repo = _repo(session)
    user = _new_user(repo, 1, email="google@morficenter.test", password_hash=None)

    link = repo.link_provider(user, AuthProvider.GOOGLE, "sub-123")
    assert link.id is not None
    assert link.linked_at is not None

    found = repo.get_provider(AuthProvider.GOOGLE, "sub-123")
    assert found is not None
    assert found.user_id == user.id


def test_get_provider_not_found_returns_none(session):
    repo = _repo(session)
    assert repo.get_provider(AuthProvider.GOOGLE, "no-existe") is None


def test_link_provider_local_without_uid(session):
    repo = _repo(session)
    user = _new_user(repo, 1)
    link = repo.link_provider(user, AuthProvider.LOCAL)
    assert link.provider_uid is None
    assert link.provider == AuthProvider.LOCAL
