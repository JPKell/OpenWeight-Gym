"""weightroom.services.freeweight_actions — what FreeWeight's tab asks FreeWeight to do (row WP3).

Every call goes through :mod:`~weightroom.services.app_api`, so FreeWeight validates and refuses in
its own words (arc index §2 item 4). Two actions are not here, because they already exist: starting
a run is W9's ``freeweight_suite_run`` job, which runs under ADR-0119's cap and is enqueued through
the jobs route's own helper; enabling a model is W8's ``catalog.set_enabled``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

from weightroom.services.app_api import call
from weightroom.services.freeweight_pages import APP, segment

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings

__all__ = ["cancel_run", "discover", "repeat_run"]

_DISCOVER_TIMEOUT_SECONDS: Final = 120.0
"""Discovery asks the provider for every model and its descriptor; LoadCoach's takes as long."""
_ACTION_TIMEOUT_SECONDS: Final = 30.0


def _answer(body: Any) -> dict[str, Any]:  # noqa: ANN401 — the application's JSON body
    return dict(body) if isinstance(body, Mapping) else {}


def discover(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``POST /models/discover``: the added, updated, unchanged and total counts.

    Raises:
        AppRefused: ``PROVIDER_UNAVAILABLE`` and the like, in FreeWeight's words.
        AppUnreachable: It did not answer.
    """
    return _answer(
        call(client, settings, APP, "POST", "models/discover",
             timeout_seconds=_DISCOVER_TIMEOUT_SECONDS)
    )  # fmt: skip


def cancel_run(client: httpx.Client, settings: Settings, run_id: str) -> dict[str, Any]:
    """``POST /runs/{id}/cancel``: the run's new state — ``cancelling`` for one that is running.

    Raises:
        AppRefused: ``409 RUN_NOT_CANCELLABLE`` for a finished run, ``RUN_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _answer(
        call(client, settings, APP, "POST", f"runs/{segment(run_id)}/cancel",
             timeout_seconds=_ACTION_TIMEOUT_SECONDS)
    )  # fmt: skip


def repeat_run(
    client: httpx.Client, settings: Settings, run_id: str, *, force: bool, label: str
) -> dict[str, Any]:
    """``POST /runs/{id}/repeat``: a new run with the original's frozen configuration.

    FreeWeight checks this machine against the original's fingerprint first and refuses by name;
    ``force`` proceeds and records the divergence on the new run, where its page shows it.

    Args:
        client: The pooled HTTP client.
        settings: The validated settings.
        run_id: The run to repeat.
        force: Proceed past every blocker, recording the divergence.
        label: A label for the new run; blank takes FreeWeight's default.

    Raises:
        AppRefused: ``REPEAT_REFUSED`` with every blocker in its details, ``RUN_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _answer(
        call(
            client, settings, APP, "POST", f"runs/{segment(run_id)}/repeat",
            params={"force": "true" if force else None, "label": label.strip() or None},
            timeout_seconds=_ACTION_TIMEOUT_SECONDS,
        )
    )  # fmt: skip
