# ADR Gap Review — 102 records, five categories, 21 findings

**Review date:** 2026-09-07 · **Scope:** `docs/adr/0001`–`0102` (the brief said 0104; `0103` and
`0104` do not exist yet — the highest record on disk and in the index is `0102`), the master
architecture, the standards, the two arc roadmaps and all 45 handoffs in `docs/history/`. Read-only:
nothing outside this file was written.

## Verdict

The ADR set is unusually good and unusually well cross-referenced — the amendment discipline works,
the back-notes are mostly present in both directions, and the recent records (0085–0102) are written
tightly enough that a newcomer could act on them. The failures are concentrated in three places and
they are all the same failure: **a decision that was taken, argued and confirmed by the operator, and
then deliberately left out of the ADR set because the row that found it was scoped to something
else.** Three of those are contradictions a reader would act on and get wrong — LoadCoach's `usage`
object breaking ADR-0016 on two of five fields in a shipped 1.0 API, ADR-0062's "the `Provider`
protocol does not change" against a protocol that gained two methods, and ADR-0063's "at most one
`lora` entry" against a wire that now sends every registered adapter. A fourth, ADR-0011's
second-consumer extraction trigger, has fired so completely that the ADR's own sizing argument is
off by a factor of seven and the record still reads as if nothing happened. Structurally, twelve
ADRs — including five of the last thirty — ship with no "Revisit when" section at all, against the
directory's own stated rule that a decision without one is a decision nobody can safely revisit. And
one cross-cutting concern named in the gold standards (the OpenAPI snapshot as the contract for API
bodies) is simply not true of the code, with the substitute decided inside one application's test
docstring. None of this is rot; all of it is debt of the kind this directory was built to prevent.

## Top findings

| # | Finding | Records | Severity |
|---|---|---|---|
| 1 | LoadCoach's `usage` renders `null` on two fields and `"unsupported"` on three, in one object, in a released 1.0 API. Flagged in C6 as needing an ADR; none written | 0016, 0009, 0070 | **High** |
| 2 | ADR-0011's second-consumer trigger has fired; two LoadCoach HTTP clients of 1 422 and 1 291 lines exist, and the ADR still says one consumer, ~200 lines, eight calls | 0011 | **High** |
| 3 | ADR-0063 rules 1–2 ("at most one `lora` entry") are contradicted by the shipped wire; the operator confirmed the new reading *without amending the ADR* | 0063, 0062 | **High** |
| 4 | ADR-0022 §3 — the suite's most load-bearing cross-application contract — carries no "Amended by" note for 0085 or 0086 | 0022, 0085, 0086 | **High** |
| 5 | The OpenAPI snapshot discipline in G6/G7, api-standards §11 and testing-standards §8.4 does not exist as written; IdeaPress commits no snapshot at all | — | **High** |
| 6 | ADR-0016 and ADR-0030 carry no "Amended by" note for ADR-0070's carve-out; CLAUDE.md still states 0016 unqualified | 0016, 0030, 0070 | **High** |
| 7 | ADR-0062 decision 1 states the `Provider` protocol does not change; it gained `list_adapters` and `register_adapters`, confirmed and left unrecorded | 0062, 0007 | High |
| 8 | ADR-0078 rule 5's migration obligation is undischarged after four PromptCadence releases | 0078 | Medium |
| 9 | Twelve ADRs have no "Revisit when" section, five of them recent | 0038–0044, 0073, 0075, 0076, 0084, 0085 | Medium |
| 10 | ADR-0013's client obligation (version negotiation on first contact) is unimplemented in PromptCadence and implemented in IdeaPress; nothing records the split | 0013 | Medium |

---

## 1. Decisions taken in code or handoffs that no ADR records

