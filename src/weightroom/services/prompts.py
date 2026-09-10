"""weightroom.services.prompts — each application's prompt pack and the operator's overrides.

Spec §7.10 and prompt standards §6. An override is a whole prompt record at
``$XDG_CONFIG_HOME/<app>/prompts/<prompt_id>.json``: the application loads it in place of the
shipped record and marks what rendered it ``user_override``. The console lists the shipped pack
through the application's own ``prompts list|show`` — never by importing it (ADR-0123 rule 3) —
and writes, diffs and deletes the override files; it touches nothing else.

**A record the editor accepts is one the application will load.** A candidate is validated with
``setspec.prompts.load_record`` — the loader the application itself runs over its override
directory — on a copy written beside the real path, and only then moved into place. A candidate
the loader refuses is never written, because an override that does not load stops IdeaPress
starting and fails every FreeWeight run.

**Two applications have a pack to edit**: FreeWeight, and IdeaPress since row W9. LoadCoach and
PromptCadence ship prompt records but have no ``prompts`` command and read no override directory;
they are named as such rather than guessed at. What each application does with an override is its
own rule, shown beside the editor and never bypassed (:data:`PROMPT_SURFACES`).
"""

from __future__ import annotations

import difflib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import SuiteError
from setspec.prompts import PromptPackInvalid, load_record, prompt_record_hash

from weightroom.services.apps import AppNotInstalled, require_app
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    from collections.abc import Mapping

    from weightroom.config import Settings
    from weightroom.services.processes import Runner

__all__ = [
    "NO_PROMPT_SURFACE",
    "PROMPT_SURFACES",
    "Pack",
    "PackEntry",
    "PromptDetail",
    "PromptOverrideInvalid",
    "PromptSurface",
    "PromptsCommandFailed",
    "PromptsUnavailable",
    "canonical_text",
    "delete_override",
    "list_pack",
    "override_directory",
    "override_path",
    "prompt_detail",
    "surface_for",
    "write_override",
]

_PROMPT_ID: Final = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
_TIMEOUT_SECONDS: Final = 30.0


@dataclass(frozen=True, slots=True)
class PromptSurface:
    """How the console reads one application's pack, and that application's rule for an override.

    Attributes:
        list_args: The pack listing, as JSON.
        show_args: One shipped record, as JSON; ``{prompt_id}`` is replaced.
        rule: What the application does with an override, in its own terms.
    """

    list_args: tuple[str, ...]
    show_args: tuple[str, ...]
    rule: str


PROMPT_SURFACES: Final[Mapping[str, PromptSurface]] = {
    "freeweight": PromptSurface(
        list_args=("prompts", "list", "--json"),
        show_args=("prompts", "show", "{prompt_id}", "--json"),
        rule=(
            "FreeWeight refuses to run a benchmark whose suite renders an overridden prompt "
            "unless the run passes --allow-prompt-override (a freeweight_suite_run job's "
            "allow_prompt_override), and then marks the run prompt_overridden with prompt_source "
            "user_override: its results are not comparable with the shipped prompt's. A run "
            "started from the command line, as the console's jobs are, reads the override "
            "directory when it starts; the FreeWeight service reads it once, when it starts, so "
            "restart FreeWeight before a run it queues itself."
        ),
    ),
    "ideapress": PromptSurface(
        list_args=("prompts", "list", "--shipped", "--json"),
        show_args=("prompts", "show", "{prompt_id}", "--shipped", "--json"),
        rule=(
            "IdeaPress renders an override in place of the shipped record and marks every attempt "
            "that used it prompt_source user_override. It reads its prompts once, when it starts: "
            "restart IdeaPress for a written or deleted override to take effect. An override that "
            "does not load stops IdeaPress starting."
        ),
    ),
}
"""The two applications with a pack to edit (spec §7.10, row W9)."""

NO_PROMPT_SURFACE: Final[Mapping[str, str]] = {
    "loadcoach": (
        "LoadCoach ships prompt records for its own corrective retries but has no prompts command "
        "and reads no override directory, so there is no pack to list or override here."
    ),
    "promptcadence": (
        "PromptCadence ships prompt records for its planner and steps but has no prompts command "
        "and reads no override directory, so there is no pack to list or override here."
    ),
}


