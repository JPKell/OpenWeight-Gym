"""``configure_logging``: routine HTTP calls stay out of the operator's log unless asked for."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from weightroom.observability.logging import configure_logging

_TOUCHED = ("", "httpx", "httpcore", "sqlalchemy.engine")


@pytest.fixture(autouse=True)
def _restore_loggers() -> Iterator[None]:
    """configure_logging replaces the root handlers; put every touched logger back afterwards."""
    saved = {
        name: (logging.getLogger(name).level, list(logging.getLogger(name).handlers))
        for name in _TOUCHED
    }
    try:
        yield
    finally:
        for name, (level, handlers) in saved.items():
            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.handlers[:] = handlers


@pytest.mark.parametrize("level", ["INFO", "WARNING"])
def test_httpx_request_lines_are_quiet_at_ordinary_levels(level: str) -> None:
    """One INFO line per sampler and version-check call buried everything else an operator reads."""
    configure_logging(level=level, log_format="json")
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


def test_debug_brings_the_request_lines_back() -> None:
    logging.getLogger("httpx").setLevel(logging.NOTSET)
    logging.getLogger("httpcore").setLevel(logging.NOTSET)
    configure_logging(level="DEBUG", log_format="json")
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.DEBUG
