# ADR-0114 — The runtime dependency budget is an enumerated set, not a count

**Status:** Accepted (2026-09-07)
**Amends:** [gold-standards §1.1](../standards/gold-standards.md) — the budget table is replaced by
the enumeration below, edited into the standard in this record's commit. Standards are edited;
this record is the reason.
**Relates to:** G16 (minimal dependency footprint),
[ADR-0002](0002-web-framework.md) (FastAPI), [ADR-0005](0005-database-strategy.md) (SQLAlchemy 2.0 +
Alembic), [ADR-0019](0019-python-baseline-and-config-format.md) (config is TOML),
[ADR-0020](0020-ui-rendering-strategy.md) (server-rendered HTML, no SPA),
[ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md) (an application owns its
migration history, so it declares Alembic itself),
[packaging and release standards §1.1](../standards/packaging-and-release-standards.md).
**Source:** the M9 audit (`~/ai/suite/M9_AUDIT.md`) Group 7, item Q1/G16; scheduled as row L2 of
[outstanding work §1](../roadmap/outstanding-work.md).

## Context

`gold-standards` §1.1 gave each application "`fastapi`, `uvicorn`, `typer`, `pydantic-settings`,
plus suite packages — **≤ 6 direct non-suite**", and MirrorWall 2. Every `pyproject.toml` in the
suite was read for this record. The declared counts are:

| Component | Declared non-suite runtime dependencies | Count |
|---|---|---:|
| FreeWeight | `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `alembic`, `typer`, `jinja2`, `python-multipart`, `httpx` | 10 |
| IdeaPress | the same ten | 10 |
| LoadCoach | the same, without `python-multipart` | 9 |
| PromptCadence | the same, without `python-multipart` | 9 |
| MirrorWall | `jinja2`, `starlette`, `anyio` | 3 |

So five components are nominally in breach of a standard that says "exceeding a budget requires an
ADR", and no such ADR exists. That is either five violations or one wrong number, and the code
settles it: every one of those names except one is imported by the component that declares it.
`pydantic` builds the wire models, `sqlalchemy` and `alembic` are each application's own schema and
migration history (a package may ship tables but never a migration history —
[ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)), `jinja2` is
`web/rendering.py` in all four, `httpx` is the CLI's client and the peer-application clients,
`python-multipart` is what Starlette's form parser requires for the `Form(...)`/`UploadFile` routes
FreeWeight and IdeaPress have and the other two do not. MirrorWall's `starlette` is the framework it
extends (`starlette.responses`, `.datastructures`, `.staticfiles`) and `anyio` is what its SSE and
threading helpers are built on.

Three of those names — `pydantic`, `sqlalchemy`, `alembic` — also arrive transitively through
`setspec` and `weightsdb`. Declaring them directly is not appetite; it is
[PEP 508 correctness](../standards/packaging-and-release-standards.md): a package that imports a
name and does not declare it is one intermediate release away from an `ImportError` in a clean venv.
Undeclaring them would have made the count look right and the wheel wrong.

**The one exception is `pydantic-settings`, which all four applications declare and none of them
imports.** Each application's `config.py` performs its own layered merge of defaults, file,
environment and overrides — deliberately, and each says so in its module docstring — because
`config show` has to report *which* layer produced every leaf value, and pydantic-settings' own
source machinery does not carry that provenance. The name is in the budget because the standard put
it there in 2026-08-21, and it is in four `pyproject.toml` files because the standard put it there.

## Decision

1. **The budget is an enumerated set per component, not a count.** `gold-standards` §1.1 now lists
   the exact names each component may declare. A count is a consequence of the list, reported for
   orientation, and is never the rule.

2. **A transitive dependency promoted to direct because the component imports it is not a budget
   breach.** It is required by the packaging standard. The budget exists to stop a *new third-party
   name* entering the suite unargued; it has never been about how honestly a component declares
   what it already uses.

3. **G16 is unchanged: adding a name to any component's set requires an ADR.** Removing one requires
   nothing but a release. A version-range change is not a set change.

4. **`pydantic-settings` is not in any application's approved set.** No application imports it, so
   it is a documented over-declaration that leaves each `pyproject.toml` at that application's next
   release. Until then §1.1 lists it as *declared, unapproved, owed removal* rather than pretending
   either that it is used or that it is already gone.

5. **G16's gate is the test, and it is owed by eleven repositories.** "A test asserting the declared
   set" exists in three (`BaseAiCore/tests/test_packaging.py`,
   `CutCtx/tests/unit/test_packaging.py`, `ToolYard/tests/unit/test_boundaries.py`). The other
   eleven have no such test, which is a gap in the *gate*, not a breach of the *budget*, and it is
   what makes §1.1 checkable rather than aspirational once closed.

6. **Development and optional-extra dependencies stay outside the budget**, as they already were.
   `[postgres]`/`[postgresql]`, `[sql]`, `[telemetry]`, `[pynvml]`, `[psutil]` and every `dev` set
   are unbudgeted; they are not installed by a plain `pip install <component>`.

## Alternatives considered

* **Hold ≤ 6 and cut four dependencies per application.** Ask which four. `httpx` goes and the CLI
  and the peer clients have no HTTP. `jinja2` goes and there is no server-rendered HTML, reversing
  [ADR-0020](0020-ui-rendering-strategy.md). `sqlalchemy`/`alembic` go and either the application
  stops owning its migration history, reversing
  [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md), or WeightsDB starts
  owning it, reversing the same record from the other side. `pydantic` goes and the wire models are
  hand-rolled, reversing [ADR-0009](0009-setspec-schema-strategy.md)'s premise. A budget that can
  only be met by reversing four accepted decisions is the wrong number, not a discipline.

* **Hold ≤ 6 by leaving the transitively-available names undeclared.** This is the option that
  makes the audit's table green today and breaks a clean-venv install the first time `setspec`
  drops `pydantic` or `weightsdb` drops `alembic`. Rejected outright: it optimises the measurement
  against the property being measured, and G2's clean-venv install-check exists precisely to catch
  what it would introduce.

* **Raise the number to 10 and keep counting.** Rejected. A number is headroom, not a budget: it
  says the eleventh dependency is the problem and the tenth is fine, when the actual question is
  whether *this* name was argued for. An enumeration answers that question by construction — a name
  is either on the list or it needs an ADR — and it makes G16's test a set comparison instead of a
  `len()`.

* **Drop the budget entirely and rely on review.** Rejected: review is what let five components
  drift past the number for weeks without anyone noticing, and the audit found it by reading
  `pyproject.toml` rather than by any gate firing. The enumeration is the smallest thing a test can
  check.

## Consequences

* G16 becomes mechanically checkable: a test compares each `pyproject.toml`'s `dependencies` against
  the §1.1 table, ignoring version ranges. Eleven repositories owe that test.
* Five components stop being nominally in violation of a standard nobody intended them to break.
* §1.1 becomes a maintenance surface with a low but real cost: a *name* added or removed is a table
  edit and, for an addition, an ADR. A version-range bump is neither.
* The four applications carry a dependency they do not use until their next release each. That is
  visible in the table, which is better than a count that hid it — the audit counted
  `pydantic-settings` as one of the ten legitimate imports, and it is not one.
* MirrorWall's three are now stated with reasons, so "why does the UI package depend on `anyio`" has
  a written answer instead of an argument.

## Revisit when

* **A component's set passes twelve names, or an application declares a name no other application
  declares.** Either says the enumeration has stopped functioning as a budget and started
  functioning as an inventory.
* **FastAPI absorbs `python-multipart`, or Starlette's dependency shape changes.** Both would remove
  a name from two applications' sets for free.
* **A fifth application joins the suite.** The four current sets are within one name of each other;
  a fifth that is not says the shape of "an application" has changed and §1.1's per-component table
  should probably become a shared base set plus per-component additions.