**1.1 — `usage.input_tokens` / `usage.output_tokens` render `null`, not `"unsupported"`. High.**
ADR-0016 rule 4 (`0016-unavailable-is-not-zero.md:46`) is unambiguous: "**JSON:** the string
`"unsupported"`. Never `null`, never `0`", and ADR-0009 rule 5 repeats it for writers. LoadCoach's
job document and execution outcome render one `usage` object in which `cache_write_tokens`,
`cache_read_tokens` and `thinking_tokens` correctly emit `"unsupported"` while `input_tokens` and
`output_tokens` emit `null` for the same condition — `services/queue.py:1416-1430` and
`services/execution.py:545-560`, fed by `_count()` at `services/execution.py:632-634`, whose own
docstring says it returns `None` "when it was not reported". `C6_HANDOFF.md:145-157` found this,
declined to fix it because it changes a field's type on a released `1.0` API, and wrote: "**It
should become a small ADR.**" No such ADR exists, and the defect is still live in the prepared
`loadcoach 1.1.2`. **What the missing record should say:** whether a `1.0` response may keep two
fields on the pre-ADR-0016 spelling until `/api/v2`, and if so that the divergence inside one object
is deliberate and named — because a consumer today reads one object where `null` and `"unsupported"`
mean the same thing on different keys.

**1.2 — The `Provider` protocol gained two methods and no record says so. High.**
`0062-llamacpp-serves-adapters-through-a-supervised-process.md:43` states "**The `Provider` protocol
does not change** — it already has exactly these methods". `py/ModelRack/src/modelrack/provider.py`
now declares `list_adapters()` (line 488) and `register_adapters()` (line 511) on the protocol.
`F3_HANDOFF.md:327-334` records the change, calls it "**the decision most worth a second opinion**",
and `F3_HANDOFF.md:395-398` records the operator confirming it — explicitly "**without an ADR
recording the expansion**". ModelRack's spec §7 (`packages/modelrack/spec.md:104-105`) does carry the
new methods, so the normative surface is documented; what is not documented is that ADR-0062's
sentence is now false. **What the missing record should say:** that the adapter inventory belongs on
the protocol rather than on the concrete provider, because the alternative is `isinstance`-checking
`LlamaCppProvider` in LoadCoach — and that ADR-0062 decision 1 is narrowed to the load/unload seam it
was actually about.

**1.3 — PromptCadence does not negotiate LoadCoach's API version. Medium.**
`0013-api-versioning.md:23` requires clients to "check compatibility on first contact and fail with
`API_VERSION_UNSUPPORTED`", and api-and-contract-standards §12 obligation 1 adds the TTL cache.
IdeaPress implements exactly that (`infrastructure/backends/loadcoach.py:473-492`, with
`_version_checked_at` and `_VERSION_CACHE_SECONDS`). PromptCadence's `LoadCoachClient` defines
`version()` at `infrastructure/loadcoach.py:884` and **nothing in `src/` calls it** — the only
LoadCoach pre-flight is a health read (`services/loadcoach_status.py`). The application ADR-0045 says
reaches a model *only* through LoadCoach is the one that never asks LoadCoach what it speaks.
**What the missing record should say:** either that PromptCadence is exempt because the contract test
pins the vendored snapshot, or — more likely — that this is a defect and a row owns it.

**1.4 — Three applications, three failure modes for one unreadable settings row. Medium.**
`I8_I9_HANDOFF.md:428-460` item 2: FreeWeight raises at startup on a stored settings row it cannot
coerce (`apply_stored` feeds it through `Settings.model_validate`), where LoadCoach and PromptCadence
fall back to configuration and keep serving. It is named in ADR-0102's Consequences as *unfixed*, not
decided. **What the missing record should say:** which behaviour is the suite's — a row written by a
version with wider bounds is either "a row this build cannot read" (serve on) or a refusal to start,
and it cannot be both across three applications built on one idea.

**1.5 — FreeWeight's runtime-settings refusal is an allowlist; the other two are
blocklist-plus-registry. Medium.** Same handoff, item 3, which notes that FreeWeight has the
**stronger** direction (a security-relevant key nobody remembered to forbid is config-only by
default) and that convergence should go that way. This is a security posture recorded in a handoff
paragraph. ADR-0100 reasoned the blocklist for PromptCadence; nothing states the general rule.
**What the missing record should say:** that a runtime-changeable set is an allowlist, or that the
two shapes are both acceptable and why.