class PromptsUnavailable(SuiteError):
    """No pack the console can edit for this application, or no such prompt, or no override."""

    code: ClassVar[str] = "NOT_FOUND"


class PromptsCommandFailed(SuiteError):
    """The application's own ``prompts`` command failed, or printed something that is not JSON."""

    code: ClassVar[str] = "APP_UNREACHABLE"


class PromptOverrideInvalid(SuiteError):
    """A candidate override the application would not load, or one that overrides nothing."""

    code: ClassVar[str] = "VALIDATION_ERROR"


@dataclass(frozen=True, slots=True)
class PackEntry:
    """One shipped prompt, and the override beside it if there is one."""

    prompt_id: str
    version: str
    sha256: str | None
    purpose: str
    override_version: str | None
    override_problem: str | None

    @property
    def overridden(self) -> bool:
        """Whether an override file sits in the application's override directory."""
        return self.override_version is not None or self.override_problem is not None

    def as_json(self) -> dict[str, Any]:
        """The api.md §4 shape."""
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "sha256": self.sha256,
            "purpose": self.purpose,
            "overridden": self.overridden,
            "override_version": self.override_version,
            "override_problem": self.override_problem,
        }


@dataclass(frozen=True, slots=True)
class Pack:
    """One application's shipped pack, joined with its overrides."""

    app: str
    entries: tuple[PackEntry, ...]
    override_directory: Path
    rule: str

    def as_json(self) -> dict[str, Any]:
        """The api.md §4 shape."""
        return {
            "app": self.app,
            "override_directory": str(self.override_directory),
            "rule": self.rule,
            "prompts": [entry.as_json() for entry in self.entries],
        }


def canonical_text(record: Mapping[str, Any]) -> str:
    """A record as the editor shows and writes it: sorted keys, two-space indent, one newline."""
    return json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


@dataclass(frozen=True, slots=True)
class PromptDetail:
    """One prompt: the shipped record, the override if any, and the difference."""

    app: str
    prompt_id: str
    shipped: dict[str, Any]
    override: dict[str, Any] | None
    override_path: Path
    override_problem: str | None
    rule: str

    @property
    def shipped_sha256(self) -> str:
        """The shipped record's hash (prompt standards §3)."""
        return prompt_record_hash(self.shipped)

    @property
    def override_sha256(self) -> str | None:
        """The override's hash, or ``None`` without one."""
        return prompt_record_hash(self.override) if self.override is not None else None

    @property
    def has_override_file(self) -> bool:
        """Whether a file is at the override path, loadable or not."""
        return self.override_path.is_file()

    @property
    def diff(self) -> tuple[str, ...]:
        """The unified diff from the shipped record to the override, both canonical."""
        if self.override is None:
            return ()
        return tuple(
            line.rstrip("\n")
            for line in difflib.unified_diff(
                canonical_text(self.shipped).splitlines(keepends=True),
                canonical_text(self.override).splitlines(keepends=True),
                fromfile=f"shipped {self.shipped.get('version')}",
                tofile=f"override {self.override.get('version')}",
            )
        )

    def as_json(self) -> dict[str, Any]:
        """The api.md §4 shape."""
        return {
            "app": self.app,
            "prompt_id": self.prompt_id,
            "rule": self.rule,
            "shipped": self.shipped,
            "shipped_sha256": self.shipped_sha256,
            "override": self.override,
            "override_sha256": self.override_sha256,
            "override_path": str(self.override_path),
            "override_problem": self.override_problem,
            "diff": "\n".join(self.diff),
        }


def surface_for(app: str) -> PromptSurface:
    """The application's pack surface.

    Raises:
        AppUnknown: Not one of the four.
        PromptsUnavailable: LoadCoach or PromptCadence, which have none.
    """
    name = require_app(app)
    surface = PROMPT_SURFACES.get(name)
    if surface is None:
        raise PromptsUnavailable(
            NO_PROMPT_SURFACE.get(name, f"{name} has no prompt pack to edit."),
            details={"app": name},
        )
    return surface


