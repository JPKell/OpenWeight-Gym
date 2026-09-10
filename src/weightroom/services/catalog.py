"""weightroom.services.catalog — every model FreeWeight and LoadCoach know, joined by identity.

Spec §7.9, api.md §5. Only these two applications own a ``models`` table at all (ADR-0008,
ADR-0118) — IdeaPress and PromptCadence carry none of their own and route every model call through
LoadCoach — so the join is over two databases, read the way ``services/overview.py`` reads every
other application's database: tables reflected on the read-only engine ``services/db_reader.py``
already opens for each application, never a second registry (the kickoff's own words).

**Evidence freshness is always FreeWeight's answer** (spec §7.9), even for a row LoadCoach also
knows: FreeWeight is where a benchmark run lands, and LoadCoach's own ``capability_evidence`` is an
import of the same fact, so reading it twice would only risk the two going out of step.

**Residency** comes first from LoadCoach's own ``residency`` table — a fact it already tracks per
model, not a name match — and only for a row LoadCoach does not carry (typically one FreeWeight
knows and LoadCoach has never routed to) does an Ollama-kind row fall back to a live
``/api/ps``-style check through :func:`~weightroom.services.ollama.resident_models`, which is
ModelRack's own client, never a second one (ADR-0125 rule 4's reasoning, applied here too).

**The pull job is deliberately not durable.** ADR-0010's queue is row W9's; until it exists, a pull
is a plain daemon thread and its progress a list held in memory (:class:`PullRegistry`), lost on a
restart and unreachable from a second console process — exactly what the kickoff's "run in a
thread until W9 hosts it" asks for, no more. Ollama's own HTTP API (``/api/pull``, streamed
newline-delimited JSON) is used directly: pulling a model is not in ModelRack's scope (its spec's
explicit non-goal list), so there is no client to reuse here as there is for residency.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final
from uuid import uuid4

import httpx
from baseaicore import SuiteError
from sqlalchemy import func, select

from weightroom.services.apps import bearer_token
from weightroom.services.db_curated import CuratedResult, delete_results
from weightroom.services.db_reader import AppDatabaseUnavailable, open_app_database, reflect_table
from weightroom.services.ollama import resident_models

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import BinaryIO

    from sqlalchemy import Engine

    from weightroom.config import Settings
    from weightroom.services.database import Database
    from weightroom.services.db_reader import DatabaseUrlCache

__all__ = [
    "CATALOG_APPS",
    "GGUF_MAGIC",
    "CatalogAppRow",
    "CatalogDeletePreview",
    "CatalogDeleteResult",
    "CatalogDropinRefused",
    "CatalogEntry",
    "CatalogRefused",
    "DropinResult",
    "LlamaCppTarget",
    "PullEvent",
    "PullJob",
    "PullRegistry",
    "catalog_delete_confirm",
    "catalog_delete_preview",
    "catalog_entries",
    "find_entry",
    "llamacpp_targets",
    "perform_dropin_path",
    "perform_dropin_stream",
    "set_enabled",
    "validate_gguf",
]

logger = logging.getLogger(__name__)

CATALOG_APPS: Final[tuple[str, ...]] = ("freeweight", "loadcoach")
GGUF_MAGIC: Final = b"GGUF"
_MIN_GGUF_BYTES: Final = 1024
"""Anything smaller is not a weights file — catches an empty or truncated upload cheaply, before
the magic-byte read."""

_HTTP_TIMEOUT_SECONDS: Final = 10.0
_DISCOVER_TIMEOUT_SECONDS: Final = 120.0
_MIN_FREE_BYTES_FOR_PULL: Final = 2 * 1024 * 1024 * 1024
"""A floor, not a per-model estimate — Ollama does not report a manifest's size before pulling it.
Below this, a pull is refused outright rather than left to fail Ollama-side partway through."""


class CatalogRefused(SuiteError):
    """A catalog action asked for wrongly: an unknown app, a bad confirmation, no target model."""

    code: ClassVar[str] = "VALIDATION_ERROR"


class CatalogDropinRefused(SuiteError):
    """A GGUF drop-in this console will not perform (spec §14): bad magic, oversize, escaping
    the configured directory, or no directory configured at all."""

    code: ClassVar[str] = "CATALOG_DROPIN_REFUSED"


# --- The join -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CatalogAppRow:
    """One application's own row for a model the catalog has joined by canonical identity.

    Attributes:
        model_id: The application's own primary key — what ``POST /models/{model_id}/enabled``
            on that application takes, never the canonical id (ADR-0024).
        provider_kind: This application's own record of it (identical across apps by construction
            of the join key, kept per-row rather than assumed).
        provider_model_name: Ditto — the ``ollama pull`` name, or the GGUF file's name for
            ``llamacpp``.
        enabled: ADR-0118's flag, this application's own.
        available: The provider's own last-seen reachability, where the application tracks it
            (LoadCoach only — FreeWeight benchmarks on demand and keeps no such fact).
        size_bytes: The weights' size, where known.
        max_context: The trained context length, where known.
        resident: Whether this application currently holds the model loaded, or ``None`` when
            this build has no way to know (ADR-0016 — never a guessed ``False``).
        evidence_measured_at: The newest ``capability_evidence.measured_at`` FreeWeight holds for
            this model, or ``None`` for a model never benchmarked.
    """

    model_id: str
    provider_kind: str
    provider_model_name: str
    enabled: bool
    available: bool | None
    size_bytes: int | None
    max_context: int | None
    resident: bool | None
    evidence_measured_at: datetime | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 per-application shape."""
        return {
            "model_id": self.model_id,
            "enabled": self.enabled,
            "available": self.available,
            "size_bytes": self.size_bytes,
            "max_context": self.max_context,
            "resident": self.resident,
            "evidence_measured_at": (
                self.evidence_measured_at.isoformat() if self.evidence_measured_at else None
            ),
        }


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One model, joined across every application that knows it.

    Attributes:
        canonical_id: The join key (ADR-0008).
        provider_kind: ``ollama``, ``llamacpp``, ``openai_compatible``, … — from whichever
            application's row supplied the identity first.
        provider_model_name: Ditto.
        family: The model family, when a descriptor states one.
        quantization: Ditto.
        apps: Every application that has a row for this model, keyed by name.
    """

    canonical_id: str
    provider_kind: str
    provider_model_name: str
    family: str | None
    quantization: str | None
    apps: Mapping[str, CatalogAppRow]

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 ``GET /catalog`` row shape."""
        return {
            "canonical_id": self.canonical_id,
            "provider_kind": self.provider_kind,
            "provider_model_name": self.provider_model_name,
            "family": self.family,
            "quantization": self.quantization,
            "apps": {name: row.as_json() for name, row in self.apps.items()},
        }


