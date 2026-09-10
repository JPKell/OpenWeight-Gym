"""weightroom.domain.guard — ADR-0124's five conditions, its never-writable tables, and the
statement they are applied to. No I/O: the domain-purity contract.

A raw write into another application's database passes five conditions or does not happen, and a
named set of tables is never written from WeightRoomGym at all
([ADR-0124](../../../docs/adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)).
[ADR-0133](../../../docs/adr/0133-the-guard-follows-foreign-keys-observes-stopped-twice-and-binds-a-write-to-its-dry-run.md)
adds that a table reached through the database's own foreign-key actions is written too, that
*stopped* is the unit and the port together, and that a write is bound to the dry run it showed.
Everything here is a pure function of what ``services/db_guard.py`` observed — the unit's state and
the port, the backup, the dry run's counts, the names the operator typed, the audit row — so each
condition fails alone in a unit test. The service observes; this module decides.

**The statement is read by a lexer, not a parser.** It knows strings, quoted identifiers, comments
and PostgreSQL's dollar quotes, so a ``;`` or a keyword inside one is never taken for one outside,
and it refuses what it cannot close rather than guessing. From the tokens it takes the leading
keyword (for ``WITH``, the statement the common table expressions lead into), every table named
after ``FROM``, ``JOIN`` and ``USING``, and the tables written after ``INSERT INTO``, ``UPDATE``,
``DELETE FROM``, ``REPLACE INTO`` and ``MERGE INTO`` wherever they sit — so a PostgreSQL
data-modifying CTE inside a ``SELECT`` is a write. The lock is applied to the written tables, which
come from those five patterns alone, and to what the foreign keys reach from them; the wider list of
named tables decides only what the operator is asked to type.
"""

from __future__ import annotations

import hashlib
import re
from collections import deque
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal

from baseaicore import SuiteError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "CONDITION_TITLES",
    "NEVER_WRITABLE",
    "STOPPED_UNIT_STATES",
    "WRITE_VERBS",
    "Condition",
    "ForeignKey",
    "GuardAppRunning",
    "GuardAuditFailed",
    "GuardBackupFailed",
    "GuardDryRunFailed",
    "GuardError",
    "GuardStatementRefused",
    "GuardTableLocked",
    "GuardTableMismatch",
    "LockClass",
    "Reach",
    "Statement",
    "Token",
    "application_stopped",
    "checklist",
    "classify",
    "dry_run_id",
    "lock_for",
    "reach",
    "require_read",
    "require_writable",
    "require_write",
    "tokenize",
    "typed_mismatch",
]

# --- Refusals ------------------------------------------------------------------------------------


class GuardError(SuiteError):
    """A refusal by the guard; never raised itself, only through one of the codes below.

    ``details`` always carries ``condition`` — ADR-0124's number, 1 to 5, for the condition that
    failed, or ``None`` for ``GUARD_TABLE_LOCKED`` and ``GUARD_STATEMENT_REFUSED``, which no
    changed fact satisfies (ADR-0133 rule 6) — and ``adr``, the record being enforced.
    """

    condition: ClassVar[int | None] = None

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        """Build the refusal with its condition number beside the caller's evidence."""
        super().__init__(
            message, details={"condition": self.condition, "adr": "ADR-0124", **(details or {})}
        )


class GuardAppRunning(GuardError):
    """Condition 1: the unit is running, or something answers on the application's port."""

    code: ClassVar[str] = "GUARD_APP_RUNNING"
    condition: ClassVar[int | None] = 1


class GuardBackupFailed(GuardError):
    """Condition 2: the backup could not be taken, so nothing was written."""

    code: ClassVar[str] = "GUARD_BACKUP_FAILED"
    condition: ClassVar[int | None] = 2


class GuardDryRunFailed(GuardError):
    """Condition 3: the dry run errored, or no longer matches the one the operator was shown."""

    code: ClassVar[str] = "GUARD_DRY_RUN_FAILED"
    condition: ClassVar[int | None] = 3


class GuardTableMismatch(GuardError):
    """Condition 4: the typed names are not exactly the tables the statement names."""

    code: ClassVar[str] = "GUARD_TABLE_MISMATCH"
    condition: ClassVar[int | None] = 4


class GuardAuditFailed(GuardError):
    """Condition 5: the ``pending`` audit row could not be written, so the statement did not run."""

    code: ClassVar[str] = "GUARD_AUDIT_FAILED"
    condition: ClassVar[int | None] = 5


class GuardTableLocked(GuardError):
    """A table ADR-0124 never lets WeightRoomGym write, named or reached by a foreign key."""

    code: ClassVar[str] = "GUARD_TABLE_LOCKED"