def override_directory(app: str) -> Path:
    """``$XDG_CONFIG_HOME/<app>/prompts`` — where the application itself looks (§6)."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / app / "prompts"


def override_path(app: str, prompt_id: str) -> Path:
    """``<override directory>/<prompt_id>.json``.

    Raises:
        PromptOverrideInvalid: ``prompt_id`` is not a dotted lowercase id — which is also what
            keeps the path inside the directory: an id carries no separator and no leading dot.
    """
    if not _PROMPT_ID.fullmatch(prompt_id):
        raise PromptOverrideInvalid(
            f"{prompt_id!r} is not a prompt id (dotted lowercase words, e.g. stages.draft.write).",
            details={"prompt_id": prompt_id},
        )
    directory = override_directory(app)
    path = directory / f"{prompt_id}.json"
    if not path.resolve().is_relative_to(directory.resolve()):  # pragma: no cover — by the id rule
        raise PromptOverrideInvalid(
            f"{prompt_id!r} would land outside {directory}.", details={"prompt_id": prompt_id}
        )
    return path


def _call(settings: Settings, app: str, args: tuple[str, ...], *, runner: Runner) -> Any:  # noqa: ANN401 — the application's JSON
    executable = executable_for(settings, app)
    if executable is None:
        raise AppNotInstalled(
            f"{app} is not installed, so its prompt pack cannot be read.", details={"app": app}
        )
    result = runner([executable, *args], child_environment(), _TIMEOUT_SECONDS)
    command = f"{app} {' '.join(args)}"
    if not result.ok:
        raise PromptsCommandFailed(
            f"`{command}` failed: {result.failure_text}", details={"app": app, "argv": list(args)}
        )
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise PromptsCommandFailed(
            f"`{command}` printed no JSON: {exc}", details={"app": app, "argv": list(args)}
        ) from exc


def _read_override(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """The override on disk and, when the application would not load it, why."""
    if not path.is_file():
        return None, None
    try:
        return dict(load_record(path, source="user_override").body), None
    except PromptPackInvalid as exc:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = None
        return (dict(raw) if isinstance(raw, dict) else None), exc.message


def list_pack(settings: Settings, app: str, *, runner: Runner = run_command) -> Pack:
    """The shipped pack from the application's own listing, joined with the override files.

    Raises:
        AppUnknown, PromptsUnavailable: As :func:`surface_for`.
        AppNotInstalled: No executable.
        PromptsCommandFailed: The listing failed or was not a list of records.
    """
    surface = surface_for(app)
    answer = _call(settings, app, surface.list_args, runner=runner)
    raw = answer.get("prompts") if isinstance(answer, dict) else answer
    if not isinstance(raw, list):
        raise PromptsCommandFailed(
            f"{app}'s prompt listing is not a list of records.", details={"app": app}
        )
    entries: list[PackEntry] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("prompt_id"), str):
            continue
        prompt_id = str(item["prompt_id"])
        override, problem = (
            _read_override(override_path(app, prompt_id))
            if _PROMPT_ID.fullmatch(prompt_id)
            else (None, None)
        )
        entries.append(
            PackEntry(
                prompt_id=prompt_id,
                version=str(item.get("version", "")),
                sha256=str(item["sha256"]) if isinstance(item.get("sha256"), str) else None,
                purpose=str(item.get("purpose", "")),
                override_version=(
                    str(override["version"]) if override and "version" in override else None
                ),
                override_problem=problem,
            )
        )
    return Pack(app, tuple(entries), override_directory(app), surface.rule)


def _shipped_record(
    settings: Settings, app: str, prompt_id: str, *, runner: Runner
) -> dict[str, Any]:
    surface = surface_for(app)
    args = tuple(arg.replace("{prompt_id}", prompt_id) for arg in surface.show_args)
    answer = _call(settings, app, args, runner=runner)
    if isinstance(answer, dict) and isinstance(answer.get("record"), dict):
        return dict(answer["record"])
    if isinstance(answer, dict) and "schema_version" in answer:
        return dict(answer)
    raise PromptsCommandFailed(
        f"{app} printed no whole record for {prompt_id}; this version of {app} cannot have an "
        "override started or diffed from the console.",
        details={"app": app, "prompt_id": prompt_id},
    )


def _require_shipped(settings: Settings, app: str, prompt_id: str, *, runner: Runner) -> Pack:
    pack = list_pack(settings, app, runner=runner)
    if not any(entry.prompt_id == prompt_id for entry in pack.entries):
        raise PromptsUnavailable(
            f"{app}'s pack has no prompt {prompt_id}; an override replaces a shipped record "
            "(prompt standards §6).",
            details={"app": app, "prompt_id": prompt_id},
        )
    return pack


def prompt_detail(
    settings: Settings, app: str, prompt_id: str, *, runner: Runner = run_command
) -> PromptDetail:
    """The shipped record, the override if any, and why an override on disk would not load.

    Raises:
        PromptOverrideInvalid: ``prompt_id`` is not a prompt id.
        PromptsUnavailable: No pack for this application, or no such prompt in it.
        AppNotInstalled, PromptsCommandFailed: As :func:`list_pack`.
    """
    path = override_path(app, prompt_id)
    _require_shipped(settings, app, prompt_id, runner=runner)
    shipped = _shipped_record(settings, app, prompt_id, runner=runner)
    override, problem = _read_override(path)
    return PromptDetail(app, prompt_id, shipped, override, path, problem, surface_for(app).rule)


def write_override(
    settings: Settings,
    app: str,
    prompt_id: str,
    record: Mapping[str, Any],
    *,
    runner: Runner = run_command,
) -> PromptDetail:
    """Validate ``record`` as the application's loader would, then write it as the override.

    Raises:
        PromptOverrideInvalid: The record declares another ``prompt_id``; the prompt ships in
            several versions (the loader would replace only one of them); or the loader refuses
            the record — its message, unchanged. Nothing is written.
        PromptsUnavailable, AppNotInstalled, PromptsCommandFailed: As :func:`prompt_detail`.
    """
    path = override_path(app, prompt_id)
    if record.get("prompt_id") != prompt_id:
        raise PromptOverrideInvalid(
            f"The record declares prompt_id {record.get('prompt_id')!r}; an override of "
            f"{prompt_id} must declare the same prompt_id (prompt standards §6).",
            details={"app": app, "prompt_id": prompt_id},
        )
    pack = _require_shipped(settings, app, prompt_id, runner=runner)
    versions = [entry.version for entry in pack.entries if entry.prompt_id == prompt_id]
    if len(versions) > 1:
        raise PromptOverrideInvalid(
            f"{app} ships {len(versions)} versions of {prompt_id}, and an override replaces only "
            "one of them; the console does not override a prompt shipped in several versions.",
            details={"app": app, "prompt_id": prompt_id, "versions": versions},
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".candidate-") as scratch:
        candidate = Path(scratch) / path.name
        candidate.write_text(canonical_text(record), encoding="utf-8")
        try:
            load_record(candidate, source="user_override")
        except PromptPackInvalid as exc:
            raise PromptOverrideInvalid(
                exc.message, details={"app": app, "prompt_id": prompt_id}
            ) from exc
        candidate.replace(path)
    return prompt_detail(settings, app, prompt_id, runner=runner)


def delete_override(app: str, prompt_id: str) -> Path:
    """Remove the override, so the application renders the shipped record again.

    Returns:
        The path that was removed.

    Raises:
        PromptsUnavailable: No pack for this application, or no override to delete.
        PromptOverrideInvalid: ``prompt_id`` is not a prompt id.
    """
    surface_for(app)
    path = override_path(app, prompt_id)
    if not path.is_file():
        raise PromptsUnavailable(
            f"There is no override of {prompt_id} in {path.parent}; {app} already renders the "
            "shipped record.",
            details={"app": app, "prompt_id": prompt_id},
        )
    path.unlink()
    return path
