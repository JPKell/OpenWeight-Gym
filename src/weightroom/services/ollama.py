"""weightroom.services.ollama — read Ollama's unit, its residency and its journal; restart it once.

ADR-0125 rules 4 and 5. Ollama is a **system** unit; WeightRoomGym runs as the operator and is
never root, so everything here except one call is a read:

* ``systemctl show ollama.service`` — readable by any user — checked against
  ``MEMORY_SAFETY.md`` §2.1 by :mod:`weightroom.domain.ollama`.
* ``/api/ps`` through **ModelRack's** Ollama client, never a second client written here
  (ADR-0123 rule 5). Residency figures that the provider does not report are ``UNSUPPORTED`` and
  are rendered ``—``, never ``0`` (ADR-0016). The transport is injected — ModelRack's documented
  ``client=`` — so this process owns one pooled connection for the console's lifetime and closes
  it. The injected client must carry Ollama's ``base_url``: when one is supplied the provider
  issues **relative** paths against it and does not rebuild the URL from its own argument, which
  is a silent misroute if the client is a general-purpose one (found at row W2).
* ``journalctl -u ollama`` where the operator's group permits it, and *journal not readable* by
  name where it does not.

**The polkit grant, and how it is probed.** ADR-0125 rule 5 left the mechanism to this row and
suggested the rule file's presence or a recorded outcome. The file's presence is not available
here: ``/etc/polkit-1/rules.d`` is ``0750 root:polkitd`` on the reference machine, so the
operator cannot even ``stat`` a file inside it and every probe would answer *absent*. Nor can
polkit be asked directly — ``pkcheck`` refuses to evaluate an action with **details** for an
untrusted caller (*"Only trusted callers (e.g. uid 0 or an action owner) can use
CheckAuthorization() and pass details"*), and the rule keys on exactly those details (the unit
and the verb), so a detail-less check answers ``auth_admin_keep`` whether the rule is installed
or not. ``systemctl --dry-run restart`` exits ``0`` either way, because a dry run authorises
nothing.

So the probe is **the recorded outcome of the last attempt**, and the record is the audit trail
that already exists: the newest ``ollama.restart`` row says ``ok`` (permitted), ``refused`` (not
permitted) or is absent (not yet known). The attempt itself passes ``--no-ask-password``, which
is not optional: without it the call blocks on the desktop's interactive polkit agent — measured
at row W2, where it hung until it was killed — and a console request would hold a worker open
waiting for a password prompt nobody is looking at.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal

from baseaicore import Measurement, SuiteError, is_supported

from weightroom.domain.ollama import (
    APPLY_SCRIPT,
    CHECK_PROPERTIES,
    Finding,
    evaluate,
)
from weightroom.services.journal import JournalReader, JournalUnreadable
from weightroom.services.processes import SystemdController, UnitUnsupported

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings
    from weightroom.services.database import Database

__all__ = [
    "POLKIT_INSTALL_COMMAND",
    "POLKIT_RULE_PATH",
    "OllamaReport",
    "OllamaRestartNotPermitted",
    "ResidentView",
    "polkit_rule_text",
    "ollama_client",
    "ollama_report",
    "resident_models",
    "restart_ollama",
]

logger = logging.getLogger(__name__)

POLKIT_RULE_PATH: Final = "/etc/polkit-1/rules.d/50-weightroom-ollama.rules"
POLKIT_INSTALL_COMMAND: Final = (
    "sudo install -m 0644 <the file printed above> /etc/polkit-1/rules.d/50-weightroom-ollama.rules"
)
"""Printed for the operator to run in their own shell; this process never invokes it."""

_RESIDENCY_TIMEOUT_SECONDS: Final = 3.0

_NOT_PERMITTED_SIGNATURES: Final[tuple[str, ...]] = (
    "interactive authentication",
    "access denied",
    "not authorized",
    "permission denied",
)
"""What ``systemctl`` says when polkit refused, lower-cased. Anything else is a real failure.