def _freeweight_rows(
    engine: Engine,
) -> list[tuple[str, str | None, str | None, CatalogAppRow]]:
    """FreeWeight's own models, their latest descriptor and their evidence freshness."""
    models = reflect_table(engine, "models")
    if models is None:
        return []
    descriptors = reflect_table(engine, "model_descriptors")
    evidence = reflect_table(engine, "capability_evidence")
    latest: dict[str, tuple[int | None, int | None, str | None, str | None]] = {}
    if descriptors is not None:
        with engine.connect() as connection:
            statement = select(
                descriptors.c.model_id,
                descriptors.c.size_bytes,
                descriptors.c.max_context,
                descriptors.c.family,
                descriptors.c.quantization,
            ).order_by(descriptors.c.model_id, descriptors.c.observed_at.desc())
            for row in connection.execute(statement):
                # The first row seen per model_id is the newest (the ORDER BY above); a later one
                # for the same model is older and never overwrites it.
                latest.setdefault(
                    row.model_id, (row.size_bytes, row.max_context, row.family, row.quantization)
                )
    freshness: dict[str, datetime] = {}
    if evidence is not None:
        with engine.connect() as connection:
            statement = (
                select(evidence.c.model_id, func.max(evidence.c.measured_at).label("measured_at"))
                .where(evidence.c.model_id.is_not(None))
                .group_by(evidence.c.model_id)
            )
            freshness = {row.model_id: row.measured_at for row in connection.execute(statement)}
    out: list[tuple[str, str | None, str | None, CatalogAppRow]] = []
    with engine.connect() as connection:
        for row in connection.execute(select(models)):
            size_bytes, max_context, family, quantization = latest.get(
                row.id, (None, None, None, None)
            )
            out.append(
                (
                    row.canonical_id,
                    family,
                    quantization,
                    CatalogAppRow(
                        model_id=row.id,
                        provider_kind=row.provider_kind,
                        provider_model_name=row.provider_model_name,
                        enabled=row.enabled,
                        available=None,
                        size_bytes=size_bytes,
                        max_context=max_context,
                        resident=None,
                        evidence_measured_at=freshness.get(row.id),
                    ),
                )
            )
    return out


