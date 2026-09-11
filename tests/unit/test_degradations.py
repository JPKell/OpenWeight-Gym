"""Every degradation spec §16 and §20 name has a test, by file and by name (row W10, gate B).

A renamed or deleted test fails here before it is missed: no systemd, an application stopped, an
unknown revision, no FTS5, no GPU, no journal, no network, an application not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DEGRADATIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "no systemd (spec §16, ADR-0125 rule 7)": {
        "integration/test_apps_routes.py": (
            "test_a_host_without_systemd_reports_unsupported_and_the_page_still_renders",
        ),
        "integration/test_processes.py": (
            "test_without_systemctl_the_host_is_unsupported_by_name",
            "test_sync_on_a_host_without_systemd_is_unsupported_by_name",
        ),
        "integration/test_ollama_routes.py": (
            "test_a_host_without_systemd_reports_the_pane_unsupported_and_keeps_rendering",
        ),
        "integration/test_health_and_status.py": (
            "test_a_host_without_systemd_reports_units_not_configured",
        ),
        "integration/test_setup.py": (
            "test_a_host_without_systemd_finishes_the_wizard_and_says_so_by_name",
        ),
    },
    "no journal": {
        "integration/test_journal.py": ("test_without_journalctl_the_host_is_unsupported_by_name",),
        "integration/test_alerts.py": (
            "test_memory_cap_without_journalctl_or_with_a_refused_journal_says_so",
        ),
    },
    "an application stopped (spec §20 criterion 7)": {
        "integration/test_apps_routes.py": (
            "test_every_page_still_renders_with_every_application_stopped",
            "test_health_of_a_stopped_application_comes_from_the_unit",
            "test_a_stopped_application_is_never_probed",
        ),
        "integration/test_shell.py": (
            "test_every_page_still_carries_the_shell_with_every_application_stopped",
        ),
        "integration/test_settings_routes.py": (
            "test_a_runtime_key_on_a_stopped_application_is_refused_and_offers_the_file",
        ),
        "integration/test_chat_loadcoach.py": (
            "test_a_stopped_loadcoach_refuses_the_send_by_name_and_old_conversations_still_read",
        ),
        "integration/test_chat_promptcadence.py": (
            "test_a_stopped_promptcadence_disables_sending_and_old_conversations_still_read",
        ),
    },
    "an application not installed": {
        "integration/test_apps_routes.py": (
            "test_an_application_that_is_not_installed_says_so_rather_than_stopped",
        ),
        "unit/test_doctor.py": (
            "test_an_application_that_is_not_installed_is_a_notice_not_a_failure",
        ),
    },
    "an unknown revision (spec §20 criterion 8, ADR-0123 rule 3)": {
        "integration/test_database_routes.py": (
            "test_an_unknown_revision_degrades_the_pages_by_name_and_refuses_in_json",
        ),
        "integration/test_db_reader.py": (
            "test_an_unknown_revision_refuses_by_name_and_still_reports_itself",
        ),
        "unit/test_overview.py": (
            "test_an_unknown_revision_degrades_the_table_by_name_never_zero",
        ),
        "unit/test_fixture_databases.py": (
            "test_the_unknown_revision_fixture_is_not_in_known_revisions",
        ),
    },
    "no FTS5 (spec §7.5)": {
        "unit/test_docs_index.py": ("test_the_like_fallback_finds_the_same_page_when_forced",),
    },
    "no GPU (spec §16, sweatmeter's matrix, ADR-0016)": {
        "unit/test_telemetry.py": (
            "test_a_failing_gpu_reader_degrades_only_gpu_fields",
            "test_unsupported_never_serializes_as_zero",
        ),
    },
    "no network (spec §20 criterion 10)": {
        "e2e/test_network_isolation.py": (
            "test_every_page_renders_with_every_application_stopped_and_no_socket",
            "test_every_json_read_answers_with_every_application_stopped_and_no_socket",
        ),
    },
}


@pytest.mark.parametrize("degradation", sorted(DEGRADATIONS))
def test_every_named_degradation_has_its_tests(degradation: str) -> None:
    root = Path(__file__).resolve().parents[1]
    for file, names in DEGRADATIONS[degradation].items():
        text = (root / file).read_text(encoding="utf-8")
        for name in names:
            assert name in text, f"{degradation}: {file} no longer holds {name}"
