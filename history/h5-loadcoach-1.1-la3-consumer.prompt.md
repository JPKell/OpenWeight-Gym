# Kickoff — H5: LoadCoach 1.1 + FreeWeight 1.1 — LA3's consumer half, and the two releases it cuts

**Row:** H5 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**, as scheduled. The judgement is in §0.1 (a decided question that two
ADRs answer differently), in the ordering of §0.2, and in refusing the join that looks like the
feature working.
**Repositories:** `/home/jpk/ai/suite/docs` first (gate A), then `/home/jpk/ai/suite/LoadCoach` (the
weight), then `/home/jpk/ai/suite/FreeWeight` (one live re-export, two follow-ups and one release
commit), and `/home/jpk/ai/suite/PromptCadence` for a **three-line comment deletion** and nothing
else.
**Ships:** **`loadcoach 1.1.0` and `freeweight 1.1.0` prepared, not published.** Version bumps,
changelog moves and release commits are yours; **`git push`, tags and publishes are the operator's**
(standing instruction of 2026-09-04). Do not run a push dry-run.
**Runs after:** **H4** — done, pushed, and `commissioner 0.1.1` is published.
**Runs before:** LA3's PromptCadence half (§4.5, riding I2), which is blocked on this row and on
nothing else.
**Not in this session:** ModelRack, SetSpec (no payload changes here — see §0.3), IdeaPress,
LoadLedger, ToolYard, and every part of PromptCadence except the stale comment.

---

## 0. Machine facts, verified 2026-09-06 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **LoadCoach `main` is at `3f6f1a6`, clean and level with `origin`.** `__about__.py` already says
  `1.1.0` — the release commit `9829361` landed on 2026-09-05 — and `CHANGELOG.md` carries a
  `## [1.1.0] — 2026-09-05` section **and** an `## [Unreleased]` section above it. **There is no
  `v1.1.0` tag and `loadcoach 1.1.0` is not on PyPI**: the release was held by operator decision on
  2026-09-06 so that this row rides it. **Confirm** `git status -sb` in all three repositories at
  the start and at the end.
* **The row says six follow-on commits; there are seven.** `eca8e96`, `e0d811a`, `5f0f254`,
  `cbe1ef9`, `8e72a8a`, `25ce551` **and `3f6f1a6`** — the last landed after the row was written and
  carries the PostgreSQL migration fixes. All seven fold into the `1.1.0` section (§11).
* **Migrations end at `0012_reliability_on_the_subject.py`, so yours are `0013` and `0014`** — one
  per step, per the row.
* **The consumer's uniqueness key lives in four places in `services/evidence.py`, and they must
  move together**: `_uniqueness_key()` at `:284`, the `existing_keys` set at `:588`, the
  `upsert(..., index_elements=[...])` at `:640`, and the `complete`-driven supersede `filter_by`
  at `:682`. The `upsert` one is the one that bites — §0.1.
* **The reader half is already done.** `EvidenceIdentity` carries `adapter_name` and
  `adapter_artifact_digest` (`services/evidence.py:259`–`:266`), and the importer validates through
  `CapabilityEvidenceV1_1In` (`:40`). H2 did that. **No SetSpec change, no payload change, no
  schema-version move anywhere in this row** — ADR-0085 rule 5.
* **`bind_identity` refuses adapter-bearing records on purpose.**
  `domain/evidence_policy.py:206`–`:243`, rule 0, ahead of ADR-0022 §4's four rules: an
  adapter-bearing record is retained `unmatched` with a note naming the adapter. That rule is a
  guard against attaching a LoRA's score to the bare weights (ADR-0058 §4, ADR-0059, ADR-0081).
  **Gate C replaces it with a real subject binding. It does not weaken it and does not delete it
  without a replacement.**
* **Routing reads evidence keyed by model, not by subject.**
  `services/evidence.py:1213` `bound_signals_for_routing` returns `model_id -> signals`;
  `services/routing.py:415` merges that into the **base** candidate only; `:427` `_adapter_signals`
  gives an adapter candidate its manifest's declarations and nothing else. That function's
  docstring states as a rule that an adapter subject's only signals are declarations — **that
  sentence becomes false at gate D and must be rewritten, not left to rot.**
