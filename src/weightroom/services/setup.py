"""weightroom.services.setup — what ``wr-gym setup`` does, given the operator's answers.

The prompts live in the CLI; this module takes the answers and does the work, so a test drives
it without a terminal. Steps (development plan Phase 1): the CA (``tls init`` unless present),
the operator account (unless present), ``server.allowed_hosts`` from the host's names and
addresses, ``server.host`` as chosen, and an application token for every **installed**
application that issues them (ADR-0126 rule 8: ``loadcoach`` with ``write``, ``promptcadence``
with ``write,approve``) written to ``<config>/secrets/<app>.token`` (``0600``) and named by
``api_key_file`` — never the value. The configuration file is edited in place with ``tomlkit``,
comments kept, written beside and renamed over with a ``.bak`` (ADR-0117's mechanism).

Row W2 added the last two steps, in this order and for this reason: **lingering first, then the
units** (ADR-0125 rule 2). A unit written under a session that does not linger stops at logout,
so writing five of them and then discovering the session does not linger would leave the
operator with a console that dies with their SSH connection and no message saying why. The
wizard therefore enables lingering, and refuses to go on with the command to run by hand when
it cannot.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess  # noqa: S404 — explicit argv, an allowlisted environment, never a shell
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import tomlkit

from weightroom.config import (
    APPLICATIONS,
    EXAMPLE_CONFIG_TOML,
    Settings,
    load_settings,
    secrets_dir,
)
from weightroom.services.auth import create_operator, operator_count
from weightroom.services.processes import (
    SubprocessSystemdController,
    SystemdController,
    UnitActionFailed,
    UnitUnsupported,
    sync_units,
)
from weightroom.services.tls import HostIdentity, TlsPaths, TlsStatus, init_tls, tls_status

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from weightroom.services.database import Database

__all__ = [
    "TOKEN_SCOPES",
    "Bind",
    "SetupAnswers",
    "SetupReport",
    "TokenIssuer",
    "enable_linger_step",
    "installed_executable",
    "issue_token_via_cli",
    "run_setup",
    "write_config_changes",
]

logger = logging.getLogger(__name__)

TOKEN_SCOPES: dict[str, str] = {"loadcoach": "admin", "promptcadence": "admin,approve"}
"""ADR-0126 rule 8: which applications get a token, and with which scope.

``admin`` rather than ``write`` since **ADR-0130** — WeightRoomGym's application tokens carry
admin scope: both applications' ``PUT /api/v1/settings`` requires it, and ADR-0127 rule 4
routes every runtime-changeable key through exactly that endpoint. An install made before that
record keeps its narrower token and is refused in the application's own words, and
``wr-gym doctor`` says so.
"""

_ENV_ALLOWLIST = ("PATH", "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "LANG")
_OUTPUT_CAP = 64 * 1024

type Bind = Literal["loopback", "lan", "all"]
type TokenIssuer = Callable[[str, str], str]
"""``(executable, scope) -> token``; injected so a test needs no application installed."""


@dataclass(frozen=True, slots=True)
class SetupAnswers:
    """What the operator decided at the prompts."""

    username: str
    password: str | None
    bind: Bind
    lan_address: str | None = None


@dataclass(slots=True)
class SetupReport:
    """What the wizard did, step by step, for the terminal and the audit row."""

    tls: str = ""
    account: str = ""
    bind: str = ""
    allowed_hosts: tuple[str, ...] = ()
    tokens: dict[str, str] = field(default_factory=dict)
    config_path: Path | None = None
    linger: str = ""
    units: dict[str, str] = field(default_factory=dict)
    console: str = ""
    deferred: tuple[str, ...] = ("settings: the per-application settings forms arrive at W4",)

    def as_params(self) -> dict[str, Any]:
        """The audit row's ``params``: no secret, only what was done."""
        return {
            "tls": self.tls,
            "account": self.account,
            "bind": self.bind,
            "allowed_hosts": list(self.allowed_hosts),
            "tokens": dict(self.tokens),
            "config_path": str(self.config_path) if self.config_path else None,
            "linger": self.linger,
            "units": dict(self.units),
            "console": self.console,
        }


def installed_executable(settings: Settings, app: str) -> str | None:
    """The application's CLI: ``[apps.<app>] executable`` when set, else ``shutil.which``."""
    configured = getattr(settings.apps, app).executable
    if configured:
        return configured if Path(configured).is_file() else None
    return shutil.which(app)


