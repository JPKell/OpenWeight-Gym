# Dependency and Boundary Rules

**Status:** Normative. Violations are build failures, not style opinions.

The suite's promise — four applications that each work alone and compose when combined — survives
exactly as long as these rules do. This document states them, explains why each exists, and defines
how each is checked.

---

## 1. The dependency direction

```text
Applications  →  Capability packages  →  Contract package  →  Domain foundation
FreeWeight       ModelRack                SetSpec              BaseAiCore
LoadCoach        SweatMeter
IdeaPress        WeightsDB
PromptCadence    MirrorWall
                 CutCtx
                 ToolYard
                 LoadLedger
                 Commissioner
```

Every arrow points right. There are no arrows pointing left, and no arrows between siblings in the
capability layer.

### 1.1 Allowed imports

| From | May import |
|---|---|
| `baseaicore` | Python standard library only |
| `setspec` | stdlib, `pydantic`, `baseaicore` |
| `modelrack` | stdlib, `httpx`, `baseaicore` |
| `sweatmeter` | stdlib, `baseaicore` |
| `weightsdb` | stdlib, `sqlalchemy`, `alembic`, `baseaicore` |
| `mirrorwall` | stdlib, `fastapi`/`starlette`, `jinja2`, `baseaicore`, `setspec` |
| `cutctx` | stdlib, `baseaicore` — and not even a clock, a filesystem or a database ([ADR-0052](../adr/0052-compaction-is-a-view-and-the-package-plans-it-only.md)) |
| `toolyard` | stdlib, `jsonschema`, `httpx` (confined to `toolyard.tools.fetch`), `baseaicore` |
| `loadledger` | stdlib, `baseaicore`, and `sqlalchemy` under the `[sql]` extra |
| `commissioner` | stdlib, `baseaicore`, `setspec`, and `sqlalchemy` under the `[sql]` extra |
| `freeweight`, `loadcoach`, `ideapress`, `promptcadence` | any package above, plus their own declared dependencies |
| `weightroom` | `baseaicore`, `setspec`, `weightsdb`, `mirrorwall`, `sweatmeter`, `modelrack` (read-only provider calls), `loadledger[sql]`, plus its declared dependencies; **never** an application and never `toolyard`, `cutctx` or `commissioner` ([ADR-0123](../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rules 3–4) |

`setspec` is permitted in `mirrorwall` solely for the event and error envelope models, which are
cross-application payloads by definition, and in `commissioner` for the same reason — it owns the
Python form of `governance.egress_decision`
([ADR-0051](../adr/0051-plans-stay-internal-and-one-payload-travels.md)).
`promptcadence` imports neither `modelrack` nor `sweatmeter`: a harness with direct provider access
would own a second, ungoverned egress path
([ADR-0045](../adr/0045-promptcadence-reaches-models-only-through-loadcoach.md)).

### 1.2 Forbidden imports

```python
# In any shared package — always wrong, including inside TYPE_CHECKING or a function body:
from freeweight...   from loadcoach...   from ideapress...   from promptcadence...

# In any application — always wrong:
from loadcoach...    # inside freeweight, ideapress or promptcadence
from freeweight...   # inside loadcoach, ideapress or promptcadence
from ideapress...    # inside freeweight, loadcoach or promptcadence

# In a capability package — always wrong:
from modelrack import ...     # inside sweatmeter
from weightsdb import ...     # inside modelrack
from toolyard import ...      # inside cutctx
```

A shared package that "needs" an application type has been given application responsibility by
mistake. The fix is always to move the code back into the application, never to add the import.

---

## 2. Why each rule exists

| Rule | The failure it prevents | Evidence it is a real risk |
|---|---|---|
| Packages never import applications | The package becomes un-installable on its own; the "independent download" promise dies quietly | `content_factory/models/backend.py` imported `engine.types`, which is exactly why that provider layer could never be reused ([inventory §3](../inventory/legacy-material-inventory.md)) |
| Applications never import applications | IdeaPress would require LoadCoach to be installed to start | Requirement §2; the old planning explicitly warned about `from loadcoach.routing.router import Router` |
| No cross-application database access | The reader binds to the writer's internal schema; the writer can never migrate | Old planning proposed shared DB access "as a temporary shortcut" — rejected |
| Capability packages do not import each other | `sweatmeter` importing `modelrack` would force every telemetry consumer to install an HTTP client | — |
| Domain layer imports no framework | Business logic becomes untestable without a server and unusable from the CLI | Two prior projects put logic in HTTP handlers and then needed a second copy for the terminal |
| One provider client | Three implementations means three error-handling behaviours and three bug fixes | Three separate Ollama clients existed across the old projects |

---

## 3. Cross-application communication

The **only** permitted channels:

1. **HTTP over a versioned public API** (`/api/v1/…`), payloads validated against SetSpec schemas.
2. **Exported files** carrying SetSpec payloads (JSON/JSONL), moved by the user or by a scheduled
   task.

Explicitly forbidden:

* Importing another application's Python modules — including "just the models".
* Opening another application's database file or connection string.
* Reading another application's config, log, artifact or cache files.
* Sharing an in-process object, a Unix socket, or a filesystem queue directory.
* Depending on another application's undocumented HTTP endpoints (anything not in its OpenAPI
  document for the declared major version).

