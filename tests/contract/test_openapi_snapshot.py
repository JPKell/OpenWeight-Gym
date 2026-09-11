"""The committed OpenAPI snapshot matches the application, and api.md matches the snapshot.

Packaging standards §6 (applications publish the OpenAPI snapshot) and Gold Standards G7. The
snapshot is ``docs/openapi.json``; ``api.md`` is the human document, and the second test keeps
its route list exactly the snapshot's — no route documented that does not exist, none served
that is not documented (row W10, gate C).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from weightroom.bootstrap import bootstrap
from weightroom.services.tls import HostIdentity

pytestmark = pytest.mark.contract

_XDG = ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs" / "openapi.json"
API_MD = ROOT / "docs" / "apps" / "weightroom" / "api.md"

_DOCUMENTED = re.compile(r"`(?:GET|POST|PUT|DELETE|PATCH) (/[^`\s?·]*)")
"""``\\`GET /path\\``, ``\\`POST /path/{id}\\``; a query string or a ``·`` list ends the path."""
_ROW = re.compile(r"^\| `(?:GET|POST|PUT|DELETE|PATCH) /", re.M)
"""Only a table row's first cell names one of this API's routes; prose cites other applications'."""


def current_openapi() -> dict[str, Any]:
    """The schema this build serves, in a stable key order.

    Built in a throwaway XDG tree of its own, whatever the caller's environment: ``bootstrap``
    prepares a real runtime (TLS, the database), and run from a shell it would otherwise renew
    the operator's leaf certificate and migrate the operator's database — it did, once, at W10.
    """
    with tempfile.TemporaryDirectory() as scratch:
        saved = {key: os.environ.get(key) for key in _XDG}
        for key in _XDG:
            os.environ[key] = str(Path(scratch) / key.lower())
        try:
            application = bootstrap(
                now=datetime(2026, 9, 10, tzinfo=UTC), identity=HostIdentity("jordan-main", ())
            )
            document = application.app.openapi()
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    return cast("dict[str, Any]", json.loads(json.dumps(document, sort_keys=True)))


def write() -> None:
    """Regenerate ``docs/openapi.json`` — the one way it is ever written."""
    SNAPSHOT.write_text(json.dumps(current_openapi(), indent=2, sort_keys=True) + "\n")


def _shape(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_the_committed_snapshot_matches_the_application() -> None:
    assert SNAPSHOT.is_file(), "docs/openapi.json is missing; regenerate it"
    committed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert committed == current_openapi(), (
        "docs/openapi.json drifted; regenerate with "
        "python -c 'from tests.contract.test_openapi_snapshot import write; write()'"
    )


def test_api_md_documents_exactly_the_routes_the_snapshot_serves() -> None:
    served = {_shape(path) for path in current_openapi()["paths"]}
    rows = [line for line in API_MD.read_text(encoding="utf-8").splitlines() if _ROW.match(line)]
    documented = {
        _shape("/api/v1" + path) for row in rows for path in _DOCUMENTED.findall(row.split("|")[1])
    }
    assert served - documented == set(), f"served but not in api.md: {sorted(served - documented)}"
    assert documented - served == set(), f"in api.md but not served: {sorted(documented - served)}"