Distinguishing the two matters: *you may not do this* is answered with the rule to install, and
*the unit would not restart* is answered with systemd's own message. Reporting the second as the
first would send an operator to write a polkit rule for a daemon that had crashed.
"""

type GrantState = Literal["permitted", "not_permitted", "unknown"]


class OllamaRestartNotPermitted(SuiteError):
    """No polkit grant: the restart is shown as the command to run (ADR-0125 rule 5)."""

    code: ClassVar[str] = "OLLAMA_RESTART_NOT_PERMITTED"


def polkit_rule_text(user: str) -> str:
    """The rule file ADR-0125 rule 5 specifies, for this operator.

    Args:
        user: The operator's OS user name.

    Returns:
        The complete file, ready to be saved and installed. A **unit and a verb** are granted,
        not a command: a sudoers line would grant ``systemctl`` itself, and this console is
        reachable from the LAN.
    """
    return (
        f"// {POLKIT_RULE_PATH}\n"
        "// Lets one user restart one unit, without a password and without granting systemctl.\n"
        "// Written by WeightRoomGym (ADR-0125 rule 5). Install it as root; this console cannot.\n"
        "polkit.addRule(function (action, subject) {\n"
        '    if (action.id == "org.freedesktop.systemd1.manage-units" &&\n'
        '        action.lookup("unit") == "ollama.service" &&\n'
        '        (action.lookup("verb") == "restart" || action.lookup("verb") == "start" ||\n'
        '         action.lookup("verb") == "stop") &&\n'
        f'        subject.user == "{user}") {{\n'
        "        return polkit.Result.YES;\n"
        "    }\n"
        "});\n"
    )


@dataclass(frozen=True, slots=True)
class ResidentView:
    """One model Ollama currently holds, in the fields the pane shows.

    ``vram_bytes`` and ``context_length`` are ``None`` where the provider did not report them —
    the console renders ``—``. They are never ``0``: a figure this environment cannot supply and
    a figure that is genuinely zero are different facts (ADR-0016).
    """

    name: str
    vram_bytes: int | None
    total_bytes: int | None
    context_length: int | None
    expires_at: str | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 shape."""
        return {
            "name": self.name,
            "vram_bytes": self.vram_bytes,
            "total_bytes": self.total_bytes,
            "context_length": self.context_length,
            "expires_at": self.expires_at,
        }


def _number(value: Measurement | None) -> int | None:
    """A measurement as a number, or ``None`` when the provider does not supply it.

    ``is_supported`` rather than a comparison: the sentinel raises on every numeric operation
    precisely so an unavailable figure cannot be summed or rendered as ``0`` by accident
    (ADR-0016).
    """
    if value is None or not is_supported(value):
        return None
    return int(value)


def ollama_client(settings: Settings) -> httpx.Client:
    """The pooled transport ModelRack's Ollama provider is handed.

    It carries ``base_url`` — see this module's docstring for why that is not optional. Owned by
    whoever builds it: the console's lifespan, or the ``with`` block of a CLI command.
    """
    import httpx as httpx_runtime

    return httpx_runtime.Client(
        base_url=settings.host.ollama_base_url, timeout=_RESIDENCY_TIMEOUT_SECONDS, trust_env=False
    )


def resident_models(
    settings: Settings, *, client: httpx.Client | None = None
) -> tuple[tuple[ResidentView, ...], str | None]:
    """What Ollama is holding, through ModelRack's client (ADR-0123 rule 5).

    Args:
        settings: The validated settings; ``[host] ollama_base_url``.
        client: A transport carrying Ollama's ``base_url`` — :func:`ollama_client` builds one.
            ``None`` lets ModelRack build and own its own.

    Returns:
        The resident models and ``None``, or an empty tuple and the reason the provider could not
        be reached — a daemon that is down is a state this pane renders, not an exception.
    """
    from modelrack.errors import ProviderError
    from modelrack.providers.ollama import OllamaProvider

    provider = OllamaProvider(settings.host.ollama_base_url, client=client)
    try:
        resident = provider.list_resident()
    except (ProviderError, OSError) as exc:
        logger.info("ollama.residency_unavailable", extra={"detail": str(exc)})
        return (), f"{type(exc).__name__}: {exc}"
    return (
        tuple(
            ResidentView(
                name=entry.identity.provider_model_name,
                vram_bytes=_number(entry.vram_bytes),
                total_bytes=_number(entry.total_bytes),
                context_length=_number(entry.context_length),
                expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
            )
            for entry in resident
        ),
        None,
    )