class GuardStatementRefused(GuardError):
    """Not one DML statement (the guard) or not one ``SELECT`` (the console), refused by name."""

    code: ClassVar[str] = "GUARD_STATEMENT_REFUSED"


# --- The never-writable tables -----------------------------------------------------------------

_APPLICATIONS: Final = ("freeweight", "loadcoach", "ideapress", "promptcadence")


@dataclass(frozen=True, slots=True)
class LockClass:
    """One row of ADR-0124's never-writable table, as data.

    Attributes:
        name: The class, as the record names it.
        reason: Why no condition makes these tables writable, in the record's words.
        tables: Per application, table names — or an ``fnmatch`` pattern for a mounted family,
            ``ledger_*`` — that the class covers.
    """

    name: str
    reason: str
    tables: Mapping[str, tuple[str, ...]]


NEVER_WRITABLE: Final[tuple[LockClass, ...]] = (
    LockClass(
        "Migration state",
        "the application's migration history owns it",
        dict.fromkeys(_APPLICATIONS, ("alembic_version",)),
    ),
    LockClass(
        "Credentials",
        "token create and revoke are the only writers; a hand-inserted hash is an unaudited "
        "credential",
        dict.fromkeys(_APPLICATIONS, ("api_tokens",)),
    ),
    LockClass(
        "Runtime settings rows",
        "the application's PUT /settings is the audited path, and WeightRoomGym uses it",
        dict.fromkeys(_APPLICATIONS, ("settings",)),
    ),
    LockClass(
        "Subject identity, hashed",
        "a row hashed into a fingerprint or subject that is edited becomes a lie about every "
        "result that cites it",
        {
            "freeweight": (
                "machines",
                "models",
                "model_descriptors",
                "runtime_profiles",
                "adapters",
            ),
            "loadcoach": ("models", "runtime_profiles", "adapters"),
        },
    ),
    LockClass(
        "Queue and lease state",
        "the worker's recovery pass reasons about these rows; a hand edit is a state the state "
        "machine never produced",
        {
            "loadcoach": ("jobs", "job_attempts", "residency"),
            "ideapress": ("stage_runs",),
            "promptcadence": ("trajectories", "threads", "turns"),
        },
    ),
    LockClass(
        "Governance and decision records",
        "approved and denied alike are the record; an edited record is not a record",
        {
            "loadcoach": ("routing_decisions", "routing_candidates"),
            "ideapress": ("egress_decisions",),
            "promptcadence": (
                "execution_intents",
                "plan_approvals",
                "approval_requests",
                "deviations",
                "egress_decisions",
            ),
        },
    ),
    LockClass(
        "Money",
        "store usage, derive cost; the ledger is append-only",
        {"ideapress": ("ledger_*",), "promptcadence": ("ledger_*",)},
    ),
    LockClass(
        "Event logs",
        "each is replayed over SSE by sequence; a gap or an edit corrupts replay",
        {
            "freeweight": ("run_events",),
            "loadcoach": ("job_events",),
            "ideapress": ("stage_events",),
            "promptcadence": ("events",),
        },
    ),
    LockClass(
        "Engine catalog",
        "the database engine's own bookkeeping; sqlite_sequence is what stops an id being reused "
        "(ADR-0133 rule 2)",
        dict.fromkeys(_APPLICATIONS, ("sqlite_*", "pg_*")),
    ),
)
"""ADR-0124's table, class by class, plus ADR-0133's engine catalog. A test compares the first
eight against the record's own Markdown and every name against the fixture databases' tables."""


def lock_for(app: str, table: str) -> LockClass | None:
    """The class that makes ``table`` never writable in ``app``, or ``None`` when it is writable.

    Args:
        app: One of the four applications.
        table: A table name, compared case-insensitively — both engines fold an unquoted name,
            and a quoted ``"API_TOKENS"`` is refused rather than argued about.

    Returns:
        The :class:`LockClass`, or ``None``.
    """
    name = table.lower()
    for lock in NEVER_WRITABLE:
        if any(fnmatchcase(name, pattern) for pattern in lock.tables.get(app, ())):
            return lock
    return None


# --- The lexer ---------------------------------------------------------------------------------

type TokenKind = Literal["word", "identifier", "string", "number", "parameter", "symbol"]