def issue_token_via_cli(executable: str, scope: str) -> str:
    """Run ``<app> token create weightroom --scope <scope> --json`` and return the token.

    Explicit argv, an allowlisted environment, a timeout and an output cap (spec §14).

    Raises:
        RuntimeError: The command failed or printed no token.
    """
    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    try:
        completed = subprocess.run(  # noqa: S603 — argv is fixed; executable was resolved once
            [executable, "token", "create", "weightroom", "--scope", scope, "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"{executable} token create failed to run: {exc}"
        raise RuntimeError(message) from exc
    if completed.returncode != 0:
        detail = completed.stderr[:_OUTPUT_CAP].strip()
        message = f"{executable} token create exited {completed.returncode}: {detail}"
        raise RuntimeError(message)
    for line in reversed(completed.stdout[:_OUTPUT_CAP].splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                token = json.loads(line).get("token")
            except json.JSONDecodeError:
                continue
            if isinstance(token, str) and token:
                return token
    message = f"{executable} token create printed no token"
    raise RuntimeError(message)


def _write_secret(path: Path, secret: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(secret + "\n")
        Path(temporary).chmod(0o600)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_config_changes(path: Path, changes: Mapping[str, Any]) -> None:
    """Set dotted keys in ``path`` with comments kept; write beside, keep ``.bak``, rename.

    A missing file starts from the commented example so the operator gets the same file
    ``config init`` writes, with the wizard's values in it.

    Args:
        path: The configuration file.
        changes: ``{"server.host": "10.0.0.5", "apps.loadcoach.api_key_file": "…"}``.
    """
    text = path.read_text(encoding="utf-8") if path.is_file() else EXAMPLE_CONFIG_TOML
    document = tomlkit.parse(text)
    for dotted, value in changes.items():
        parts = dotted.split(".")
        node: Any = document
        for part in parts[:-1]:
            if part not in node:
                node[part] = tomlkit.table()
            node = node[part]
        node[parts[-1]] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(tomlkit.dumps(document))
        handle.flush()
        os.fsync(handle.fileno())
    if path.is_file():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    Path(temporary).replace(path)


def enable_linger_step(controller: SystemdController, *, user: str, report: SetupReport) -> None:
    """Enable lingering for ``user``, or refuse to continue (ADR-0125 rule 2).

    Args:
        controller: The systemd boundary.
        user: The operator's own OS user.
        report: Filled in with what happened.

    Raises:
        UnitActionFailed: Lingering is off and could not be turned on. ``details['command']``
            is what the operator runs by hand; without it every unit this wizard is about to
            write stops at logout.
    """
    already = controller.linger_enabled(user)
    if already:
        report.linger = f"already enabled for {user}"
        return
    command = f"loginctl enable-linger {user}"
    result = controller.enable_linger(user)
    if not result.ok:
        report.linger = f"failed: {result.failure_text}"
        raise UnitActionFailed(
            f"lingering is required and could not be enabled: {result.failure_text}. Run "
            f"`{command}` and start again — units under user@<uid>.service stop at logout "
            f"otherwise (ADR-0125 rule 2).",
            details={"command": command, "user": user, "stderr": result.stderr.strip()},
        )
    confirmed = controller.linger_enabled(user)
    if confirmed is False:
        report.linger = "enable-linger reported success but lingering is still off"
        raise UnitActionFailed(
            f"`{command}` reported success but lingering is still off. Run it by hand and "
            f"check `loginctl show-user {user} -p Linger`.",
            details={"command": command, "user": user},
        )
    report.linger = f"enabled for {user}"


def run_setup(
    settings: Settings,
    *,
    config_path: Path,
    database: Database,
    answers: SetupAnswers,
    identity: HostIdentity,
    now: datetime,
    issue_token: TokenIssuer = issue_token_via_cli,
    controller: SystemdController | None = None,
    start_console: bool = True,
) -> tuple[SetupReport, TlsStatus]:
    """Do the wizard's work.

    Args:
        settings: The settings as loaded before the wizard.
        config_path: The file to write.
        database: The readied database.
        answers: The operator's decisions.
        identity: The host's names and addresses.
        now: The clock.
        issue_token: How to obtain an application token; the CLI subprocess by default.
        controller: The systemd boundary; the real one when ``None``.
        start_console: Whether to enable and start ``weightroom.service`` (ADR-0125 rule 6), so
            the console outlives the login that installed it. ``False`` leaves the unit written
            but not enabled — for a scratch install, or an operator who runs ``wr-gym serve`` in
            the foreground.

    Returns:
        The report and the certificate status.

    Raises:
        ValueError: ``lan`` was chosen without an address, or a password is needed and absent.
        UnitActionFailed: Lingering could not be enabled (ADR-0125 rule 2).
    """
    report = SetupReport(config_path=config_path)
    paths = TlsPaths.for_settings(settings)
    if paths.complete():
        tls = tls_status(paths, now=now)
        report.tls = f"kept {paths.directory} ({tls.days_left} days left on the leaf)"
    else:
        tls = init_tls(settings, identity=identity, now=now, force=bool(paths.present()))
        report.tls = f"created {paths.directory}"

    if operator_count(database):
        report.account = "kept the existing operator account"
    else:
        if not answers.password:
            message = "a password is required to create the operator account"
            raise ValueError(message)
        create_operator(database, username=answers.username, password=answers.password, now=now)
        report.account = f"created operator {answers.username!r}"

    hosts = (identity.hostname, f"{identity.hostname}.local", *identity.addresses)
    changes: dict[str, Any] = {"server.allowed_hosts": list(dict.fromkeys(hosts))}
    if answers.bind == "loopback":
        changes["server.host"] = "127.0.0.1"
        report.bind = "127.0.0.1 (loopback; the console is not on the LAN)"
    elif answers.bind == "lan":
        if not answers.lan_address:
            message = "the LAN bind needs an address"
            raise ValueError(message)
        changes["server.host"] = answers.lan_address
        report.bind = f"{answers.lan_address} (one LAN interface)"
    else:
        changes["server.host"] = "0.0.0.0"  # noqa: S104 — the operator chose every interface
        changes["server.allow_lan_exposure"] = True
        report.bind = "0.0.0.0 (every interface; allow_lan_exposure = true)"
    report.allowed_hosts = tuple(changes["server.allowed_hosts"])

    for app in APPLICATIONS:
        scope = TOKEN_SCOPES.get(app)
        if scope is None:
            continue
        executable = installed_executable(settings, app)
        if executable is None:
            report.tokens[app] = "not installed; no token"
            continue
        secret_path = secrets_dir() / f"{app}.token"
        try:
            token = issue_token(executable, scope)
        except RuntimeError as exc:
            report.tokens[app] = f"failed: {exc}"
            logger.warning("setup.token_failed", extra={"app": app, "detail": str(exc)})
            continue
        _write_secret(secret_path, token)
        changes[f"apps.{app}.api_key_file"] = str(secret_path)
        report.tokens[app] = f"scope {scope} → {secret_path}"

    write_config_changes(config_path, changes)
    reloaded = load_settings(config_path=config_path)  # the file the wizard wrote must load

    systemd = controller if controller is not None else SubprocessSystemdController()
    try:
        enable_linger_step(
            systemd, user=os.environ.get("USER", "") or Path.home().name, report=report
        )
        sync = sync_units(reloaded.settings, controller=systemd)
    except UnitUnsupported as exc:
        report.linger = report.linger or "unsupported on this host"
        report.units = {"all": f"unsupported on this host: {exc.message}"}
        report.console = "unsupported on this host; run `wr-gym serve` in the foreground"
        return report, tls
    report.units = {plan.app: plan.outcome for plan in sync.plans}
    report.console = _console_unit_step(systemd, start=start_console)
    return report, tls


def _console_unit_step(controller: SystemdController, *, start: bool) -> str:
    """Enable — and, unless told not to, start — ``weightroom.service`` (ADR-0125 rule 6)."""
    if not start:
        return "written, not enabled (--no-start-console); `wr-gym serve` runs it in the foreground"
    enabled = controller.act("weightroom.service", "enable")
    if not enabled.ok:
        return f"enable failed: {enabled.failure_text}"
    started = controller.act("weightroom.service", "start")
    if not started.ok:
        return f"enabled; start failed: {started.failure_text}"
    return "enabled and started as weightroom.service"