### 3.1 Optionality is mandatory

Every cross-application connection is optional and degrades explicitly:

| Connection | If unavailable |
|---|---|
| LoadCoach → FreeWeight evidence | Route on declared capabilities and production evidence; UI states "no benchmark evidence"; routing explanation records it |
| IdeaPress → LoadCoach | Fall back to the configured direct backend, or fail the stage with `BACKEND_UNAVAILABLE` if the user pinned LoadCoach; never a startup failure |
| PromptCadence → LoadCoach | The only path to a model PromptCadence has ([ADR-0045](../adr/0045-promptcadence-reaches-models-only-through-loadcoach.md)), and still not a startup dependency: it starts, serves, reports degraded health and parks submitted trajectories with a recorded reason, and never executes around the outage |
| Any → provider (Ollama) | Health endpoint reports degraded; operations that need inference fail with `PROVIDER_UNAVAILABLE`; the rest of the app works |

A cross-application dependency that is required to *start* is a design error.

### 3.2 The one component above these rules

**WeightRoom** ([ADR-0123](../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md))
is the host operator's console and is excepted from this section's channel list by enumeration:
it may open another application's database (read-only; a write passes
[ADR-0124](../adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)'s
guard), read and edit another application's configuration file in place, run its CLI, drive its
`systemd --user` unit, and call its HTTP API. It is **not** excepted from §1: it never imports an
application, and its `.importlinter` forbids the four names exactly as a package's does. The
exception exists because the operator already holds every one of those rights at a shell; it
grants WeightRoom nothing the machine did not already grant, and it is audited. Nothing else in
the suite may claim it.

---

## 4. Internal application boundaries

```text
web/ ─┐
      ├─► services/ ─► domain/        (pure: no framework, no I/O)
cli/ ─┘            └─► infrastructure/ (implements ports defined near the domain)
```

Rules:

1. `domain/` imports no `fastapi`, `starlette`, `sqlalchemy`, `typer`, `httpx`, `jinja2`, or
   `alembic`. It may import `baseaicore` and `setspec` types.
2. `services/` orchestrates: transaction scope, port calls, domain calls, event emission. It never
   returns framework objects.
3. `web/` and `cli/` never import each other, and never import `infrastructure/` directly — they
   receive services through the application's composition root.
4. Ports (Protocols) are declared where they are *used* (domain/services), implemented in
   `infrastructure/`. Dependency inversion at every external boundary: provider, telemetry, clock,
   filesystem, event sink, external application client.
5. The composition root (`<app>/bootstrap.py`) is the only module that instantiates concrete
   infrastructure. Tests build their own composition root with fakes.

---

## 5. Enforcement

### 5.1 `import-linter` contracts (every repository, every CI run)

Each repository ships `.importlinter`. Package repositories declare a forbidden contract against
all four application names; application repositories declare their layer contract.