@dataclass(frozen=True, slots=True)
class Token:
    """One lexical token.

    Attributes:
        kind: ``word`` (a keyword or an unquoted name), ``identifier`` (a quoted name),
            ``string``, ``number``, ``parameter`` or ``symbol``.
        text: The token; a quoted identifier or string without its quotes.
    """

    kind: TokenKind
    text: str

    @property
    def keyword(self) -> str:
        """The upper-cased text of a ``word``, or ``""`` for anything else."""
        return self.text.upper() if self.kind == "word" else ""

    def is_symbol(self, text: str) -> bool:
        """Whether this is the punctuation ``text``."""
        return self.kind == "symbol" and self.text == text


_WORD: Final = re.compile(r"[^\W\d]\w*(?:\$\w*)*")
_NUMBER: Final = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_DOLLAR_TAG: Final = re.compile(r"\$(?:[^\W\d]\w*)?\$")
_PARAMETER: Final = re.compile(r"\?\d*|[:@$][\w]+")


def _refuse(what: str) -> GuardStatementRefused:
    return GuardStatementRefused(
        f"The statement holds {what}; the guard refuses a statement it cannot read exactly.",
        details={"reason": what},
    )


def _quoted(sql: str, start: int, quote: str, *, backslash: bool = False) -> tuple[str, int]:
    """Read a quoted run from ``sql[start]``; a doubled quote is one quote. Returns text, end."""
    parts: list[str] = []
    index = start + 1
    while index < len(sql):
        char = sql[index]
        if backslash and char == "\\":
            parts.append(sql[index : index + 2])
            index += 2
            continue
        if char == quote:
            if sql.startswith(quote * 2, index):
                parts.append(quote)
                index += 2
                continue
            return "".join(parts), index + 1
        parts.append(char)
        index += 1
    raise _refuse(f"an unterminated {quote}…{quote}")


def tokenize(sql: str) -> tuple[Token, ...]:
    """Split ``sql`` into tokens, dropping whitespace and comments.

    Args:
        sql: The text as submitted.

    Returns:
        The tokens, in order.

    Raises:
        GuardStatementRefused: A string, quoted identifier, comment or dollar quote is not closed,
            or a block comment nests another — SQLite ends it at the first ``*/`` and PostgreSQL
            at the matching one, so the two engines would not run the same statement.
    """
    tokens: list[Token] = []
    index = 0
    while index < len(sql):
        char = sql[index]
        if char.isspace():
            index += 1
        elif sql.startswith("--", index):
            end = sql.find("\n", index)
            index = len(sql) if end < 0 else end + 1
        elif sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end < 0:
                raise _refuse("an unterminated /* comment")
            if "/*" in sql[index + 2 : end]:
                raise _refuse("a nested /* comment, which SQLite and PostgreSQL end differently")
            index = end + 2
        elif char == "'":
            # PostgreSQL's E'…' string is the one place a backslash escapes a quote.
            escaped = bool(tokens) and tokens[-1] in (Token("word", "E"), Token("word", "e"))
            escaped = escaped and index > 0 and sql[index - 1] in "Ee"
            text, index = _quoted(sql, index, "'", backslash=escaped)
            if escaped:
                tokens.pop()
            tokens.append(Token("string", text))
        elif char in '"`':
            text, index = _quoted(sql, index, char)
            tokens.append(Token("identifier", text))
        elif char == "[":
            end = sql.find("]", index + 1)
            if end < 0:
                raise _refuse("an unterminated [identifier]")
            tokens.append(Token("identifier", sql[index + 1 : end]))
            index = end + 1
        elif char == "$" and (tag := _DOLLAR_TAG.match(sql, index)):
            end = sql.find(tag.group(0), tag.end())
            if end < 0:
                raise _refuse("an unterminated dollar-quoted string")
            tokens.append(Token("string", sql[tag.end() : end]))
            index = end + len(tag.group(0))
        elif word := _WORD.match(sql, index):
            tokens.append(Token("word", word.group(0)))
            index = word.end()
        elif number := _NUMBER.match(sql, index):
            tokens.append(Token("number", number.group(0)))
            index = number.end()
        elif parameter := _PARAMETER.match(sql, index):
            tokens.append(Token("parameter", parameter.group(0)))
            index = parameter.end()
        else:
            tokens.append(Token("symbol", char))
            index += 1
    return tuple(tokens)


# --- The statement -----------------------------------------------------------------------------

WRITE_VERBS: Final[frozenset[str]] = frozenset({"INSERT", "UPDATE", "DELETE", "REPLACE", "MERGE"})
"""The statements the guard runs. Everything else but ``SELECT`` is refused by its keyword."""