@dataclass(frozen=True, slots=True)
class OllamaReport:
    """Everything ``GET /ollama`` answers (api.md §5).

    Attributes:
        unit: ``ollama.service``.
        state: The unit's ``ActiveState``, or ``unsupported`` on a host with no systemd.
        findings: The §2.1 checklist, line by line.
        grant: Whether restarting is permitted, as far as the last attempt showed.
        journal_readable: Whether the operator's groups let them read this unit's journal.
        journal_detail: journalctl's own words when they do not.
        properties: The raw ``systemctl show`` values the findings were read from.
        apply_script: The fix, printed and never run.
    """

    unit: str
    state: str
    findings: tuple[Finding, ...]
    grant: GrantState
    journal_readable: bool
    journal_detail: str
    properties: dict[str, str]
    residency: tuple[ResidentView, ...] = ()
    residency_error: str | None = None
    apply_script: str = APPLY_SCRIPT

    @property
    def passing(self) -> int:
        """How many checklist lines pass."""
        return sum(1 for finding in self.findings if finding.outcome == "pass")

    @property
    def total(self) -> int:
        """How many lines there are."""
        return len(self.findings)

    @property
    def safe(self) -> bool:
        """Whether every line passes — the pane is green only then."""
        return self.total > 0 and self.passing == self.total

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 shape."""
        return {
            "unit": self.unit,
            "state": self.state,
            "safe": self.safe,
            "passing": self.passing,
            "total": self.total,
            "findings": [finding.as_json() for finding in self.findings],
            "restart_permitted": self.grant,
            "journal_readable": self.journal_readable,
            "journal_detail": self.journal_detail,
            "properties": self.properties,
            "residency": [entry.as_json() for entry in self.residency],
            "residency_error": self.residency_error,
            "apply_script": self.apply_script,
        }


def last_grant_state(database: Database | None) -> GrantState:
    """What the newest ``ollama.restart`` audit row says about the polkit grant.

    See this module's docstring for why this is the probe rather than the rule file's presence.

    Args:
        database: The trail; ``None`` (the CLI's read-only path) answers ``unknown``.

    Returns:
        ``permitted`` after a successful restart, ``not_permitted`` after a refused one, and
        ``unknown`` until one has been tried — which is the honest answer, and the pane says so
        rather than showing a button that may not work or hiding one that would.
    """
    if database is None:
        return "unknown"
    from sqlalchemy.exc import SQLAlchemyError

    from weightroom.services.audit import list_audit

    try:
        rows, _more = list_audit(database, limit=1, action="ollama.restart")
    except SQLAlchemyError:
        # A trail that cannot be read — an unmigrated database under `wr-gym doctor` on a fresh
        # install — is "not known", which is what this function already answers for "not tried".
        return "unknown"
    if not rows:
        return "unknown"
    return {"ok": "permitted", "refused": "not_permitted"}.get(rows[0].outcome, "unknown")  # type: ignore[return-value]


def ollama_report(
    settings: Settings,
    *,
    controller: SystemdController,
    client: httpx.Client | None = None,
    journal: JournalReader | None = None,
    database: Database | None = None,
    residency: bool = True,
) -> OllamaReport:
    """Read the unit, the checklist, the journal's readability and (optionally) residency.

    Args:
        settings: The validated settings.
        controller: The systemd boundary.
        client: An HTTP client for the residency read.
        journal: The journal boundary, for the readability probe.
        database: The audit trail, for the grant probe.
        residency: Whether to ask ``/api/ps``; the doctor and the table want it, a page that is
            only rendering the checklist does not.

    Returns:
        The report. Never raises for an unreadable unit or an unreachable daemon: both are
        states this pane exists to show.
    """
    unit = settings.host.ollama_unit
    try:
        properties = controller.properties(unit, CHECK_PROPERTIES, scope="system")
        state = properties.get("ActiveState", "unknown")
    except UnitUnsupported:
        return OllamaReport(
            unit=unit,
            state="unsupported",
            findings=evaluate(
                {}, memory_high=settings.host.memory_high, memory_max=settings.host.memory_max
            ),
            grant="unknown",
            journal_readable=False,
            journal_detail="unsupported on this host: no systemctl",
            properties={},
        )
    except SuiteError as exc:
        logger.warning("ollama.show_failed", extra={"detail": exc.message})
        properties, state = {}, "unknown"

    readable, detail = _journal_readable(unit, journal)
    resident: tuple[ResidentView, ...] = ()
    error: str | None = None
    if residency and state == "active":
        resident, error = resident_models(settings, client=client)
    return OllamaReport(
        unit=unit,
        state=state,
        findings=evaluate(
            properties, memory_high=settings.host.memory_high, memory_max=settings.host.memory_max
        ),
        grant=last_grant_state(database),
        journal_readable=readable,
        journal_detail=detail,
        properties=properties,
        residency=resident,
        residency_error=error,
    )


def _journal_readable(unit: str, journal: JournalReader | None) -> tuple[bool, str]:
    """One cheap read of the system journal, to find out whether the operator's groups allow it."""
    if journal is None or not journal.available():
        return False, "journal not readable: no journalctl on this host"
    try:
        journal.history([unit], scope="system", limit=1)
    except JournalUnreadable as exc:
        return False, f"journal not readable: {exc.details.get('stderr') or exc.message}"
    except UnitUnsupported:
        return False, "journal not readable: no journalctl on this host"
    return True, "readable"


def restart_ollama(
    settings: Settings,
    *,
    controller: SystemdController,
    user: str,
) -> str:
    """Restart Ollama's system unit, or refuse with the rule to install (ADR-0125 rule 5).

    Args:
        settings: The validated settings.
        controller: The systemd boundary.
        user: The operator's OS user, for the rule text.

    Returns:
        systemd's own output on success, which is usually empty.

    Raises:
        OllamaRestartNotPermitted: polkit refused. ``details`` carries the command to run, the
            rule file's text and its path, so the page can show all three.
        UnitActionFailed: systemd tried and the unit would not restart — a different fact, and
            answered with systemd's message rather than with a polkit rule.
        UnitUnsupported: This host has no systemd.
    """
    from weightroom.services.processes import UnitActionFailed

    result = controller.act(settings.host.ollama_unit, "restart", scope="system")
    if result.ok:
        return result.stdout.strip()
    text = result.failure_text.lower()
    if any(signature in text for signature in _NOT_PERMITTED_SIGNATURES):
        raise OllamaRestartNotPermitted(
            f"Restarting {settings.host.ollama_unit} needs a polkit grant this host has not "
            f"given. Install the rule below as root and try again; WeightRoomGym never runs "
            f"sudo itself.",
            details={
                "unit": settings.host.ollama_unit,
                "command": f"systemctl restart {settings.host.ollama_unit}",
                "rule_path": POLKIT_RULE_PATH,
                "rule": polkit_rule_text(user),
                "install": POLKIT_INSTALL_COMMAND,
                "stderr": result.stderr.strip(),
            },
        )
    raise UnitActionFailed(
        f"systemctl restart {settings.host.ollama_unit} failed: {result.failure_text}",
        details={"unit": settings.host.ollama_unit, "stderr": result.stderr.strip()},
    )
