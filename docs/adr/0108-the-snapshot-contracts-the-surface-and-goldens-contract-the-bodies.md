# ADR-0108 — The OpenAPI snapshot contracts the surface; captured goldens contract the bodies

**Status:** Accepted (2026-09-07)
**Amends:** [Gold standards](../standards/gold-standards.md) G6 and G7,
[API and contract standards §11](../standards/api-and-contract-standards.md) and
[Testing standards §8.4](../standards/testing-standards.md) item 4 — all three of which promise a
mechanism that was never built, and are edited in the same commit as this record.
**Relates to:** [ADR-0013](0013-api-versioning.md) (what the surface has to hold still for),
[ADR-0009](0009-setspec-schema-strategy.md) (the golden discipline this borrows, for payloads where
it genuinely works), [ADR-0107](0107-two-loadcoach-clients-are-not-yet-one-package.md) (the
consumers whose contract tests this describes, and whose extraction question turns on the same
fact).
**Source:** The 2026-09-07 ADR gap review, finding 5.1 — a cross-cutting mechanism named in the
gold standards, contradicted by every application, with the substitute decided inside one
application's test docstring.

## Context

Three documents describe how an application's HTTP responses are contracted, and they describe
something that does not exist:

* **G6** — "API bodies contracted by the committed OpenAPI snapshot."
* **API standards §11** — the snapshot is committed as `docs/api/openapi-v1.json` in each app repo.
* **Testing standards §8.4 item 4** — each application "ships its committed OpenAPI snapshot as
  package data (`<app>/api/openapi-v1.json`, loadable through `importlib.resources`) and exposes it
  as `<app>.api_snapshot()`", from which a consumer "drives a schema-driven mock".

None of it is true. No repository contains an `openapi-v1.json`; `api_snapshot` appears in no
`src/`. The real artifact is `docs/openapi.json`, committed by FreeWeight, LoadCoach and
PromptCadence and by **not IdeaPress**, which commits no snapshot at all while serving
`/api/v1/openapi.json` from nine route modules. IdeaPress verified the packaging half against the
published wheel at M8-01: `loadcoach 1.0.0` ships no `__init__.py`, no `api_snapshot` and no
`openapi*.json`, so the distribution channel the technique needs is absent at both ends.

**And the technique could not work even if the plumbing existed**, because of what a FastAPI
snapshot of these applications actually contains. LoadCoach's route handlers return plain
dictionaries, so its committed document (version 1.1.2) describes **no body at all for 32 of its
49 JSON responses** — 26 as `{"type": "object", "additionalProperties": true}` and six as an empty
schema — `POST /api/v1/generate`'s `200` among them. A schema-driven mock validated against that
agrees with any response whatsoever.

IdeaPress discovered this the expensive way. Three M8 defects had one cause — the mock encoded the
implementer's assumption, the adapter matched the mock, and the real service did something else:
version negotiation read flat keys where the body nests them, the profile list was keyed on `id`
where the body says `profile_id`, and a declined stage arrives as HTTP 200 with a `failed` job
record that benign defaults turned into a successful empty generation. Each was invisible offline
because the mock agreed. The fix, and the reasoning behind it, currently live in a test docstring
(`IdeaPress/tests/contract/test_snapshot_coverage.py`): "the only authority on a response shape is
a running LoadCoach, so the fixtures are captured from one."

**What the snapshot *is* good for is real, and is being undersold.** Request schemas are closed:
LoadCoach's `GenerateBody` is `extra="forbid"`, so the document types it with
`additionalProperties: false` and a field a consumer invents is a `422` in production. IdeaPress's
mock validates **every request it receives** against the snapshot before answering, and that
asymmetry — requests schema-enforced, responses fixtures — is the snapshot's own shape, not a
shortcut.

## Decision

**The committed OpenAPI snapshot contracts the *surface*. Captured goldens plus each consumer's
contract tests contract the *bodies*. Both are obligations, neither substitutes for the other, and
the standards are corrected to say so.**

### 1. What the snapshot contracts

Which paths exist, on which methods, with which parameters, which **request** schemas (closed,
`additionalProperties: false`, and therefore genuinely enforceable), and which status codes. It is
committed at **`docs/openapi.json`** in each application repository — the path that exists — and it
is compared **byte for byte** against the document the application serves, in a test that fails on
any drift. Not path keys, not a subset: the whole document, so a parameter rename or a status-code
change cannot pass.

### 2. What the snapshot does not contract

Response bodies. A FastAPI application whose handlers return dictionaries produces open response
schemas, and this suite's applications do. **No test, mock or generated client may treat an open
response schema as agreement about a body.** Asserting a body against
`additionalProperties: true` is worth exactly nothing, and the danger is that it looks like a
contract test in a CI report.

### 3. What contracts the bodies