_REFUSAL_REASONS: Final[Mapping[str, str]] = {
    **dict.fromkeys(
        ("CREATE", "ALTER", "DROP", "TRUNCATE", "REINDEX", "COMMENT", "GRANT", "REVOKE"),
        "the schema is the owning application's migration history, and a hand-edited schema is "
        "a database that application can no longer migrate",
    ),
    **dict.fromkeys(
        ("PRAGMA", "VACUUM", "ANALYZE", "SET", "RESET", "ATTACH", "DETACH", "COPY", "LOAD"),
        "engine settings, files and maintenance belong to the owning application's own db verbs, "
        "offered as curated operations",
    ),
    **dict.fromkeys(
        ("BEGIN", "COMMIT", "ROLLBACK", "END", "SAVEPOINT", "RELEASE", "START", "ABORT"),
        "the guard owns the transaction the one statement runs in",
    ),
}

_ENDS_REFERENCE: Final[frozenset[str]] = frozenset(
    {
        *("WHERE", "SET", "VALUES", "DEFAULT", "SELECT", "ON", "USING", "JOIN", "INNER", "LEFT"),
        *("RIGHT", "FULL", "CROSS", "NATURAL", "OUTER", "GROUP", "ORDER", "HAVING", "LIMIT"),
        *("OFFSET", "FETCH", "FOR", "UNION", "INTERSECT", "EXCEPT", "RETURNING", "WINDOW", "AS"),
        *("INDEXED", "NOT", "DO", "WHEN", "THEN", "ELSE", "END", "INTO", "WITH", "AND", "OR"),
        *("TABLESAMPLE", "UPDATE", "DELETE", "INSERT", "MERGE", "MATCHED", "ORDINALITY"),
    }
)
"""Keywords that end a table reference — never a table, never an alias."""

_NOT_CALLS: Final[frozenset[str]] = frozenset(
    {
        *("IN", "EXISTS", "FROM", "JOIN", "AS", "ANY", "ALL", "SOME", "ARRAY", "LATERAL", "SELECT"),
        *("WHERE", "AND", "OR", "NOT", "ON", "VALUES", "USING", "SET", "THEN", "ELSE", "WHEN"),
        *("RETURNING", "INTO", "WITH", "UNION", "INTERSECT", "EXCEPT", "MATERIALIZED", "CASE"),
        *("BY", "HAVING", "LIMIT", "OFFSET", "DISTINCT", "IS", "RECURSIVE", "UPDATE", "DELETE"),
        *("INSERT", "DO", "LIKE", "BETWEEN", "END", "RETURN", "OVER", "FILTER", "WITHIN"),
    }
)
"""Words before ``(`` that open a subquery or a list rather than a function call — inside a call
(``extract(epoch FROM created_at)``) a ``FROM`` names no table."""

_CONFLICT_WORDS: Final[frozenset[str]] = frozenset(
    {"INSERT", "REPLACE", "MERGE", "IGNORE", "ABORT", "FAIL", "ROLLBACK"}
)


@dataclass(frozen=True, slots=True)
class Statement:
    """One statement, as the guard reads it.

    Attributes:
        text: The statement as submitted, whitespace-trimmed — the text shown beside the dry-run
            count, run, and written on the audit row.
        verb: The leading keyword; for ``WITH``, the keyword of the statement it leads into.
        tables: Every table the statement names, in order of first appearance, CTE names
            excluded, unquoted names folded to lower case as both engines fold them.
        written: The tables it inserts into, updates or deletes from — a subset of ``tables``.
        events: The foreign-key events its writes can fire: ``DELETE`` for a delete, a replace or a
            merge, ``UPDATE`` for an update, a merge or an upsert. A plain insert fires none.
    """

    text: str
    verb: str
    tables: tuple[str, ...]
    written: tuple[str, ...]
    events: frozenset[str]


def _fold(token: Token) -> str:
    return token.text.lower() if token.kind == "word" else token.text


def _is_name(token: Token) -> bool:
    return token.kind == "identifier" or (
        token.kind == "word" and token.keyword not in _ENDS_REFERENCE
    )


def _after_group(tokens: Sequence[Token], index: int) -> int:
    """The index after the parenthesis group opening at ``tokens[index]``."""
    depth = 0
    for position in range(index, len(tokens)):
        if tokens[position].is_symbol("("):
            depth += 1
        elif tokens[position].is_symbol(")"):
            depth -= 1
            if depth == 0:
                return position + 1
    return len(tokens)