* **`require_adapter_evidence` is what I18 has to flip.** `domain/routing/constraints.py:636`
  rejects an adapter candidate as `adapter_unmeasured` unless a signal for the top-weighted
  capability has `source` in `{"benchmark", "production"}` (`:389`). Today every adapter subject is
  rejected by it. After this row, the measured one is not — and the unmeasured `pirate` still is.
  That contrast **is** the exit demonstration.
* **`reliability_stats` is the shipped precedent for a subject key in this application.**
  `infrastructure/db/models.py:790`ff: `adapter_id` (nullable FK, `SET NULL`) **beside**
  `adapter_key` (non-null `String`, `""` for the bare base), unique constraint named explicitly
  because the convention's name came out 64 characters. Read it before designing `0013`.
* **FreeWeight `main` is at `cb7d411`**, clean and level with `origin` — one commit past what
  `H4_HANDOFF.md` §7 lists (`cb7d411` regenerated the configuration reference). `__about__.py` says
  `1.0.0` and `CHANGELOG.md` still has its `## [Unreleased]`; the `1.1.0` cut is one bump and one
  changelog move.
* **`commissioner 0.1.1` is published** (`pip index versions commissioner` → `0.1.1, 0.1.0`), so
  H4's operator steps are all done and `PromptCadence/pyproject.toml:65`'s comment is stale.
* **The artefacts are present**: `~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf`, three LoRA GGUFs
  under `~/ai/models/adapters/llm/`, and `llama-server` at `~/.local/bin/llama-server`. I18 is
  runnable in minutes; the H4 scratchpad bundle is gone, so **re-export it** (§9).
* **Python: name each repository's interpreter and the exact invocation** (M5C-13). LoadCoach's
  coverage floor is **85 %** (application), FreeWeight's likewise.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 The trap this row will die on if it is taken at face value

**ADR-0085 decision 2 and ADR-0080 rule 5 spell the same column differently, and ADR-0080 is right
about LoadCoach.**

[ADR-0085](docs/adr/0085-the-evidence-uniqueness-key-carries-the-adapter.md) — written from
FreeWeight's side, where the writer is a `replace_for_subject` that matches `IS NULL` explicitly —
says `adapter_artifact_digest` is **nullable**, `NULL` meaning the bare base.
[ADR-0080](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
rule 5 decided the same question inside LoadCoach and decided it the other way, for a reason that
has not changed: *SQLite and PostgreSQL both treat `NULL`s as distinct in a unique index*, so the
bare-base row is written with a **sentinel** — the empty string — and the foreign key column stays
`NULL` beside it.

The consumer's write path makes this decisive rather than stylistic. `services/evidence.py:637`
calls `weightsdb.upsert`, which is `INSERT ... ON CONFLICT (index_elements) DO UPDATE`
(`py/WeightsDB/src/weightsdb/types.py:119`–`:147`). **A conflict target containing a `NULL` never
fires.** Spell the key with a nullable column and every re-import of a bare-base record inserts a
*second* row instead of updating the first: no error, no rejection, the counters say `imported`
for ever, and `bound_signals_for_routing` starts scoring one subject twice. That is a worse defect
than the one this row exists to close, and it lands in the same table.

So: **decide it explicitly (§0.3 decision 1), and write the decision down as `ADR-0086`.** ADRs are
amended by new ADRs, never edited — ADR-0085 gains an `Amended by:` line, ADR-0086 states which
spelling the consumer uses and why the producer's may legitimately differ (a delete-then-insert
writer and an `ON CONFLICT` writer do not have the same constraint).

## 0.2 The order is not negotiable, and the halfway point is not the feature

ADR-0085's consequences say it plainly: **the key first, then the axis.** Until the key moves there
are no surviving records to bind — the two adapter-bearing records are discarded at the uniqueness
check, one step before binding is even attempted.