**1.6 — One application spells the adapter key two ways on purpose. Low–Medium.**
`H5_HANDOFF.md` §5 closing note: `capability_evidence.adapter_artifact_digest` carries the digest
while `reliability_stats.adapter_key` carries the adapter's **row id**, "same idea, different
spelling, for a stated reason" (imported evidence may name an adapter that has never been on this
machine). The reason is sound and lives only in the handoff; ADR-0086 decides the evidence column and
says nothing about its neighbour. **What the missing record should say:** one sentence in ADR-0086's
consequences naming the reliability spelling and why it differs, so the next reader does not
"harmonize" them.

**Not findings.** Several handoff decisions marked "no ADR" are correctly covered by an authoritative
default and I checked each: I2 decision 5 (`turn_overrun` vs `STEP_LIMIT_EXCEEDED` → PromptCadence
spec §13); I8/I9 D1–D4 (→ configuration standards §7 and ADR-0100/0101); H4's panel composition
(→ ADR-0089 and the benchmark catalogue); E4's ten edge decisions (→ PromptCadence spec §12 and
lifecycle §5); I4's `args_sha256` fix (→ a docstring contract it restored, plus the changelog);
G1's `corrective_retries` (→ spec §12); E6's `[provider.fake]` block (→ LoadCoach spec).

## 2. ADRs contradicted, or missing an amendment note

**2.1 — ADR-0022 has no back-note for 0085 or 0086. High.** `0085` header lines 9–13 say it amends
"ADR-0022 §3 (the producer and consumer uniqueness keys)"; `0086` header lines 4–6 say it amends
0085 "and through it ADR-0022 §3". `0022`'s header (lines 3–5) carries an "Amended by" note for
ADR-0032 only. A reader who opens ADR-0022 to implement an evidence importer gets the pre-adapter
uniqueness key — which is precisely the bug ADR-0085 exists to fix (a `1.1` bundle carrying three
subjects imported one and rejected two as duplicates). **Fix:** add "Amended by ADR-0085, ADR-0086"
to 0022's head via a new record or the standing amendment mechanism.

**2.2 — ADR-0016 and ADR-0030 have no back-note for ADR-0070. High.** `0070`'s header states it
amends "ModelRack spec §11 contract 2 … [ADR-0016] is applied, not reversed; [ADR-0030]'s adapter
reconciliation duty now covers cache detail". Whatever the framing, 0070 rule 1 introduces the first
carve-out in the suite's most-quoted rule: *a class the protocol cannot bill is zero, never
unavailable.* Neither 0016 nor 0030 says so, and `CLAUDE.md` still leads with "`Unsupported` is not
zero … never `None` or `0` (ADR-0016)" unqualified. Combined with finding 1.1, a newcomer has no way
to learn from the ADR set alone when a zero is legitimate.

**2.3 — ADR-0063's wire rule is contradicted by the shipped provider. High.**
`0063-one-adapter-at-a-time.md:41` — "The provider sends at most one `lora` entry" — and line 43 —
"The provider sends the single `lora` entry with `scale: 1.0`". `_llamacpp_wire.py:589-602`
(`lora_field`) sends "the complete adapter configuration, always": the selected adapter at `1.0` and
**every other registered adapter explicitly at `0.0`**. `F3_HANDOFF.md:180-218` explains why (a
`b10792` llama-server restores the launch-time set for a request that names none, so an absent field
runs the bare base under *every* adapter) and `F3_HANDOFF.md:395-398` records the operator confirming
the reading "without amending the ADR's wording". The reasoning is right; the record is wrong.
**What the amendment should say:** rule 1 governs *enabled* entries — an entry at scale `0.0` is a
disable, not a second adapter — and a server with no adapters registered still sends no `lora` key.

