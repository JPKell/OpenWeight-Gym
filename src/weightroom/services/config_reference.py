"""weightroom.services.config_reference — ``docs/configuration.md``, generated from the model.

Configuration standards §8: per field, the key path, the environment variable, the type, the
default, the range, whether it is runtime-changeable, its security implications and an example;
a test fails when the generated document differs from the committed one. Sections recurse, so
``[apps.loadcoach]`` renders as its own table under ``[apps]``.
"""

from __future__ import annotations

import types
import typing
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from weightroom.config import ENV_PREFIX, Settings, security_keys
from weightroom.services.settings import RUNTIME_SETTINGS

__all__ = ["render_configuration_reference"]

_HEADER = """# Configuration reference

**Generated** from `weightroom.config.Settings` by `wr-gym config reference`; do not edit by
hand — `tests/unit/test_config_reference.py` fails when this file differs from the model.

Precedence, field by field (configuration standards §1): built-in defaults, then `config.toml`
(`wr-gym config path` prints where), then `WEIGHTROOM_*` environment variables, then CLI flags.
Sections and fields are joined with a double underscore in the environment: `[server] port` is
`WEIGHTROOM_SERVER__PORT` and `[apps.loadcoach] base_url` is `WEIGHTROOM_APPS__LOADCOACH__BASE_URL`.
Lists are comma-separated in the environment.

**Runtime-changeable** keys (spec §12: six of them) may also be set while the server runs, through
`PUT /api/v1/settings` or the Settings page. Their stored value sits *between* the file and the
environment (configuration standards §7): `defaults -> file -> database -> env -> CLI`; a stored
value whose key is set in the environment is kept but does nothing until that variable is unset,
and `wr-gym config show` says so. **Security keys** — every key under `[server]`, `[tls]`,
`[auth]`, `[apps.*]` and `[host]` — are config-only and editable on WeightRoomGym's own settings
page only after re-authentication (ADR-0127 rule 6).
"""


def _type_name(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return " | ".join(_type_name(arg) for arg in get_args(annotation))
    if origin is typing.Literal:
        return " | ".join(repr(arg) for arg in get_args(annotation))
    if origin in (list, tuple, dict, set, frozenset):
        inner = ", ".join(_type_name(arg) for arg in get_args(annotation)) or "…"
        return f"{origin.__name__}[{inner}]"
    if annotation is type(None):
        return "None"
    if isinstance(annotation, type):
        return "table" if issubclass(annotation, BaseModel) else annotation.__name__
    return str(annotation).replace("typing.", "")


def _default(info: FieldInfo) -> str:
    if info.default_factory is not None:
        return "—"
    if info.default is PydanticUndefined:
        return "required"
    return f"`{info.default!r}`"


def _range(info: FieldInfo) -> str:
    parts = []
    for meta in info.metadata:
        for name, symbol in (("ge", "≥"), ("gt", ">"), ("le", "≤"), ("lt", "<")):
            value = getattr(meta, name, None)
            if value is not None:
                parts.append(f"{symbol} {value}")
    return ", ".join(parts) if parts else "—"


def _example(info: FieldInfo) -> str:
    examples = info.examples or []
    return f"`{examples[0]!r}`" if examples else "—"


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _section(
    lines: list[str], model: type[BaseModel], prefix: str, security: frozenset[str]
) -> None:
    doc = (model.__doc__ or "").strip().split("\n")[0]
    lines.append(f"\n## `[{prefix}]`\n\n{_escape(doc)}\n")
    nested: list[tuple[str, type[BaseModel]]] = []
    rows: list[str] = []
    for field_name, info in model.model_fields.items():
        key = f"{prefix}.{field_name}"
        annotation = info.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested.append((key, annotation))
            continue
        env = f"`{ENV_PREFIX}{key.upper().replace('.', '__')}`"
        runtime = "yes" if key in RUNTIME_SETTINGS else "no"
        security_cell = "**security key** (config-only)" if key in security else "—"
        rows.append(
            f"| `{key}` | {env} | `{_escape(_type_name(annotation))}` | "
            f"{_escape(_default(info))} | {_escape(_range(info))} | {runtime} | "
            f"{security_cell} | {_escape(_example(info))} | {_escape(info.description or '')} |"
        )
    if rows:
        lines.append(
            "| Key | Environment variable | Type | Default | Range | Runtime-changeable | "
            "Security | Example | Description |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        lines.extend(rows)
    for key, sub_model in nested:
        _section(lines, sub_model, key, security)


def render_configuration_reference() -> str:
    """Render the reference as Markdown, section by section, field by field."""
    lines = [_HEADER]
    security = security_keys()
    for section_name, section_field in Settings.model_fields.items():
        model = section_field.annotation
        assert isinstance(model, type) and issubclass(model, BaseModel), section_name  # noqa: S101 — a settings section is always a model
        _section(lines, model, section_name, security)
    lines.append("")
    return "\n".join(lines)