def _dotted(tokens: Sequence[Token], index: int) -> tuple[str, int]:
    """Read ``schema.table`` (or ``table``) from ``index``; the last part is the table."""
    name = _fold(tokens[index])
    index += 1
    while (
        index + 1 < len(tokens)
        and tokens[index].is_symbol(".")
        and tokens[index + 1].kind in ("word", "identifier")
    ):
        name = _fold(tokens[index + 1])
        index += 2
    return name, index


def _name_at(tokens: Sequence[Token], index: int) -> str | None:
    if index < len(tokens) and _is_name(tokens[index]):
        return _dotted(tokens, index)[0]
    return None


def _table_list(tokens: Sequence[Token], index: int, *, many: bool) -> list[str]:
    """The tables in a ``FROM``/``JOIN``/``USING`` reference starting at ``index``."""
    names: list[str] = []
    count = len(tokens)
    while index < count:
        while index < count and tokens[index].keyword in ("ONLY", "LATERAL"):
            index += 1
        if index >= count:
            break
        if tokens[index].is_symbol("("):
            index = _after_group(tokens, index)  # a subquery: its own FROM is scanned on its own
        elif _is_name(tokens[index]):
            name, index = _dotted(tokens, index)
            if index < count and tokens[index].is_symbol("("):
                index = _after_group(tokens, index)  # a table-valued function, not a table
            else:
                names.append(name)
        else:
            break
        if index < count and tokens[index].keyword == "AS":
            index += 1
        if index < count and _is_name(tokens[index]):
            index += 1
            if index < count and tokens[index].is_symbol("("):
                index = _after_group(tokens, index)  # PostgreSQL's alias column list
        if many and index < count and tokens[index].is_symbol(","):
            index += 1
            continue
        break
    return names


def _cte_names(tokens: Sequence[Token]) -> frozenset[str]:
    names: set[str] = set()
    count = len(tokens)
    for start, token in enumerate(tokens):
        if token.keyword != "WITH":
            continue
        index = start + 1
        if index < count and tokens[index].keyword == "RECURSIVE":
            index += 1
        while index < count and tokens[index].kind in ("word", "identifier"):
            name = _fold(tokens[index])
            index += 1
            if index < count and tokens[index].is_symbol("("):
                index = _after_group(tokens, index)
            if index >= count or tokens[index].keyword != "AS":
                break
            names.add(name)
            index += 1
            while index < count and tokens[index].keyword in ("NOT", "MATERIALIZED"):
                index += 1
            if index < count and tokens[index].is_symbol("("):
                index = _after_group(tokens, index)
            if index < count and tokens[index].is_symbol(","):
                index += 1
                continue
            break
    return frozenset(names)


def _scan(tokens: Sequence[Token]) -> tuple[list[tuple[str, bool]], set[str]]:
    """Every ``(table, written)`` in order, and the foreign-key events the writes fire."""
    found: list[tuple[str, bool]] = []
    events: set[str] = set()
    calls: list[bool] = []
    for index, token in enumerate(tokens):
        previous = tokens[index - 1] if index else Token("symbol", "")
        if token.is_symbol("("):
            calls.append(previous.kind == "word" and previous.keyword not in _NOT_CALLS)
            continue
        if token.is_symbol(")"):
            if calls:
                calls.pop()
            continue
        word = token.keyword
        in_call = bool(calls) and calls[-1]
        if word in ("FROM", "JOIN") and not in_call:
            deleting = word == "FROM" and previous.keyword == "DELETE"
            if deleting:
                events.add("DELETE")
            many = word == "FROM" and not deleting
            found.extend((one, deleting) for one in _table_list(tokens, index + 1, many=many))
        elif word == "USING" and not in_call:
            if index + 1 < len(tokens) and not tokens[index + 1].is_symbol("("):
                found.extend((one, False) for one in _table_list(tokens, index + 1, many=True))
        elif word == "INTO" and previous.keyword in _CONFLICT_WORDS:
            name = _name_at(tokens, index + 1)
            if name is not None:
                found.append((name, True))
            if previous.keyword in ("REPLACE", "MERGE"):
                events.add("DELETE")  # REPLACE INTO and INSERT OR REPLACE INTO delete the old row
            if previous.keyword == "MERGE":
                events.add("UPDATE")
        elif word == "UPDATE":
            if previous.keyword == "DO":
                events.add("UPDATE")  # INSERT … ON CONFLICT DO UPDATE: an upsert updates rows
                continue
            if previous.keyword in ("FOR", "KEY", "ON"):
                continue  # SELECT … FOR [NO KEY] UPDATE locks rows; it writes none
            position = index + 1
            if position < len(tokens) and tokens[position].keyword == "OR":
                position += 2
            if position < len(tokens) and tokens[position].keyword == "ONLY":
                position += 1
            name = _name_at(tokens, position)
            if name is not None:
                found.append((name, True))
                events.add("UPDATE")
    return found, events


