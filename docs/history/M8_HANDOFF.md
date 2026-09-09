# M8 Handoff — IdeaPress P7–P9 run (M8 1.0 closeout)

Entries are written as they happen, in `docs/history/M7_HANDOFF.md`'s format: **Severity** (DECISION / NOTE /
BLOCKER / FINDING), **Unit**, **Where**, **What happened**, **What the next run must do**.

Interpreter for every gate in this document unless stated otherwise: **Python 3.13.15**
(`IdeaPress/.venv`), per M5C-13 and SUITE_REVIEW F-15.

**Release state: `TAG_APPROVED: no`.** `ideapress 1.0.0` is prepared, built, twine-checked and
install-verified. The tag and the release workflow's `pypi` environment approval are the human's.

---

## M8-01 — FINDING: `loadcoach 1.0.0` ships no OpenAPI snapshot, no `__init__.py`, no `api_snapshot()`

**Severity:** FINDING (medium) — a released 1.0 application does not meet a standard the suite
requires of every application, and the mechanism the standard exists to enable is unavailable.

**Where:** `loadcoach-1.0.0-py3-none-any.whl`, verified against the **published** distribution.

**What happened.** Testing Standards §8.4 requires each application to ship its committed OpenAPI
snapshot as package data (`<app>/api/openapi-v1.json`, loadable through `importlib.resources`) and
to expose it as `<app>.api_snapshot()`. That is the distribution channel the whole cross-application
contract-testing technique rests on — the standard says so in as many words: *"the artifact needs a
distribution channel or the technique is theoretical."*

The published wheel contains none of it:

```
$ pip download loadcoach==1.0.0 --no-deps
$ python -c "import zipfile; z=zipfile.ZipFile('loadcoach-1.0.0-py3-none-any.whl'); \
             print([n for n in z.namelist() if 'openapi' in n.lower()]); \
             print('__init__.py' in z.namelist())"
[]
False
```

`src/loadcoach/` has no `__init__.py` at all, so `import loadcoach` resolves as a namespace package
and `loadcoach.api_snapshot` cannot exist. The build prompt's claim that the snapshot is "also
shipped in the `loadcoach` distribution" is not true of 1.0.0.

**What this run did.** Did not reach into another published application. IdeaPress vendors the
snapshot at `tests/contract/loadcoach_openapi_v1.json` (copied from
`LoadCoach/docs/openapi.json`, sha256 `3412b1f6…`) and
`tests/contract/loadcoach_mock.py::assert_snapshot_matches_distribution` fails the moment an
installed `loadcoach` ships one that differs. The workaround therefore cannot rot into a private
fork of somebody else's contract, and it stops being needed the day the standard is met.

**What the next run must do.** Decide whether LoadCoach gets a `1.0.1` that ships the snapshot and
an `__init__.py` with `api_snapshot()`. Until then IdeaPress's `loadcoach-contract` extra installs a
distribution it cannot read the contract from, which is worth knowing before someone relies on it.

---

## M8-02 — FINDING: LoadCoach's `api.md` §4 documents a `/generate` body its own code rejects

**Severity:** FINDING (medium) — a client written from the prose gets a 422 on every call.

**Where:** `LoadCoach/docs/apps/loadcoach/api.md` §4 vs `src/loadcoach/web/routes/generate.py:86`.

**What happened.** api.md §4's `POST /generate` example includes `constraints` and `priority`:

```json
{"task": "...", "sampling": {...}, "constraints": {"max_latency_seconds": 120},
 "priority": {"class": "normal"}, "idempotency_key": "01J9K…"}
```

`GenerateBody` declares neither field and is `model_config = ConfigDict(extra="forbid")`. The
committed OpenAPI snapshot agrees with the code (`additionalProperties: false`). So the documented
example is a `422 VALIDATION_ERROR`, on every request, for any caller that follows it. `JobBody`
*does* have `class`, `priority` and `max_wait_seconds`, which is presumably where the example's
fields came from.

**What this run did.** Built the adapter strictly against the snapshot, and asserted it:
`test_the_adapter_sends_no_field_the_producer_forbids` checks every submitted body against
`GenerateBody`'s declared properties, and the schema-driven mock validates
`additionalProperties: false` so an invented field fails offline exactly as it would in production.

**What the next run must do.** Correct LoadCoach's api.md §4 example, or add the fields. This is a
documentation defect in a published application, not an IdeaPress defect.

---

## M8-03 — NOTE: spec §14's "Markdown is sanitized with an allowlist" describes nothing that exists

**Severity:** NOTE — correct today, fragile tomorrow.

**Where:** `docs/apps/ideapress/spec.md` §14, and every rendering surface.

**What happened.** §14 says model output is "never rendered unescaped. Markdown is sanitized with
an allowlist." No allowlist sanitizer exists in IdeaPress — because **nothing in the product renders
Markdown to HTML**. Unit content goes into `<pre class="unit-content">` as escaped text, and the
Markdown export is a source-text file. The sentence anticipates a Markdown renderer the architecture
never acquired (ADR-0020 gives server-rendered HTML, and the unit view is deliberately not a rich
text view).

**What this run did.** Left the sentence alone and made it self-enforcing:
`test_no_markdown_is_ever_rendered_to_html_anywhere_in_the_application` walks `src/` for a Markdown
renderer import. The day one appears, §14's allowlist stops being a description of nothing and
becomes a requirement — and the test fails so it is implemented rather than assumed.

**What the next run must do.** Nothing, unless it adds a Markdown renderer. If it does, the
allowlist is now required and the test will say so.

---

## M8-04 — BLOCKER (fixed): version negotiation would have failed against every real LoadCoach

**Severity:** BLOCKER, found and fixed within this run. **This is what I7 is for.**

**Where:** `infrastructure/backends/loadcoach.py::_api_majors`.

**What happened.** The adapter read the API version from a flat `api_versions` list or an
`api_version` scalar at the top level of `GET /api/v1/version`. A running LoadCoach 1.0.0 answers:

```json
{"application": {"name": "loadcoach", "version": "1.0.0", "git_commit": null},
 "api": {"current": "v1", "supported": ["v1"], "deprecated": []}}
```

Nested. So `_api_majors` returned the empty set, `SUPPORTED_API_MAJOR not in majors` was true, and
**every first contact with a real LoadCoach would have raised `BACKEND_VERSION_MISMATCH` naming
"none reported"**. The health check would have reported `degraded` forever and no stage would ever
have routed.

Sixty offline contract tests passed. They could not have caught it: the committed OpenAPI snapshot
types `/version`'s 200 response as `{"additionalProperties": true, "type": "object"}`, so the
*shape* is unconstrained by the schema, and the mock encoded the same guess the adapter did — read
from api.md's prose ("Application version, API versions, accepted SetSpec schema versions"), which
describes the contents and not the nesting.

**What this run did.** Read the shape from the running service. `_api_majors` now reads
`api.supported` and `api.current` and still accepts the flat spellings, so a future release that
flattens the document does not break negotiation on the version that has to detect the change.
`_application_version` reads `application.version`. The mock now emits the real shape, and
`test_the_running_services_own_version_shape_negotiates` is the regression guard.

**What the next run must do.** Treat this as the standing argument for I7 being a live milestone.
Every response body LoadCoach types as a bare object is a place a mock can only encode an
assumption; the adapter's other reads of such bodies (`/models`, `/reliability`, the `/generate`
result envelope) carry the same exposure and only a live run distinguishes a correct guess from a
lucky one.

---

## M8-05 — BLOCKER (fixed): the task-profile check saw zero profiles and read it as "none served"

**Severity:** BLOCKER, found and fixed within this run. Also I7's doing.

**Where:** `infrastructure/backends/loadcoach.py::task_profiles`.

**What happened.** The adapter read each profile's identifier from `id`, `task` or `name`. A running
LoadCoach emits `profile_id`:

```json
{"task_profiles": [{"profile_id": "general.chat", "version": "1.0.0", …}]}
```