**2.4 — ADR-0078 rule 5's obligation is undischarged. Medium–High.** Rule 5
(`0078-…:51`) names the migration: "PromptCadence at its next touch, IdeaPress at H3". LoadCoach
ships `tool_calls_assembled` (`services/queue.py:1379`, `services/execution.py:510`). PromptCadence
still reads the superseded fragment field — `infrastructure/loadcoach.py:638` reads
`output.get("tool_calls")` and regroups it locally through `assemble_tool_calls`
(`infrastructure/loadcoach.py:1212`) — across four releases since (1.0.0, 1.0.1, 1.1.0, 1.2.0). So
ADR-0078 rule 3's whole point, that "the grouping … has exactly one implementation and it is the
server's", is still false. **Fix:** either a row, or a note on 0078 recording why the caller stayed.

**2.5 — ADR-0007's protocol block is stale. Medium.** `0007-provider-abstraction.md:24-33` lists
eight methods. The shipped protocol has eleven (`resolve`, `list_resident`, `list_adapters`,
`register_adapters`) plus `refresh` keywords on three of the originals. Rule 2 delegates the
capability list to ModelRack §7, which is normative and current; the method block delegates nothing
and is simply out of date. ADR-0007 carries no "Amended by" line at all.

**2.6 — Three older back-notes missing, mechanically. Medium.** A both-directions check of every
header produced exactly three genuine one-way references, beyond 2.1 and 2.2:

* ADR-0023 header line 4 says it amends ADR-0008 ("measurement subject in execution"); ADR-0008's
  "Amended by" lists 0024 and 0058 only.
* ADR-0028 header says it amends ADR-0012; ADR-0012 has no "Amended by" line at all — the only
  amended record in the set with none.
* ADR-0068 says it amends ADR-0009 additively; ADR-0009's "Amended by" lists 0025, 0022 and 0028.

**2.7 — Label asymmetries, cosmetic. Low.** ADR-0033 says "Amended by ADR-0034"; ADR-0034 files 0033
under "Related". ADR-0031 says "Amended by ADR-0032"; ADR-0032 files 0031 under "Depends on". Both
pairs are internally consistent in substance; only the vocabulary disagrees.

## 3. "Revisit when" triggers that have already fired

**3.1 — ADR-0011: the second consumer arrived, and the extraction did not. High.**
`0011-shared-package-boundaries.md` "Revisit when" bullet 1: "A second consumer of the LoadCoach HTTP
API appears outside IdeaPress → create `LoadCoachClient`, extracted from IdeaPress's adapter and from
the OpenAPI document." ADR-0045 makes PromptCadence reach models *only* through LoadCoach, and
PromptCadence's `infrastructure/loadcoach.py` is **1 291 lines** containing a class literally named
`LoadCoachClient`, beside IdeaPress's **1 422**-line `infrastructure/backends/loadcoach.py`. The ADR's
own rejection reasoning is now false in both of its premises: line 44 says "IdeaPress implements a
thin `LoadCoachBackend` adapter (~200 lines)" (off by 7×) and the Alternatives section rejects "a
package whose only job is to wrap eight HTTP calls" (PromptCadence's client exposes eleven, plus a
strict response parser and an error map). Both applications additionally hand-vendor a 62 KB copy of
LoadCoach's OpenAPI document into `tests/contract/`. `docs/README.md:114` still summarises the
decision as "`LoadCoachClient` deferred". **What the follow-up should say:** extract, or record that
the two clients diverged enough (IdeaPress's stage bindings vs PromptCadence's turn provenance) that
the trigger is judged not to have fired — but say which, because right now the record and the tree
disagree.

**3.2 — ADR-0007: two more providers were implemented and the interface fitted badly. Medium.**
"Revisit when: A second provider is implemented and the interface proves to fit it badly — that is
the moment to reshape, **before 1.0 freezes the API**." `OpenAICompatibleProvider` and
`LlamaCppProvider` both shipped; the second forced two new protocol methods and a fourteenth
capability flag, and F3 called that "the decision most worth a second opinion". ModelRack is at
`0.7.1`, so the pre-1.0 window this trigger names is still open — and nothing has been written into
it.

