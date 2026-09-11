# Kickoff — WP3: application pages III — FreeWeight measurement

**Row:** WP3 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WPC1 (operator, 2026-09-10), **at the same time as WP5**. It uses its own branch and
worktree, under the parallel-row rules in `weightroom-work.md` §3: read them before the first
commit. Part of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased. FreeWeight's Models, Runs, Results, Evidence, Adapters and Provider pages,
at full parity with FreeWeight's own UI. Goals and grading are WP4's.
**Component:** `~/ai/suite/WeightRoom`. `~/ai/suite/FreeWeight` for any missing API route (arc
index §2 item 4).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index §2; `history/handoffs/WP1_HANDOFF.md` and `WP2_HANDOFF.md` (the
kit, and what the first two rows learned); `apps/freeweight/api.md` §2–§8a;
`apps/freeweight/spec.md` (runs, comparability, export); ADR-0074, ADR-0089, ADR-0118, ADR-0119,
ADR-0134, ADR-0135; `history/handoffs/W8_HANDOFF.md` and `W9_HANDOFF.md` (the catalog's
FreeWeight calls, the `freeweight_suite_run` job kind and its memory-cap scope);
`history/handoffs/H6_HANDOFF.md` (adapter evidence that measured the bare base).
**Parity target:** FreeWeight's own `web/templates/{models,runs,results,compare,evidence,machines,providers,sources,system,dashboard}`
and their routes. Inventory them before Gate A. `goals` and `grading` belong to WP4. `database`
is already the console's Database page (W7/ADR-0134): check its coverage of stats, backup,
vacuum and results deletion, and close any gap here.

## Decisions already taken — do not reopen

* Everything in the arc index §2.
* **Models.** List with `provider_kind`, `family`, `quantization`, `has_results`, and sort. Detail
  with identity, latest descriptor, descriptor history, evidence summary, and paginated results
  filterable by suite and runtime profile. **Scan** shows the added/updated/unchanged counts
  FreeWeight returns. Enable/disable reuses W8's catalog call (a form field, not a JSON body, on
  FreeWeight).
* **Runs.** List with status/model/suite/machine/label/date filters and a cursor. Detail with
  tests, aggregate metrics (`metric_key`), degradations and the fingerprint document; the live
  event stream with `Last-Event-ID` replay; test and sample drill-down, with samples escaped and
  cursor-paginated. **Cancel** handles `409 RUN_NOT_CANCELLABLE` as itself. **Repeat** offers
  `?force` and `?label`, and shows the divergence a forced repeat records. **Start** is a form over
  `GET /benchmarks` (suite, model, label) that **enqueues W9's `freeweight_suite_run` job**, which
  already runs under ADR-0119's cap and is already audited. Spec §7.3 names the CLI for run start.
  The page then follows the run FreeWeight reports. Verify whether `POST /runs/{id}/repeat`
  executes inside a capped unit on the reference machine, and record the answer. If it does not,
  send repeat through the job kind too.
* **Results.** The metric query; **compare** (`?subjects=…&suite=…`) with each comparability
  verdict and, where comparison is refused, the reason stated rather than a blank; **export**
  proxied as a streamed download with every FreeWeight option. The 500-run refusal renders as
  itself.
* **Evidence.** `GET /evidence` with FreeWeight's filters, `user.*` records with `goal_hash`,
  `judge_set`, `calibration` and `judge_validity_factor`, and the `benchmark.evidence_bundle`
  download.
* **Machines.** List and detail, linked from runs and results. No new menu entry unless there is
  no natural home. In that case amend spec §7.3 in the same commit.
* **Adapters.** FreeWeight serves no adapters endpoint. Adapters are in `runtime_profiles`
  (`adapters_registered`, read at its own SetSpec minor per ADR-0135), in results measured with
  `GenerationRequest.adapter` (H6), and in the panel cap (ADR-0089). The page shows each adapter
  with its base, the runs and results measured under it, and whether the base-only canary passed.
  If no API gives that, add a read route to FreeWeight in its own commit, with `api.md` first.
* **Provider.** `GET|PUT /provider`, the `[provider]` block, with re-auth for security keys.
  `_PAGE_ELSEWHERE` is deleted in this row.

## Gates

**Gate A — Models, Runs.** Including the start-as-job path against the fake `systemd-run`, the
event-stream proxy, and cancel/repeat. Running and stopped against fixtures and FreeWeight's
fixture database at its WA1 revision. Commit.

**Gate B — Results, Evidence, Machines.** The export proxy is tested for streaming, headers and
the refusal. Commit.

**Gate C — Adapters, Provider, database-page gaps.** Any FreeWeight API commit first, in
FreeWeight, with its gate green. Stubs for FreeWeight reduce to `Goals` only, which WP4 closes.
`EXERCISES`, the §14 registry, the OpenAPI snapshot and `api.md` updated. `CHANGELOG.md` updated.
Commit.

## Demonstrate

On the reference machine:

1. Scan, then start a small suite run from the Runs page and follow it live.
2. Drill into a sample.
3. Compare two models and read one refused comparison's reason.
4. Export a run as CSV.
5. Open an adapter's page and its results.
6. Stop FreeWeight and reload every page.

Take screenshots in both themes.

## Finish line

Gate green in every repository touched, with the interpreter named. Coverage held. One commit per
gate. A handoff at `docs/history/handoffs/WP3_HANDOFF.md` with the parity table, the repeat/cap
answer, and what the kickoff got wrong. The row marked done.