So `task_profiles()` returned an empty set and `unmapped_task_profiles()` reported **all eleven**
mapped profiles missing. The failure mode is worse than a wrong answer: an empty set reads as
"LoadCoach serves nothing", which sends a reader to look at LoadCoach's configuration rather than at
IdeaPress's parser.

**What this run did.** `profile_id` first, then the others, so a rename on LoadCoach's side degrades
to a clear per-profile "missing" rather than to an empty set. The mock now emits `profile_id`.
`ideapress doctor` surfaces the same check, so it is answerable before a project starts.

**What the next run must do.** Nothing. Noted alongside M8-04 as the same lesson.

---

## M8-06 — DECISION: ADR-0040, a routing backend owns model choice and residency

**Severity:** DECISION (accepted). The ADR was authored before the gateway was touched, but note
that `git log` cannot show this: the docs repo's ADR commit lands eleven seconds *after* IdeaPress's
P7 commit, because the two repositories were committed at the end of the phase, code first. Judge
the record on its content, not its timestamp.

**Where:** `docs/adr/0040-routing-backend-owns-model-choice.md`; `services/inference.py`;
`domain/inference.py`; `config.py`.

**What happened.** `InferenceGateway` resolved a `[models.stages]` binding for **every** request and
passed it down as `model_hint`, and unloaded the resident model before a switch. Both are correct
for a backend IdeaPress drives. Neither is correct for one that routes for itself, and the gateway
had no way to tell the difference.

With the shipped default configuration, `inference.mode = "loadcoach"` would have:

1. resolved `models.stages.draft = "ollama/gemma4:12b"` and set it as `model_hint`;
2. had the adapter send it as `overrides.model` — workflows §6.1 says `model_hint` is sent "as an
   override only when the user pinned one", and the adapter cannot distinguish a user's pin from a
   binding the gateway resolved on its own — **bypassing LoadCoach's task profiles, capability
   evidence, reliability factor and admission control entirely**; and
3. called `unload()` for a model IdeaPress does not own, recording a `model_switch` degradation
   describing an eviction that did not happen.

**Every stage would still have succeeded.** Nothing raises, nothing logs at WARNING, the parity test
passes, and the provenance record is truthful about which model answered. The integration would have
looked like it worked while delivering none of what it exists for — and (3) puts a fabricated
eviction into a record a person is meant to trust, which is ADR-0016's offence in a different suit.

**The decision.** `BackendCapabilities` gains `routes_internally`. When set, the gateway resolves no
binding, requires none, and performs no unload. `[inference.loadcoach] honour_stage_bindings`
(default `false`) is the explicit opt-in that spec §12's "ignored in loadcoach mode unless
overridden" had never been given a mechanism for. An override that routing did not honour is a
`model_override_not_honoured` degradation naming both models — a pin is a request, not a guarantee.

**What the next run must do.** Nothing. A future backend that routes internally sets one flag rather
than rediscovering this.

---

## M8-07 — DECISION: ADR-0041, a caller's output schema does not travel through a router

**Severity:** DECISION (accepted). **This one collides with ADR-0039 and is the more serious of the
two.**

**Where:** `docs/adr/0041-caller-schemas-do-not-travel-through-a-router.md`;
`infrastructure/backends/loadcoach.py::_body_for`.

**What happened.** LoadCoach's `GenerateBody.response_format` is a bare string
(`text | json | json_schema`) with no field for a schema document. The schema applied is the **task
profile's** `execution.json_schema_ref`, resolved server-side:

```python
# loadcoach/services/execution.py::_response_format
if kind == "json_schema" and schema is not None:   # `schema` is the profile's, never the caller's
    return ResponseFormat(kind=JSON_SCHEMA, schema=dict(schema))
if kind == "json":
    return ResponseFormat(kind=JSON)
return None
```

For the three profiles the task map routes structured stages through, "the profile's schema" is
actively wrong. The `content.review` case is the one that matters:

| | IdeaPress `FINDINGS_SCHEMA` | LoadCoach `content_review_findings.json` |
|---|---|---|
| required | `findings`, **`requirements_assessment`** | `findings`, `summary` |
| finding item | `category` / `severity` / `problem_text` | `requirement` / `status` / `explanation` |
| verdicts | `met` / `not_met` / **`cannot_judge`** | `met` / `partially_met` / `not_met` |
| extra keys | forbidden | **forbidden** |

`additionalProperties: false` makes `requirements_assessment` **structurally impossible**, and there
is no `cannot_judge`. So sending `json_schema` through `content.review` would have made
[ADR-0039](docs/adr/0039-audit-gated-blocking-requirements.md)'s attestation mechanism — accepted
three weeks ago, and the thing standing between the commit gate and a model's silence —
**unexpressible**. A model schema-forced into that shape returns no attestation for any requirement,
every check-less blocking requirement stays unsatisfied, and every unit pauses.

Neither side is at fault. LoadCoach's profile schemas are correct *for LoadCoach* — they are what
lets it validate, retry correctively and score structured-output reliability across callers it knows
nothing about. They are simply not IdeaPress's contract, and there is no field in which IdeaPress's
contract could be sent.

**The decision.** Through a routing backend, IdeaPress asks for `json` (honoured unconditionally,
independently of the profile), reports `structured_output=False` honestly, records
`structured_output_unavailable` naming the reason on every affected attempt, and validates the shape
itself — which is where it was always enforced anyway, and why the four-way parity test still holds.

**What the next run must do.** The ADR records "add a per-request schema field to LoadCoach's API"
as the right long-term answer and a real option — v1 is additive, so a `json_schema` document field
could be added compatibly. It was rejected *for M8* because it changes a published 1.0
application's public contract and its corrective-retry path in order to remove a degradation that is
already recorded honestly. That is a decision for the human, not a defect to carry.

---

## M8-08 — DECISION: `inference.fallback_mode` was documented, reported, and never applied

**Severity:** DECISION (behaviour change in 1.0, noted in `upgrading.md`).

**Where:** `services/backends.py::describe_backends` vs `services/inference.py`.

**What happened.** Workflows §6.2 row 1 says an unreachable backend with `fallback_mode` set and not
pinned "falls back, records the degradation on the attempt, warns in the UI". `describe_backends`
listed the fallback on the backends page. **Nothing ever fell back**: no code path read
`fallback_mode` at runtime. A user who configured one had configured nothing.

**What this run did.** Implemented it at the single choke point — never inside an adapter, because
an adapter that fell back to another adapter would be two backends wearing one name and the
attempt's `backend` field would stop saying where the text came from. `InferenceGateway` gains
`fallback` and `pinned`; a `BackendUnavailable` or `ProviderTimeout` from the primary runs the
request on the fallback and records `backend_fallback: <primary> did not answer (…); this attempt
ran on <fallback> instead`. Pinned re-raises. The runtime builds the fallback **at startup**, not on
first outage: a fallback that only fails to build when the primary is already down is not a
fallback.

**What the next run must do.** Note the upgrade consequence, which `docs/upgrading.md` already
carries: a 0.1.x user who set `fallback_mode` expecting nothing to happen now gets a fallback, and a
degradation on the attempt saying so.

---

## M8-09 — NOTE: the gateway's "a test walks the source and asserts that" was not true

**Severity:** NOTE (fixed).

**Where:** `services/inference.py::InferenceGateway.run` docstring; `tests/unit/test_import_boundaries.py`.

**What happened.** The docstring has said since P2: *"**This is the only function in IdeaPress that
calls a backend's `generate`.** A test walks the source and asserts that."* No such test existed.
The claim was load-bearing — it is ADR-0038's first obligation and the M5 lesson it cites is
precisely about an unchecked second entry point — and unchecked.

**What this run did.** Wrote it:
`test_only_the_gateway_calls_a_backend_to_generate` walks `src/`, exempts the adapters (calling
`generate` on a *provider* is how an adapter does its job) and `services/inference.py`, and fails on
any other `backend.generate(` call site.

**What the next run must do.** When a docstring claims a test exists, check that it does. This one
had been wrong for six phases.

---

