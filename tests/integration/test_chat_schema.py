"""Spec §11 contract 6 at the bottom layer: the database itself has no third backend."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from weightroom.infrastructure.db.models import Conversation, Message
from weightroom.services.database import Database, ensure_ready

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("backend", ["loadcoach", "promptcadence"])
def test_a_conversation_on_either_backend_is_stored(tmp_path: object, backend: str) -> None:
    database = Database.from_url(f"sqlite:///{tmp_path}/chat.sqlite3")
    ensure_ready(database, auto_migrate=True)
    with database.write() as session:
        session.add(Conversation(backend=backend, title="t", created_at=NOW, updated_at=NOW))
    database.close()


@pytest.mark.parametrize("backend", ["ollama", "llamacpp", "openai_compatible", "modelrack", ""])
def test_the_check_constraint_refuses_any_third_backend(tmp_path: object, backend: str) -> None:
    database = Database.from_url(f"sqlite:///{tmp_path}/chat.sqlite3")
    ensure_ready(database, auto_migrate=True)
    with pytest.raises(IntegrityError, match="ck_conversations_backend|CHECK constraint"):  # noqa: PT012
        with database.write() as session:
            session.add(Conversation(backend=backend, title="t", created_at=NOW, updated_at=NOW))
    database.close()


def test_a_message_sequence_is_unique_within_its_conversation(tmp_path: object) -> None:
    database = Database.from_url(f"sqlite:///{tmp_path}/chat.sqlite3")
    ensure_ready(database, auto_migrate=True)
    with database.write() as session:
        conversation = Conversation(backend="loadcoach", title="t", created_at=NOW, updated_at=NOW)
        session.add(conversation)
        session.flush()
        session.add(Message(conversation_id=conversation.id, sequence=1, role="user", text="a"))
    with pytest.raises(IntegrityError):  # noqa: PT012
        with database.write() as session:
            session.add(Message(conversation_id=conversation.id, sequence=1, role="user", text="b"))
    database.close()