def _leading_verb(tokens: Sequence[Token]) -> str:
    index = 0
    while index < len(tokens) and tokens[index].is_symbol("("):
        index += 1
    if index == len(tokens) or tokens[index].kind != "word":
        raise GuardStatementRefused(
            "The statement does not begin with a keyword.", details={"keyword": None}
        )
    verb = tokens[index].keyword
    if verb != "WITH":
        return verb
    depth = 0
    for token in tokens[index + 1 :]:
        if token.is_symbol("("):
            depth += 1
        elif token.is_symbol(")"):
            depth -= 1
        elif depth == 0 and token.keyword in {"SELECT", "VALUES", *WRITE_VERBS}:
            return token.keyword
    raise GuardStatementRefused("A WITH that leads into no statement.", details={"keyword": "WITH"})


def classify(sql: str) -> Statement:
    """Read one statement: its verb, the tables it names and the tables it writes.

    Args:
        sql: The text as submitted. One trailing ``;`` is allowed.

    Returns:
        The :class:`Statement`. A ``SELECT`` and a write both classify; which one a route accepts
        is :func:`require_read` or :func:`require_write`.

    Raises:
        GuardStatementRefused: The text is empty, holds more than one statement, cannot be read
            exactly (:func:`tokenize`), or begins with anything but ``SELECT``, ``WITH`` or one of
            :data:`WRITE_VERBS` — ``CREATE``, ``ALTER``, ``DROP``, ``PRAGMA``, ``VACUUM``,
            ``ATTACH``, ``BEGIN`` and every other keyword are refused by name (ADR-0124).
    """
    text = sql.strip()
    tokens = list(tokenize(text))
    if tokens and tokens[-1].is_symbol(";"):
        tokens.pop()
    if not tokens:
        raise GuardStatementRefused("The statement is empty.", details={"keyword": None})
    if any(token.is_symbol(";") for token in tokens):
        raise GuardStatementRefused(
            "One statement per guarded write or console query (ADR-0124): this text holds more "
            "than one. A second statement is a second guard.",
            details={"reason": "multiple_statements"},
        )
    verb = _leading_verb(tokens)
    if verb != "SELECT" and verb not in WRITE_VERBS:
        reason = _REFUSAL_REASONS.get(verb, "only SELECT reads and only DML writes")
        raise GuardStatementRefused(
            f"{verb} is refused by name from WeightRoomGym (ADR-0124): {reason}.",
            details={"keyword": verb},
        )
    ctes = _cte_names(tokens)
    found, events = _scan(tokens)
    kept = [(name, written) for name, written in found if name not in ctes]
    return Statement(
        text=text,
        verb=verb,
        tables=tuple(dict.fromkeys(name for name, _written in kept)),
        written=tuple(dict.fromkeys(name for name, written in kept if written)),
        events=frozenset(events),
    )


def require_read(statement: Statement) -> Statement:
    """Refuse anything the SQL console may not run: it runs one ``SELECT``, on a read-only line.

    Raises:
        GuardStatementRefused: The statement writes — including a PostgreSQL data-modifying CTE
            under a ``SELECT``.
    """
    if statement.verb != "SELECT" or statement.written:
        raise GuardStatementRefused(
            f"The console runs one SELECT on a read-only connection; {statement.verb} writes "
            "and goes through the guard (ADR-0124).",
            details={"keyword": statement.verb, "tables_written": list(statement.written)},
        )
    return statement


def require_write(statement: Statement) -> Statement:
    """Refuse anything the guard may not run: one statement whose own verb is the write.

    Raises:
        GuardStatementRefused: The verb is ``SELECT`` — a query reports rows returned, not rows
            written, so its dry-run count would describe nothing — or it names no written table.
    """
    if statement.verb not in WRITE_VERBS or not statement.written:
        raise GuardStatementRefused(
            f"The guard runs one INSERT, UPDATE, DELETE, REPLACE or MERGE whose own verb is the "
            f"write; this is a {statement.verb}. A SELECT belongs in the console.",
            details={"keyword": statement.verb},
        )
    return statement


# --- What a write reaches ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ForeignKey:
    """One foreign key, as the database reports it.

    Attributes:
        child: The table holding the key.
        parent: The table it refers to.
        on_delete: The ``ON DELETE`` action, upper case, or ``""`` for none.
        on_update: The ``ON UPDATE`` action, upper case, or ``""`` for none.
    """

    child: str
    parent: str
    on_delete: str = ""
    on_update: str = ""


