# WeightRoomGym Work — the arc's schedule

**Started 2026-09-09** (row W0, from the operator interview of the same day). The fifth
application — WeightRoomGym, the host operator's console — in execution order, one row per model
session. Rationale lives in [ADR-0123](../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
– [ADR-0127](../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)
and [`apps/weightroom/`](../apps/weightroom/spec.md); the plan the rows execute is
[`apps/weightroom/development-plan.md`](../apps/weightroom/development-plan.md); model choice
follows the [model-assignment guide](model-assignment.md) (§3.5: one model per phase, the
stronger; §2.12: overnight rules).

**This is the first arc with a file of its own.** [`outstanding-work.md`](outstanding-work.md)
carried every row from A1 to W0 and had grown to three hundred lines of mixed arcs; from W0 on,
each arc the operator starts gets its own `roadmap/<arc>-work.md` in this shape, `outstanding-work.md`
keeps only its pre-existing rows plus an index of the arc files (its §1.2), and
[`roadmap/README.md`](README.md) lists every work file. Status marks (**done <date>** with the
handoff link in the `#` cell), the `docs/history/<ROW>_HANDOFF.md` rule and the kickoff-prompt
convention (`docs/history/w<N>-….prompt.md`, its **Row:** line naming this file) are identical to
the original's. All paths are relative to `~/ai/suite/WeightRoom/docs/`.

**How to use a row.** Copy the row into a session and hand it its kickoff prompt from
`history/`; every prompt carries the standing preamble by reference (§2). Rows are listed in
execution order; §3 says which orderings are load-bearing.

## 1. The master table

| # | Phase → ships | Model · effort | Runs after | Work overview — and required reading | Why this model |
|---|---|---|---|---|---|
| **W0** — **done 2026-09-09** (`history/W0_HANDOFF.md`; no code) | **WeightRoomGym Phase 0** → ADRs 0123–0128, `apps/weightroom/{spec,api,data-model,design,risks,development-plan}.md`, the repository move (`~/ai/suite/docs` → `~/ai/suite/WeightRoom`, docs under `docs/`, a `docs` symlink for one transition), the skeleton at `0.0.0` with the gate green, master architecture and its satellites amended, `MEMORY_SAFETY.md` §2.2 and `LAN_ACCESS.md` rewritten, `expose_on_lan.sh` deleted, this file and the fifteen kickoff prompts below | **Fable 5.1 · attended** | N6 | The interview as decisions; the PyPI name confirmed against the index and then decided by the operator: product WeightRoomGym, distribution and CLI `wr-gym` (`weightroom` is taken); the "htmx" question was put to the operator and decided as the library (ADR-0128). **Read:** `history/w0-weightroom-phase-0.prompt.md` | Judgment throughout — the boundary exception, the write guard, the CA, the schema verbs; the operator wanted to be present |
| **W1** | **WeightRoomGym P1** → skeleton, configuration, database, TLS, login, `setup` (`0.1.0`, unpublished) | **Opus 5 · xhigh** | W0 | The standard application layout; `config.py` with spec §12 and the startup refusals; Alembic `0001`; the CA and leaf issuer, uvicorn HTTPS, the trust listener; scrypt, sessions, the cookie, the rate limit, CSRF and same-origin on JSON; the audit service; `wr-gym setup` minus units; `ci.lock` and the full CI shape; the `.importlinter` contracts un-deferred. **Read:** `apps/weightroom/spec.md` §§1–6, §12–14, `development-plan.md` Phase 1, ADR-0126, ADR-0026, ADR-0014, `standards/security-standards.md` §2–3, §14, `standards/configuration-standards.md`; LoadCoach's `config.py`/`services/settings.py` as the precedent; `history/w1-weightroom-p1-skeleton-tls-login.prompt.md` | A TLS edge and a login are the suite's first; every rule in ADR-0126 is a security decision with a silent failure mode. **Never overnight** |
| **W2** | **WeightRoomGym P2** → process control, unified logs, audit page (`0.2.0`) | **Opus 5 · high** | W1 | Unit-file rendering and `units sync`; the `SystemdController` port with a fake; journal history and SSE follow; the unified stream; Ollama status, the §2.1 checklist, the polkit rule and the gated restart; `apps status`, `logs`; version negotiation per application. **Read:** spec §7.1–7.3 (the process routes), §11, `development-plan.md` Phase 2, ADR-0125, `MEMORY_SAFETY.md` §2, ADR-0119; `history/w2-weightroom-p2-processes-logs-audit.prompt.md` | Subprocess discipline (explicit argv, allowlisted environment, output caps) is a security surface, and the polkit decision has to be implemented exactly as written. Reviewed same day |
| **WM** — **done 2026-09-09** (`history/WM_HANDOFF.md`) | **MirrorWall 0.3** → the design brief's tokens and seven generic components, prepared (not published) | Sonnet 5 · high | W0 | `tokens.css`/`tokens.json` deltas (§2 of the brief: the 13 px scale, 32 px dense rows behind `data-density`, sidebar width, JetBrains Mono vendored, label tracking, the four status tokens, the meter); macros: `app_tab`, `status_dot`, meters in `telemetry_bar`, `figure_card`, `table(density=…)`, `log_pane` with its ES module, `side_nav` — swaps and SSE regions as htmx attributes, htmx and its SSE extension vendored and pinned, opt-in per page (ADR-0128); contrast pairs both themes; the four applications' template suites still render byte-identically under 0.3 (Gold Standards MirrorWall bullet 1); CHANGELOG; release-prepared. **Read:** `apps/weightroom/design.md`, `packages/mirrorwall/spec.md`, `standards/ui-ux-standards.md` §1, §3, §4, §7, §9, ADR-0020; `history/wm-mirrorwall-0.3.prompt.md` | A written brief with exact values; the judgment (what is generic) is already in the brief's §5 table |
| **W3** | **WeightRoomGym P3** → telemetry strip and the shell (`0.3.0`) | Sonnet 5 · high | W2, WM | `sweatmeter` in process, the sampler, `telemetry_samples`, downsampling, the SSE stream and history pages; residency from `/api/ps` via ModelRack and LoadCoach; the shell from the brief over MirrorWall 0.3; each application's Overview from API or database with the source in the footer; `/system/status` completed. **Read:** spec §7.3, §7.7, §15, `design.md` §3–4, `development-plan.md` Phase 3, ADR-0016, ADR-0021, `packages/sweatmeter/spec.md`; `history/w3-weightroom-p3-telemetry-shell.prompt.md` | Templates over a published component set and a sampler with a spec; the `—`-never-`0` rule is tested by a fault-injecting reader the package already ships |
| **WS1** — **done 2026-09-09** (`history/WS1_HANDOFF.md`) | **FreeWeight 1.2.1** → `config schema --json`, `config validate --file` | Sonnet 5 · high | W0 | ADR-0127 rule 1's document from `Settings.model_json_schema()`, `RUNTIME_SETTINGS`, `CONFIG_ONLY_SECURITY_KEYS` and `config show`'s sources; rule 2's `--file`; a golden of the document; CHANGELOG; release-prepared. **Read:** ADR-0127, `apps/freeweight/spec.md` §7.2, §12, FreeWeight `config.py` and `services/settings.py`, `standards/configuration-standards.md` §4, §7, §8; `history/ws1-freeweight-config-schema.prompt.md` | Transcription of objects that exist; the golden is the test |
| **WS2** — **done 2026-09-09** (`history/WS2_HANDOFF.md`) | **LoadCoach 1.3.1** → the same two verbs | Sonnet 5 · high | W0 | As WS1 over LoadCoach's `config.py`/`services/settings.py`; note the singular `[provider]` and plural `[providers.<name>]` forms both appear in `json_schema` (ADR-0077) and the document says which the file uses. **Read:** ADR-0127, `apps/loadcoach/spec.md` §7.2, §12, ADR-0077, ADR-0117; `history/ws2-loadcoach-config-schema.prompt.md` | As WS1 |
| **WS3** | **IdeaPress 1.4.1** → the same two verbs | Sonnet 5 · high | W0 | As WS1; IdeaPress keeps its runtime registry in `api.md` §6's terms — the row names the module it lives in and emits the same document shape. **Read:** ADR-0127, `apps/ideapress/spec.md` §7.2, §12, `apps/ideapress/api.md` §6; `history/ws3-ideapress-config-schema.prompt.md` | As WS1 |
| **WS4** | **PromptCadence 1.3.3** → the same two verbs | Sonnet 5 · high | W0 | As WS1 over PromptCadence's registry (ADR-0100: five keys, whole sections refused); `sources` carries `shadowed_by`. **Read:** ADR-0127, `apps/promptcadence/spec.md` §7.2, §12, ADR-0100; `history/ws4-promptcadence-config-schema.prompt.md` | As WS1 |
| **W4** | **WeightRoomGym P4** → settings forms over the schema verbs, the doctor, tokens pages (`0.4.0`) | **Opus 5 · high** | W3, WS1–WS4 | The schema-document reader and form generator; `tomlkit` round-trips with validate-before-write, `.bak`, `base_mtime`; runtime keys through `PUT /settings`; *pending restart*; security keys behind `POST /reauth`; WeightRoomGym's own settings page from its own verb; the doctor with printed commands; per-application token pages. **Read:** spec §7.4, §12, ADR-0127, ADR-0117, ADR-0100, `standards/configuration-standards.md` §7–8, `MEMORY_SAFETY.md` §6, `LAN_ACCESS.md`; `history/w4-weightroom-p4-settings-doctor.prompt.md` | A file another process owns is rewritten in place; the round-trip and the race are where this goes wrong silently |
| **W5** | **WeightRoomGym P5** → docs viewer (`0.5.0`) | Sonnet 5 · high | W3 | `mistune` with a sanitising renderer, heading ids, link rewriting, containment; FTS5 index and the LIKE fallback; the ADR index from `adr/README.md`; mermaid vendored and loaded only where a fence exists; the `docs_index` job kind stub. **Read:** spec §7.5, §14 (docs rows), §15, `development-plan.md` Phase 5, ADR-0020; `history/w5-weightroom-p5-docs-viewer.prompt.md` | Rendering with goldens and a containment test set that already exists in ToolYard's shape |
| **W6** | **WeightRoomGym P6** → chat: LoadCoach, then PromptCadence, thinking collapse (`0.6.0`) | **Opus 5 · high** | W4 | The conversation/message/event model; LoadCoach streaming with the routing decision and cost; PromptCadence trajectories with plan/step/tool/egress cards and inline approvals under the `approve` token; the thinking state machine; attachments; `message_events` persisted and replayable; the network-isolation test. **Read:** spec §7.6, §14 (chat rows), `apps/loadcoach/api.md` (generate/stream, explanation), `apps/promptcadence/api.md` §3–4, ADR-0045, ADR-0049, ADR-0016, ADR-0069, PromptCadence's `tests/security/test_injection_corpus.py`; `history/w6-weightroom-p6-chat.prompt.md` | Two streaming protocols, an approval that spends money, and model text reaching the DOM. **Never overnight** |
| **W7** | **WeightRoomGym P7** → database viewer and the guard (`0.7.0`) | **Opus 5 · xhigh** | W4 | `domain/guard.py` (the five conditions, the never-writable list as data, statement classification); read-only connections both dialects; the revision check; the grid and the SQL console; the guarded write with its pending → ok audit row; curated operations wired per table; fixture databases at each known revision. **Read:** ADR-0124 in full, spec §7.8, §11, `data-model.md` §4, `standards/database-standards.md` §1, §8, `packages/weightsdb/spec.md` (backup, session read-only); `history/w7-weightroom-p7-db-viewer-guard.prompt.md` | The one place the suite crosses its own boundary on purpose; every condition is a test that must fail alone. **Never overnight** |
| **W8** | **WeightRoomGym P8** → catalog, costs, backups and migrations (`0.8.0`) | Sonnet 5 · high | W7 | The cross-application model join; `ollama pull` as a job; GGUF drop-in with magic and containment checks; enable/disable through each application; delete with preview and cleanup; `loadledger.sql` reads with unpriced counts; the backup/upgrade/restore pages as curated calls. **Read:** spec §7.9, ADR-0118, ADR-0069, ADR-0030, `packages/loadledger/spec.md` (`sql`, balances), `standards/database-standards.md` §7–8, `packages/modelrack/spec.md` (discovery, residency); `history/w8-weightroom-p8-catalog-costs-backups.prompt.md` | Joins and curated calls over surfaces that already exist and are tested in their owners |
| **W9** | **WeightRoomGym P9** → jobs, alerts, prompt editor (`0.9.0`) | **Opus 5 · high** | W8 | The lease-based queue and worker (ADR-0010/0029 shape), the cron parser, catch-up semantics, the four kinds plus `catalog_pull`/`docs_index`; the alert evaluator with five sources and one open alert per subject; the prompt editor writing validated override records. **Read:** spec §7.10, ADR-0010, ADR-0029, ADR-0119 (the journal match), ADR-0012, ADR-0028, `standards/prompt-management-standards.md` §2, §6, `apps/loadcoach/queue-and-scheduling.md` §5–7; `history/w9-weightroom-p9-jobs-alerts-prompts.prompt.md` | A queue with leases and a crash-recovery pass is the shape the suite has been most often wrong about (ADR-0029's four findings) |
| **W10** | **WeightRoomGym P10** → hardening, performance, docs, `1.0.0` prepared | **Opus 5 · xhigh** | W9 | Security Standards §14 plus spec §14's rows; the injection corpus against chat; redaction sweep; every §15 budget on the reference machine; the operator docs and the generated configuration reference; the OpenAPI snapshot; the `docs` symlink removed and every `~/ai/suite/docs` reference rewritten; verification on an independent device with permission to say *not ready*. **Read:** spec §§14–20, `development-plan.md` Phase 10, `standards/testing-standards.md`, `standards/packaging-and-release-standards.md` §4–6, `history/M7_HANDOFF.md` (the verification precedent); `history/w10-weightroom-p10-hardening-release.prompt.md` | The phase that proves the list; won by review. **Never overnight** |
| **WM2** | **The four applications adopt MirrorWall 0.3** → density, dots, meters, log pane, tab strip | Sonnet 5 · high | W10 | Four rows in one line: each application opts into `data-density="dense"` where its tables want it, the status dot on its health page, meters in its telemetry bar, the log pane on run/job pages, the tab strip linking to WeightRoomGym and its peers; template snapshots updated; four patch releases. Outside this arc's `1.0.0`. **Read:** `apps/weightroom/design.md` §6, each application's `web/templates`; `history/wm2-four-apps-adopt-mirrorwall-0.3.prompt.md` (written at W10, not here) | Mechanical adoption of a published component set |

## 2. The standing preamble

Every kickoff prompt in this arc states what [`outstanding-work.md` §2](outstanding-work.md)
states — the component directory and venv, the finish line, the house method, the reading order,
the local-pin rule for unpublished suite dependencies, the overnight rules — and it says so by
linking there rather than copying it. Two additions for this arc:

* **The component directory is `~/ai/suite/WeightRoom`** for every W row; `WS` rows work in the
  named application's repository and end with one docs commit in `~/ai/suite/WeightRoom` (the
  row marked done here, the handoff written). Nothing is pushed, tagged or published.
* **Every W row's demonstration runs on the reference machine against the real four applications
  where the acceptance criterion says so** (the plan's "what a person sees"), and against the
  fake `systemctl`/fixture databases in the suite. A criterion demonstrated only against the fake
  is reported as such, not as passed.

## 3. Which orderings are load-bearing

* **W0 before everything** — the ADRs before any code, the standing rule.
* **W1 before W2** — no process control before the login and the audit log exist (security
  before reach).
* **WM before W3** — the shell is built on 0.3's tokens; building it on 0.2.2 and re-skinning is
  the work twice. Soft only if WM slips: W3 may pin MirrorWall as an editable path install with a
  `TODO: re-pin on publish`.
* **WS1–WS4 before W4** — hard: the forms are generated from the documents. The four rows are
  independent of each other and of W1–W3, so they can run in parallel with W1–W3 on Sonnet.
* **W4 before W6 and W7** — the application tokens (W4's tokens pages, W1's wizard) and the
  connection strings (from the schema documents) are what chat and the database viewer read.
* **W7 before W8** — delete-with-cleanup and restore are curated operations over the guard's
  machinery.
* **W1–W10 strictly in order otherwise**; W5 (docs) is the one flexible row — any time after W3.
* **WM2 after W10** — adoption targets a released MirrorWall 0.3 and a released WeightRoomGym.

## 4. Not model sessions — the human/ops checklist

* **Reserve the PyPI name `wr-gym`** before W1 publishes anything (decided 2026-09-09; `weightroom`
  is taken by an unrelated `0.0.1`).
* ~~Confirm the "htmx" reading~~ — **decided 2026-09-09: the library.** ADR-0128; MirrorWall 0.3
  (row WM) vendors htmx and its SSE extension, opt-in per page.
* Create the GitHub remote's settings for the renamed repository (it is still `weightroom`;
  no rename needed); the `pypi` environment for the release workflow before W10.
* Apply `MEMORY_SAFETY.md` §2.1 on the reference machine (`docs/scripts/apply_memory_safety.sh`):
  the override still reads `OLLAMA_CONTEXT_LENGTH=112000` with no cap as of W0 — W2's Ollama pane
  will show it red until then, which is correct.
* Install the polkit rule W2 prints, if the Ollama restart button is wanted.
* Decide whether Ollama stays on `0.0.0.0` (`LAN_ACCESS.md` §5).
* Remove the `docs` symlink at the workspace root at W10 (the row does it; the operator confirms
  nothing else on the machine still resolves through it).
* Per release: tag, Release-workflow `pypi` environment approval, post-publish install check —
  for `mirrorwall 0.3.0` (WM), the four `WS` patch releases, and `wr-gym 1.0.0`.
* Review W1, W6, W7 and W10 same-day; they never run overnight.

## 5. Milestone map

| Milestone | Rows | Declared when |
|---|---|---|
| **WR-α** — the console exists | W1, W2, WM, W3 | Spec §20 #1, #7 and #9 demonstrated on the reference machine from a phone: HTTPS, login, the four tabs with dots, the strip moving, an application started and stopped from the console |
| **WR-β** — the console operates | WS1–WS4, W4, W5, W6, W7 | Spec §20 #3–#6 and #8 demonstrated: a guarded write end to end, a schema-driven form with a live key and a re-authenticated security key, chat through both paths with an approval, an unknown revision degrading by name |
| **WR-1.0** — `wr-gym 1.0.0` | W8, W9, W10 | Every spec §20 criterion; the independent-device verification says *ready* |
