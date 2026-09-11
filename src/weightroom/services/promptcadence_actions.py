"""weightroom.services.promptcadence_actions — what an operator does to PromptCadence (row WP1).

Submit a trajectory, cancel one, grant or deny its pending approval: each is one call to
PromptCadence's own API, which validates the request and refuses in its own words — nothing here
re-decides what PromptCadence decides. Two things are done here and nowhere else: translating a
form's text fields into the wire body (a decimal amount into ``nanos``, a blank field into an
absent key), and ADR-0049's precondition that the console's token holds ``approve`` before a grant
or a denial is attempted at all.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import DataClassification, SuiteError

from weightroom.services.app_api import call
from weightroom.services.promptcadence_pages import APP, segment, tiers_api, tools_api

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings

__all__ = [
    "CLASSIFICATIONS",
    "PARTIAL_PRICING",
    "TrajectoryFormInvalid",
    "budget_raise",
    "cancel",
    "decide",
    "require_approve_scope",
    "submission_body",
    "submission_options",
    "submit",
]

CLASSIFICATIONS: Final[tuple[str, ...]] = tuple(level.value for level in DataClassification)
PARTIAL_PRICING: Final[tuple[str, ...]] = ("floor", "strict")
_NANOS: Final = Decimal(1_000_000_000)
_ACTION_TIMEOUT_SECONDS: Final = 30.0
_REASON_CHARS: Final = 2000


class TrajectoryFormInvalid(SuiteError):
    """A field the page sent cannot become PromptCadence's body; nothing was sent."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def _whole(label: str, raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        message = f"{label} must be a whole number; got {text!r}."
        raise TrajectoryFormInvalid(message, details={"field": label}) from exc
    if value < 1:
        message = f"{label} must be at least 1; got {value}."
        raise TrajectoryFormInvalid(message, details={"field": label})
    return value