@dataclass(frozen=True, slots=True)
class Reach:
    """A table a write changes through a foreign-key action (ADR-0133 rule 1).

    Attributes:
        table: The table reached.
        path: From the written table to this one, ``("runs", "run_events")``.
        action: What the database does to it, ``"ON DELETE CASCADE"``.
    """

    table: str
    path: tuple[str, ...]
    action: str

    def as_json(self) -> dict[str, Any]:
        """The dry-run response's shape."""
        return {"table": self.table, "path": list(self.path), "action": self.action}


_ACTING: Final = frozenset({"CASCADE", "SET NULL", "SET DEFAULT"})


def reach(
    written: Sequence[str], events: frozenset[str], keys: Sequence[ForeignKey]
) -> tuple[Reach, ...]:
    """Every table a write reaches through the database's own foreign-key actions.

    Args:
        written: The tables the statement writes.
        events: The events it fires (:attr:`Statement.events`).
        keys: Every foreign key in the database.

    Returns:
        Each reached table once, by its shortest path, written tables excluded. A cascaded delete
        is followed onward as a delete; a row nulled, defaulted or cascade-updated is followed
        onward as an update. Actions that change no row — ``RESTRICT``, ``NO ACTION`` — reach
        nothing: they make the dry run fail instead.
    """
    written_set = set(written)
    queue: deque[tuple[str, str, tuple[str, ...]]] = deque(
        (table, event, (table,)) for table in written for event in sorted(events)
    )
    seen = {(table, event) for table, event, _path in queue}
    found: dict[str, Reach] = {}
    while queue:
        table, event, path = queue.popleft()
        for key in keys:
            action = (key.on_delete if event == "DELETE" else key.on_update).upper()
            if key.parent != table or action not in _ACTING:
                continue
            onward = (*path, key.child)
            if key.child not in written_set and key.child not in found:
                found[key.child] = Reach(key.child, onward, f"ON {event} {action}")
            next_event = "DELETE" if event == "DELETE" and action == "CASCADE" else "UPDATE"
            if (key.child, next_event) not in seen:
                seen.add((key.child, next_event))
                queue.append((key.child, next_event, onward))
    return tuple(found.values())


def require_writable(app: str, statement: Statement, reached: Sequence[Reach] = ()) -> None:
    """Refuse a write into a never-writable table, named or reached.

    Args:
        app: The application whose database it is.
        statement: The statement.
        reached: What its foreign keys reach (:func:`reach`).

    Raises:
        GuardTableLocked: A written or reached table is on :data:`NEVER_WRITABLE`; the message
            names it, its class and the record, and ``details`` carries the path for a reach.
    """
    for table in statement.written:
        lock = lock_for(app, table)
        if lock is not None:
            raise GuardTableLocked(
                f"{table} is never writable from WeightRoomGym (ADR-0124) — {lock.name}: "
                f"{lock.reason}.",
                details={"app": app, "table": table, "class": lock.name},
            )
    for one in reached:
        lock = lock_for(app, one.table)
        if lock is not None:
            raise GuardTableLocked(
                f"This statement reaches {one.table} through {' → '.join(one.path)} "
                f"({one.action}), and {one.table} is never writable from WeightRoomGym "
                f"(ADR-0124, ADR-0133) — {lock.name}: {lock.reason}.",
                details={
                    "app": app,
                    "table": one.table,
                    "class": lock.name,
                    "via": list(one.path),
                    "action": one.action,
                },
            )


# --- The five conditions -----------------------------------------------------------------------

type Verdict = Literal["pass", "fail", "pending"]

CONDITION_TITLES: Final[Mapping[int, str]] = {
    1: "The application is stopped",
    2: "A backup was taken first",
    3: "A dry run counted the rows, shown beside the statement",
    4: "Every table in the statement was typed",
    5: "The audit row is pending before the statement runs",
}

STOPPED_UNIT_STATES: Final[frozenset[str]] = frozenset(
    {"inactive", "failed", "absent", "unsupported"}
)
"""Unit states that are not a running process (ADR-0133 rule 3). ``activating`` and
``deactivating`` are not among them: a process is still there."""


@dataclass(frozen=True, slots=True)
class Condition:
    """One of the five, with its verdict and the fact behind it.

    Attributes:
        number: ADR-0124's number.
        title: What the condition asks.
        verdict: ``pass``, ``fail`` or ``pending`` (not yet observable — a backup is taken when the
            write runs, never at a dry run).
        evidence: The observation, in words the dialog shows.
    """

    number: int
    title: str
    verdict: Verdict
    evidence: str

    def as_json(self) -> dict[str, Any]:
        """The checklist entry of ``POST …/db/write/dry-run``."""
        return {
            "condition": self.number,
            "title": self.title,
            "verdict": self.verdict,
            "evidence": self.evidence,
        }