**3.3 — ADR-0060: the measurement was taken and lives only in a handoff. Medium–Low.**
"Revisit when: the measured serving-mode overhead proves **material on reference hardware** — at
which point the default flips to clean serving." `H4_HANDOFF.md` §4 measured it at **+0.9 %** and
§5 records "**No ADR**, because the measured overhead is not material enough". That is the right
outcome and the right reasoning; the number that discharges the trigger exists in one handoff and in
no specification, so the next reader of ADR-0060 has a live trigger and no way to know it was
evaluated. **Fix:** one line in the adapter serving document, or the roadmap, carrying the figure.

**Checked and not fired:** 0008 (fourth identity field — fired and correctly closed by ADR-0058, with
the back-note present), 0022 (second evidence producer), 0027 and 0066 (second GPU), 0050 (third
mountable package — LoadLedger and Commissioner are two), 0061 (third adapter-inventory reader —
IdeaPress pins by name through LoadCoach and never reads the directory), 0072 (second pricing-file
reader), 0092 (Phase 9's sweep did land — `services/retention.py`, `worker.sweep_retention`), 0098
(the live remote run has not happened), 0014 and 0026 (no multi-user deployment).

## 4. Structural defects in the index

**4.1 — Four index titles differ from the files' own titles. Medium for one, Low for three.**
Mechanically compared, all 102 rows present, all links correct, all statuses consistent:

| ADR | Index title | File title |
|---|---|---|
| 0033 | Benchmark interactions, the two scorer protocols, and **enforced capability requirements** | Benchmark interactions: **multi-turn execution** and the two scorer protocols |
| 0077 | …are one registry | …are one registry, **and both together is a refusal** |
| 0078 | …superseded beside its replacement | …superseded beside its replacement, **never reshaped under it** |
| 0079 | …is a routing rejection | …is a routing rejection, **recorded in the explanation** |

0077–0079 are truncations that drop the load-bearing half of each title (the refusal, the
prohibition, the location of the record). 0033's index title names a subject the file's title does
not, which is the one an index reader could search for and fail to find.

**4.2 — Twelve ADRs have no "Revisit when" section. Medium.** 0038, 0039, 0040, 0041, 0042, 0043,
0044, 0073, 0075, 0076, 0084, 0085. `README.md:20` states the rule: "A decision without a 'revisit
when' trigger is a decision nobody can safely revisit." Two clusters: the IdeaPress M7/M8 records
(0038–0044) and five recent ones (0073, 0075, 0076, 0084, 0085), so this is not only an early-days
lapse. 0073 and 0075 additionally have no "Alternatives considered" section, also mandated by the
format block. 0085 is the worst of them — it is the record every future evidence-key question routes
through and it names no condition under which the key changes again.

**4.3 — The index carries no supersession or amendment column. Low.** Every one of the 102 rows
reads "Accepted". Nothing in the index tells a reader that ADR-0022 §3 has been amended twice, that
ADR-0062 decision 1 is contradicted by shipped code, or that ADR-0063's wire rule has been reread.
The amendment narrative under the table now runs to 40 paragraphs and is the only place this
information exists.

**4.4 — `CLAUDE.md` and `README.md` disagree on the audit's ADR range. Low.** `CLAUDE.md` says
"ADRs 0022–0030 came from it"; `adr/README.md:138` says "ADRs 0022–0029 were added by the final
architecture audit". ADR-0030 is dated 2026-08-22, a day after the audit's 0022–0029. The README is
right.

**Not a finding:** dates are monotonic in ADR number throughout; there are no numbering gaps and no
orphan files.

## 5. Coverage holes in the architecture

**5.1 — The OpenAPI snapshot is not the contract the standards say it is. High.**
Gold standard G6 (`gold-standards.md:18`) says "API bodies contracted by the committed OpenAPI
snapshot"; G7 (line 19) makes the committed snapshot a blocking CI gate; api-and-contract-standards
§11 (line 349) names the artifact `docs/api/openapi-v1.json`; testing-standards §8.4 (lines 146-153)
says each application "**ships its committed OpenAPI snapshot as package data**
(`<app>/api/openapi-v1.json`, loadable through `importlib.resources`) and exposes it as
`<app>.api_snapshot()`", from which a consumer drives a schema-driven mock. Every clause of that is
untrue today:

* No repository contains `openapi-v1.json`, and `api_snapshot` appears in no `src/`. The real
  artifact is `docs/openapi.json`.
* **IdeaPress commits no snapshot at all**, has no test over its own surface, and serves
  `/api/v1/openapi.json` (`web/app.py:260`) from nine route modules. G7 is unmet in one of four
  applications.
* The schema-driven-mock technique cannot work against LoadCoach: **32 of 49 JSON responses in
  `LoadCoach/docs/openapi.json` (version 1.1.2) are bare `{"type":"object","additionalProperties":
  true}`**, including `/api/v1/generate` 200. IdeaPress discovered this and wrote it up in a test
  docstring — `IdeaPress/tests/contract/test_snapshot_coverage.py:9-16`: "a mock cannot be checked
  against it, and agreement with it is worth nothing … the only authority on a response shape is a
  running LoadCoach, so the fixtures are captured from one."
* FreeWeight's snapshot test compares path keys only where LoadCoach's and PromptCadence's compare
  byte for byte, and FreeWeight's snapshot had been stale since its 1.1.0 bump
  (`I8_I9_HANDOFF.md:428-435`).

A newcomer asking "what guarantees a LoadCoach response shape?" finds G6 saying the snapshot,
testing-standards describing a mechanism nobody built, and one application's test file saying the
answer is captured goldens from a live server. **What the missing record should say:** that response
bodies are contracted by captured goldens plus consumer contract tests, that the snapshot contracts
the *surface* (which endpoints exist, what they accept) and not the bodies, and what each application
owes — because the current standards promise something stronger than the code delivers.

**5.2 — Everything else the brief named is covered.** I checked each and found an authoritative
home: multi-user/tenancy → ADR-0014 with an unfired, well-specified trigger, plus ADR-0026 and
ADR-0094 for the console; runtime settings precedence across the three applications → configuration
standards §7 plus ADR-0100, 0101 and 0102 (the residue is findings 1.4 and 1.5, which are behavioural
divergences, not a missing rule); migration-with-foreign-keys-off → ADR-0082; the mounted-tables
upgrade story → ADR-0050 rule 5 plus `docs/mounted-table-upgrades.md`, exercised by
`loadledger 0.2.0`'s "no table, column or index changed" note; thinking control → ADR-0099 with the
I6 probe behind it; evidence uniqueness → ADR-0085 and ADR-0086; approver identity on an open
loopback install → ADR-0094 decision 1 (`approver:loopback`); credential and secret handling →
security standards §§6–8; the `estimate_vram` question ADR-0038 deferred → still one implementation,
so the trigger has not fired.

---

## Suggested order of work

1. One record closing findings 1.1 and 2.2 together — what a `null` means in a shipped `usage`
   object, and ADR-0016's one carve-out — because CLAUDE.md quotes the unqualified rule.
2. One record amending ADR-0062 and ADR-0063 to the shipped reality (findings 1.2, 2.3), since both
   were confirmed by the operator and only the writing-down is outstanding.
3. Back-notes on ADR-0022, ADR-0016, ADR-0030, ADR-0012, ADR-0009, ADR-0008, ADR-0007 (findings 2.1,
   2.2, 2.5, 2.6) — mechanical, and 2.1 is the one that would cost a future implementer a day.
4. A decision on ADR-0011's fired trigger (3.1), stated either way.
5. The OpenAPI record (5.1), because three of the four applications are already living under an
   informal substitute and the fourth has nothing at all.
6. Retro-fit "Revisit when" onto the twelve records that lack it (4.2), starting with 0085.
