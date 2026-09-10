"""weightroom.services.chat — conversations, attachments, the persisted stream, and rendering.

The shape of one reply (spec §7.6, data model §2, ADR-0044):

1. ``POST …/messages`` stores the operator's message and an empty assistant message, and hands the
   reply to :class:`ChatRunner` — a small thread pool, because the reply outlives the request.
2. The runner reads the backend's stream (:mod:`weightroom.services.chat_loadcoach`), folds each
   step through the pure thinking state machine, and writes one ``message_events`` row per emitted
   kind, as it happens.
3. On the terminal step, **one transaction** fills the message (answer, thinking, routing, usage,
   cost, finish reason), drops the delta rows, and writes the ``done`` or ``halt`` row — the
   state and its event are one write, so a reader never sees one without the other.
4. The page's stream (``GET …/stream``) is a poll of ``message_events`` by integer id, resumed
   from ``Last-Event-ID`` — the telemetry stream's pattern. A client that joins after the deltas
   were coalesced still receives ``done`` and re-renders the finished message from the server.

**Nothing raw.** Live deltas are written into the page as ``textContent`` by the thread's script.
The finished answer is rendered here by :func:`render_reply` — ``mistune`` with ``escape=True``,
links only to ``http(s)`` through MirrorWall's ``safe_href``, images reduced to their alt text so
nothing a model wrote is ever fetched — and handed to the template as :class:`SafeReplyHtml`,
whose ``__html__`` Jinja's autoescape honours. No chat template contains ``| safe`` (a test
asserts it), so the only HTML that reaches a thread is HTML this function built.
"""

from __future__ import annotations

import hashlib
import html
import logging
import re
import shutil
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

import httpx
import mistune
from baseaicore import SuiteError, ValidationError, new_id
from mirrorwall import Event, format_frame, safe_href
from setspec import GeneratorInfo
from sqlalchemy import delete, func, select