def application_stopped(*, unit_state: str, port_open: bool | None) -> bool:
    """Condition 1: no process under the unit, and nothing answering on the port.

    Args:
        unit_state: The unit's state in the console's vocabulary.
        port_open: Whether a connection to the application's port was accepted; ``None`` when it
            could not be tried, which proves nothing and so is not stopped.

    Returns:
        Whether both observations say stopped.
    """
    return unit_state in STOPPED_UNIT_STATES and port_open is False


def typed_mismatch(
    tables: Sequence[str], typed: Sequence[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Condition 4: which tables were not typed, and which typed names the statement lacks.

    Args:
        tables: The tables the statement names.
        typed: What the operator typed — compared exactly, case included, after trimming.

    Returns:
        ``(missing, extra)``, each sorted; both empty is a pass.
    """
    wanted = set(tables)
    given = {name.strip() for name in typed if name.strip()}
    return tuple(sorted(wanted - given)), tuple(sorted(given - wanted))


def checklist(
    *,
    unit_state: str,
    port_open: bool | None,
    backup_path: str | None = None,
    backup_error: str | None = None,
    dry_run_count: int | None = None,
    dry_run_error: str | None = None,
    tables: Sequence[str] = (),
    typed: Sequence[str] | None = None,
    audit_id: str | None = None,
    audit_error: str | None = None,
) -> tuple[Condition, ...]:
    """The five conditions' verdicts over what has been observed so far.

    Args:
        unit_state: The unit's state.
        port_open: Whether the port accepted a connection; ``None`` if it could not be tried.
        backup_path: Where the backup was written, once it has been.
        backup_error: Why the backup failed.
        dry_run_count: The rows the rolled-back statement reported.
        dry_run_error: The dry run's error, verbatim.
        tables: The tables the statement names.
        typed: The names the operator typed; ``None`` before anything was typed.
        audit_id: The ``pending`` audit row, once written.
        audit_error: Why it could not be written.

    Returns:
        Conditions 1 to 5 in order.
    """
    port = "unknown" if port_open is None else "open" if port_open else "closed"
    stopped = application_stopped(unit_state=unit_state, port_open=port_open)
    first: Verdict = "pass" if stopped else "fail"
    second: tuple[Verdict, str] = (
        ("fail", backup_error)
        if backup_error
        else ("pass", backup_path)
        if backup_path
        else ("pending", "taken when the write runs, before the statement")
    )
    third: tuple[Verdict, str] = (
        ("fail", dry_run_error)
        if dry_run_error is not None
        else ("pass", f"{dry_run_count} rows")
        if dry_run_count is not None
        else ("pending", "not run yet")
    )
    if typed is None:
        fourth: tuple[Verdict, str] = ("pending", "type " + ", ".join(tables))
    else:
        missing, extra = typed_mismatch(tables, typed)
        problems = [f"not typed: {', '.join(missing)}"] if missing else []
        problems += [f"not in the statement: {', '.join(extra)}"] if extra else []
        fourth = ("fail", "; ".join(problems)) if problems else ("pass", ", ".join(sorted(tables)))
    fifth: tuple[Verdict, str] = (
        ("fail", audit_error)
        if audit_error
        else ("pass", audit_id)
        if audit_id
        else ("pending", "written just before the statement runs")
    )
    verdicts = ((first, f"unit {unit_state}, port {port}"), second, third, fourth, fifth)
    return tuple(
        Condition(number, CONDITION_TITLES[number], verdict, evidence)
        for number, (verdict, evidence) in enumerate(verdicts, start=1)
    )


def dry_run_id(*, app: str, statement: str, count: int, reached: Mapping[str, int | None]) -> str:
    """The digest that binds a write to the dry run it showed (ADR-0133 rule 5).

    Not a credential — the session is — only a proof that what the operator was shown is still
    what would happen: the same application, the same text, the same count, the same changes to
    the reached tables.

    Args:
        app: The application.
        statement: The statement text, exactly as run.
        count: The rows the statement itself reported.
        reached: Each reached table's change in row count, ``None`` where it is not counted.

    Returns:
        32 hexadecimal characters.
    """
    material = "\x1f".join(
        [app, statement, str(count), *(f"{table}={reached[table]}" for table in sorted(reached))]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
