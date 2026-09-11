# Kickoff — WPF1: FreeWeight's Settings form saves, a refused write is audited, a slow call is not a refusal

**Row:** WPF1 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), findings 1, 2 and 3). Runs after WP6,
and before WPF2, whose demonstration saves FreeWeight's settings through the form.
**Ships:** unreleased, no version bump.
- **WeightRoomGym:** the generated settings form writes only what the operator changed, and renders
  an unset nullable boolean as unset. A settings write the application refuses leaves its audit
  row. A call to an application that takes longer than the console's client timeout is no longer
  reported as that application's refusal.

**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` findings 1–3; spec §7.4, §11 (contracts 2 and 5); ADR-0127;
`W4_HANDOFF.md` (the form generator, `base_mtime`, validate-before-write); `W10_HANDOFF.md` §2
items 10 and 11 (`touched_security`, the *clear* control); the arc index §2 items 4 and 7.

**Code to read first:** `services/settings_forms.py` (field parsing, the empty-string rule),
`services/config_files.py` and the settings routes (the candidate file, the refusal path);
`services/app_api.py` (`DEFAULT_TIMEOUT_SECONDS`), `services/freeweight_actions.py` (`discover`);
`tests/security/test_audit_routes.py` (`EXERCISES`, `test_each_state_changing_route_writes_exactly_one_audit_row`).

## What WP6 saw on the reference machine (2026-09-11)

1. **The form cannot save FreeWeight's file keys.** At 12:23:46 PDT, saving `[adapters] directory`
   on `/apps/freeweight/settings` rendered *Refused. freeweight refused the new configuration: …
   Value error, runtime.flash_attention is not honoured by provider.kind = 'ollama' (Ollama's flash
   attention and KV-cache type are daemon-wide environment). Unset it, or use provider.kind =
   'llamacpp'.* FreeWeight's file held only `[runtime] context_size = 8192`.
   `runtime.flash_attention` is FreeWeight's one nullable boolean (schema default `null`). The
   form renders it as `<select name="field:runtime.flash_attention"><option value="true">…
   <option value="false" selected>`, so every save posts `false` and writes a key the operator never
   touched. `runtime.fit_to_device` renders the same way. With FreeWeight's default provider no
   save through the form can succeed. The raw editor saved the same change (audit
   `01M28YZDTJSKWY8ZJZKGRJST77`). LoadCoach, IdeaPress and PromptCadence publish no nullable boolean
   (checked against each `config schema --json`).
2. **The refusal left no audit row.** The console's journal shows two
   `POST /apps/freeweight/settings` requests answered `200` with the refusal rendered, at 12:23:46.213
   (`01M28YT24SABZ0WN7K7XCWPCK9`) and 12:23:46.980 (`01M28YT2TPE2PZ8RVWR5PXP3GF`). There is no
   `settings.write` row for either. A LoadCoach provider refusal a few minutes later did write its
   `refused` row (`01M28ZC4M7NJYFKCD1FENG88RE`). The audit test exercises each route's success only.
3. **A slow refresh was reported as refused.** After FreeWeight's provider was switched to
   `llamacpp`, *Refresh from provider* rendered *freeweight did not answer POST
   /api/v1/models/discover: timed out* (audit `01M28YXX7NRYPAB99Z97J8DGV4`, `refused`) after the
   client's 10 s default. FreeWeight carried on hashing 195 GB of GGUF files. Its digest file was
   written at 12:27:50, and 27 `llamacpp` models were persisted. The work succeeded, but the page and
   the audit row both say it was refused.
4. **Polish** (`WP6_HANDOFF.md` §4), none of it blocking:
   * At 412 px, FreeWeight's machine page (`/apps/freeweight/machines/{id}`) scrolls sideways by
     138 px, FreeWeight's adapter page (`/apps/freeweight/adapters/{name}`) by 96 px, and LoadCoach's
     Database page by 19 px, in both themes. The probe did not locate the
     element in either.
   * The strip's QUEUE shows its last reading on the first paint after LoadCoach stops
     (`TelemetryService.peek_queue`), for up to one refresh interval.
   * While FreeWeight is stopped, Compare keeps its query form enabled and names no source, and the
     calibration page keeps *Start grading* enabled although the grading page needs the API.
   * After a grant, the Approvals page shows the new state but no notice.
   * A LoadCoach job whose routing refused it reads *Model: not yet routed*.

## Decisions already taken — do not reopen

* **The form hardcodes no key** (spec §11 contract 5, ADR-0127). The fix is in the generator, not a
  FreeWeight special case.
* **An untouched field writes nothing.** TOML has no null. `settings_forms.py` already applies this
  rule to empty strings, and it extends to every kind.
* **Every state-changing route writes one audit row, and a refusal is an outcome** (spec §11
  contract 2, arc index §2 item 7).
* **The console calls `/api/v1` only** and renders the application's own refusal. It never
  re-validates FreeWeight's configuration itself.

## Decisions for this row — make each, and record it in the handoff

1. **How a nullable boolean renders and posts.** A tri-state select with an *unset* option is the
   obvious shape. Decide it, and decide how the candidate file is compared with the current
   document so that only changed keys are written.
2. **Which routes can refuse without a row.** Enumerate every route that renders an application's
   refusal at `200`. Give each a refusal exercise in the audit test, beside its success exercise.
3. **Slow calls.** For discovery, decide between a longer per-call timeout, the existing
   `model_refresh` job kind, or an honest *still working* state. Whatever is chosen, a client
   timeout is never recorded as the application's refusal. Check the catalog's discover call too.

## Gates

**Gate A — the form.** Tests first, against a schema golden with a nullable boolean: an untouched
save writes no key, and an unset boolean stays unset. Implement. Commit.

**Gate B — refusals audited.** Write the refusal exercises, then implement. Commit.

**Gate C — slow calls.** Test with a fake application that answers after the client timeout.
Implement. Commit.

**Gate D — the live proof.** On the reference machine, with FreeWeight on `provider.kind =
"ollama"`: save a file key through the form and restart FreeWeight. Show a refused save and its
audit row. Show a llamacpp refresh that is not reported as refused. If FreeWeight's provider is
switched to show it, switch it back through the Provider page. Fix each polish item whose cause is
small, and record the rest with the reason. Restart `weightroom.service`. Commit the handoff.

## Finish line

- The gate green, with the interpreter named, and coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF1_HANDOFF.md`: the rendering chosen, the routes given refusal
  exercises, the slow-call decision, the audit ids of the live proof, and what this kickoff got
  wrong.
- The row marked done. Nothing pushed.
