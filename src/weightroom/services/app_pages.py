"""weightroom.services.app_pages — where an application page's data comes from (spec §7.3).

One rule for every page under an application's tab, written once so no page re-decides it:

* **Running and reachable** — the application's own API. A call that fails renders as its
  refusal, never as the database's figures quietly substituted for what the application itself
  could not answer (the Overview's rule, W3).
* **Stopped, or not answering** — the application's database, read-only and only at a revision
  this console knows (ADR-0123 rule 3); a page with no database source says so.
* **A version outside the range** — neither: the page degrades by name (spec §19).

The footer names which, in words (spec §7.3: *from the API*, *from the database at revision 0015*).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from baseaicore import SuiteError

from weightroom.services.apps import AppVersionMismatch

if TYPE_CHECKING:
    from weightroom.services.apps import AppView
    from weightroom.services.db_reader import AppDatabase

__all__ = ["Sourced", "read"]


@dataclass(frozen=True, slots=True)
class Sourced[T]:
    """A page's data and where it came from.

    Attributes:
        source: ``api``, ``database`` or ``none``.
        detail: The footer's sentence.
        data: What the source answered, or ``None`` when nothing did.
        error: Why nothing did, when that was a refusal the page should show by its code.
    """

    source: Literal["api", "database", "none"]
    detail: str
    data: T | None
    error: SuiteError | None = None

    @property
    def live(self) -> bool:
        """Whether the application's API answered — the condition for every API-only action."""
        return self.source == "api"


def read[T](
    view: AppView,
    *,
    api: Callable[[], T],
    database: Callable[[AppDatabase], T] | None,
    open_database: Callable[[], AppDatabase],
) -> Sourced[T]:
    """Read one page's data by spec §7.3's rule.

    Args:
        view: The application as this request sees it.
        api: Reads the data from the running application's API.
        database: Reads the same data from an open, known-revision database handle; ``None`` for a
            page whose subject exists only in the running process (a tool registry, a probe).
        open_database: Opens the application's database read-only, refusing an unknown revision
            (``db_reader.open_app_database``, bound by the route).

    Returns:
        The :class:`Sourced` result. Never raises a :class:`~baseaicore.SuiteError`: every
        refusal, unreachable database and unknown revision becomes ``source="none"`` with the
        error attached, so a page renders it rather than an error page.
    """
    if view.pill == "version mismatch":
        mismatch = AppVersionMismatch(
            f"{view.name} {view.version} is outside the range this console speaks to "
            f"({view.supported_range}); its pages are degraded by name rather than guessed at.",
            details={"app": view.name, "version": view.version},
        )
        return Sourced("none", mismatch.message, None, mismatch)
    if view.running and view.reachable:
        try:
            return Sourced("api", "From the API", api())
        except SuiteError as exc:
            return Sourced("none", f"The API did not answer this page: {exc.message}", None, exc)
    if database is None:
        return Sourced(
            "none",
            f"{view.name} is not answering, and this page reads only from its running API.",
            None,
        )
    try:
        with open_database() as handle:
            revision = handle.revision.found or "none"
            return Sourced(
                "database", f"From the database at revision {revision}", database(handle)
            )
    except SuiteError as exc:
        return Sourced("none", exc.message, None, exc)
