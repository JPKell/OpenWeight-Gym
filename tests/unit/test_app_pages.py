"""weightroom.services.app_pages — spec §7.3's source rule, decided once for every page."""

from __future__ import annotations

from types import SimpleNamespace, TracebackType
from typing import Any

import pytest

from weightroom.services.app_api import AppRefused
from weightroom.services.app_pages import read
from weightroom.services.apps import AppView
from weightroom.services.db_reader import SchemaUnknown


def _view(*, running: bool, reachable: bool, verdict: str = "ok") -> AppView:
    return AppView(
        name="promptcadence",
        installed=True,
        executable="/usr/bin/promptcadence",
        unit="promptcadence.service",
        unit_state="active" if running else "inactive",
        uptime_seconds=60.0 if running else None,
        restarts=0,
        base_url="http://127.0.0.1:8768",
        version="1.3.3" if reachable else None,
        api_version="v1" if reachable else None,
        verdict=verdict if reachable else "unreadable",
        supported_range=">=1.0,<2",
    )


class _Handle:
    """A stand-in for an open ``AppDatabase``: a revision and a context manager."""

    def __init__(self, revision: str) -> None:
        self.revision = SimpleNamespace(found=revision)
        self.closed = False

    def __enter__(self) -> _Handle:
        return self

    def __exit__(
        self, kind: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.closed = True


def _never() -> Any:  # noqa: ANN401
    pytest.fail("this source must not be read")


def test_running_and_reachable_reads_the_api_and_never_opens_the_database() -> None:
    result = read(
        _view(running=True, reachable=True),
        api=lambda: ["from api"],
        database=lambda _handle: ["from db"],
        open_database=_never,
    )
    assert (result.source, result.data, result.live) == ("api", ["from api"], True)
    assert result.detail == "From the API"


def test_an_api_refusal_renders_as_the_refusal_not_the_databases_rows() -> None:
    refused = AppRefused("promptcadence refused: busy", details={"app_code": "BUSY"})

    def api() -> list[str]:
        raise refused

    result = read(
        _view(running=True, reachable=True),
        api=api,
        database=lambda _h: ["db"],
        open_database=_never,
    )
    assert (result.source, result.data, result.error) == ("none", None, refused)


def test_stopped_reads_the_database_and_names_its_revision() -> None:
    handle = _Handle("0011")
    result = read(
        _view(running=False, reachable=False),
        api=_never,
        database=lambda h: [h.revision.found],
        open_database=lambda: handle,  # type: ignore[arg-type,return-value]  # a duck-typed handle
    )
    assert (result.source, result.data, result.live) == ("database", ["0011"], False)
    assert result.detail == "From the database at revision 0011"
    assert handle.closed


def test_a_page_with_no_database_source_says_so_when_stopped() -> None:
    result = read(
        _view(running=False, reachable=False), api=_never, database=None, open_database=_never
    )
    assert result.source == "none"
    assert result.data is None
    assert "reads only from its running API" in result.detail


def test_an_unknown_revision_degrades_the_page_by_name() -> None:
    def refuse() -> Any:  # noqa: ANN401
        raise SchemaUnknown("promptcadence's schema at revision 9999 is not known")

    result = read(
        _view(running=False, reachable=False),
        api=_never,
        database=lambda _h: [],
        open_database=refuse,
    )
    assert result.source == "none"
    assert isinstance(result.error, SchemaUnknown)
    assert "9999" in result.detail


def test_a_version_outside_the_range_reads_neither_source() -> None:
    result = read(
        _view(running=True, reachable=True, verdict="too_new"),
        api=_never,
        database=lambda _h: [],
        open_database=_never,
    )
    assert result.source == "none"
    assert result.error is not None
    assert result.error.code == "APP_VERSION_MISMATCH"