from weightroom.__about__ import __version__
from weightroom.domain.chat import (
    ATTACHMENT_MEDIA_TYPES,
    DELTA_KINDS,
    Chunk,
    CostCell,
    ThinkingState,
    advance,
    cost_cell,
    require_backend,
    sanitise_filename,
)
from weightroom.infrastructure.db.models import Attachment, Conversation, Message, MessageEvent
from weightroom.services.chat_loadcoach import (
    BackendRefused,
    build_request,
    context_block,
    fetch_routing,
    stream_reply,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from weightroom.config import Settings
    from weightroom.services.apps import AppView
    from weightroom.services.database import Database

__all__ = [
    "AttachmentTooLarge",
    "AttachmentTypeRefused",
    "ChatBackendUnavailable",
    "ChatRunner",
    "ConversationNotFound",
    "ConversationView",
    "MessageView",
    "SafeReplyHtml",
    "add_attachment",
    "backend_unavailable_reason",
    "create_conversation",
    "delete_conversation",
    "events_after",
    "get_conversation",
    "heartbeat_frame",
    "list_conversations",
    "recover_interrupted",
    "render_reply",
    "ApprovalRefused",
    "ApprovalScopeMissing",
    "decide_approval",
    "run_loadcoach_reply",
    "run_promptcadence_reply",
    "run_reply",
    "sse_frame",
    "start_reply",
]

logger = logging.getLogger(__name__)

_GENERATOR: Final = GeneratorInfo(name="weightroom", version=__version__)
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
_LANGUAGE = re.compile(r"^[A-Za-z0-9_+-]{1,32}$")


class ChatBackendUnavailable(SuiteError):
    """The conversation's backend cannot take a message now; old conversations still read."""

    code: ClassVar[str] = "CHAT_BACKEND_UNAVAILABLE"


class AttachmentTooLarge(SuiteError):
    """The file exceeds ``[chat] max_attachment_bytes``."""

    code: ClassVar[str] = "ATTACHMENT_TOO_LARGE"


class AttachmentTypeRefused(SuiteError):
    """The file is not text or markdown — by extension, encoding or content."""

    code: ClassVar[str] = "ATTACHMENT_TYPE_REFUSED"


class ApprovalScopeMissing(SuiteError):
    """The console's PromptCadence token cannot approve (ADR-0049's separate scope)."""

    code: ClassVar[str] = "FORBIDDEN"


class ApprovalRefused(SuiteError):
    """PromptCadence refused the decision — nothing pending, already resolved — in its words."""

    code: ClassVar[str] = "VALIDATION_ERROR"


class ConversationNotFound(SuiteError):
    """No conversation or message with that id."""

    code: ClassVar[str] = "NOT_FOUND"


# --- Rendering -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SafeReplyHtml:
    """HTML built by :func:`render_reply` and nothing else; Jinja prints it unescaped via
    ``__html__``, so no template needs ``| safe`` (this module's docstring)."""

    html: str

    def __html__(self) -> str:
        """The markup-safe protocol Jinja's autoescape honours."""
        return self.html

    def __str__(self) -> str:
        """The same HTML, for tests and JSON."""
        return self.html


class _ChatRenderer(mistune.HTMLRenderer):
    """Escaped markdown for model text: no raw HTML, no images fetched, links only to http(s)."""

    def __init__(self) -> None:
        super().__init__(escape=True)

    def link(self, text: str, url: str, title: str | None = None) -> str:
        href = safe_href(url)
        if href is None or not href.lower().startswith(("http://", "https://")):
            return text
        return (
            f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer nofollow" '
            f'target="_blank">{text}</a>'
        )

    def image(self, text: str, url: str, title: str | None = None) -> str:
        # Never fetched: an image URL in a reply is something a model wrote, and loading it would
        # be the console making a request on a model's instruction (spec §14).
        return html.escape(text or "", quote=False)

    def block_code(self, code: str, info: str | None = None) -> str:
        language = (info or "").split(None, 1)[0] if info else ""
        attribute = (
            f' class="language-{html.escape(language)}"' if _LANGUAGE.match(language) else ""
        )
        return (
            f'<div class="chat-code"><pre><code{attribute}>{html.escape(code)}</code></pre></div>\n'
        )


def render_reply(text: str) -> SafeReplyHtml:
    """Render one answer as sanitised HTML. The one constructor of :class:`SafeReplyHtml`."""
    convert = mistune.create_markdown(
        renderer=_ChatRenderer(), plugins=["table", "strikethrough", "url"]
    )
    body = convert(text or "")
    return SafeReplyHtml(body if isinstance(body, str) else "")


# --- Views ---------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MessageView:
    """One message as the thread shows it."""

    id: str
    sequence: int
    role: str
    text: str
    thinking: str | None
    routing: dict[str, Any] | None
    usage: dict[str, Any] | None
    cost: dict[str, Any] | None
    finish_reason: str | None
    remote_job_id: str | None
    remote_step_id: str | None
    created_at: datetime
    completed_at: datetime | None
    halt_message: str | None = None
    cards: tuple[dict[str, Any], ...] = ()

    @property
    def in_progress(self) -> bool:
        """Whether this is an assistant reply still streaming."""
        return self.role == "assistant" and self.completed_at is None

    @property
    def pending_approvals(self) -> frozenset[str]:
        """Approval requests this reply raised that nobody has granted or denied yet."""
        requested: set[str] = set()
        resolved: set[str] = set()
        for card in self.cards:
            if card.get("kind") != "approval_pending":
                continue
            request_id = str(card.get("approval_request_id") or "")
            if card.get("status") == "requested":
                requested.add(request_id)
            elif card.get("status") in {"granted", "denied"}:
                resolved.add(request_id)
        return frozenset(requested - resolved - {""})

    @property
    def html(self) -> SafeReplyHtml:
        """The answer, rendered (:func:`render_reply`)."""
        return render_reply(self.text)

    @property
    def cost_line(self) -> CostCell | None:
        """The cost cell for a finished assistant reply, or ``None``."""
        if self.role != "assistant" or self.completed_at is None or self.usage is None:
            return None
        return cost_cell(self.usage, self.cost, remote=bool((self.routing or {}).get("is_remote")))

    def as_json(self) -> dict[str, Any]:
        """The ``GET /chat/conversations/{id}`` message shape (api.md §6)."""
        return {
            "id": self.id,
            "sequence": self.sequence,
            "role": self.role,
            "text": self.text,
            "thinking": self.thinking,
            "routing": self.routing,
            "usage": self.usage,
            "cost": self.cost,
            "finish_reason": self.finish_reason,
            "remote_job_id": self.remote_job_id,
            "remote_step_id": self.remote_step_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "halt": self.halt_message,
            "cards": list(self.cards),
        }


@dataclass(frozen=True, slots=True)
class AttachmentView:
    """One attachment's metadata; its text is never shown back, only named."""

    id: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ConversationView:
    """One conversation with its messages."""

    id: str
    backend: str
    title: str
    task_profile: str | None
    model_override: str | None
    classification: str | None
    tier: str | None
    tools: list[str] | None
    remote_trajectory_id: str | None
    created_at: datetime
    updated_at: datetime
    messages: tuple[MessageView, ...] = ()
    attachments: tuple[AttachmentView, ...] = ()
    last_event_id: int = 0

    @property
    def in_progress(self) -> MessageView | None:
        """The reply still streaming, if any."""
        return next((one for one in self.messages if one.in_progress), None)

    @property
    def resume_after(self) -> int:
        """Where the page's stream starts: just before the streaming reply's first row, so its
        deltas so far are replayed; otherwise after every row this render already shows."""
        return self.last_event_id

    def as_json(self) -> dict[str, Any]:
        """The ``GET /chat/conversations/{id}`` body (api.md §6)."""
        return {
            "id": self.id,
            "backend": self.backend,
            "title": self.title,
            "task_profile": self.task_profile,
            "model_override": self.model_override,
            "classification": self.classification,
            "tier": self.tier,
            "tools": self.tools,
            "remote_trajectory_id": self.remote_trajectory_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [one.as_json() for one in self.messages],
            "attachments": [
                {
                    "id": one.id,
                    "filename": one.filename,
                    "media_type": one.media_type,
                    "size_bytes": one.size_bytes,
                    "sha256": one.sha256,
                }
                for one in self.attachments
            ],
        }


# --- Conversations -------------------------------------------------------------------------------


def create_conversation(
    database: Database,
    *,
    backend: str,
    title: str,
    now: datetime,
    task_profile: str | None = None,
    model_override: str | None = None,
    classification: str | None = None,
    tier: str | None = None,
    tools: Sequence[str] | None = None,
) -> str:
    """Store a new conversation and return its id.

    Raises:
        BackendUnknown: ``backend`` is not one of the two (the check constraint would too).
        ValidationError: The title is empty.
    """
    require_backend(backend)
    clean_title = title.strip()
    if not clean_title:
        raise ValidationError(
            "A conversation needs a title.",
            details={"fields": [{"path": "title", "problem": "empty"}]},
        )
    with database.write() as session:
        row = Conversation(
            backend=backend,
            title=clean_title[:200],
            task_profile=(task_profile or None) if backend == "loadcoach" else None,
            model_override=(model_override or None) if backend == "loadcoach" else None,
            classification=(classification or None) if backend == "promptcadence" else None,
            tier=(tier or None) if backend == "promptcadence" else None,
            tools=list(tools) if (tools and backend == "promptcadence") else None,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        return str(row.id)


def list_conversations(database: Database) -> list[dict[str, Any]]:
    """Every conversation, most recently active first, with its message count."""
    with database.read() as session:
        counts: dict[str, int] = {
            str(conversation_id): int(count)
            for conversation_id, count in session.execute(
                select(Message.conversation_id, func.count()).group_by(Message.conversation_id)
            ).all()
        }
        rows = session.execute(
            select(Conversation).order_by(Conversation.updated_at.desc())
        ).scalars()
        return [
            {
                "id": row.id,
                "backend": row.backend,
                "title": row.title,
                "updated_at": row.updated_at.isoformat(),
                "messages": int(counts.get(row.id, 0)),
            }
            for row in rows
        ]


def _require_id(value: str) -> str:
    if not _ULID.match(value):
        raise ConversationNotFound(f"No conversation {value!r}.", details={"id": value})
    return value


def get_conversation(database: Database, conversation_id: str) -> ConversationView:
    """One conversation with its messages, attachments and structured cards.

    Raises:
        ConversationNotFound: No such conversation.
    """
    _require_id(conversation_id)
    with database.read() as session:
        row = session.get(Conversation, conversation_id)
        if row is None:
            raise ConversationNotFound(
                f"No conversation {conversation_id!r}.", details={"id": conversation_id}
            )
        messages = list(
            session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence)
            ).scalars()
        )
        events = list(
            session.execute(
                select(MessageEvent)
                .join(Message, Message.id == MessageEvent.message_id)
                .where(Message.conversation_id == conversation_id)
                .order_by(MessageEvent.id)
            ).scalars()
        )
        attachments = list(
            session.execute(
                select(Attachment)
                .where(Attachment.conversation_id == conversation_id)
                .order_by(Attachment.created_at)
            ).scalars()
        )
        by_message: dict[str, list[MessageEvent]] = {}
        for event in events:
            by_message.setdefault(event.message_id, []).append(event)
        streaming = next(
            (one for one in messages if one.role == "assistant" and one.completed_at is None),
            None,
        )
        if streaming is not None and by_message.get(streaming.id):
            last_event_id = by_message[streaming.id][0].id - 1
        else:
            last_event_id = max((event.id for event in events), default=0)
        views = tuple(_message_view(one, by_message.get(one.id, [])) for one in messages)
        return ConversationView(
            id=row.id,
            backend=row.backend,
            title=row.title,
            task_profile=row.task_profile,
            model_override=row.model_override,
            classification=row.classification,
            tier=row.tier,
            tools=list(row.tools) if isinstance(row.tools, list) else None,
            remote_trajectory_id=row.remote_trajectory_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            messages=views,
            attachments=tuple(
                AttachmentView(one.id, one.filename, one.media_type, one.size_bytes, one.sha256)
                for one in attachments
            ),
            last_event_id=last_event_id,
        )


