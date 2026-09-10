"""WeightRoomGym's own migration history: up and down on both dialects, parity, the seed."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from weightsdb import MigrationRunner
from weightsdb.testing import temporary_postgres, temporary_sqlite

from weightroom.infrastructure.db.models import Base
from weightroom.services.database import MIGRATIONS_LOCATION, Database, ensure_ready, get_status

EXPECTED_SEED = {
    "freeweight": "0009",
    "loadcoach": "0015",
    "ideapress": "0010",
    "promptcadence": "0011",
}


def _head() -> str:
    with temporary_sqlite() as engine:
        heads = MigrationRunner(engine, script_location=MIGRATIONS_LOCATION).heads()
    assert len(heads) == 1, f"the history must stay linear; found {heads}"
    return heads[0]


def _seed(engine: object) -> dict[str, str]:
    from sqlalchemy import Engine

    assert isinstance(engine, Engine)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT app, revision FROM known_revisions")).all()
    return {str(app): str(rev) for app, rev in rows}


def test_fresh_sqlite_migrates_to_head_seeds_known_revisions_and_has_parity() -> None:
    with temporary_sqlite() as engine:
        runner = MigrationRunner(engine, script_location=MIGRATIONS_LOCATION)
        assert runner.current() is None
        assert runner.upgrade(backup=False).to_revision == _head()
        assert runner.is_at_head()
        assert _seed(engine) == EXPECTED_SEED
        parity = runner.check_parity(Base.metadata)
        assert parity.matches, parity.diff
        runner.downgrade("base")
        assert runner.current() is None
        names = {
            row[0]
            for row in engine.connect()
            .execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            .all()
        }
        assert names <= {"alembic_version"}


@pytest.mark.integration
def test_fresh_postgres_migrates_to_head_and_back() -> None:
    with temporary_postgres() as engine:
        runner = MigrationRunner(engine, script_location=MIGRATIONS_LOCATION)
        assert runner.upgrade(backup=False).to_revision == _head()
        assert _seed(engine) == EXPECTED_SEED
        parity = runner.check_parity(Base.metadata)
        assert parity.matches, parity.diff
        runner.downgrade("base")
        assert runner.current() is None


def test_ensure_ready_migrates_a_fresh_database_and_is_a_no_op_at_head() -> None:
    with temporary_sqlite() as engine:
        database = Database(engine)
        outcome = ensure_ready(database, auto_migrate=True)
        assert outcome is not None and outcome.to_revision == _head()
        assert ensure_ready(database, auto_migrate=True) is None
        status = get_status(database)
        assert status.is_at_head and status.integrity_ok
        assert status.table_row_counts["known_revisions"] == 4


def test_ensure_ready_refuses_a_revision_this_build_does_not_know() -> None:
    from weightsdb import SchemaAhead

    with temporary_sqlite() as engine:
        runner = MigrationRunner(engine, script_location=MIGRATIONS_LOCATION)
        runner.upgrade(backup=False)
        runner.stamp(_head())
        assert ensure_ready(Database(engine), auto_migrate=False) is None
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = '9999'"))
        with pytest.raises(SchemaAhead, match="9999"):
            ensure_ready(Database(engine), auto_migrate=True)
