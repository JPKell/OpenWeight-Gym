"""The ADR-0127 settings-schema document, applied to WeightRoomGym itself, stays stable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from weightroom.config import Settings, leaf_keys, security_keys
from weightroom.services.settings import RUNTIME_SETTINGS, SCHEMA_VERSION, config_schema_document

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "config" / "config_schema.json"


def _resolve_field_schema(json_schema: dict[str, Any], path: str) -> dict[str, Any]:
    parts = path.split(".")
    node: type[Any] = Settings
    for part in parts[:-1]:
        node = node.model_fields[part].annotation
    return cast("dict[str, Any]", json_schema["$defs"][node.__name__]["properties"][parts[-1]])


def test_every_runtime_and_security_key_exists_in_json_schema() -> None:
    json_schema = Settings.model_json_schema()
    for key in list(RUNTIME_SETTINGS) + sorted(security_keys()):
        assert _resolve_field_schema(json_schema, key), key


def test_the_three_key_sets_partition_the_leaves(tmp_path: Path) -> None:
    document = config_schema_document(tmp_path / "absent.toml")
    runtime = {entry["key"] for entry in document["runtime_changeable"]}
    security = set(document["security_keys"])
    config_only = set(document["config_only"])
    assert runtime.isdisjoint(security) and runtime.isdisjoint(config_only)
    assert security.isdisjoint(config_only)
    assert runtime | security | config_only == set(leaf_keys())
    assert set(document["sources"]) == set(leaf_keys())
    assert document["schema_version"] == SCHEMA_VERSION
    assert document["problems"] == []


@pytest.mark.contract
def test_the_committed_schema_matches_the_model(tmp_path: Path) -> None:
    from weightroom import __about__

    document = config_schema_document(tmp_path / "absent-config.toml")
    assert document["version"] == __about__.__version__
    document["config_path"] = "<config_path>"
    document["version"] = "<version>"
    document["sources"] = {k: "default" for k in document["sources"]}
    assert GOLDEN.is_file(), f"{GOLDEN} missing; write it with the snippet in this test"
    assert json.loads(GOLDEN.read_text(encoding="utf-8")) == document, (
        "the schema document drifted from tests/fixtures/config/config_schema.json; regenerate "
        'it with: python -c "import json; from weightroom.services.settings import '
        "config_schema_document as d; x=d('/nonexistent.toml'); x['config_path']='<config_path>'; "
        "x['version']='<version>'; x['sources']={k:'default' for k in x['sources']}; "
        'print(json.dumps(x, indent=2, sort_keys=True))"'
    )


def test_a_file_problem_is_reported_and_secrets_never_appear(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[apps.loadcoach]\napi_key_file = "/var/lib/wr/secret.token"\nbogus = 1\n')
    document = config_schema_document(file)
    assert document["problems"] == ["unknown configuration key 'apps.loadcoach.bogus'"]
    assert "/var/lib/wr/secret.token" not in json.dumps(document)
    assert document["sources"]["apps.loadcoach.api_key_file"] == "file"