def _loadcoach_rows(engine: Engine) -> list[tuple[str, str | None, str | None, CatalogAppRow]]:
    """LoadCoach's own models, with the residency it already tracks per model."""
    models = reflect_table(engine, "models")
    if models is None:
        return []
    residency = reflect_table(engine, "residency")
    resident_ids: set[str] = set()
    if residency is not None:
        with engine.connect() as connection:
            statement = select(residency.c.model_id).where(residency.c.resident.is_(True))
            resident_ids = {row.model_id for row in connection.execute(statement)}
    out: list[tuple[str, str | None, str | None, CatalogAppRow]] = []
    with engine.connect() as connection:
        for row in connection.execute(select(models)):
            out.append(
                (
                    row.canonical_id,
                    row.family,
                    row.quantization,
                    CatalogAppRow(
                        model_id=row.id,
                        provider_kind=row.provider_kind,
                        provider_model_name=row.provider_model_name,
                        enabled=row.enabled,
                        available=row.available,
                        size_bytes=row.size_bytes,
                        max_context=row.max_context,
                        resident=row.id in resident_ids,
                        evidence_measured_at=None,
                    ),
                )
            )
    return out


_APP_READERS: Final[
    dict[str, Callable[[Engine], list[tuple[str, str | None, str | None, CatalogAppRow]]]]
] = {"freeweight": _freeweight_rows, "loadcoach": _loadcoach_rows}


def catalog_entries(
    settings: Settings,
    database: Database,
    *,
    urls: DatabaseUrlCache,
    monotonic: float,
    ollama_client: httpx.Client | None = None,
) -> tuple[CatalogEntry, ...]:
    """Every model FreeWeight and LoadCoach know, joined by canonical identity.

    Args:
        settings: The validated settings.
        database: WeightRoomGym's own database, for the ``known_revisions`` check.
        urls: The effective-database-URL cache.
        monotonic: A monotonic clock reading, for that cache.
        ollama_client: A transport carrying Ollama's ``base_url``, for the residency fallback;
            ``None`` skips it (a row LoadCoach does not carry residency for then reports ``None``).

    Returns:
        Every joined row, sorted by canonical id. An application whose database is unreachable or
        at a revision this build does not know contributes nothing, silently — the join is a
        best-effort read of what answers, not a page that fails because one side is down.
    """
    by_canonical: dict[str, dict[str, CatalogAppRow]] = {}
    identity: dict[str, tuple[str, str, str | None, str | None]] = {}
    for app in CATALOG_APPS:
        try:
            with open_app_database(
                settings, database, app, urls=urls, now=monotonic, require_known=False
            ) as handle:
                if not handle.revision.is_known:
                    continue
                rows = _APP_READERS[app](handle.engine)
        except AppDatabaseUnavailable:
            continue
        for canonical_id, family, quantization, app_row in rows:
            by_canonical.setdefault(canonical_id, {})[app] = app_row
            prior = identity.get(canonical_id)
            if prior is None:
                identity[canonical_id] = (
                    app_row.provider_kind,
                    app_row.provider_model_name,
                    family,
                    quantization,
                )
            else:
                pk, pmn, fam, quant = prior
                identity[canonical_id] = (
                    pk,
                    pmn,
                    fam if fam is not None else family,
                    quant if quant is not None else quantization,
                )
    ollama_names: set[str] | None = None
    if ollama_client is not None:
        resident, error = resident_models(settings, client=ollama_client)
        if error is None:
            ollama_names = {view.name for view in resident}
    entries: list[CatalogEntry] = []
    for canonical_id, apps in by_canonical.items():
        if ollama_names is not None:
            for app_name, app_row in list(apps.items()):
                if app_row.resident is None and app_row.provider_kind == "ollama":
                    apps[app_name] = replace(
                        app_row, resident=app_row.provider_model_name in ollama_names
                    )
        provider_kind, provider_model_name, family, quantization = identity[canonical_id]
        entries.append(
            CatalogEntry(
                canonical_id, provider_kind, provider_model_name, family, quantization, apps
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.canonical_id))