def _money(raw: str, currency: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        message = f"The money amount must be a decimal number such as 2.50; got {text!r}."
        raise TrajectoryFormInvalid(message, details={"field": "money"}) from exc
    if not amount.is_finite() or amount <= 0:
        message = f"The money amount must be more than zero; got {text!r}."
        raise TrajectoryFormInvalid(message, details={"field": "money"})
    code = currency.strip().upper()
    if len(code) != 3 or not code.isalpha():  # noqa: PLR2004 — ISO 4217 codes are three letters
        message = f"The currency must be a three-letter code such as USD; got {currency!r}."
        raise TrajectoryFormInvalid(message, details={"field": "currency"})
    return {"currency": code, "nanos": int(amount * _NANOS)}


def submission_body(
    *,
    task: str,
    classification: str,
    project: str,
    tools: Iterable[str],
    tier: str,
    max_steps: str,
    max_turns: str,
    bypass_planning: str,
    budget_tokens: str,
    budget_money: str,
    currency: str,
    partial_pricing: str,
) -> dict[str, Any]:
    """The ``POST /trajectories`` body the New-trajectory form describes.

    ``tools`` is always sent, empty when nothing was ticked: PromptCadence reads an omitted
    allowlist as every configured tool, so leaving it out would grant what nobody chose (found at
    W6). A text field naming tools comma-separated — the form's fallback when the registry cannot be
    read — is split the same way. Every other blank field is left out, so PromptCadence's own
    default applies: an absent ``partial_pricing`` is *the configured default*, which is not the
    same as pinning either value (ADR-0069).

    Args:
        task: What the trajectory is for. Required.
        classification: ``public``, ``internal`` or ``confidential``; blank means ``confidential``
            (ADR-0046). Anything else is sent as given, for PromptCadence to refuse by name.
        project: A configured ``[budget.projects.<name>]``, or blank.
        tools: The ticked tool names (or one comma-separated field).
        tier: A tier to pin, or blank for the policy's own choice.
        max_steps: A whole number, or blank.
        max_turns: A whole number, or blank.
        bypass_planning: ``true``, ``false`` or blank for PromptCadence's decision.
        budget_tokens: A whole-number token ceiling, or blank.
        budget_money: A decimal money ceiling, or blank.
        currency: The money ceiling's three-letter currency.
        partial_pricing: ``floor``, ``strict`` or blank for the configured default.

    Returns:
        The JSON body.

    Raises:
        TrajectoryFormInvalid: The task is blank, or a number or an amount does not parse.
    """
    if not task.strip():
        message = "The task is empty; PromptCadence needs one to plan from."
        raise TrajectoryFormInvalid(message, details={"field": "task"})
    names = sorted({part.strip() for one in tools for part in one.split(",") if part.strip()})
    body: dict[str, Any] = {
        "task": task,
        "data_classification": classification.strip() or "confidential",
        "tools": names,
    }
    if project.strip():
        body["project"] = project.strip()
    if tier.strip():
        body["tier"] = tier.strip()
    for key, label, raw in (
        ("max_steps", "Max steps", max_steps),
        ("max_turns", "Max turns", max_turns),
    ):
        value = _whole(label, raw)
        if value is not None:
            body[key] = value
    if bypass_planning in {"true", "false"}:
        body["bypass_planning"] = bypass_planning == "true"
    budget: dict[str, Any] = {}
    tokens = _whole("The token budget", budget_tokens)
    if tokens is not None:
        budget["tokens"] = tokens
    money = _money(budget_money, currency)
    if money is not None:
        budget["money"] = money
    if partial_pricing in PARTIAL_PRICING:
        budget["partial_pricing"] = partial_pricing
    if budget:
        body["budget"] = budget
    return body


def submission_options(client: httpx.Client, settings: Settings) -> dict[str, list[str] | None]:
    """The registered tools and configured tiers the form offers; ``None`` for one not readable.

    Never raises: a registry that cannot be read turns its field into free text, and PromptCadence
    still refuses an unknown name as ``TOOL_NOT_FOUND`` or ``TIER_NOT_CONFIGURED``.
    """
    tools: list[str] | None
    tiers: list[str] | None
    try:
        report = tools_api(client, settings)
        tools = [
            str(one.get("name"))
            for one in report.get("tools") or []
            if isinstance(one, Mapping) and one.get("registered")
        ]
    except SuiteError:
        tools = None
    try:
        rows = tiers_api(client, settings).get("rows") or []
        tiers = [str(one.get("name")) for one in rows if isinstance(one, Mapping)]
    except SuiteError:
        tiers = None
    return {"tools": tools, "tiers": tiers}


def submit(client: httpx.Client, settings: Settings, body: Mapping[str, Any]) -> dict[str, Any]:
    """``POST /trajectories``; PromptCadence's ``202`` trajectory document.

    Raises:
        AppRefused: ``VALIDATION_ERROR``, ``CLASSIFICATION_INVALID``, ``PROJECT_UNKNOWN``,
            ``TOOL_NOT_FOUND``, ``TIER_NOT_CONFIGURED``, in PromptCadence's words.
        AppUnreachable: It did not answer.
    """
    document = call(
        client, settings, APP, "POST", "trajectories", body=dict(body),
        timeout_seconds=_ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(document) if isinstance(document, Mapping) else {}


def cancel(client: httpx.Client, settings: Settings, trajectory_id: str) -> dict[str, Any]:
    """``POST /trajectories/{id}/cancel``: at once unleased, at the next turn boundary leased.

    Raises:
        AppRefused: ``TRAJECTORY_NOT_CANCELLABLE`` for a terminal one, ``TRAJECTORY_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    document = call(
        client, settings, APP, "POST", f"trajectories/{segment(trajectory_id)}/cancel",
        timeout_seconds=_ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(document) if isinstance(document, Mapping) else {}


def require_approve_scope(settings: Settings) -> None:
    """Refuse before any call unless the console's PromptCadence token holds ``approve``.

    Granting is a scope of its own, separate from submitting (ADR-0049); a console whose token
    cannot tell is refused as one that cannot, never waved through.

    Raises:
        ApprovalScopeMissing: The token lacks ``approve``/``admin``, or its scopes cannot be read.
    """
    from weightroom.services.chat import ApprovalScopeMissing
    from weightroom.services.chat_promptcadence import token_can_approve

    allowed = token_can_approve(settings)
    if allowed is not True:
        raise ApprovalScopeMissing(
            "The console's PromptCadence token has no approve scope (ADR-0049)."
            if allowed is False
            else "Whether the console's PromptCadence token can approve could not be read.",
            details={"app": APP},
        )


def budget_raise(*, tokens: str, amount: str, currency: str) -> dict[str, Any] | None:
    """A ``ceiling_raise`` grant's ``budget`` from the form, or ``None`` when both are blank.

    Raises:
        TrajectoryFormInvalid: A number or an amount does not parse.
    """
    raised: dict[str, Any] = {}
    ceiling = _whole("The new token ceiling", tokens)
    if ceiling is not None:
        raised["tokens"] = ceiling
    money = _money(amount, currency)
    if money is not None:
        raised["money"] = money
    return raised or None


def decide(
    client: httpx.Client,
    settings: Settings,
    trajectory_id: str,
    decision: str,
    *,
    reason: str | None,
    budget: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """``POST /trajectories/{id}/approve|deny`` for the trajectory's pending request.

    Args:
        client: The pooled HTTP client.
        settings: The validated settings.
        trajectory_id: The trajectory whose pending request is resolved.
        decision: ``approve`` or ``deny``.
        reason: A denial's reason, cut to PromptCadence's 2000 characters; ignored on a grant.
        budget: A ceiling raise's ``{tokens, money}``; sent only on a grant, where PromptCadence
            requires it for a ``ceiling_raise`` and refuses it for every other kind.

    Raises:
        ValueError: ``decision`` is neither ``approve`` nor ``deny``.
        AppRefused: ``APPROVAL_INVALID_STATE``, ``VALIDATION_ERROR``, in PromptCadence's words.
        AppUnreachable: It did not answer.
    """
    if decision not in {"approve", "deny"}:
        message = f"{decision!r} is not approve or deny"
        raise ValueError(message)
    body: dict[str, Any] | None = None
    if decision == "deny" and reason:
        body = {"reason": reason[:_REASON_CHARS]}
    if decision == "approve" and budget:
        body = {"budget": dict(budget)}
    document = call(
        client, settings, APP, "POST", f"trajectories/{segment(trajectory_id)}/{decision}",
        body=body, timeout_seconds=_ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(document) if isinstance(document, Mapping) else {}