**And the halfway state looks like progress and is not the exit.** With `0013` in and `0014` not,
the import prints `rejected 0, unmatched 2`. That is the state H2's handoff described and it means
the records survived, nothing more: no subject is scored, no routing decision changes, and
`require_adapter_evidence` still rejects every adapter. **Do not report `unmatched 2` as I18
passing**, and do not cut either release on it.

## 0.3 The decisions this row must take, and record

1. **The key column's spelling.** §0.1. Recommendation: **follow ADR-0080 rule 5** — a non-null
   `adapter_artifact_digest` with `""` for the bare base, in the unique constraint, with a nullable
   `adapter_id` FK beside it for the binding. Write `ADR-0086`. If you take `NULL` instead, you owe
   a demonstration that a bare-base record re-imported twice produces exactly one row, on **both**
   dialects, and `weightsdb.upsert` will not give you one.
2. **What an adapter-bearing record binds to.** ADR-0080's shape — by reference *and* by string —
   is already the house pattern: `adapter_id` FK to `adapters` plus the digest in the key. The join
   is on the adapter's artifact digest, never its name (ADR-0085 rule 3). **Check which side
   carries the `sha256:` prefix before writing it**: `adapters.artifact_sha256` feeds
   `AdapterFacts.artifact_digest`, which `domain/routing/subject.py:152` documents as the
   *normalized* `sha256:` form. A prefix mismatch here is a silent no-match, not an error.
3. **What happens to a record whose adapter this operator does not have.** Recommendation:
   `unmatched`, retained, bound with no re-import the next time the directory scan finds it — the
   same shape as ADR-0022 §4 rule 4 for an undiscovered model. **Not** rejected: a rejection
   discards a measurement because of a local absence, and this row exists because that already
   happened once.
4. **Whether `match_state` gains a value.** Recommendation: **no.** `bound` / `unmatched` /
   `ambiguous_name_only` already describe every case; a fourth value is a migration, a check
   constraint, a UI branch and a vocabulary change to say something the existing three say.
5. **How the routing read is keyed.** `bound_signals_for_routing` must return signals per
   **subject**, not per model. Pick the subject key shape once and make it the same shape the
   reliability code already uses (`(model_id, adapter_key)`), so one application does not carry two
   spellings of one concept.
6. **What an adapter subject may see of its base: nothing.** ADR-0081, ADR-0059, ADR-0058 §4. This
   is the failure that passes every test you would think to write, because a base's evidence
   attached to an adapter subject *looks* like the feature working. Assert the absence, in a test
   named for it, on real data: `pirate` is measured nowhere and must stay unmeasured and
   unroutable after `terse`'s evidence lands.

## 0.4 Two rules that are newer than most of the documents you will read

* **A migration is not proved on SQLite** — `docs/standards/testing-standards.md` §10.1, added
  2026-09-06 after LoadCoach's PostgreSQL job had been red since the LA2 gates. This row writes two
  migrations. Run them against a real PostgreSQL **before** the release commit:

  ```bash
  docker run -d --rm --name pg -e POSTGRES_USER=weightsdb -e POSTGRES_PASSWORD=weightsdb \
    -e POSTGRES_DB=weightsdb_test -p 5432:5432 postgres:16
  WEIGHTSDB_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest tests/integration
  ```

  Without `WEIGHTSDB_REQUIRE_POSTGRES=1` the fixture **skips**, and a skipped dialect is an
  untested dialect. The three traps §10.1 names by name: an integer server default on a boolean
  column, a generated constraint name over PostgreSQL's 63-character limit (name yours explicitly,
  in the migration **and** the model, or `check_parity` disagrees), and `sa.JSON()` /
  `sa.DateTime(timezone=True)` in a migration whose model uses `PortableJSON` / `UtcDateTime`.
* **[ADR-0082](docs/adr/0082-a-migration-run-suspends-sqlite-foreign-key-enforcement.md)** — a
  migration run suspends SQLite foreign-key enforcement. Relevant the moment `0014` adds an FK.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/LoadCoach status -sb