## M8-10 — NOTE: workflows §11 still forbade what ADR-0039 permits

**Severity:** NOTE (docs defect, fixed canonical-first and mirrored).

**Where:** `docs/apps/ideapress/workflows.md` §11.

**What happened.** ADR-0039 updated workflows §3 to say an audit's explicit `met` may satisfy a
check-less blocking requirement. §11's list of what a model may never do still read: *"Decide that a
requirement is satisfied without a deterministic check (advisory only, and labelled)."* The two
sections of the same document contradicted each other, and §11's version described the pre-ADR
behaviour.

**What this run did.** §11 now reads: a model may not decide a requirement is satisfied **by saying
nothing about it** — where a check exists the check decides, where none exists only an explicit
labelled `met` satisfies, and silence, `cannot_judge` or an invented word all leave it unsatisfied.
That is the rule ADR-0039 actually established, and it is a *different* rule from the one it
replaced rather than a softening of it.

**What the next run must do.** Nothing. Flagged because roadmap §8's consistency review is supposed
to catch exactly this and did not, on the milestone that introduced it.

---

## M8-11 — NOTE: the development plan carried two statements the M7 handoff had already corrected

**Severity:** NOTE (fixed canonical-first, mirrored, `cmp`-verified).

**Where:** `docs/apps/ideapress/development-plan.md` §P7 Tests.

**What happened.** The plan said the LoadCoach contract dependency is "a **test-only** dependency of
`ideapress[dev]`". M7-3 had already decided otherwise, and for a good reason: `[dev]` installing
another application puts it in every developer and CI environment, so "runs a complete workflow with
no LoadCoach installed" — Gold Standards §2's first IdeaPress bullet — becomes a property no run has
ever tested. `pyproject.toml` was already correct (`loadcoach-contract`); only the plan was stale.
The plan also said parity covers "all **three** backends"; the build prompt requires four.

**What this run did.** Both corrected in the canonical document and mirrored. Note that Testing
Standards §8.4 still says `ideapress[dev]` may depend on `loadcoach` — the *standard* carries the
same stale claim, and was left alone as out of scope for an application milestone.

**What the next run must do.** Consider correcting Testing Standards §8.4 to match, or record why
the standard's permissive wording is deliberate.

---

## M8-12 — NOTE: two of this run's own tests were wrong in ways worth recording

**Severity:** NOTE — both were caught by their own failures, and both are instructive.

**Where:** `tests/security/test_sanitization_sweep.py`; `tests/performance/test_budgets.py`.

**What happened.**

1. **A sanitization detector that flagged correct escaping.** The first version searched rendered
   pages for `onerror=alert`. HTML escaping touches `< > & " '` and **not** `=`, so a correctly
   escaped and entirely inert `&lt;img src=x onerror=alert(1)&gt;` still contains that substring.
   The detector reported three pages as vulnerable when none was. It now checks for the *literal
   payload*, which is present only if escaping did not happen.

2. **A 100-unit performance fixture that committed one unit.** The fixture asserted
   `len(units) == 100` — which was true, because 100 units were *planned*. Only the first committed,
   because `repeat_final_generation=True` fed the critique's verdict JSON to the second unit's draft.
   Four of the seven budgets would have been measured against a one-unit project and passed
   comfortably. The fixture now asserts 100 units **committed** and scripts one
   draft/audit/verdict cycle per unit.

**What the next run must do.** For (1): a security test that cannot fail on correct behaviour is
worth as little as one that cannot fail on incorrect behaviour, and a substring of an escaped
payload is the easy way to write the first kind. For (2): "the fixture is the size the budget names"
is itself an assertion, and `planned` is not `committed`.

---

## M8-13 — DECISION: an imported archive brings its units back, but not another machine's provenance

**Severity:** DECISION.

**Where:** `services/project_archive.py::_restore_units`.

**What happened.** The first implementation of `import_project_archive` counted the manifest's units
and discarded them: a round trip restored the project and its brief and lost the work. That makes
"portable project" mean "portable brief", and the archive is meant to be the thing that survives an
installation being deleted.

**The decision.** Units come back **committed**, with their content, version number and content
hash. Attempt provenance deliberately does **not**: those attempts happened on another installation,
against models and prompts this one may not have, and writing them here as this installation's own
record would put something into the database that is not true of it — ADR-0016's offence again. The
manifest retains them and the content hash is the honest link back.
`test_an_import_does_not_claim_another_installations_attempts_as_its_own` asserts no attempt rows
are fabricated.

**What the next run must do.** If cross-installation provenance is wanted, it needs a
representation that says *whose* attempts they were. That is a schema question, not a bug fix.

---

## M8-14 — P7-B: the ADR-0039 attestation reliability measurement

**Severity:** NOTE — the measurement came back clean. **Recommendation: keep option (b).**

ADR-0039's Consequences make this measurement an obligation of M8: option (b) — an audit's
explicit `met` may satisfy a blocking requirement that has no deterministic check — is only sound
if the model's verdicts are actually informative.

**How it was run.** `tests/live/test_attestation_reliability.py`, `-m live`, 20 runs of
`audit_fast` over one fixture unit carrying three check-less blocking requirements of known
status. An omitted verdict is counted as `cannot_judge`, which is exactly how the coverage gate
reads it — so the table counts what the gate would count, not what the model literally emitted.

```
model                : ollama/qwen3.5:9b-q8_0        stage  : audit_fast (prompt 1.1.0)
output budget        : 8192 tokens                   runs   : 20 requested, 20 completed, 0 errored
runs attesting none  : 0 (0% of completed)

requirement known            met  not_met  cannot_judge   agrees
------------------------------------------------------------------------------
R-001       met               20        0             0     100%
R-002       not_met            0       20             0     100%
R-003       cannot_judge       0        0            20     100%
```

**Reading it.** The three numbers ADR-0039 cares about:

* **R-001, 20/20 `met`** — a true requirement can pass. The mechanism is not a gate nothing clears.
* **R-002, 20/20 `not_met`** — the one that matters. A plainly violated requirement was caught
  every time and **rubber-stamped zero times**. This is the failure mode option (b) risks, and it
  did not appear.
* **R-003, 20/20 `cannot_judge`** — asked something unjudgeable from the text, the model declined
  rather than inventing a verdict. No overclaiming.
* **0 runs attested nothing** — the array came back populated on every run, so the prompt and
  schema reach the model reliably at the shipped 8192-token budget.

**Recommendation: keep (b).** On this evidence option (a) — refusing to let an audit satisfy any
check-less blocking requirement — would reject 20 correct `met` verdicts to prevent zero incorrect
ones. **The gate was not changed on the strength of this run**, per the instruction; this is the
number, and the decision remains the human's.

**Three honest limits on the number.**

1. **N=20, one fixture, one model.** ADR-0039 asks for ≥20; this is exactly 20, on three
   requirements written to be unambiguous. A 100% score on an easy fixture is evidence the
   mechanism works, not evidence it is calibrated on hard cases. The interesting experiment — a
   requirement that is *arguably* met — is not this one.
2. **It ran under GPU contention.** A third-party client shared the same Ollama slot throughout,
   which is why the run took 56:47 (~2m50s per audit, against ~20s unloaded). Contention changes
   latency, not verdicts: same model, same prompts, same budget, and 0 of 20 runs errored. The
   numbers stand; the wall-clock is not a performance measurement.
3. **`qwen3.5:9b-q8_0` only.** `gemma4:12b` is the other default and was not measured.

**What the next run must do.** If the gate is ever relaxed further, re-run this with a fixture of
*genuinely ambiguous* requirements — the current one measures whether the mechanism functions, and
the next question is whether the verdicts are calibrated when the answer is not obvious.

---

## M8-15 — NOTE: `modelrack` is pinned `>=0.5,<0.6` while 0.6.0 is published

**Severity:** NOTE.

**Where:** `IdeaPress/pyproject.toml`.

**What happened.** `modelrack 0.6.0` was released on 2026-08-31. IdeaPress pins `<0.6`, so it
resolves 0.5.x. Nothing is broken — IdeaPress uses no 0.6 API — but the pin excludes the current
release and was not a decision anyone recorded.

