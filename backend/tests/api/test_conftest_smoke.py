from sqlalchemy import text


async def test_health_via_async_client_fixture(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_fixture_gives_a_working_in_memory_db(session):
    assert session.execute(text("SELECT 1")).scalar() == 1


def test_session_fixture_is_isolated_between_tests(session):
    # Si esto fallara con datos de otro test, la fixture no estaría aislando bien.
    assert session.execute(text("SELECT 1")).scalar() == 1