```ini
# py/ModelRack/.importlinter
[importlinter]
root_packages = modelrack

[importlinter:contract:no-application-imports]
name = ModelRack must not import applications
type = forbidden
source_modules = modelrack
forbidden_modules = freeweight
                    loadcoach
                    ideapress
                    promptcadence

[importlinter:contract:no-sibling-packages]
name = ModelRack must not import sibling capability packages
type = forbidden
source_modules = modelrack
forbidden_modules = sweatmeter
                    weightsdb
                    mirrorwall
                    cutctx
                    toolyard
                    loadledger
                    commissioner
```

```ini
# FreeWeight/.importlinter
[importlinter]
root_packages = freeweight

[importlinter:contract:layers]
name = FreeWeight internal layering
type = layers
layers =
    freeweight.web
    freeweight.cli
    freeweight.services
    freeweight.domain
containers = freeweight
# web and cli are independent siblings above services:
[importlinter:contract:web-cli-independence]
name = Web and CLI never import each other
type = independence
modules = freeweight.web
          freeweight.cli

[importlinter:contract:domain-purity]
name = Domain imports no frameworks
type = forbidden
source_modules = freeweight.domain
forbidden_modules = fastapi
                    starlette
                    sqlalchemy
                    typer
                    httpx
                    jinja2

[importlinter:contract:no-other-applications]
name = FreeWeight must not import other applications
type = forbidden
source_modules = freeweight
forbidden_modules = loadcoach
                    ideapress
```

### 5.2 Additional automated checks

| Check | Tool | Fails on |
|---|---|---|
| Package installs alone | CI job in a clean venv: `pip install <package>` then `python -c "import <pkg>"` | Any transitive dependency on an application |
| No other application's DB is opened | `grep`-based test asserting no connection string or path references another app's data directory | Direct DB access |
| API surface is the documented one | Contract tests generate requests from the OpenAPI/JSON Schema documents | Undocumented endpoint use |
| Schema major-version rejection | Contract tests feed a `2.0` payload to a v1 reader | Silent acceptance |
| No prompts in Python | `tests/test_no_inline_prompts.py` scans for string literals over N lines containing prompt markers | Embedded prompts |
| Route/CLI thinness | Review checklist plus a test asserting handler modules import no repository or provider module | Logic in the edge |

### 5.3 Review checklist (human)

* Does this change make a shared package aware of an application concept?
* Does this change move logic *out* of a service into a handler?
* Does this add a required cross-application dependency?
* Does this introduce a second way to name a model, a machine, or a capability?
* Does this add an infrastructure service? If so, where is the ADR?

---

## 6. Circular dependency analysis

Checked at freeze time and re-checked whenever a dependency is added.

| Potential cycle | Present? | Why not |
|---|---|---|
| `BaseAiCore ↔ SetSpec` | No | SetSpec imports BaseAiCore; BaseAiCore has zero suite imports |
| `ModelRack ↔ SetSpec` | No | ModelRack does not import SetSpec. Its types are in-process; applications serialize them |
| `SweatMeter ↔ SetSpec` | No | SweatMeter produces `MachineProfile` (BaseAiCore type); serialization to the exchange schema happens in the application |
| `FreeWeight ↔ LoadCoach` | No | FreeWeight publishes; LoadCoach imports over HTTP/file; FreeWeight has no knowledge of LoadCoach |
| `IdeaPress ↔ LoadCoach` | No | IdeaPress calls LoadCoach; LoadCoach never calls back. Feedback is IdeaPress-initiated |
| `MirrorWall ↔ applications` | No | MirrorWall exposes macros and helpers; applications supply their own pages and navigation data |
| `WeightsDB ↔ applications` | No | WeightsDB never sees a model class; applications pass their own `MetaData`/`Base` |

**The one asymmetry worth stating:** LoadCoach *consumes* FreeWeight evidence, and IdeaPress
*consumes* LoadCoach execution. The arrows are consumer → producer over HTTP, and producers never
know their consumers. This is what keeps each application independently deployable.