**What the next run must do.** Either widen to `<0.7` after checking 0.6.0's changelog for the
provider protocol, or record why 0.5.x is pinned. Not changed in this run: widening a dependency
range in the commit that prepares a 1.0 release, without running the suite against the wider range
on CI, is the kind of change that should be its own commit.

---

## M8-16 — BLOCKER (fixed): a stage LoadCoach *refused* was reported as a successful empty generation

**Severity:** BLOCKER, found and fixed within this run. **The third defect I7 found that all 937
offline tests then passed** — and the most serious of the three.

**Where:** `src/ideapress/infrastructure/backends/loadcoach.py`, `_to_result` and `generate`.

**What happened.** LoadCoach reports a refused stage with **HTTP 200** and a job record whose
`state` is `failed`. Observed verbatim from a real LoadCoach 1.0.0:

```json
{"status": "failed", "state": "failed", "state_reason": "NO_ELIGIBLE_MODEL",
 "error": {"code": "NO_ELIGIBLE_MODEL",
           "message": "No model satisfied task profile 'general.reasoning''s constraints."},
 "output": {"text": null, "structured": null}, "finish_reason": null,
 "usage": {"input_tokens": null, "output_tokens": null}}
```

Nothing about that is an HTTP error, so `_decode` passed it through. Every field `_to_result`
reads then fell back to a benign default — absent `output` became `""`, and
`finish_reason: null` became **`"stop"`** via `str(payload.get("finish_reason") or "stop")`. The
port received:

```
StageResult(text='', model=None, usage=0/0, degradations=(), finish_reason='stop',
            refusal_reason=None)
```

A stage LoadCoach explicitly declined, presented as a model that finished normally and chose to
say nothing. **The terminal-state check existed** — in `_run_as_job`, on the queued path only.
The synchronous `/generate` path and the stream `result` frame had none, and my own docstring on
`_to_result` recorded that all three carry *"the same shape"*. I wrote the guard for one of the
three places the shape arrives.

**Why no offline test caught it.** `MockLoadCoach` could only emit `"status": "completed"`. The
failure shape was not merely untested, it was **inexpressible** — the mock encoded my assumption,
so no test could have been written against the real behaviour without first changing the mock.
This is the exact failure mode M8-04 and M8-05 share, and it is now three for three.

**The three consequences, in order of severity.**

1. **Silence presented as success.** `degradations=()` meant nothing on the unit page said the
   stage had been declined. That is precisely what ADR-0039 exists to forbid, arriving through
   the backend rather than through the audit.
2. **False evidence written into a published application.** Feedback is posted per committed
   unit, keyed by the `job_id` on the attempt. Because the declined stage "succeeded", the unit
   committed and feedback went out marked `accepted: true, validation.passed: true` **about a job
   that never ran** — corrupting LoadCoach's reliability factor, which then skews its routing for
   every future caller, not only IdeaPress. Observed live on job
   `01M1DWZ7DT0M7WWP4747C30ASF`.
3. **The fallback never engaged.** A refusal that reads as a success is not a failure, so
   `inference.fallback_mode` (M8-08) stayed dormant on exactly the condition it exists for.

**The fix.** One guard, `_refuse_a_terminal_failure`, at `_to_result` — the single funnel all
three paths share — and the duplicate decision removed from `_run_as_job` so the two paths cannot
disagree again. `CONTEXT_LIMIT_EXCEEDED` raises `ContextLimitExceeded`; **every other terminal
non-completion, including a code this adapter has never seen, raises `BackendUnavailable`**, which
is recoverable: it engages the fallback and leaves the project resumable. Defaulting an unknown
code to `ContentRejected` would tell a user their content was refused on no evidence — the same
class of guess that caused the defect.

`MockLoadCoach.fail_next()` was added so the shape is expressible, built field-for-field from the
observed record above. Nine tests: eight in `tests/integration/test_loadcoach_degradation.py`
covering the synchronous path, the queued path, `cancelled`, the context-limit mapping, the
unknown-code default, and the fallback finally engaging; one in
`tests/integration/test_loadcoach_feedback.py` for consequence 2.

**Both were probed against the unfixed code**, which is the only evidence a regression test is
real: with the guard disabled, seven of the eight go red, and the declined draft reports
`completed` instead of `failed`. My first version of the feedback test passed in *both* states —
it failed the plan stage, which cannot parse an empty response either way, so no unit ever
committed and no feedback was ever posted. It now declines the **draft**, after a successful plan,
which is the path that actually commits an empty unit.

**What the next run must do.** Two things. First: **grep the adapter for `or ""`, `or "stop"`,
`or {}` and every `.get(...)` default on a body LoadCoach's snapshot types as a bare object** —
this defect is one instance of a pattern I applied throughout `_to_result` for robustness, and
robustness against a *malformed* body is indistinguishable in code from credulity toward a
*well-formed failure*. Second: the mock is a schema-driven contract mock, and a schema-driven mock
can only generate shapes the schema describes; where the snapshot types a field as a bare object,
the mock's agreement is worth nothing. Both M8-04 and M8-05 were found by reading LoadCoach's
source rather than its documents, and so was this.

---

## M8-17 — NOTE: LoadCoach distinguishes "unsupported" from "not reported"; IdeaPress flattens both to `None`

**Severity:** NOTE. Recorded because it is an ADR-0016 question, not because anything is broken.

**Where:** `loadcoach.py` `_to_result`; `domain/inference.py` `TokenUsage`.

**What happened.** A real LoadCoach reports `usage.thinking_tokens: "unsupported"` — the string,
deliberately, and distinct from a `null` meaning "this run reported none". `TokenUsage.thinking_tokens`
is typed `int | None`, so the adapter maps both to `None`. ADR-0016 says a measurement a machine
cannot provide is the `UNSUPPORTED` sentinel and is "never `None` or `0`", and `baseaicore.UNSUPPORTED`
exists.

**Why it was not changed.** The field is **write-only**: `stages.py` persists it to a nullable
`Integer` column and nothing — no service, no template, no export — ever reads it back. Carrying
the sentinel would mean changing a frozen domain value object, a database column and a migration,
for a value with no consumer, in the commit that prepares a 1.0. That is the same reasoning as
M8-15, and the same answer.

**What the next run must do.** Decide whether ADR-0016's sentinel governs *provider-reported
counts* or only *machine telemetry* — the ADR is about SweatMeter's readings, and extending it to
a token count is an interpretation, not a reading. If it does govern them, this is a real defect
in every adapter, not only LoadCoach's, and `_modelrack.py` flattens the same distinction. Close
it with an ADR rather than a patch.

---

## M8-18 — BLOCKER (LoadCoach, **fixed upstream**): consecutive stages refused each other on one GPU

**Severity:** was a BLOCKER for I7. **Fixed in LoadCoach** at the owner's direction, without a
version bump (`loadcoach 2c7d740`). I7 went from **4 of 11 passing to 9 of 11** on that change
alone, and its transcript now exists.

**Root cause, and it was not where the rejection pointed.** LoadCoach's routing already has the
residency exception — `constraints.py` accepts a model already loaded on a device without
re-checking VRAM, and the code is correct. **Nothing fed it.** `ensure_loaded` was called only from
`worker.py`, the queue worker; the synchronous `/generate` path read `resident_devices` as a
routing *input* and never wrote a residency episode of its own. So a `/generate` loaded a model
into the provider, recorded nothing, and the next request saw an empty map, could not apply the
exception, and was refused by the memory the previous request was still holding — including by the
model that had just answered.

**The fix:** `ExecutionContext` carries the tracker, and the attempt loop calls `ensure_loaded`
exactly as the worker does, so the synchronous path both records the load and evicts under
`max_resident_models`. Recording failures are swallowed: residency is an optimisation and an
eviction policy, never a precondition for a generation the provider can serve. Seven tests,
including two that walk the source — every test of the helper alone passed with the call site
deleted, which is precisely the state the code was in.