def find_entry(entries: tuple[CatalogEntry, ...], canonical_id: str) -> CatalogEntry:
    """The one row named ``canonical_id``.

    Raises:
        CatalogRefused: No such row in ``entries``.
    """
    for entry in entries:
        if entry.canonical_id == canonical_id:
            return entry
    raise CatalogRefused(
        f"{canonical_id} is not in the catalog.", details={"canonical_id": canonical_id}
    )


# --- Talking to the two applications ----------------------------------------------------------


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"{response.status_code} {response.text[:200]}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return f"{response.status_code} {error['message']}"
    return str(response.status_code)


def _call(
    settings: Settings,
    app: str,
    method: str,
    path: str,
    *,
    client: httpx.Client,
    json_body: Mapping[str, Any] | None = None,
    timeout: float = _HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    """One call to ``app``'s own API; ``None`` on anything short of a successful JSON object."""
    base_url = getattr(settings.apps, app).base_url
    if not base_url:
        return None
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.request(
            method,
            f"{base_url.rstrip('/')}{path}",
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def set_enabled(
    settings: Settings, app: str, model_id: str, *, enabled: bool, client: httpx.Client
) -> dict[str, Any]:
    """``POST {app}/api/v1/models/{model_id}/enabled`` — ADR-0118, api.md §5.

    Raises:
        CatalogRefused: The application did not answer, or refused.
    """
    base_url = getattr(settings.apps, app).base_url
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.post(
            f"{base_url.rstrip('/')}/api/v1/models/{model_id}/enabled",
            json={"enabled": enabled},
            headers=headers,
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise CatalogRefused(f"{app} did not answer: {exc}", details={"app": app}) from exc
    if not response.is_success:
        raise CatalogRefused(
            f"{app} refused: {_error_message(response)}",
            details={"app": app, "status": response.status_code},
        )
    try:
        return dict(response.json())
    except ValueError:
        return {}


# --- GGUF drop-in ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LlamaCppTarget:
    """One application's llama.cpp provider, live, naming its own ``model_directory``."""

    app: str
    provider_name: str
    model_directory: Path


def llamacpp_targets(settings: Settings, *, client: httpx.Client) -> tuple[LlamaCppTarget, ...]:
    """Every llama.cpp-configured provider across FreeWeight and LoadCoach, read live.

    FreeWeight names one provider at ``GET /api/v1/provider``; LoadCoach may name several named
    registrations at ``GET /api/v1/providers``. An application that is stopped, not llama.cpp, or
    names no directory contributes nothing.
    """
    targets: list[LlamaCppTarget] = []
    freeweight = _call(settings, "freeweight", "GET", "/api/v1/provider", client=client)
    provider = freeweight.get("provider") if freeweight else None
    if (
        isinstance(provider, dict)
        and provider.get("kind") == "llamacpp"
        and provider.get("model_directory")
    ):
        targets.append(
            LlamaCppTarget("freeweight", "", Path(str(provider["model_directory"])).expanduser())
        )
    loadcoach = _call(settings, "loadcoach", "GET", "/api/v1/providers", client=client)
    registrations = loadcoach.get("registrations") if loadcoach else None
    if isinstance(registrations, list):
        for registration in registrations:
            if not isinstance(registration, dict):
                continue
            if registration.get("kind") == "llamacpp" and registration.get("model_directory"):
                targets.append(
                    LlamaCppTarget(
                        "loadcoach",
                        str(registration.get("name", "")),
                        Path(str(registration["model_directory"])).expanduser(),
                    )
                )
    return tuple(targets)


def _single_directory(targets: tuple[LlamaCppTarget, ...]) -> Path:
    if not targets:
        raise CatalogDropinRefused(
            "No application configures a llama.cpp model_directory; there is nowhere to drop a "
            "GGUF file in."
        )
    directories = {target.model_directory.resolve() for target in targets}
    if len(directories) > 1:
        raise CatalogDropinRefused(
            "The configured llama.cpp applications name different model_directory paths: "
            + ", ".join(sorted(str(one) for one in directories))
            + ". Point them at the same directory before dropping a file in from here.",
            details={"directories": sorted(str(one) for one in directories)},
        )
    return next(iter(directories))


def _resolve_within(directory: Path, filename: str) -> Path:
    """``directory / filename``, containment-checked (spec §14)."""
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise CatalogDropinRefused(f"{filename!r} is not a usable file name.")
    target = (directory / safe_name).resolve()
    if not (target == directory or target.is_relative_to(directory)):
        raise CatalogDropinRefused(
            f"{filename!r} would land outside the configured model directory.",
            details={"directory": str(directory), "filename": filename},
        )
    return target


def validate_gguf(path: Path) -> int:
    """Check ``path``'s magic bytes and size; return its size in bytes.

    Raises:
        CatalogDropinRefused: It cannot be read, is too small to be real weights, or does not
            start with the GGUF magic bytes.
    """
    try:
        size_bytes = path.stat().st_size
    except OSError as exc:
        raise CatalogDropinRefused(
            f"{path} does not exist or cannot be read: {exc}", details={"path": str(path)}
        ) from exc
    if size_bytes < _MIN_GGUF_BYTES:
        raise CatalogDropinRefused(
            f"{path} is only {size_bytes} bytes; too small to be a GGUF weights file.",
            details={"path": str(path), "size_bytes": size_bytes},
        )
    with path.open("rb") as handle:
        magic = handle.read(len(GGUF_MAGIC))
    if magic != GGUF_MAGIC:
        raise CatalogDropinRefused(
            f"{path} does not start with the GGUF magic bytes.",
            details={"path": str(path), "magic": magic.hex()},
        )
    return size_bytes


@dataclass(frozen=True, slots=True)
class DropinResult:
    """What a GGUF drop-in did."""

    destination: Path
    size_bytes: int
    refreshed: tuple[str, ...]
    """Every application ``POST /models/discover`` was called on afterwards."""

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 ``POST /catalog/dropin`` response shape."""
        return {
            "path": str(self.destination),
            "size_bytes": self.size_bytes,
            "refreshed": list(self.refreshed),
        }


def _refresh_after_dropin(
    settings: Settings, targets: tuple[LlamaCppTarget, ...], *, client: httpx.Client
) -> tuple[str, ...]:
    refreshed = []
    for target in targets:
        _call(
            settings,
            target.app,
            "POST",
            "/api/v1/models/discover",
            client=client,
            timeout=_DISCOVER_TIMEOUT_SECONDS,
        )
        refreshed.append(target.app)
    return tuple(refreshed)


def perform_dropin_path(settings: Settings, *, source: str, client: httpx.Client) -> DropinResult:
    """The ``{"path": …}`` form: copy a file already on the host into the model directory."""
    source_path = Path(source).expanduser()
    size_bytes = validate_gguf(source_path)
    targets = llamacpp_targets(settings, client=client)
    directory = _single_directory(targets)
    directory.mkdir(parents=True, exist_ok=True)
    destination = _resolve_within(directory, source_path.name)
    shutil.copy2(source_path, destination)
    refreshed = _refresh_after_dropin(settings, targets, client=client)
    return DropinResult(destination, size_bytes, refreshed)


def perform_dropin_stream(
    settings: Settings, *, filename: str, stream: BinaryIO, client: httpx.Client
) -> DropinResult:
    """The multipart-upload form: written to the model directory, then validated in place."""
    targets = llamacpp_targets(settings, client=client)
    directory = _single_directory(targets)
    directory.mkdir(parents=True, exist_ok=True)
    destination = _resolve_within(directory, filename)
    with destination.open("wb") as handle:
        shutil.copyfileobj(stream, handle)
    try:
        size_bytes = validate_gguf(destination)
    except CatalogDropinRefused:
        destination.unlink(missing_ok=True)
        raise
    refreshed = _refresh_after_dropin(settings, targets, client=client)
    return DropinResult(destination, size_bytes, refreshed)


# --- Ollama, over its own HTTP API --------------------------------------------------------------


def _ollama_tag_exists(settings: Settings, name: str, *, client: httpx.Client) -> bool:
    try:
        response = client.get(
            f"{settings.host.ollama_base_url.rstrip('/')}/api/tags", timeout=_HTTP_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        return False
    models = body.get("models") if isinstance(body, dict) else None
    if not isinstance(models, list):
        return False
    return any(isinstance(one, dict) and one.get("name") == name for one in models)


def _ollama_delete_tag(settings: Settings, name: str, *, client: httpx.Client) -> bool:
    try:
        response = client.request(
            "DELETE",
            f"{settings.host.ollama_base_url.rstrip('/')}/api/delete",
            json={"name": name},
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return False
    return response.is_success


# --- Delete with cleanup -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CatalogDeletePreview:
    """What ``DELETE /catalog/{ref}`` with ``preview: true`` would remove, and from where."""

    canonical_id: str
    ollama_tag_found: bool
    gguf_path: Path | None
    freeweight: CuratedResult | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 preview shape."""
        return {
            "canonical_id": self.canonical_id,
            "ollama_tag_found": self.ollama_tag_found,
            "gguf_path": str(self.gguf_path) if self.gguf_path else None,
            "freeweight": self.freeweight.as_json() if self.freeweight else None,
        }


@dataclass(frozen=True, slots=True)
class CatalogDeleteResult:
    """What ``DELETE /catalog/{ref}`` with a typed confirmation actually removed."""

    canonical_id: str
    ollama_removed: bool
    gguf_removed: Path | None
    freeweight: CuratedResult | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 deletion result shape."""
        return {
            "canonical_id": self.canonical_id,
            "ollama_removed": self.ollama_removed,
            "gguf_removed": str(self.gguf_removed) if self.gguf_removed else None,
            "freeweight": self.freeweight.as_json() if self.freeweight else None,
        }


def _gguf_candidate(
    settings: Settings, entry: CatalogEntry, *, client: httpx.Client
) -> Path | None:
    if entry.provider_kind != "llamacpp":
        return None
    for target in llamacpp_targets(settings, client=client):
        candidate = target.model_directory / entry.provider_model_name
        if candidate.is_file():
            return candidate
    return None


def catalog_delete_preview(
    settings: Settings, entry: CatalogEntry, *, client: httpx.Client
) -> CatalogDeletePreview:
    """Preview a catalog delete: what an ``ollama rm``/file removal and FreeWeight's own
    deletion would each do, without doing any of it (Database Standards §8)."""
    ollama_found = (
        _ollama_tag_exists(settings, entry.provider_model_name, client=client)
        if entry.provider_kind == "ollama"
        else False
    )
    gguf_path = _gguf_candidate(settings, entry, client=client)
    freeweight = (
        delete_results(settings, client, "freeweight", scope="model", selector=entry.canonical_id)
        if "freeweight" in entry.apps
        else None
    )
    return CatalogDeletePreview(entry.canonical_id, ollama_found, gguf_path, freeweight)


def catalog_delete_confirm(
    settings: Settings, entry: CatalogEntry, *, typed: str, token: str, client: httpx.Client
) -> CatalogDeleteResult:
    """Remove the Ollama tag or the GGUF file, then FreeWeight's own stored results.

    Args:
        settings: The validated settings.
        entry: The catalog row to remove, already resolved by canonical id.
        typed: Must equal ``entry.canonical_id`` — the confirmation, never assumed.
        token: FreeWeight's preview token, from a fresh :func:`catalog_delete_preview`.
        client: The console's HTTP client.

    Raises:
        CatalogRefused: ``typed`` does not match.
    """
    if typed.strip() != entry.canonical_id:
        raise CatalogRefused(
            f"Type {entry.canonical_id} to delete it: this removes the weights and every stored "
            "result FreeWeight holds for it.",
            details={"canonical_id": entry.canonical_id, "typed": typed},
        )
    ollama_removed = False
    gguf_removed: Path | None = None
    if entry.provider_kind == "ollama":
        ollama_removed = _ollama_delete_tag(settings, entry.provider_model_name, client=client)
    elif entry.provider_kind == "llamacpp":
        candidate = _gguf_candidate(settings, entry, client=client)
        if candidate is not None:
            candidate.unlink()
            gguf_removed = candidate
    freeweight = (
        delete_results(
            settings,
            client,
            "freeweight",
            scope="model",
            selector=entry.canonical_id,
            token=token,
            typed=entry.canonical_id,
        )
        if "freeweight" in entry.apps
        else None
    )
    return CatalogDeleteResult(entry.canonical_id, ollama_removed, gguf_removed, freeweight)


# --- The pull job: a thread, until W9 hosts it as a real one -----------------------------------


@dataclass(frozen=True, slots=True)
class PullEvent:
    """One line of Ollama's own pull progress, or this console's own terminal event."""

    id: int
    status: str
    digest: str | None = None
    total: int | None = None
    completed: int | None = None
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        """One SSE frame's payload."""
        return {
            "status": self.status,
            "digest": self.digest,
            "total": self.total,
            "completed": self.completed,
            "error": self.error,
        }


@dataclass
class PullJob:
    """One ``ollama pull``, running in its own thread; ``events`` only ever grows."""

    id: str
    name: str
    started_at: datetime
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    events: list[PullEvent] = field(default_factory=list)
    finished: bool = False
    ok: bool = False

    def _append(self, status: str, **fields: Any) -> None:
        with self._lock:
            self.events.append(PullEvent(len(self.events) + 1, status, **fields))

    def events_after(self, after_id: int) -> list[PullEvent]:
        """Every event after ``after_id``, for the SSE route's replay."""
        with self._lock:
            return list(self.events[after_id:])

    def _finish(self, *, ok: bool) -> None:
        with self._lock:
            self.finished = True
            self.ok = ok


def _home_free_bytes() -> int:
    return shutil.disk_usage(Path.home()).free


def _run_pull(
    job: PullJob,
    *,
    client: httpx.Client,
    base_url: str,
    free_bytes: Callable[[], int] = _home_free_bytes,
) -> None:
    try:
        free = free_bytes()
        if free < _MIN_FREE_BYTES_FOR_PULL:
            job._append(  # noqa: SLF001 — this module's own worker
                "failed", error=f"only {free} bytes free; refusing to start a pull"
            )
            job._finish(ok=False)  # noqa: SLF001
            return
        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/pull",
            json={"name": job.name, "stream": True},
            timeout=None,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(data, dict):
                    continue
                error = data.get("error")
                job._append(  # noqa: SLF001
                    str(data.get("status", "")),
                    digest=data.get("digest"),
                    total=data.get("total"),
                    completed=data.get("completed"),
                    error=str(error) if error else None,
                )
                if error:
                    job._finish(ok=False)  # noqa: SLF001
                    return
        job._finish(ok=True)  # noqa: SLF001
    except httpx.HTTPError as exc:
        job._append("failed", error=str(exc))  # noqa: SLF001
        job._finish(ok=False)  # noqa: SLF001
    except Exception:
        logger.exception("catalog.pull_worker_crashed", extra={"job_id": job.id, "name": job.name})
        job._append("failed", error="the pull worker crashed; see the server log")  # noqa: SLF001
        job._finish(ok=False)  # noqa: SLF001


class PullRegistry:
    """Every pull this process has started, since it started. Not persisted (module docstring)."""

    def __init__(self) -> None:
        """An empty registry — one lives on ``app.state`` for the process's lifetime."""
        self._jobs: dict[str, PullJob] = {}
        self._lock = threading.Lock()

    def start(
        self,
        name: str,
        *,
        client: httpx.Client,
        base_url: str,
        free_bytes: Callable[[], int] = _home_free_bytes,
    ) -> PullJob:
        """Start a pull of ``name`` in a daemon thread and return its job at once."""
        job = PullJob(id=str(uuid4()), name=name, started_at=datetime.now(UTC))
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(
            target=_run_pull,
            args=(job,),
            kwargs={"client": client, "base_url": base_url, "free_bytes": free_bytes},
            name=f"wr-gym-pull-{job.id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def get(self, job_id: str) -> PullJob | None:
        """The job, or ``None`` when this process never started one by that id."""
        with self._lock:
            return self._jobs.get(job_id)
