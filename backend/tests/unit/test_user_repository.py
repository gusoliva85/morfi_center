import pytest

from app.core.enums import AuthProvider, Role, UserStatus
from app.models import User
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def repo(session) -> UserRepository:
    return UserRepository(session)


def new_user(repo: UserRepository, **overrides) -> User:
    data = {"first_name": "Ana", "last_name": "Pérez", "email": "ana@example.com"}
    data.update(overrides)
    return repo.create(**data)


def test_create_assigns_an_id_and_defaults(repo):
    user = new_user(repo)

    assert user.id is not None
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash is None


def test_create_stores_the_email_normalized(repo):
    user = new_user(repo, email="  Ana@Example.COM ")

    assert user.email == "ana@example.com"


def test_get_by_id_finds_the_user_and_returns_none_when_missing(repo):
    user = new_user(repo)

    assert repo.get_by_id(user.id) is user
    assert repo.get_by_id(99999) is None


def test_get_by_email_ignores_case_and_surrounding_spaces(repo):
    user = new_user(repo, email="ana@example.com")

    assert repo.get_by_email("ana@example.com") is user
    assert repo.get_by_email("ANA@Example.com") is user
    assert repo.get_by_email("  ana@example.com  ") is user


def test_get_by_email_returns_none_when_missing(repo):
    assert repo.get_by_email("nadie@example.com") is None


def test_create_accepts_staff_roles_and_a_password_hash(repo):
    driver = new_user(
        repo, email="repartidor@example.com", role=Role.DELIVERY, password_hash="hash-bcrypt"
    )

    assert driver.role == Role.DELIVERY
    assert driver.password_hash == "hash-bcrypt"


def test_list_returns_every_user_with_the_total(repo):
    for i in range(3):
        new_user(repo, email=f"u{i}@example.com")

    users, total = repo.list()

    assert len(users) == 3
    assert total == 3


def test_list_filters_by_role(repo):
    new_user(repo, email="cliente@example.com", role=Role.CUSTOMER)
    new_user(repo, email="admin@example.com", role=Role.ADMIN)
    new_user(repo, email="repartidor@example.com", role=Role.DELIVERY)

    admins, total = repo.list(role=Role.ADMIN)

    assert [u.email for u in admins] == ["admin@example.com"]
    assert total == 1


def test_list_paginates_and_total_ignores_the_page(repo):
    for i in range(5):
        new_user(repo, email=f"u{i}@example.com")

    first_page, total = repo.list(page=1, page_size=2)
    second_page, _ = repo.list(page=2, page_size=2)
    third_page, _ = repo.list(page=3, page_size=2)

    assert [u.email for u in first_page] == ["u0@example.com", "u1@example.com"]
    assert [u.email for u in second_page] == ["u2@example.com", "u3@example.com"]
    assert [u.email for u in third_page] == ["u4@example.com"]
    assert total == 5  # el total es el global, no el de la página


def test_list_beyond_the_last_page_is_empty_not_an_error(repo):
    new_user(repo)

    users, total = repo.list(page=99, page_size=20)

    assert users == []
    assert total == 1


def test_list_total_counts_only_the_filtered_role(repo):
    for i in range(3):
        new_user(repo, email=f"c{i}@example.com", role=Role.CUSTOMER)
    new_user(repo, email="admin@example.com", role=Role.ADMIN)

    customers, total = repo.list(role=Role.CUSTOMER, page=1, page_size=2)

    assert len(customers) == 2
    assert total == 3


def test_link_provider_and_get_provider_round_trip(repo):
    user = new_user(repo)

    link = repo.link_provider(user, AuthProvider.GOOGLE, provider_uid="google-sub-1")

    assert link.id is not None
    found = repo.get_provider(AuthProvider.GOOGLE, "google-sub-1")
    assert found is link
    assert found.user_id == user.id
    assert found.linked_at is not None


def test_get_provider_returns_none_for_an_unknown_uid(repo):
    user = new_user(repo)
    repo.link_provider(user, AuthProvider.GOOGLE, provider_uid="google-sub-1")

    assert repo.get_provider(AuthProvider.GOOGLE, "otro-sub") is None


def test_get_provider_does_not_mix_up_providers(repo):
    user = new_user(repo)
    repo.link_provider(user, AuthProvider.GOOGLE, provider_uid="mismo-uid")

    assert repo.get_provider(AuthProvider.LOCAL, "mismo-uid") is None


def test_link_provider_local_leaves_the_uid_empty(repo):
    user = new_user(repo)

    link = repo.link_provider(user, AuthProvider.LOCAL)

    assert link.provider == AuthProvider.LOCAL
    assert link.provider_uid is None


def test_a_user_can_have_local_and_google_linked(repo):
    user = new_user(repo)

    repo.link_provider(user, AuthProvider.LOCAL)
    repo.link_provider(user, AuthProvider.GOOGLE, provider_uid="google-sub-1")

    assert {p.provider for p in user.auth_providers} == {AuthProvider.LOCAL, AuthProvider.GOOGLE}