git -C /home/jpk/ai/suite/FreeWeight status -sb
source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show baseaicore setspec modelrack weightsdb | grep -E "^(Name|Version)"
ls ~/ai/models/adapters/llm/ ~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf
```

Every scratch database, config file, adapter directory, exported bundle and log goes in the session
scratchpad — **never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside the component directory. Nothing at the workspace root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional Commit
  per gate**, every path staged by name — never `git add -A`.
* Docstring-first: define behaviour, write the Google-style docstring including what the function
  *refuses*, write the tests against it, then implement.
* Workspace `docs/` is edited first and mirrored into the component; prove every mirror with `cmp`
  before the commit that carries it.
* `UNSUPPORTED` is not zero (ADR-0016). Evidence rows carry measurement columns; the rule applies.
* Name the interpreter and the exact invocation in the gate report (M5C-13).

## 3. Reading list, in this order

1. [`docs/adr/0085-the-evidence-uniqueness-key-carries-the-adapter.md`](docs/adr/0085-the-evidence-uniqueness-key-carries-the-adapter.md)
   — whole, including the four rejected alternatives. Each one is a shortcut somebody will be
   tempted by at about gate C.
2. [`docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md`](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
   rule 5 — then §0.1 of this prompt, then decide.
3. `docs/history/H4_HANDOFF.md` §3 (I18's evidence, both halves, verbatim) and §12 (the two
   follow-ups this row inherits).
4. [`docs/adr/0022-capability-evidence-record-contract.md`](docs/adr/0022-capability-evidence-record-contract.md)
   §3 and §4 — the amended key, and the four binding rules the new rule 0 has to sit inside.
5. [`docs/adr/0081-an-adapter-subject-inherits-no-evidence-from-its-base.md`](docs/adr/0081-an-adapter-subject-inherits-no-evidence-from-its-base.md)
   and [ADR-0059](docs/adr/0059-adapter-evidence-is-measured-never-inherited.md) — decision 6.
6. `LoadCoach/src/loadcoach/services/evidence.py:250`–`:300` and `:575`–`:700` — the identity, the
   key, the upsert and the supersede pass; the whole of gate B.
7. `LoadCoach/src/loadcoach/domain/evidence_policy.py:200`–`:250` — rule 0 and its four successors.
8. `LoadCoach/src/loadcoach/services/routing.py:385`–`:445` — `build_candidates` and
   `_adapter_signals`; the whole of gate D.
9. `LoadCoach/src/loadcoach/infrastructure/db/models.py:768`–`:800` — `reliability_stats`, the
   precedent decisions 1 and 5 follow.
10. `docs/standards/testing-standards.md` §10.1 and `docs/history/H2_HANDOFF.md` §7 — the dialect
    rule, and the LA2 migrations it was written about.

## 4. The shape of the work — seven gates

| Gate | What | Depends on |
|---|---|---|
| **A** | The documents: `ADR-0086`, ADR-0085's `Amended by`, spec, data model, development plan phase | nothing |
| **B** | Migration `0013` — the uniqueness key gains the adapter (all four call sites) | A |
| **C** | Migration `0014` — the adapter axis, and `bind_identity`'s rule 0 replaced | B |
| **D** | Routing and the read paths: signals per subject; `evidence show`, `/evidence`, explanation | C |
| **E** | **I18 whole**, live, two applications, one file | D |
| **F** | The three scheduled follow-ups (§10) | E |
| **G** | Both release commits, both changelogs | E, F |

Gate boundaries are commit boundaries, so the row can be stopped and resumed.

## 5. Gate A — the documents

In workspace `docs/` first, mirrored byte-identically into `LoadCoach/docs/` and (for the FreeWeight
follow-ups) `FreeWeight/docs/`; prove every mirror with `cmp`.

* **`ADR-0086`** — §0.3 decision 1, in the house shape, with the `ON CONFLICT` fact as its evidence
  and the rejected alternative (nullable, as ADR-0085 wrote it) named and refused for a stated
  reason. Add `**Amended by:** ADR-0086` to ADR-0085 and to ADR-0022's amendment block if the key's
  final spelling differs from what ADR-0085 recorded.
* **`apps/loadcoach/data-model.md`** — `capability_evidence`'s new columns and the new unique
  constraint, with the sentinel stated where a reader will look for it (§92ff), and the same
  sentence pattern `reliability_stats` already uses at §299.
* **`apps/loadcoach/spec.md`** — the evidence contract section: an adapter-bearing record binds to a
  subject, an unknown adapter stays `unmatched`, and an adapter subject inherits nothing.
* **`apps/loadcoach/development-plan.md`** — **Phase 11**, in the house shape (Goal, Prerequisites,
  Work, Tests, Acceptance criteria, Known risks, Likely failure modes, Gold standards, Deferred),
  acceptance criteria written as **demonstrable** statements. Phase 10 was LA2; this is its
  consumer completion.

**Commit:** `docs(loadcoach): the evidence key carries the adapter (ADR-0086)`.

## 6. Gate B — migration `0013`, the key

* The column, per decision 1, and the unique constraint replacing `uq_capability_evidence_subject`.
  **Name the constraint explicitly** — the convention's generated name is already 96 characters here
  and the model says so at `models.py:235`; one more column does not improve that.
* Existing rows backfill to "no adapter" — sentinel or `NULL` per decision 1 — and mean exactly what
  they meant before.
* All four call sites in `services/evidence.py` (§0), together, plus `_uniqueness_key`'s docstring
  and the `DUPLICATE_RECORD` detail string at `:610`, which enumerates the key in prose and would
  otherwise lie.
* **Tests:** two adapter subjects on one base under one profile, one machine, one capability now
  produce **two rows and no rejection**; a genuine duplicate — same subject twice in one bundle —
  is still `DUPLICATE_RECORD`; **a bare-base record imported twice produces exactly one row**
  (the §0.1 assertion, on both dialects); the `complete` supersede pass still finds and marks the
  right rows.
* Run §0.4's PostgreSQL command before committing.

**Commit:** `feat(evidence): the uniqueness key carries the adapter (ADR-0085, ADR-0086)`.

**Do not go further in this gate.** The import now prints `rejected 0, unmatched 2` — §0.2.

## 7. Gate C — migration `0014`, the axis

* `capability_evidence` gains its adapter reference (decision 2). `bind_identity`'s rule 0 is
  **replaced**: an adapter-bearing record resolves its base by the existing four rules **and** its
  adapter by artifact digest, binding only when both resolve; an unresolvable adapter is
  `unmatched` with the note it already writes (decision 3).
* The binding re-evaluation that already runs on every discovery pass must also pick up an adapter
  that appears later — a directory rescan binds the record with **no re-import** (ADR-0022 §4).
* **Tests:** a `(base, terse)` record binds to the `terse` subject and **not** to the base; the
  base's own record still binds to the base; a record naming an adapter this operator does not have
  is `unmatched`, then binds after a rescan; **no signal crosses between subjects** (decision 6),
  asserted for `pirate`, which is measured nowhere.
* §0.4's PostgreSQL command again — this migration adds a foreign key (ADR-0082).

**Commit:** `feat(evidence): adapter-bearing evidence binds to its subject (ADR-0085)`.

## 8. Gate D — the read paths tell the truth about subjects

* `bound_signals_for_routing` keyed by subject (decision 5); `build_candidates` merges each
  subject's own evidence into that subject's candidate; `_adapter_signals`' docstring rewritten —
  it is now the declared half of a subject's signals, not the whole of them.
* `require_adapter_evidence` needs no change and gets none: a measured adapter now has a
  `benchmark` signal and passes the gate it always applied.
* Where a person can see it: `loadcoach evidence show` names the subject rather than the base; the
  models/evidence views group an adapter subject's evidence under it; the routing **explanation**
  names the subject whose evidence moved the decision. Route handlers and CLI bodies stay one
  service call plus a render.
* **Tests:** one decision, two candidates on one base, and the adapter selected **because** of
  imported evidence — with the explanation naming it; the same decision with the evidence absent
  selects the base and rejects the adapter as `adapter_unmeasured`.

**Commit:** `feat(routing): a subject's own evidence scores it (ADR-0081)`.

