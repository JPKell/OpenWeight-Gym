"""The trust listener serves exactly two routes, without a cookie, and refuses every other path."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from weightroom.config import load_settings
from weightroom.services.tls import HostIdentity, init_tls
from weightroom.web.trust_app import create_trust_app

IDENTITY = HostIdentity("jordan-main", ("10.77.10.84",))


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = load_settings(config_path=tmp_path / "absent.toml").settings
    status = init_tls(settings, identity=IDENTITY, now=datetime.now(UTC))
    return TestClient(
        create_trust_app(settings, tls=status, identity=IDENTITY), base_url="http://localhost"
    )


def test_root_crt_and_trust_answer_200_without_any_cookie(client: TestClient) -> None:
    certificate = client.get("/root.crt")
    assert certificate.status_code == 200
    assert certificate.headers["content-type"].startswith("application/x-x509-ca-cert")
    assert certificate.content.startswith(b"-----BEGIN CERTIFICATE-----")
    assert "set-cookie" not in certificate.headers
    page = client.get("/trust")
    assert page.status_code == 200
    assert "set-cookie" not in page.headers
    assert "SHA-256" in page.text and "root.crt" in page.text
    assert "http://jordan-main.local:8770/root.crt" in page.text
    assert "https://10.77.10.84:8769" in page.text
    assert "CA certificate" in page.text  # the Android store, by name


@pytest.mark.parametrize(
    "path", ["/", "/login", "/api/v1/version", "/trust/root.crt", "/static/css/tokens.css"]
)
def test_every_other_path_is_404_with_the_envelope_and_no_cookie(
    client: TestClient, path: str
) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "set-cookie" not in response.headers
    assert client.post("/trust").status_code == 404
    assert client.post("/root.crt").status_code == 404


def test_a_wrong_host_header_is_421_even_here(client: TestClient) -> None:
    response = client.get("/root.crt", headers={"Host": "evil.example"})
    assert response.status_code == 421