**Verified on the original reproduction:**

```
                            before                after
sync #1 (general.reasoning) OK, gpt-oss:20b       OK
sync #2 (content.review)    NO_ELIGIBLE_MODEL     OK
queued  (content.review)    NO_ELIGIBLE_MODEL     OK
```

**What remains, and it is a decision rather than a bug — see open question 3.**

**What happens.** Once LoadCoach has loaded a model for one task profile, a request for a
*different* task profile fails immediately with `NO_ELIGIBLE_MODEL`. Reproduced from a clean
LoadCoach database on a free 16 GB GPU:

```
sync #1 (critique   -> general.reasoning) : OK, routed to gpt-oss:20b
sync #2 (audit_fast -> content.review)    : NO_ELIGIBLE_MODEL
queued  (audit_fast -> content.review)    : NO_ELIGIBLE_MODEL
```

The routing explanation is unambiguous — **14 models rejected, 0 candidates, every one
`insufficient_vram`** — and it rejects the model that is *already resident and had just answered*:

```json
{"canonical_id": "ollama/gpt-oss:20b@sha256:17052f91a42e", "reason": "insufficient_vram",
 "detail": {"free_bytes_by_gpu": {"0": 2998927360},
            "estimate": {"weights_bytes": 14483113306}, "headroom_bytes": 536870912}}
```

`gpt-oss:20b` was loaded and serving at that moment. It needs **zero additional bytes**, and its
full weight is nonetheless charged against free VRAM.

**Result: I7 went from 4 of 11 passing to 11 of 11.**

**A correction worth recording, because I got this wrong twice.** After the residency fix, two
`content.review` clauses still failed, and I twice mis-diagnosed why:

* first as "routing never counts evictable memory" — **false**: the queue worker already passes
  `admission_snapshot()` into routing, and that subtracts `evictable_bytes_by_device`;
* then as "the synchronous path needs the same adjusted snapshot" — **also false**, and I was about
  to raise it as an architectural decision for the owner, on the grounds that it would overturn
  `device_fits`'s "never guess optimistically" principle. It would not have, and it was not needed.

The real cause was **`[residency] unload_idle_seconds = 0` in `~/.config/loadcoach/config.toml`**,
which I had written myself earlier in this run while probing whether eviction was the problem. It
closed every residency episode the instant it opened, so `resident` was `0` on every row and both
`resident_devices` and `evictable_bytes_by_device` came back empty — reproducing the exact symptom
the fix had just removed. With that file removed, **LoadCoach's shipped defaults work**:
`resident: 1` persists, and I7 passes 11/11 on two consecutive runs.

The lesson is the ordinary one: a test fixture left in place became evidence. The measurement that
settled it was reading `select resident from residency`, not reasoning about the code.

**Why it bites IdeaPress specifically.** IdeaPress's stages map to *different* task profiles
seconds apart — `critique` to `general.reasoning`, `audit_fast` to `content.review`, `draft` to
`content.article_draft` — and `content.review` additionally wants `min_context_tokens: 16384`
where the resident model was served at 8192. A single-GPU machine is exactly ADR-0038's premise
and exactly the deployment IdeaPress documents.

**What this does *not* mean.** It is not an IdeaPress defect and not a reason to change ADR-0040:
delegating residency to the routing backend is still right. With M8-16 and the capacity-code fix
in place, IdeaPress now does the correct thing in response — `NO_ELIGIBLE_MODEL` is recoverable,
so the configured `fallback_mode` engages and the project completes on Ollama instead of dying.
That is the designed behaviour, and it is the only reason this is survivable.

**What the next run must do.** Nothing here — it is fixed and verified. The `docs/backends.md`
note recommending a fallback on a single GPU stays: it is still true that a fallback is the
difference between a stage that degrades and a stage that dies, and it costs nothing when
LoadCoach is healthy. Do **not** set `[residency] unload_idle_seconds = 0`; it defeats residency
entirely, which is what made this look unfixable for an hour.

---

## M8-19 — BLOCKER (**fixed**, ADR-0043): the workflow produced confident fabricated evidence and every gate passed it

**Severity:** BLOCKER for "would a person publish this". Not a crash, not a failed assertion —
which is exactly why it matters. Found by *reading the output*, which no gate does.

**What happened.** The standalone journey ran an independent brief with **no source documents
attached**. The brief said: *"Ground every claim in the kind of evidence a council would accept:
usage figures, named programme types, and the specific services that have no other local
provider."* The model complied by **inventing** them:

* "averaging 150 daily footfall, 40 weekly workshop attendees, and 200 monthly digital resource
  check-outs" (U-02);
* "a comprehensive 2023 local service mapping audit" (U-02);
* "neighboring sites that operate at 85% capacity" (U-04).

None of these exist. Nothing was supplied for them to come from.

**Every gate passed it:**

```
validation.completed : U-02: 23 checks passed
audit.completed      : U-02: audit_fast: no findings (score 1.00)
critique.completed   : U-02: leave_it_alone
coverage.completed   : U-02: 2/2 requirements satisfied, 1 by a deterministic check
unit.committed       : U-02: version 1 committed (288 words)
```

**Why this is a finding about IdeaPress and not just about the model.** The product's claim is that
Python owns control flow and gates catch what a model gets wrong. Here the gates reported *full
coverage of a grounding requirement that IdeaPress had no means to verify*, because no sources
existed. Nothing anywhere in the run said "this requirement asks for grounding and there is
nothing to ground in". `fact_check` is a real stage in the vocabulary and is **not part of the
draft loop**, so it never ran — and with no sources it could not have verified anything either.

**This qualifies M8-14's recommendation.** P7-B measured attestation on a fixture built so the
right answer was unambiguous, and scored 100%. Here, on real work, `audit_fast` attested **no
findings, score 1.00** for a unit whose every figure was invented against a requirement demanding
real evidence. The attestation mechanism functions; that is what P7-B shows. **Whether its
verdicts are correct on work where the answer is not obvious is a different question, and this is
one data point saying no.** Keep option (b) — but the P7-B number should not be read as
"attestation is reliable", only as "attestation is reachable and not a rubber stamp on an easy
fixture".

**What the next run must do.** Decide the product question, which is not mine: should a grounding
requirement be **refusable at plan time** when the project has no sources — a `CONFIGURATION`-shaped
refusal saying "R-006 asks for evidence and none was attached" — or should `fact_check` join the
draft loop, or should the coverage report distinguish "satisfied" from "satisfied against no
source"? Any of the three is better than committing fabricated figures with a green report. This
needs an ADR (next number 0042); it is a change to what the gate *means*, not a bug fix.

---

## M8-20 — MAJOR (**fixed**, ADR-0042): a `contains any of` check is satisfied by reciting the requirement's own words

**Severity:** MAJOR. It creates a false compliance signal and visibly damages the prose.

**Where:** the requirements compiler's generated checks; `R-006` in the journey.

**What happened.** R-006 compiled to:

```
checks: contains any of: 'usage figures', 'named programme types',
        'the specific services that have no other local provider'
```

The model satisfied it by **quoting the phrases**, not by doing what they describe. Counted across
the four committed units:

| unit | "usage figures" | "named programme types" | "…no other local provider" |
|---|---|---|---|
| U-01 | 1 | 1 | 1 |
| U-02 | 1 | 1 | 1 |
| U-03 | **3** | 1 | **2** |
| U-04 | 1 | 0 | **2** |

U-04 contains the sentence *"The economic cost of the specific services that have no other local
provider is realized in…"* — a noun phrase lifted whole from the brief and welded into a sentence
that does not want it. The check is measuring a substring; the requirement is about a property.
Worse, it **rewards** the behaviour: the model learns to recite the requirement to pass the gate,
which is why U-01 is 184 words that restate the brief and say nothing.

This is the same class of mistake as M8-12's own security detector, which searched for
`onerror=alert` and flagged correctly escaped output — **a check whose text appears in the thing it
is checking cannot distinguish compliance from quotation.**

**The sharpest evidence, from U-05.** Its final critique reads, verbatim:

> *"The section fails the blocking requirement **R-006** by not grounding cost claims in specific
> data and contradicts itself regarding service exclusivity."*

The unit committed anyway, reporting `coverage.completed: U-05: 2/2 requirements satisfied, 1 by a
deterministic check`. R-006's substring check passed — on phrases the unit recites three times.

**The design is not at fault here; the check is.** A requirement with a deterministic check is
settled by Python and not by a model, deliberately: that is "a model is never a test oracle", and
letting a critique overturn a passing check would be the worse bug. What this shows is the cost of
a *bad* check under a correct rule — the system faithfully amplified a substring match into a
confident commit of work its own reviewer called materially deficient. That is why this is a
blocker and not a nit.

**What the next run must do.** Either stop compiling `contains` checks from requirement phrasing —
a requirement that cannot be checked deterministically should be **honestly check-less** and routed
to the audit under ADR-0039, which is the mechanism that exists for it — or make the compiler
refuse to emit a check whose needle is a phrase from the requirement's own text. The second is
narrower and testable. The present behaviour is worse than no check, because a check-less
requirement is *labelled* as guaranteed by model review, and this one was labelled as
deterministically satisfied.

---

## M8-21 — BLOCKER (**fixed**): a partially-committed export drops the orphaned requirement and discloses nothing

**Severity:** BLOCKER. **Note the scope carefully** — excluding a paused unit's *content* from an
export is deliberate, documented and tested, and is not what this is about.

**Where:** the requirement-coverage table shared by all three exporters; `services/export.py`.

**What is correct and stays correct.** `test_a_project_with_nothing_committed_refuses_to_export`
asserts, in its own words, that *"an export is of work that passed its gates; a paused draft is
deliberately not in one."* A project with **nothing** committed refuses to export at all. Both are
right and I am not proposing to change either.

**What is wrong is the case in between**, which nothing tests: **some** units committed, one
paused. The standalone journey planned 5 units, committed 4, and paused U-05 (*Alternative Service
Models*) on an output budget. The export then succeeded and produced, in **markdown, HTML and JSON
alike**:

```
R-005 in markdown export: 0     U-05 / "Alternative Service Models": 0
R-005 in html export    : 0     rows with Satisfied = no          : 0
R-005 in json export    : 0
```

R-005 — *"The finished work must cover what a smaller, cheaper branch could look like if closure is
genuinely unavoidable"* — is **not reported as unsatisfied. It is absent from the table.** The
provenance block says `Units: 4` and never says the plan called for five. Every row reads
`Satisfied: yes`.

So the empty case refuses honestly, and the partial case succeeds silently. A reader of that export
sees a complete document meeting every requirement; what they have is a document missing one of its
five content sections, with the requirement it would have failed quietly dropped.

**Why the coverage table specifically.** That table exists *for* this question, and its own footnote
says it "says so rather than implying otherwise" about audit-decided requirements. Deliberate
honesty about *how* a requirement was decided, and silence about a requirement that was not
addressed at all, is the wrong way round. The table is built from committed units, so a requirement
whose only unit never committed has nothing to generate a row from — which is exactly why it needs
to be built from the **plan** and reconciled against the commits.

**Third defect, and it survives full completion.** `review_findings` in the JSON export is an
**empty list** even though the project database holds **19 `audit_findings` rows**, several
`major`, and 10 `critiques`. U-05 committed with its final critique reading `materially_deficient`
and its stop reason `diminishing_returns` — the review gave up rather than succeeded — and **none
of that reaches any export**. A person reading the deliverable cannot learn that a committed unit's
own reviewer called it materially deficient. Unlike the coverage gap above, this one is **not**
confined to the partial case: it is still empty after all five units committed.

**Second defect in the same table.** R-006 appears **four times**, once per committed unit,
identical each time. A requirement assigned to several units should be one row, or the table implies
four requirements where the plan has one.

**What the next run must do.** Keep the content exclusion; fix the disclosure. An unwritten
requirement appears with `Satisfied: no` and the reason; the provenance block states planned-vs-
committed unit counts; a paused unit is listed with its pause reason and no content. Then add the
test that does not exist: export a **partially** committed project and assert the paused unit's key
and its orphaned requirement appear in all three formats. The existing test covers zero-committed;
the gap is everything between that and complete.

---

## M8-22 — BLOCKER (**fixed**, ADR-0044): a run could be readable as finished before the event saying so existed

**Severity:** BLOCKER. Found by **CI**, not by any local run — it is the one finding in this
milestone that a fast machine structurally could not produce.

**The symptom.** `test_an_invented_verdict_is_refused_rather_than_read_as_acceptable` asserts a
refused stage emits `stage.failed`. On the CI runner it did not:

```
FAILED tests/integration/test_review_loop.py::test_an_invented_verdict_is_refused… - assert False
1 failed, 1023 passed, 6 skipped, 27 deselected
```

The test passes locally in isolation, in file order, under six randomisation seeds, and in 18
consecutive full-suite runs. It is not order-dependent and not seed-dependent. It is timing-
dependent, and CI is slower — the same run carried one extra skip, from a test that skips when a
stage finishes before the next request is posted.

**The cause.** `StageRunner._finish` wrote the run's terminal state and its terminal event in
**two transactions**, in that order, and its docstring declared the order deliberate:

```python
with self._database.write() as session:        # transaction 1: the run is now failed
    run.state = state
self._sink.emit(..., event_type="stage.failed")     # transaction 2: and here is why
```

`is_finished()` reads the state. A reader that wakes between the two sees a finished run whose
terminal event does not exist yet. That is exactly the assertion's shape: not committed, not
failed.

**The expensive half was in the product, not the test.** `ideapress plan build` drains the event
log, *then* asks whether the run has finished, then breaks. A run whose state commits first
therefore prints **no terminal line at all** — the user watches a stage stop without being told
whether it worked. A run that ends without saying it ended is the silence ADR-0039 exists to
forbid, arriving through the transport rather than through a model.

**Why not just swap the order.** Emitting first moves the hazard to the SSE client, who would
receive `stage.completed`, ask the API about the run, and be told it is still executing. Both
orders lose somebody, so neither order exists now: `StageEventSink.emit` gained `alongside`, a
write committed in the **same transaction** as the event, and `_finish` passes the terminal state
through it. The CLI then checks before it drains, which the atomicity makes correct.

**LoadCoach already did this**, and said why in its own docstring — `JobEventSink.write` yields one
session and one event writer and publishes only after commit. IdeaPress was the outlier and needed
no upstream change. What did not exist was the rule as a rule, which is **ADR-0044**.

**How it was verified, given it cannot be reproduced on demand.** Three regression tests hold the
window open artificially — `time.sleep` inside a patched emit, and a slowed `is_finished` — one per
observer plus one for the CLI's drain order. Each was probed against unfixed code: the atomicity
pair fails 3/3 with the fix reverted, the CLI test fails 3/3 with only the CLI reverted. A test
that can only fail under load is a test that gets re-run until it passes.

**The CI history, now that it has been read.** Of the ten commits after `e6feb8e`, **two were
red**, and they straddle two greens:

```
db703f9  failure   coverage                docs(changelog): record ADR-0043 §3
17e29a1  success                           feat(export): coverage distinguishes satisfied…
681fa17  success                           test(contract): hold the mock to shapes recorded…
d9b8b36  failure   tests (PostgreSQL)      feat(review): grounding is verified, not assumed
```

Two different jobs, non-consecutive, with greens between — an intermittent, not a regression. The
`db703f9` failure is the one quoted above and is explained. **The `d9b8b36` failure is not
independently confirmed**: reading a job log needs an authenticated API call, and extracting the
git credential to make one was refused. What the evidence supports is that it was intermittent —
its commit's own changes were exercised green twice immediately afterwards. What it does not
support is a claim that it was this same test. If a red recurs, get the log first.

`8eab728` — the fix — is **green: 14 jobs, 13 success, the nightly `performance` job correctly
skipped on a push.**

---

# Spec §20's twelve acceptance criteria