## 9. Gate E — I18, whole, and it is still a two-application demonstration

The exit condition H4 could not reach. Run it live, on this machine, with the real `llama-server`.

1. **Re-export from FreeWeight** — H4's bundle is gone with its scratchpad. Its live test
   (`FreeWeight/tests/live/test_la3_adapters.py`) produces the three-subject `1.1` bundle; the
   invocation and its environment variables are in `H4_HANDOFF.md` §3.
2. **Carry the file.** A file is the only thing that crosses. **Do not import `loadcoach` from
   FreeWeight, do not read LoadCoach's database, and do not read FreeWeight's from LoadCoach** — the
   claim I18 exists to make is that two applications agree with no shared code and no shared
   database, and one convenience import destroys both the demonstration and the boundary.
3. **Import it** through `loadcoach evidence import --file …` and show `rejected 0`, three records,
   **three bound**.
4. **Show a routing decision change**: with the base and `terse` both candidates and a profile
   weighting the measured capability, `terse` is selected and the explanation says why. Then show
   `pirate` — measured nowhere — still rejected as `adapter_unmeasured` in the same run. Capture
   both verbatim for the handoff.
5. Record the exact commands, environment and output. `H4_HANDOFF.md` §3 is the format.

**Commit:** `test(live): I18 — an adapter subject's evidence crosses and changes a decision`.

