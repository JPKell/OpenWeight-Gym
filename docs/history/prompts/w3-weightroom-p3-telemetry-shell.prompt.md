# Kickoff — W3: WeightRoomGym Phase 3 — telemetry strip and the shell

**Row:** W3 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W2 and WM.
**Ships:** `wr-gym 0.3.0` prepared: the design brief's shell, live, with each
application's Overview page; the telemetry strip and history pages; resident models.
**Component:** `~/ai/suite/WeightRoom`. If `mirrorwall 0.3.0` is prepared but unpublished, pin it
as an editable path install with a `TODO: re-pin on publish` and say so in the handoff.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../../apps/weightroom/spec.md) §7.3, §7.7, §15, §16; [`design.md`](../../apps/weightroom/design.md)
§3–§4 (the shell, line by line) and §5 (what came from MirrorWall 0.3 and what is WeightRoomGym's);
[`development-plan.md`](../../apps/weightroom/development-plan.md) Phase 3; [`api.md`](../../apps/weightroom/api.md)
§1 (`/system/*`); [`data-model.md`](../../apps/weightroom/data-model.md) (`telemetry_samples`);
ADR-0016; ADR-0021; ADR-0123 rule 3 (the revision check the Overview's database fallback uses);
`packages/sweatmeter/spec.md`; `apps/loadcoach/api.md` (`/models`, residency);
`packages/modelrack/spec.md` (`list_resident`); `history/handoffs/W2_HANDOFF.md`, `history/handoffs/WM_HANDOFF.md`.

## Decisions already taken — do not reopen

* `sweatmeter` in process at `[telemetry] interval_ms`, one sampler thread, no second sampler;
  `—` for every unavailable reading, never `0`; samples kept for `history_hours`, downsampled past
  an hour (spec §7.7).
* Resident models from `/api/ps` **through ModelRack** and from LoadCoach's `/models`, each row
  with its `source`.
* Every page renders inside the shell; a stopped application's Overview renders from its database
  at a known revision with the source in the footer; an unknown revision degrades by name.
* htmx for every swap and SSE region, through MirrorWall 0.3's vendored copy with `mirrorwall.htmx = true` (ADR-0128); behaviour stays in ES modules; `hx-boost` off.

## Gates

**Gate A — telemetry.** `services/telemetry.py` (sampler, storage, downsampling, the SSE stream
with replay, the history endpoint); the fault-injecting reader test proving `—`; cadence and
overhead measured. Commit.

**Gate B — the shell.** Top bar (brand, four `app_tab`s with `status_dot`s fed by `/apps`, the
console pages, the alerts count placeholder, the operator chip), the `telemetry_bar` with meters,
`side_nav` per application with the plan's page list (unbuilt pages stubbed *coming in phase N*),
the light toggle, the footer. MirrorWall's accessibility checklist over the shell. Commit.

**Gate C — Overviews and status.** Each application's Overview: the pill, four figures, the
primary table, the log tail — from the API when up, from the database at a known revision when
stopped (the fixture databases from W0's seeded revisions; extend `known_revisions` if an
application has moved and say so), `—` where neither; `/system/status` and `/system/resident`
completed; `CHANGELOG.md`; `0.3.0`. Commit.

## Demonstrate

Plan Phase 3 criteria 1–3 on the reference machine: the console matching the artboard, the strip
moving once a second, VRAM's history chart; `CUDA_VISIBLE_DEVICES=` on the console process turning
GPU and VRAM to `—`; all four applications stopped and every Overview rendering from its database
with the revision in the footer.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/handoffs/W3_HANDOFF.md`, the row marked done.
Overnight is allowed at effort high; the morning diff is read.