def _message_view(row: Message, events: Sequence[MessageEvent]) -> MessageView:
    halt = next((event for event in events if event.kind == "halt"), None)
    halt_payload = halt.payload if halt is not None and isinstance(halt.payload, dict) else {}
    cards = tuple(
        {
            "id": event.id,
            "kind": event.kind,
            **(event.payload if isinstance(event.payload, dict) else {}),
        }
        for event in events
        if event.kind not in DELTA_KINDS and event.kind not in {"thinking_done", "done", "halt"}
    )
    return MessageView(
        id=row.id,
        sequence=row.sequence,
        role=row.role,
        text=row.text,
        thinking=row.thinking,
        routing=row.routing if isinstance(row.routing, dict) else None,
        usage=row.usage if isinstance(row.usage, dict) else None,
        cost=row.cost if isinstance(row.cost, dict) else None,
        finish_reason=row.finish_reason,
        remote_job_id=row.remote_job_id,
        remote_step_id=row.remote_step_id,
        created_at=row.created_at,
        completed_at=row.completed_at,
        halt_message=str(halt_payload.get("message") or "") if halt is not None else None,
        cards=cards,
    )


def delete_conversation(
    database: Database, conversation_id: str, *, attachments_root: Path
) -> None:
    """Delete a conversation, its messages, events, attachment rows and stored files.

    Rows are deleted explicitly, child first, rather than trusting ``ON DELETE CASCADE``: SQLite
    enforces a foreign key only on a connection that asked it to.

    Raises:
        ConversationNotFound: No such conversation.
    """
    get_conversation(database, conversation_id)
    with database.write() as session:
        message_ids = select(Message.id).where(Message.conversation_id == conversation_id)
        session.execute(delete(MessageEvent).where(MessageEvent.message_id.in_(message_ids)))
        session.execute(delete(Message).where(Message.conversation_id == conversation_id))
        session.execute(delete(Attachment).where(Attachment.conversation_id == conversation_id))
        session.execute(delete(Conversation).where(Conversation.id == conversation_id))
    directory = _attachment_dir(attachments_root, conversation_id)
    if directory.is_dir():
        shutil.rmtree(directory)