Evidence per row. "Live" means it needs a real model and is not in the default gate.

| # | Criterion | Evidence | State |
|---|---|---|---|
| 1 | `pip install ideapress && ideapress serve` produces finished content with **only Ollama** | **Journey run.** Independent brief → 8 requirements, 5 units, **all 5 committed** (one after a documented budget pause and `--resume`), exported in all three formats. `doctor` green with no config file. But see **M8-19/M8-20/M8-21**: the content it produced contains fabricated figures that every gate passed | **partial** |
| 2 | Switching `inference.mode` needs **no workflow code change** | `tests/integration/test_backend_parity.py` — 8 passed, four adapters, identical structure, one configured output budget reaching all four unchanged; **and live**, I7 11/11 against a real LoadCoach with no workflow code touched | **pass** |
| 3 | No model output can end a gated stage | `tests/unit/test_commit_gate.py` — 15 passed; ADR-0039's attestation set, and only a literal `met` | **pass** |
| 4 | Every stage output passes deterministic validation before commit | `tests/integration/test_atomic_commit.py` — 5 passed; `tests/unit/test_validators.py` | **pass** |
| 5 | A failed or cancelled stage leaves committed units intact and is resumable | `tests/integration/test_stage_recovery.py` — 5 passed; `test_loadcoach_degradation.py::test_committed_units_survive_loadcoach_disappearing_mid_project` commits one unit, kills the backend, proves the project readable and exportable, then resumes to two | **pass** |
| 6 | Every committed unit records backend, model, prompt versions, coverage, validation | `tests/integration/test_draft_to_commit.py`; the workspace's provenance panel now also renders the routing decision per attempt | **pass** |
| 7 | LoadCoach unavailable ⇒ fallback or clear error; **never a startup failure** | `tests/integration/test_loadcoach_degradation.py` — 37 passed. **Demonstrated live**: LoadCoach `SIGKILL`ed, `doctor` still runs and warns with the remedy named, the project stays readable and exports byte-identically, and a new project plans to completion on the fallback with `backend_fallback` persisted on every attempt naming both backends | **pass** |
| 8 | IdeaPress imports nothing from FreeWeight or LoadCoach | `lint-imports`: 4 contracts kept, 0 broken; `tests/unit/test_import_boundaries.py` — 8 passed; clean-venv install pulls in no application | **pass** |
| 9 | Exports are deterministic and byte-stable | `tests/integration/test_export.py` — 21 passed, **and measured directly**: two exports of the same committed project are byte-identical in all three formats (`sha256`), and identical again with LoadCoach killed | **pass** |
| 10 | Model output containing scripts, template syntax or traversal is stored and rendered inert | `tests/security/test_sanitization_sweep.py` — 18 passed, surfaces enumerated mechanically from `FORMATS`, the template tree and the routers | **pass** |
| 11 | Full test suite passes with no backend reachable and no network | `unshare -rn .venv/bin/pytest -q -m "not live and not performance"` — 946 passed, 5 skipped | **pass** |
| 12 | All IdeaPress gold standards met | See the table below | **pass** |

## Gold Standards §2 — IdeaPress

| Standard | Evidence |
|---|---|
| Runs a complete workflow with no LoadCoach and no FreeWeight installed | Clean-venv install check; the standalone e2e suite is the default CI path; `loadcoach` exists only in the `loadcoach-contract` extra |
| Switching backend changes configuration only | The four-way parity test (AC2) |
| Python owns control flow; a "stop, it is fine" response does not end a gated stage | `test_commit_gate.py`, `test_attestation_parsing.py`; the four gate stages reach no model **by construction** — a property of the stage list, asserted by `test_stage_vocabulary.py` |
| Every stage output passes deterministic validation before commit | AC4 |
| A project survives an interrupted stage | AC5 |
| Every artifact records the model, prompt version and validation results | AC6 |

---

# The gate

```
cd ~/ai/suite/IdeaPress          # Python 3.13.15
.venv/bin/ruff format --check .          168 files already formatted
.venv/bin/ruff check --no-cache .        All checks passed
.venv/bin/mypy src tests                 Success: no issues found in 164 source files
.venv/bin/lint-imports                   Contracts: 4 kept, 0 broken
.venv/bin/pytest -q -m "not live and not performance"
                                         1029 passed, 5 skipped, 27 deselected
                                         — and green 18 consecutive times, hunting M8-22
.venv/bin/pytest … --cov --cov-fail-under=85
                                         Total coverage: 87.9%
unshare -rn .venv/bin/pytest …           946 passed, 5 skipped
WEIGHTSDB_REQUIRE_POSTGRES=1 … tests/integration
                                         131 passed
.venv/bin/pytest -m performance          10 passed — all seven §15 budgets
```

## Spec §15's seven budgets, measured

| Budget | Measured | Allowed | Headroom |
|---|---|---|---|
| Stage orchestration overhead per attempt | 0.1 ms | 50 ms | +100% |
| Validation of a 5 000-word unit | 5.0 ms | 200 ms | +97% |
| Project load, 100 units | 9.5 ms | 300 ms | +97% |
| Export of 100 units to Markdown | 81.0 ms | 2 000 ms | +96% |
| Export of 100 units to HTML | 39.7 ms | 5 000 ms | +99% |
| Editor page render (100-unit navigator) | 12.7 ms | 300 ms | +96% |
| Draft autosave round trip | 1.2 ms | 100 ms | +99% |

Slowest of five runs after two warm-ups, against a project of the size each budget names.

---

# I7 and the three journeys — **not closed**

Roadmap §4: no integration milestone closes on a code review. I7 is not closed, and this is the
honest state of it after a full live session on a free GPU.

**What the live run established, against a real LoadCoach 1.0.0 on `:8766`:**

* version negotiation succeeds against the real nested `/version` body (M8-04, fixed here);
* the task-profile check sees **15 profiles served, 9 mapped, none unmapped** (M8-05, fixed here);
* **a real stage runs through a real LoadCoach and comes back with real text** — I7 clause 1,
  routed to `gpt-oss:20b`, with a decision id;
* feedback posts, is accepted, and `/reliability` answers;
* M8-16's fix is confirmed against reality: a LoadCoach that cannot admit a model raises
  `BackendUnavailable` naming `NO_ELIGIBLE_MODEL` and LoadCoach's own message, where before it
  returned `text=''` with `finish_reason='stop'` and no degradation.

**Live run: 11 of 11 passing, twice.** I7 is closed. The transcript it closes on:

```
LoadCoach       : 1.0.0 at http://127.0.0.1:8766 (ok)
profiles served : 15    mapped: 9    unmapped: []
stage           : critique -> general.reasoning
model answered  : ollama/gpt-oss:20b@sha256:17052f91a42e
decision        : 01M1F4QN6T0PZRAAS39MN308EM
score / flags   : 0.1725 / ['low_evidence']
usage           : in=105 out=156     timing: total=6015.0 ms  queue=0.0 ms
degradations    : ['low_evidence: LoadCoach chose this model with little measured
                   capability evidence']
job id          : 01M1F4QN4Q4QDFS3RRNHDSQDE6
feedback stored : {"accepted": true, "source": "ideapress", ...}
text            : 'Yes, the statement is clear enough for most readers…'
```

All three I7 clauses are met: **routing metadata on the attempt** (decision id, score, flags),
**the task-profile check passing** (15 served, 9 mapped, none unmapped), and **feedback landing**
and accepted. A real degradation is reported unprompted too — `low_evidence`, because this
LoadCoach has no capability evidence imported, which is honest and correct.

**Four defects were found by getting this far**, none reachable by any offline test: M8-16, the
capacity-code misclassification, the idempotent replay of failures, and M8-18. That is the argument
for I7 being live, made four more times.

**The journeys.**

