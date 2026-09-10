# Kickoff — WA1: SetSpec 0.7.0 + FreeWeight 1.3.0 — `adapters_registered` on the wire and in the table

**Row:** WA1 (Opus 5 · high; attended) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W7 and **before W8** (operator, 2026-09-10).
**Ships:** `setspec 0.7.0` and `freeweight 1.3.0` prepared — not tagged, not pushed, not published
(tags are held until the W arc ends); WeightRoomGym's `known_revisions` row and FreeWeight fixture.
**Components:** `~/ai/suite/py/SetSpec`, then `~/ai/suite/FreeWeight` (each with its own `.venv`;
FreeWeight on an editable SetSpec until the release), then `~/ai/suite/WeightRoom` (the console's
revision map, and one docs commit).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** ADR-0074 in full (the tri-state field, and why `None` is dropped from the hash);
ADR-0068 (a post-freeze minor is a sibling class); ADR-0060; `standards/api-and-contract-standards.md`
schema rules 1–10; `packages/setspec/schemas.md` and `spec.md`; BaseAiCore's `runtime.py`
(`RuntimeProfile.profile_hash`); SetSpec's `benchmark/v1.py` (`RuntimeProfileFields`,
`_check_runtime_profile_hash`) and every payload that nests the profile; FreeWeight's
`infrastructure/db/models.py` (the `runtime_profiles` row, `profile_hash` unique), `config.py`
(`_profile_for`), `cli/commands/runs.py` (`serving_mode`), `services/export.py`
(`_profile_payload`); `apps/freeweight/data-model.md`; `history/handoffs/W7_HANDOFF.md` §7 (a
migration owes the console a `known_revisions` row and a fixture).

## What is wrong

`baseaicore.RuntimeProfile.profile_hash` hashes every field that is not `None`,
`adapters_registered` included. FreeWeight builds adapter-aware profiles with it stated (`True` or
`False`) and stores the resulting `profile_hash`, but its `runtime_profiles` table has no
`adapters_registered` column, `services/export.py::_profile_payload` does not send it, and SetSpec's
frozen `RuntimeProfileFields` has no such field. A `benchmark.run_summary` for such a run carries a
`runtime_profile_hash` that SetSpec's `_check_runtime_profile_hash` recomputes without the field,
and refuses. A profile that left it `None` — every run before ADR-0074 — is unaffected. Found by
the suite audit of 2026-09-08; scheduled by the operator on 2026-09-10.

## Decisions already taken — do not reopen

* **SetSpec:** per ADR-0068, a `1.1` sibling of `RuntimeProfileFields` adding only
  `adapters_registered: bool | None = None`, and a `1.1` sibling of every payload that nests it
  (at least `benchmark.result` and `benchmark.run_summary`; find the rest by reference and name
  them in the handoff), registered beside the frozen `1.0` classes, with JSON Schemas and goldens
  generated and committed. The `1.0` artifacts regenerate byte-identically. The `1.1` class's
  `profile_hash` still delegates to `baseaicore.RuntimeProfile`. `setspec 0.7.0`.
* **FreeWeight:** a migration adding a nullable `adapters_registered` column to `runtime_profiles`.
  The backfill is **recovered, never guessed**: for each existing row, recompute the profile hash
  with the field `None`, `False` and `True`, and write the one value whose hash equals the stored
  `profile_hash`; a row matching none stays `NULL` and is counted in the migration's log and the
  handoff. New rows store the value the profile was built with. The export emits the `1.1`
  payloads with the field, importing the version-qualified names (schema rule 10). A migration test
  over a copy of the fixture database with rows in all three states. `freeweight 1.3.0`.
* **Consumers:** any reader of these payloads — LoadCoach's evidence import among them — accepts
  `1.1` unchanged (schema rule 2); a test in the consumer proves it with the new golden instead of
  changing the consumer.
* **WeightRoomGym:** FreeWeight's new revision joins `known_revisions`, and
  `tests/fixtures/databases/` gains the regenerated FreeWeight file (its README says how); the
  existing never-writable test runs against it. CHANGELOG under `[Unreleased]`.
* No new ADR unless a decision above does not fit what the code shows — then the ADR first,
  before code.

## Gates

**Gate A — SetSpec.** The sibling classes, their registration, schemas and goldens; round-trip and
hash-agreement tests (a profile in each of the three states hashes identically through BaseAiCore
and through SetSpec); the frozen artifacts unchanged; CHANGELOG; `0.7.0`. Commit.

**Gate B — FreeWeight.** The failing case first, as a failing test: an export of an
adapter-registered run that SetSpec refuses. Then the migration and backfill with its test, the
model column, the export on `1.1`; both dialects (`WEIGHTSDB_REQUIRE_POSTGRES=1` against a
throwaway `postgres:16`); CHANGELOG; `1.3.0`; the data-model and spec amendments canonical-first
and mirrored. Commit.

**Gate C — the console and the docs.** WeightRoomGym's `known_revisions` row and fixture, its gate
green; `packages/setspec/schemas.md` and `apps/freeweight/data-model.md` canonical and mirrored;
the row marked done. Commit in each repository.

## Demonstrate

On a **copy** of FreeWeight's real database — never the operator's: the backfill's counts by state
(`None`, `False`, `True`, unmatched), and an export of one run served with adapters registered,
validated by SetSpec, pasted into the handoff. If the copy holds no such run, say so and make one
against the copy.

## Finish line

Gates green in all three repositories with the interpreter named, coverage held, one commit per
gate, nothing pushed or tagged, `docs/history/handoffs/WA1_HANDOFF.md`, the row marked done.