# --- Attachments ---------------------------------------------------------------------------------


def _attachment_dir(root: Path, conversation_id: str) -> Path:
    """``<root>/<conversation>``, refused if the id could step outside the root."""
    _require_id(conversation_id)
    base = root.resolve()
    target = (base / conversation_id).resolve()
    if target.parent != base:  # pragma: no cover — a ULID has no separator; defence in depth
        raise ConversationNotFound("Attachment path outside the root.", details={})
    return target


def add_attachment(
    database: Database,
    *,
    attachments_root: Path,
    conversation_id: str,
    filename: str,
    data: bytes,
    max_bytes: int,
    now: datetime,
) -> AttachmentView:
    """Store one text or markdown file under a generated name (spec §7.6, §14).

    Raises:
        ConversationNotFound: No such conversation.
        AttachmentTooLarge: Over ``max_bytes``.
        AttachmentTypeRefused: Not ``.txt``/``.md`` (and their spellings), not UTF-8, or binary.
    """
    get_conversation(database, conversation_id)
    clean = sanitise_filename(filename)
    media_type = ATTACHMENT_MEDIA_TYPES.get(Path(clean).suffix.lower())
    if media_type is None:
        raise AttachmentTypeRefused(
            f"{clean} is not a text or markdown file; only "
            f"{', '.join(sorted(ATTACHMENT_MEDIA_TYPES))} are accepted.",
            details={"filename": clean},
        )
    if len(data) > max_bytes:
        raise AttachmentTooLarge(
            f"{clean} is {len(data)} bytes; the limit is {max_bytes}.",
            details={"filename": clean, "size_bytes": len(data), "limit_bytes": max_bytes},
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AttachmentTypeRefused(
            f"{clean} is not UTF-8 text.", details={"filename": clean}
        ) from exc
    if "\x00" in text:
        raise AttachmentTypeRefused(f"{clean} contains binary data.", details={"filename": clean})
    attachment_id = new_id()
    directory = _attachment_dir(attachments_root, conversation_id)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stored = directory / attachment_id
    stored.write_bytes(data)
    stored.chmod(0o600)
    digest = hashlib.sha256(data).hexdigest()
    with database.write() as session:
        session.add(
            Attachment(
                id=attachment_id,
                conversation_id=conversation_id,
                filename=clean,
                stored_path=str(stored),
                media_type=media_type,
                size_bytes=len(data),
                sha256=digest,
                created_at=now,
            )
        )
    return AttachmentView(attachment_id, clean, media_type, len(data), digest)


# --- Replies -------------------------------------------------------------------------------------


def backend_unavailable_reason(backend: str, view: AppView | None) -> str | None:
    """Why a conversation on ``backend`` cannot take a message right now, or ``None``.

    The send button is disabled with this sentence; the conversation itself still reads.
    """
    name = {"loadcoach": "LoadCoach", "promptcadence": "PromptCadence"}.get(backend, backend)
    if view is None:
        return f"{name} is not known to this console."
    if not view.installed:
        return f"{name} is not installed, so there is nothing to send this to."
    if not view.running:
        return f"{name} is stopped. Start it on its Overview page; this conversation still reads."
    if not view.reachable:
        return f"{name} is running but its API is not answering yet."
    return None


def start_reply(
    database: Database, *, conversation_id: str, text: str, now: datetime
) -> tuple[str, str]:
    """Store the operator's message and an empty assistant reply; return both ids.

    Raises:
        ConversationNotFound: No such conversation.
        ValidationError: The message is empty, or a reply is still streaming.
    """
    body = text.strip()
    if not body:
        raise ValidationError(
            "A message needs some text.", details={"fields": [{"path": "text", "problem": "empty"}]}
        )
    view = get_conversation(database, conversation_id)
    if view.in_progress is not None:
        raise ValidationError(
            "The previous reply is still streaming; wait for it to finish.",
            details={"message_id": view.in_progress.id},
        )
    sequence = max((one.sequence for one in view.messages), default=0)
    user_id, assistant_id = new_id(), new_id()
    with database.write() as session:
        session.add(
            Message(
                id=user_id,
                conversation_id=conversation_id,
                sequence=sequence + 1,
                role="user",
                text=body,
                created_at=now,
                completed_at=now,
            )
        )
        session.add(
            Message(
                id=assistant_id,
                conversation_id=conversation_id,
                sequence=sequence + 2,
                role="assistant",
                text="",
                created_at=now,
            )
        )
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = now
    return user_id, assistant_id


def _history(
    database: Database, conversation_id: str, *, reply_id: str, attachments_root: Path
) -> tuple[ConversationView, list[tuple[str, str]]]:
    """The conversation and the ``(role, content)`` pairs a request sends, oldest first.

    Every attachment of the conversation is prepended to its **first** user message, on every
    request: the files are context for the whole conversation, and a later turn must not lose
    them. A reply that halted is not sent back as if it had been an answer.
    """
    view = get_conversation(database, conversation_id)
    history: list[tuple[str, str]] = []
    for message in view.messages:
        if message.id == reply_id or message.role not in {"user", "assistant"}:
            continue
        if message.role == "assistant" and (
            message.in_progress or message.finish_reason == "error"
        ):
            continue
        history.append((message.role, message.text))
    files = []
    for attachment in view.attachments:
        stored = _attachment_dir(attachments_root, conversation_id) / attachment.id
        try:
            files.append((attachment.filename, stored.read_text(encoding="utf-8")))
        except OSError:
            files.append((attachment.filename, "[this attachment's file is missing]"))
    if files:
        for index, (role, content) in enumerate(history):
            if role == "user":
                history[index] = (role, f"{context_block(files)}\n{content}")
                break
    return view, history


def _append_event(
    database: Database,
    message_id: str,
    sequence: int,
    kind: str,
    payload: Mapping[str, Any],
    now: datetime,
) -> None:
    with database.write() as session:
        session.add(
            MessageEvent(
                message_id=message_id, sequence=sequence, kind=kind, payload=dict(payload), at=now
            )
        )


def _complete(
    database: Database,
    message_id: str,
    *,
    state: ThinkingState,
    routing: Mapping[str, Any] | None,
    usage: Mapping[str, Any] | None,
    cost: Mapping[str, Any] | None,
    finish_reason: str | None,
    remote_job_id: str | None,
    halt: str | None,
    now: datetime,
) -> None:
    """Fill the message, drop its deltas, write ``done``/``halt`` — one transaction (ADR-0044)."""
    with database.write() as session:
        message = session.get(Message, message_id)
        if message is None:  # pragma: no cover — deleted mid-stream; nothing to complete
            return
        highest = session.execute(
            select(func.max(MessageEvent.sequence)).where(MessageEvent.message_id == message_id)
        ).scalar_one_or_none()
        message.text = state.text
        message.thinking = state.thinking or None
        message.routing = dict(routing) if routing else None
        message.usage = dict(usage) if usage else None
        message.cost = dict(cost) if cost else None
        message.finish_reason = finish_reason
        message.remote_job_id = remote_job_id
        message.completed_at = now
        session.execute(
            delete(MessageEvent).where(
                MessageEvent.message_id == message_id, MessageEvent.kind.in_(sorted(DELTA_KINDS))
            )
        )
        session.add(
            MessageEvent(
                message_id=message_id,
                sequence=(highest or 0) + 1,
                kind="halt" if halt is not None else "done",
                payload={"message_id": message_id, "finish_reason": finish_reason, "message": halt},
                at=now,
            )
        )
        conversation = session.get(Conversation, message.conversation_id)
        if conversation is not None:
            conversation.updated_at = now


class _Recorder:
    """Folds chunks and writes each emitted kind but the terminal one, which ``_complete`` owns."""

    def __init__(self, database: Database, message_id: str, clock: Callable[[], datetime]) -> None:
        self.database = database
        self.message_id = message_id
        self.clock = clock
        self.state = ThinkingState()
        self.sequence = 0

    def feed(self, chunk: Chunk) -> None:
        self.state, kinds = advance(self.state, chunk)
        for kind in kinds:
            if kind in {"done", "halt"}:
                continue
            self.sequence += 1
            payload: dict[str, Any] = {"message_id": self.message_id}
            if kind in DELTA_KINDS:
                payload["delta"] = chunk.text
            _append_event(
                self.database, self.message_id, self.sequence, kind, payload, self.clock()
            )

    def card(self, kind: str, payload: Mapping[str, Any]) -> None:
        """Write one structured card row (plan, step, tool call, egress, approval)."""
        self.sequence += 1
        body = {"message_id": self.message_id, **dict(payload)}
        _append_event(self.database, self.message_id, self.sequence, kind, body, self.clock())


def run_reply(
    database: Database,
    client: httpx.Client,
    *,
    settings: Settings,
    conversation_id: str,
    message_id: str,
    attachments_root: Path,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Stream one reply through the conversation's own backend. Never raises."""
    try:
        backend = get_conversation(database, conversation_id).backend
    except SuiteError:
        return
    runner = run_promptcadence_reply if backend == "promptcadence" else run_loadcoach_reply
    runner(
        database,
        client,
        settings=settings,
        conversation_id=conversation_id,
        message_id=message_id,
        attachments_root=attachments_root,
        clock=clock,
    )


def run_loadcoach_reply(
    database: Database,
    client: httpx.Client,
    *,
    settings: Settings,
    conversation_id: str,
    message_id: str,
    attachments_root: Path,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Stream one LoadCoach reply into ``message_id``. Never raises: every failure is a ``halt``.

    Args:
        database: The console's database.
        client: The HTTP client (the network-isolation test watches it).
        settings: The validated settings — LoadCoach's base URL, the token file, the default task.
        conversation_id: The conversation.
        message_id: The assistant message :func:`start_reply` created.
        attachments_root: Where attachment files live.
        clock: Injected for tests.
    """
    from weightroom.services.apps import bearer_token

    recorder = _Recorder(database, message_id, clock)
    routing: dict[str, Any] | None = None
    base_url = settings.apps.loadcoach.base_url
    token = bearer_token(settings, "loadcoach")
    message = "The reply ended without a result."
    try:
        view, history = _history(
            database, conversation_id, reply_id=message_id, attachments_root=attachments_root
        )
        body = build_request(
            task=view.task_profile or settings.chat.default_task_profile,
            model_override=view.model_override,
            history=history,
            idempotency_key=message_id,
        )
        for kind, value in stream_reply(client, base_url=base_url, token=token, body=body):
            if kind == "routing":
                routing = dict(value)
            elif kind == "chunk":
                recorder.feed(value)
            elif kind == "result":
                _finish_result(
                    database, client, recorder, value, routing, base_url=base_url, token=token
                )
                return
        message = recorder.state.error or message
    except BackendRefused as exc:
        message = exc.message
    except httpx.HTTPError as exc:
        message = f"LoadCoach did not answer: {exc}"
    except Exception as exc:  # noqa: BLE001 — a reply thread reports, it never dies silently
        logger.exception("chat.reply_failed", extra={"message_id": message_id})
        message = f"The reply failed: {exc}"
    if not recorder.state.finished:
        recorder.feed(Chunk("error", message))
    _complete(
        database,
        message_id,
        state=recorder.state,
        routing=routing,
        usage=None,
        cost=None,
        finish_reason="error",
        remote_job_id=None,
        halt=recorder.state.error or message,
        now=clock(),
    )


def _finish_result(
    database: Database,
    client: httpx.Client,
    recorder: _Recorder,
    result: Mapping[str, Any],
    routing: dict[str, Any] | None,
    *,
    base_url: str,
    token: str | None,
) -> None:
    reasoning = result.get("reasoning") or {}
    summary = reasoning.get("summary") if reasoning.get("available") else None
    recorder.feed(Chunk("done", reasoning=summary if isinstance(summary, str) else None))
    model = result.get("model") or {}
    decision = routing
    if decision is None:
        explanation_url = str((result.get("routing") or {}).get("explanation_url") or "")
        decision = (
            fetch_routing(client, base_url=base_url, token=token, explanation_url=explanation_url)
            or {}
        )
    decision = {
        **decision,
        "job_id": result.get("job_id"),
        "model": model.get("canonical_id") or decision.get("model"),
        "provider_name": model.get("provider_name") or decision.get("provider_name"),
        "is_remote": bool(model.get("is_remote")),
    }
    cost = result.get("cost")
    _complete(
        database,
        recorder.message_id,
        state=recorder.state,
        routing=decision,
        usage=result.get("usage") if isinstance(result.get("usage"), dict) else None,
        cost=cost if isinstance(cost, dict) else None,
        finish_reason=str((result.get("output") or {}).get("finish_reason") or "") or None,
        remote_job_id=str(result.get("job_id") or "") or None,
        halt=None,
        now=recorder.clock(),
    )


def _set_remote(
    database: Database, conversation_id: str, message_id: str, trajectory_id: str
) -> None:
    with database.write() as session:
        message = session.get(Message, message_id)
        if message is not None:
            message.remote_job_id = trajectory_id
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.remote_trajectory_id = trajectory_id


def run_promptcadence_reply(
    database: Database,
    client: httpx.Client,
    *,
    settings: Settings,
    conversation_id: str,
    message_id: str,
    attachments_root: Path,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Run one message as a PromptCadence trajectory into ``message_id``. Never raises.

    Cards are written as the trajectory's events arrive; the answer is its last assistant turn,
    read on ``trajectory.completed``; a halt carries PromptCadence's own cause.
    """
    from weightroom.services import chat_promptcadence as pc
    from weightroom.services.apps import bearer_token

    recorder = _Recorder(database, message_id, clock)
    token = bearer_token(settings, "promptcadence")
    trajectory_id: str | None = None
    last_turn: dict[str, Any] = {}
    message = "The trajectory ended without a result."
    try:
        view, history = _history(
            database, conversation_id, reply_id=message_id, attachments_root=attachments_root
        )
        trajectory_id = pc.submit_trajectory(
            client,
            settings,
            token=token,
            task=pc.build_task(history, ()),
            classification=view.classification,
            tools=view.tools or [],
            tier=view.tier,
        )
        _set_remote(database, conversation_id, message_id, trajectory_id)
        for kind, value in pc.stream_trajectory(
            client, settings, token=token, trajectory_id=trajectory_id
        ):
            if kind == "card":
                card_kind, payload = value
                if payload.get("event") == "turn.completed":
                    last_turn = dict(payload)
                recorder.card(card_kind, payload)
            elif kind == "completed":
                answer, usage = pc.fetch_answer(
                    client, settings, token=token, trajectory_id=trajectory_id
                )
                for decision in pc.fetch_egress(
                    client, settings, token=token, trajectory_id=trajectory_id
                ):
                    recorder.card("egress_decision", decision.get("payload", decision))
                recorder.feed(Chunk("text", answer))
                recorder.feed(Chunk("done"))
                _complete(
                    database,
                    message_id,
                    state=recorder.state,
                    routing=_promptcadence_routing(client, settings, last_turn, token=token),
                    usage=usage,
                    cost=None,
                    finish_reason=str(last_turn.get("finish_reason") or "stop"),
                    remote_job_id=trajectory_id,
                    halt=None,
                    now=clock(),
                )
                return
            elif kind == "halt":
                message = str(value)
                break
    except BackendRefused as exc:
        message = exc.message
    except httpx.HTTPError as exc:
        message = f"PromptCadence did not answer: {exc}"
    except Exception as exc:  # noqa: BLE001 — a reply thread reports, it never dies silently
        logger.exception("chat.trajectory_failed", extra={"message_id": message_id})
        message = f"The reply failed: {exc}"
    if not recorder.state.finished:
        recorder.feed(Chunk("error", message))
    _complete(
        database,
        message_id,
        state=recorder.state,
        routing=None,
        usage=None,
        cost=None,
        finish_reason="error",
        remote_job_id=trajectory_id,
        halt=recorder.state.error or message,
        now=clock(),
    )


def _promptcadence_routing(
    client: httpx.Client, settings: Settings, turn: Mapping[str, Any], *, token: str | None
) -> dict[str, Any]:
    """The decision line for a trajectory: its last turn's model and tier, LoadCoach's routing
    counts for that turn's job, and whether the tier is remote by PromptCadence's own flag."""
    from weightroom.services import chat_promptcadence as pc
    from weightroom.services.apps import bearer_token

    job = str(turn.get("loadcoach_job_id") or "")
    decision: dict[str, Any] = {}
    if job:
        decision = dict(
            fetch_routing(
                client,
                base_url=settings.apps.loadcoach.base_url,
                token=bearer_token(settings, "loadcoach"),
                explanation_url=f"/api/v1/jobs/{job}/explanation",
            )
            or {}
        )
    tier = str(turn.get("tier") or "")
    return {
        **decision,
        "model": turn.get("model_canonical_id") or decision.get("model"),
        "tier": tier or None,
        "job_id": job or None,
        "is_remote": pc.fetch_tier_remote(client, settings, token=token, tier=tier) is True,
    }


def decide_approval(
    database: Database,
    client: httpx.Client,
    *,
    settings: Settings,
    conversation_id: str,
    approval_request_id: str,
    decision: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Grant or deny a pending approval a reply raised, with the ``approve``-scoped token.

    Raises:
        ConversationNotFound: No pending request with that id in this conversation.
        ApprovalScopeMissing: The console's token has no ``approve`` scope, or it cannot tell.
        ApprovalRefused: PromptCadence refused the decision, in its own words.
        ChatBackendUnavailable: PromptCadence did not answer.
    """
    from weightroom.services import chat_promptcadence as pc
    from weightroom.services.apps import bearer_token

    view = get_conversation(database, conversation_id)
    message = next(
        (one for one in view.messages if approval_request_id in one.pending_approvals), None
    )
    if view.backend != "promptcadence" or message is None or not message.remote_job_id:
        raise ConversationNotFound(
            f"No pending approval {approval_request_id!r} in this conversation.",
            details={
                "conversation_id": conversation_id,
                "approval_request_id": approval_request_id,
            },
        )
    allowed = pc.token_can_approve(settings)
    if allowed is not True:
        raise ApprovalScopeMissing(
            "The console's PromptCadence token has no approve scope (ADR-0049)."
            if allowed is False
            else "Whether the console's PromptCadence token can approve could not be read.",
            details={"approval_request_id": approval_request_id},
        )
    try:
        return pc.approval_decision(
            client,
            settings,
            token=bearer_token(settings, "promptcadence"),
            trajectory_id=message.remote_job_id,
            decision=decision,
            reason=reason,
        )
    except BackendRefused as exc:
        raise ApprovalRefused(
            exc.message, details={"approval_request_id": approval_request_id}
        ) from exc
    except httpx.HTTPError as exc:
        raise ChatBackendUnavailable(
            f"PromptCadence did not answer: {exc}", details={"backend": "promptcadence"}
        ) from exc


def recover_interrupted(database: Database, *, now: datetime) -> int:
    """Halt every reply that was streaming when the console stopped; return how many.

    A reply's thread does not survive a restart, and a message left without ``completed_at`` would
    show as streaming forever. It is closed with what it had and a halt that says why.
    """
    with database.read() as session:
        ids = list(
            session.execute(
                select(Message.id).where(
                    Message.role == "assistant", Message.completed_at.is_(None)
                )
            ).scalars()
        )
    for message_id in ids:
        with database.read() as session:
            deltas = list(
                session.execute(
                    select(MessageEvent)
                    .where(MessageEvent.message_id == message_id)
                    .order_by(MessageEvent.sequence)
                ).scalars()
            )
        state = ThinkingState()
        for event in deltas:
            payload = event.payload if isinstance(event.payload, dict) else {}
            delta = str(payload.get("delta") or "")
            if event.kind == "delta.thinking":
                state, _ = advance(state, Chunk("thinking", delta))
            elif event.kind == "delta.text":
                state, _ = advance(state, Chunk("text", delta))
        reason = "The console restarted while this reply was streaming."
        state, _ = advance(state, Chunk("error", reason))
        _complete(
            database,
            message_id,
            state=state,
            routing=None,
            usage=None,
            cost=None,
            finish_reason="error",
            remote_job_id=None,
            halt=reason,
            now=now,
        )
    return len(ids)


# --- The page's stream ---------------------------------------------------------------------------


def events_after(
    database: Database, conversation_id: str, *, after_id: int, limit: int = 500
) -> list[tuple[int, str, dict[str, Any]]]:
    """Every persisted event of the conversation after ``after_id``, ascending."""
    with database.read() as session:
        rows = session.execute(
            select(MessageEvent.id, MessageEvent.kind, MessageEvent.payload)
            .join(Message, Message.id == MessageEvent.message_id)
            .where(Message.conversation_id == conversation_id, MessageEvent.id > after_id)
            .order_by(MessageEvent.id)
            .limit(limit)
        ).all()
    return [(int(row[0]), str(row[1]), dict(row[2] or {})) for row in rows]


def sse_frame(event_id: int, kind: str, payload: Mapping[str, Any]) -> str:
    """One SSE frame in the suite's event envelope; the frame ``id`` is the row id."""
    return format_frame(
        Event(sequence=event_id, type=kind, payload=dict(payload)), generator=_GENERATOR
    )


def heartbeat_frame() -> str:
    """A comment frame, so an idle stream is not closed by an intermediary."""
    return f": heartbeat {datetime.now(UTC).isoformat()}\n\n"


# --- The runner ----------------------------------------------------------------------------------


@dataclass
class ChatRunner:
    """A small thread pool for replies, which outlive the request that started them.

    ``join`` exists for tests and for an orderly shutdown; the console never waits on a reply.
    """

    max_workers: int = 2
    _executor: ThreadPoolExecutor = field(init=False)
    _futures: set[Future[None]] = field(init=False, default_factory=set)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        """Create the pool."""
        self._executor = ThreadPoolExecutor(self.max_workers, thread_name_prefix="wr-gym-chat")

    def submit(self, function: Callable[..., None], /, *args: Any, **kwargs: Any) -> Future[None]:  # noqa: ANN401
        """Run ``function`` on the pool."""
        future = self._executor.submit(function, *args, **kwargs)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._forget)
        return future

    def _forget(self, future: Future[None]) -> None:
        with self._lock:
            self._futures.discard(future)

    def join(self, timeout: float | None = 30.0) -> None:
        """Wait for every reply in flight."""
        with self._lock:
            pending = set(self._futures)
        wait(pending, timeout=timeout)

    def shutdown(self) -> None:
        """Stop accepting replies; in-flight ones end with the process."""
        self._executor.shutdown(wait=False, cancel_futures=True)