**Goldens captured from a running server**, holding keys and value types — never values — recorded
against a named producer version, plus the consumer's own contract tests over them. A golden edited
by hand to make a test pass is the assumption coming back; regenerating means running the real
service and re-recording.

### 4. What each application owes

1. **A committed snapshot** at `docs/openapi.json`, regenerable by a script in the repository.
2. **A byte-for-byte test** that the snapshot matches what the application serves, in the default
   suite, blocking.
3. **Goldens for every response body a consumer reads**, captured from a running producer, with the
   producer version recorded beside them; and contract tests that fail when the consumer's double
   drifts from the golden.

Obligation 3 falls on the **consumer**, because the consumer is the one that can be wrong about a
shape and the one that has to notice. A producer with no consumer owes only 1 and 2.

### 5. The distribution channel is dropped, not deferred

`api_snapshot()`, `<app>/api/openapi-v1.json` as package data and the schema-driven mock driven
from an installed producer distribution are removed from testing standards §8.4 rather than left
as unbuilt aspirations. Vendoring the producer's document beside the consumer's tests, with a
recorded digest and a check that it matches the installed producer's copy where one exists, is what
the consumers do and is enough: the vendored file cannot rot silently, and it costs no
test-time dependency on another application's wheel.

## Alternatives considered

* **Build the standard as written**: ship `api_snapshot()` from every application, install
  producers as test-only dependencies, drive schema-driven mocks. Rejected on the fact that decides
  everything here — the response schemas are open, so the mock the mechanism produces proves
  nothing about the bodies, which is the half consumers get wrong. It would be real work whose
  output is a green test that cannot fail for the reason it exists.
* **Type every response body** — give every handler a Pydantic `response_model` so the snapshot
  becomes a real body contract and the standard becomes true as written. This is the *right* long
  answer and it is deliberately not taken now: it means response models for 49 LoadCoach responses
  alone, and FastAPI's `response_model` **filters** output, so a field a handler returns and the
  model omits disappears silently — a breaking change to four published applications delivered by a
  refactor. It is named in the trigger below because it is the condition that changes this record,
  and it is the same condition that would reopen
  [ADR-0107](0107-two-loadcoach-clients-are-not-yet-one-package.md).
* **Contract the bodies with a live test only** — run a real producer in CI and assert against it.
  Rejected: it breaks G9 (the default suite runs with no GPU, model or network) and G4 (every
  application's suite passes with every peer absent). Live tests exist and are nightly evidence;
  they cannot be the gate.
* **Weaken the standards to "best effort"** and record nothing. Rejected: the failure this record
  closes is that a newcomer asking "what guarantees a LoadCoach response shape?" gets three
  different answers from three documents and the true one from a test docstring.
* **Keep `docs/api/openapi-v1.json` as the named path** and move the four files. Rejected as
  churn: three applications, their generator scripts, their READMEs and two vendored consumer
  copies would move so that a document could match the tree instead of the tree matching the
  document.

## Consequences

* **IdeaPress is the one application that fails obligations 1 and 2.** It commits no snapshot and
  has no test over its own surface, and it is the only one of the four whose API nobody else
  consumes — which is why it was never noticed. Closing it is a scheduled row's work: a generator
  script, `docs/openapi.json`, and the byte-for-byte test the other three already have. It is not
  fixed by this record.
* **The other three meet obligations 1 and 2 today.** FreeWeight's guard compared path keys only
  until `32b0cdd` (2026-09-07) widened it to the whole document, so all three now compare byte for
  byte.
* **Obligation 3 is met unevenly, and the two consumers differ.** IdeaPress records shapes from a
  running LoadCoach into `loadcoach_golden_v1.json` and fails when its mock lacks a key the real
  service has. PromptCadence pins response shapes by **transcribing api.md §4's documented example**
  into a unit test rather than by capture, and says so in its own contract docstring. Transcription
  catches a drifting fake; it does not catch a documented example that was wrong. PromptCadence
  therefore owes a capture, and that is owed work rather than something this record pretends is
  done.
* The two vendored copies of LoadCoach's document stay vendored, each with its digest and its
  producer version. That is the shape §5 endorses.
* Nothing changes at runtime, in any wire contract, or in any published API. This record changes
  what the standards claim and what a repository owes.

## Revisit when

* **An application types its response bodies** — `response_model` on every handler, so the snapshot
  carries real response schemas. At that point the snapshot contracts the bodies for that
  application, the goldens become a redundancy rather than the authority, and a generated client
  becomes available for nothing (see
  [ADR-0107](0107-two-loadcoach-clients-are-not-yet-one-package.md)'s trigger).
* **A consumer outside this suite appears**, which makes the distribution channel §5 drops a real
  requirement rather than an internal convenience: a third party cannot vendor a document it has no
  copy of.
* **A golden is found to have been edited by hand** rather than recaptured — that is the mechanism
  failing in the one way it can, and it means the capture step needs to be a script rather than a
  procedure.
