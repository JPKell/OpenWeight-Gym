"""End to end: the console boots with zero configuration and serves /api/v1/version."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from weightroom.bootstrap import bootstrap
from weightroom.services.tls import HostIdentity


@pytest.fixture
def application():  # type: ignore[no-untyped-def]  # a fixture returning Application
    return bootstrap(now=datetime.now(UTC), identity=HostIdentity("jordan-main", ()))


@pytest.fixture
def client(application) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    with TestClient(application.app, base_url="https://localhost") as test_client:
        yield test_client


def test_version_answers_without_a_cookie(client: TestClient) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["application"] == "weightroom" and body["api_version"] == "v1"
    assert body["schema_version"] == "1"
    assert response.headers["X-Api-Version"] == "v1"
    assert "set-cookie" not in response.headers


def test_the_trust_app_is_built_beside_the_console(application) -> None:  # type: ignore[no-untyped-def]
    with TestClient(application.trust_app, base_url="http://localhost") as trust:
        assert trust.get("/root.crt").status_code == 200
    assert application.runtime.tls.days_left >= 397


def test_a_wrong_host_is_421_before_anything_else(client: TestClient) -> None:
    response = client.get("/api/v1/version", headers={"Host": "attacker.example"})
    assert response.status_code == 421
    assert response.json()["error"]["code"] == "MISDIRECTED_REQUEST"