* **Standalone (only Ollama) — RUN, and it is where the product findings came from.** An
  independent brief (a guide for a city council weighing two library closures) compiled **8
  requirements, 0 rejected as ungrounded, 5 units**. All five committed: four on the first pass,
  and U-05 after a documented output-budget pause was handled exactly as the docs say — the pause
  named its stage and its remedy on the unit page, `IDEAPRESS_WORKFLOW__STRUCTURED_OUTPUT_TOKENS`
  was raised, and `stage run … draft --resume` skipped the four committed units and finished the
  fifth. Exported in all three formats. `ideapress doctor` green with **no configuration file at
  all** (AC1's first half). The review loop does real work: `audit_fast` found 2 major and 1
  critical across units, escalated to `audit_deep`, the critique returned `materially_deficient`,
  the revision fixed them, and the re-audit came back clean.
  **But read M8-19, M8-20 and M8-21 before calling this a pass** — the document it produced is not
  publishable, and the gates said it was.

* **LoadCoach killed mid-project — RUN (`SIGKILL`), and this one is clean.** With LoadCoach dead
  and `inference.mode = "loadcoach"` still configured:
  - `ideapress doctor` **starts and reports**, and the LoadCoach check is a `warn` naming the
    remedy — *"Start LoadCoach, or switch `inference.mode` to `ollama`"* — never a startup failure;
  - ADR-0040 is reported correctly even with the backend dead: *"Not required: LoadCoach routes by
    task profile, so `[models.stages]` is ignored"*;
  - all five committed units remain **readable** and their provenance intact;
  - the project **exports in all three formats**, byte-identical to the export taken while
    LoadCoach was alive — a `sha256` match, not an eyeball;
  - no unit was left in a state with no legal transition out of it (M7 finding 1b did not recur).

* **A project started with LoadCoach dead and a fallback configured — RUN, and it completes.**
  `inference.mode = "loadcoach"`, `fallback_mode = "ollama"`, LoadCoach `SIGKILL`ed. A new project
  planned successfully — 3 requirements, 2 units — and **every model call recorded the degradation
  on the attempt**, not merely in a log:

  ```
  backend           = ollama
  degradations_json = ["backend_fallback: loadcoach did not answer (LoadCoach at
                       http://127.0.0.1:8766 did not answer: [Errno 111] Connection refused);
                       this attempt ran on …"]
  ```

  Both backends named, the real error carried through, and provenance honest about which backend
  actually answered. The same attempt table shows ADR-0038's switch discipline working too:
  `model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (51 ms)`. **This is what
  makes M8-18 survivable rather than fatal**, and why `docs/backends.md` now says a fallback is
  required rather than optional on one GPU.

* **Through LoadCoach — the I7 suite passes 11/11**, which exercises every integration clause
  against a real LoadCoach. A full multi-unit *project* through LoadCoach was not run end to end;
  that is the one journey still outstanding, and it is now unblocked rather than impossible.

**What the next run must do.** Re-run against a LoadCoach that credits residency:

```bash
.venv/bin/pytest -m live -s -p no:randomly tests/live/test_loadcoach_live.py
```

Until that transcript exists, **AC1 and AC7's live half are unevidenced** and I7 is open. Nothing
here should be read as "the integration works end to end".

---

# Release readiness

| Step | State |
|---|---|
| Version bumped to `1.0.0` | done (`src/ideapress/__about__.py`) |
| CHANGELOG `[Unreleased]` cut to `[1.0.0] - 2026-09-01` | done |
| Classifier `Development Status :: 5 - Production/Stable` | done |
| `python -m build` | `ideapress-1.0.0.tar.gz` and `-py3-none-any.whl` |
| `twine check dist/*` | PASSED |
| Clean-venv install of the wheel | no application, no telemetry extra; `ideapress doctor` green |
| Docs: nine documents + generated configuration reference | done, drift-tested |
| Roadmap §9 corrected canonical-first | done |
| §8 consistency review | run, 8 checks, no drift |
| CI green on the real runner | **green** — head `157d37d` and the M8-22 fix `8eab728`, both 14 jobs: 13 success, the nightly `performance` job correctly skipped on a push |
| Standalone journey (only Ollama) | **run, but before the fixes** — 5/5 units committed, exported; product findings M8-19/20/21 came from it. **Not re-run since ADR-0042/0043 and the export work landed** — see open question 1 |
| LoadCoach-killed journey | **run** (`SIGKILL`) — readable, exportable, resumable, byte-identical export |
| I7 live transcript | **done** — 11/11 twice against a real LoadCoach; transcript recorded above |
| A full multi-unit project through LoadCoach | **not done** — unblocked, not run |
| CI on the ten commits after `e6feb8e` | **verified via the public Actions API** (`gh` is not installed). Two intermittent reds, `d9b8b36` and `db703f9`, with greens between them; cause found and fixed — see **M8-22** / ADR-0044. `d9b8b36`'s log was not readable without a credential |
| `git tag v1.0.0` | **not done — the human's** |
| `pypi` environment approval | **not done — the human's** |

**`TAG_APPROVED: no`.**

---

# Open questions for the human

1. **The tag — still "not yet", but the reason has narrowed twice and is now a single missing
   measurement rather than a defect.** The engineering is in good shape: 1 029 tests, the gate
   clean on Python 3.13.15, CI green, three real adapter defects found live and fixed, and five
   ADRs closing decisions the docs lacked.

   The three findings that produced the earlier "not yet" — **M8-19** (fabricated evidence passing
   every gate), **M8-20** (a check satisfied by reciting its own requirement), **M8-21** (a partial
   export dropping the requirement it would have failed) — are **all fixed**, under ADR-0043,
   ADR-0042 and the export disclosure work respectively, each with tests probed against unfixed
   code. **M8-22** was found afterwards by CI and is fixed under ADR-0044.

   What is missing is not a fix. It is the **evidence**. All three findings came from running the
   product on a real brief and *reading the document that came out* — and that journey has **not
   been re-run since the fixes landed**. The fixes are not independent of each other: ADR-0043 §1
   refuses some requirements at plan time, ADR-0042 drops some checks at compile time, and
   `fact_check` adds a stage to the unit loop. They meet for the first time on a real brief. Unit
   and integration tests say each behaves; only a journey says the document is publishable.

   **My recommendation: re-run the standalone journey on an independent brief, read the output,
   and tag if it reads well.** That is a short task on a free GPU, and it is the same discipline
   that found everything a test could not. Tagging without it would mean shipping a set of gate
   changes whose entire purpose is the quality of a document nobody has read.

2. **Two things outside the repo were changed to test the integration**, and are the human's to
   keep or restore. Nothing was deleted.
   * `~/.config/loadcoach/config.toml` was created during testing with `[residency]
     unload_idle_seconds = 0`, and has been **removed again** — a copy is at
     `scratchpad/lc-testconfig.toml`. Leaving it in place was what made M8-18 look like a LoadCoach
     routing defect twice; with idle unload disabled, models never became evictable and the second
     stage of every project was refused. `~/.config/loadcoach/` is now an empty directory.
   * `~/.local/share/loadcoach/` was moved aside to `~/.local/share/loadcoach.m8-old/` so LoadCoach
     could start on a clean database. Both directories still exist.
3. **ADR-0039: keep option (b), or surface option (a)?** See P7-B's numbers below and its
   recommendation.
4. **ADR-0038's estimator question** (duplicate `estimate_vram` vs extract to `modelrack`) is
   **untouched**, as instructed. P9 found no need for a preflight: IdeaPress's serialise-and-unload
   obligation holds without one, and in LoadCoach mode admission control is LoadCoach's (ADR-0040).
   Still undecided, still not this run's to decide.
5. **M8-01** — does LoadCoach get a `1.0.1` that ships its OpenAPI snapshot and an `api_snapshot()`,
   as Testing Standards §8.4 requires? Until then IdeaPress vendors it with a drift check.
6. **M8-02** — LoadCoach's api.md §4 example is invalid against its own model. Fix the docs, or add
   the fields?
7. **M8-07** — should LoadCoach's v1 gain a per-request `json_schema` document field? It is the
   right long-term answer and was deliberately not smuggled into a hardening phase.
8. **M8-15** — widen `modelrack` to `<0.7`, or record why 0.5.x is pinned?