## 10. Gate F — the three follow-ups this row was given

All three come from `H4_HANDOFF.md` §8.5 and §12, scheduled here by the same 2026-09-06 decision.

1. **Run FreeWeight's A-2 regression panel against a real adapter.** The LA3 journey used
   `native.echo` for speed, so the panel has never met a LoRA. `terse` is the likeliest to have lost
   instruction-following. **A negative result is a result** — it is
   `apps/freeweight/risks.md` T11's revisit trigger either way, and it gets written down either way.
2. **Bound the comparison grouping.** `FreeWeight/src/freeweight/services/evidence.py:2218`
   `group_by_base` is O(records) and `web/templates/evidence/index.html` `rowspan`s every subject. A
   dozen renders; a hundred does not read. A cap with an honest "and N more" is enough; paging is
   not asked for.
3. **Delete `PromptCadence/pyproject.toml:65`'s comment.** It says Commissioner needs widening
   before PromptCadence can adopt one. `commissioner 0.1.1` widened it and was published on
   2026-09-06. Delete the stale sentence, change nothing else in that repository, and do not touch
   its pins.

**Commits:** `test(freeweight): the regression panel, against a real adapter`,
`fix(web): the comparison grouping is bounded`, `chore: the Commissioner widen has shipped`.

## 11. Gate G — the two releases

1. **LoadCoach.** Fold **all seven** post-release commits (§0) into the existing
   `## [1.1.0] — 2026-09-05` section — the release was never published, so its section is still
   editable and a `1.2.0` would announce a version nobody can install a `1.1.0` before. Update the
   date to the day this row cuts it. Add this row's four features to it. `__about__.py` already says
   `1.1.0`; check it, do not bump it twice. Lock recompiled, full gate, **PostgreSQL run**, wheel
   built into the scratchpad and verified in a throwaway venv.
2. **FreeWeight.** `__about__.py` to `1.1.0`, `## [Unreleased]` moved to `## [1.1.0]`, release
   commit, wheel built and verified in a throwaway venv against the published `modelrack 0.7.0`,
   `baseaicore 0.4.2` and `setspec 0.6.0`.
3. **No tag, no publish, no push**, for either.

**Commits:** `chore(release): loadcoach 1.1.0`, `chore(release): freeweight 1.1.0`.

## 12. Exit conditions — all of these, demonstrably

1. `ADR-0086` states the key's spelling and why; ADR-0085 carries its `Amended by`; the data model,
   spec and a Phase 11 with demonstrable acceptance criteria describe the consumer's adapter axis;
   every mirror is `cmp`-identical.
2. Two adapter subjects and their base on one machine, one profile, one capability import as
   **three rows, zero rejections**.
3. A bare-base record imported twice is **one row**, on SQLite **and** on PostgreSQL.
4. An adapter-bearing record binds to its subject, never to the base; a record for an absent adapter
   is `unmatched` and binds after a rescan with no re-import.
5. **No signal crosses subjects**: an unmeasured adapter stays unmeasured after a sibling's evidence
   lands, asserted on real data.
6. **I18 whole**: a `1.1` bundle exported by FreeWeight, carried as a file, imported by LoadCoach,
   three records bound, and an adapter subject visibly selected in the explanation **because** of
   that evidence — with the unmeasured sibling still rejected in the same decision. No shared code,
   no shared database.
7. The regression panel has met a real adapter and the result — either sign — is written down.
8. The comparison grouping is bounded; PromptCadence's stale comment is gone.
9. `loadcoach 1.1.0` and `freeweight 1.1.0` prepared, gated, wheels verified from a clean venv, and
   both migrations proved on a real PostgreSQL.
10. Full gate green in both repositories; interpreter and exact invocations named; coverage ≥ 85 %.

## 13. Closing duties

1. Full gate in LoadCoach and FreeWeight, plus the PostgreSQL integration run; interpreter and exact
   invocations named (M5C-13).
2. **`H5_HANDOFF.md` at the workspace root**, house shape, copied into `docs/history/`: gate
   results; each §0.3 decision and why; **I18's evidence verbatim, both halves and both outcomes**
   (the selected adapter and the rejected one); the regression-panel result; what LA3's PromptCadence
   half (§4.5, riding I2) inherits now that adapter evidence binds; **and anything this prompt said
   that turned out not to be true**.
3. Say plainly what is left for the operator: push three repositories (four with PromptCadence), tag
   and publish `loadcoach 1.1.0` then `freeweight 1.1.0`, verify both published wheels.
4. Record any model deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H5 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form, and
   record **LA3 complete** in the adapter-roadmap §3 table — both halves, with I18 as the evidence.

## 14. Stop rules

* **Do not cut either release on `unmatched`.** §0.2. Records surviving is not a subject being
  scored.
* **Do not let an adapter subject read its base's evidence**, and do not let a base read an
  adapter's. ADR-0081, ADR-0059, ADR-0058 §4 — the single failure this row exists to prevent, and it
  looks exactly like a working join.
* **Do not key on the adapter's name.** ADR-0085 rule 3: a rename would merge two adapters'
  histories, and a re-export under a new label would split one.
* **Do not put the adapter in `model.canonical_id` or in the runtime profile hash.** Both are
  rejected alternatives in ADR-0085, the second by ADR-0060 before it.
* **Do not de-duplicate by last-write-wins.** It is the silent version of the bug being fixed.
* **Do not import LoadCoach from FreeWeight or read either application's database from the other.**
* **Do not push a migration proved only on SQLite** — §0.4, and it is a written standard now.
* **Do not weaken `.importlinter`, `extra="forbid"`, or the domain's framework purity**; do not put
  business logic in a route handler or a CLI body; do not let `UNSUPPORTED` become `0`.
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 15. If you finish with capacity left

Read-only, in priority order: (a) what LA3's PromptCadence half (§4.5 — tier profiles weighting
adapter-relevant capabilities) can now actually weight, as a note for I2. (b) Whether
`reliability_stats`' production evidence and `capability_evidence`' benchmark evidence agree on one
subject key spelling everywhere, or whether the two arrived at different strings for one subject.
(c) Whether anything else in the application still reads evidence keyed by model where it now means
subject — grep for `bound_signals_for_routing`'s callers and for `model_id` beside `capability_id`.
