# WPF1 Handoff — the settings form saves, a refusal is audited, a slow call is not a refusal

**Row:** WPF1 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended, wave 1 ·
**Model:** Claude Opus 5 · **Kickoff:**
`history/prompts/wpf1-weightroom-settings-form-refusals-and-slow-calls.prompt.md`
(wave note `history/prompts/wave1-wpf1-summary.md`) · **Branch:** `row/wpf1-settings-form` at
`~/ai/worktrees/weightroom-wpf1`, merged into `main` (§8). **Ships:** unreleased, no version bump.

## 1. What shipped

| Commit | Gate | What |
|---|---|---|
| `79efd56` | A | **A key the model allows to be unset renders and posts as unset.** `_resolve` records that it unwrapped a `null` member, `FormField.nullable` carries it, the template gives a nullable select its *unset* option, and `FormField.parse` reads an empty submission on a nullable leaf as unset for every kind. Two neighbours of the same rule close with it: a secret whose value is empty is compared like any other key instead of being written back on every save, and *unset* on a key the file names is refused by name as the deletion it is — that key alone |
| `ad5a719` | B | **A refused settings write leaves its audit row.** One `_audit_refusal` on every path of all five settings write routes that answers the operator a refusal; `REFUSALS` in the audit-route suite, one refused call per such route, each asserted to add exactly one row whose outcome is `refused` |
| `c2a6c25` | C | **A call the console stopped waiting for is `pending`, not the application's refusal.** `AppTimedOut` in `services/app_api`, `outcome_of()` at each of the 32 sites where a route audits a failed application call, and the catalog's drop-in no longer names an application as refreshed when its discovery pass did not answer. Spec §11 contract 2 states both this and Gate B's rule |
| `27c3a89` | D | **The polish WP6 §4 carried into this row**: `.mono` breaks at phone width; a unit verb the console runs drops the strip's QUEUE reading; a job that ended unrouted reads *never routed*; a grant or a denial lands on a notice; a stopped FreeWeight's Compare and *Start grading* say why they cannot work |
| `3e272d5` | D | **What the live proof found**: the raw editor rewrote every line of the file it saved (a browser posts CRLF), and a `settings.write` row named the whole model instead of what the write did |
| `aea1b93` | — | `main` merged in (WPF7 and WPF8 docs; no conflict) |
| this commit | docs | This handoff; the row marked done |

Nothing pushed, nothing tagged, no version bump (`wr-gym` stays `1.0.0`, under `[Unreleased]`).

**Gate**, at `3e272d5` in the worktree, `~/ai/worktrees/weightroom-wpf1/.venv`, **Python 3.14.4**:
`ruff format --check .`, `ruff check .`, `mypy src tests` (226 files), `lint-imports` (5 kept),
`pytest` → **1863 passed, 3 skipped, 10 deselected**; `pytest --cov` → **90.44 %**, over the 85 %
floor and above where the row found it. `git status --short` clean.

## 2. The decisions this row was asked to make

### 1. How a nullable leaf renders and posts, and how only changed keys are written

**A tri-state select, and the *unset* option is generated, never hardcoded.** The document's own
`json_schema` is the only source: `_resolve` — which already unwrapped `anyOf: [X, null]` to reach
the field's real schema — now records that it dropped a `null` member, `_is_nullable` also reads
the `type: [ …, "null"]` spelling, and `FormField.nullable` carries the answer to the template.
A nullable select renders `unset` first, selected when the value is `None`; an empty submission on
a nullable leaf of **any** kind is `None`. Nothing here names a key of any application
(ADR-0127 rule 3, spec §11 contract 5).

**Only changed keys are written, by comparing each field against the value the form rendered** —
`save_settings`' existing `value == one.value` rule, with the `not one.secret` carve-out removed
(see §3 item 2). **No candidate-versus-document diff was added**, and none is needed: a key the
file does not name renders from its default, so posting that default back is already `unchanged`.
What was missing was only a widget that could say *unset*.

**Unset on a key the file names is refused, by name and alone.** TOML has no null, so it is a
deletion, which stays the raw editor's job (the rule `settings_forms.py` already stated for an
empty box). Before this row a `None` reached `apply_changes`, whose `_toml_value` raised, and
`save_settings` then refused **every** file key in the same save with one message about removing a
line. Now that key alone carries the refusal and the rest of the save lands.

### 2. Which routes can refuse without a row

**Every route that renders an application's refusal at `200` already audited it — except the five
settings write routes.** `settings.py` was the only module under `web/routes/` with no
`outcome="refused"` in it; every application tab records the refusal in its own `_audit` helper,
and several `EXERCISES` entries are themselves refusals for that reason. The five, and the paths
that now leave a row:

| Route | The refusals it answers |
|---|---|
| `POST /apps/{app}/settings` | a wrong password, the re-authentication window, a stale `base_mtime`, the application's own validation, a field that will not parse |
| `POST /settings` (the console's own) | the same — it is the same handler |
| `POST /apps/{app}/settings/raw` | a wrong password, invalid TOML, the window, a stale base, the application's validation |
| `PUT /api/v1/apps/{app}/settings` | the window, a stale base, the application's validation — each of which reached the error handler unrecorded |
| `PUT /api/v1/settings` | an unknown or config-only key, a value outside its bounds |

`POST /apps/{app}/settings/validate` already recorded `pending` on both verdicts and is unchanged.
A field that would not parse was worse than absent: it rendered its error beside a row that said
`ok`, because it never reached `save_settings`. It is now a `refused` outcome inside the same row.

**The test carries the rule forward**: `REFUSALS` in `tests/security/test_audit_routes.py`, keyed
like `EXERCISES`, with `test_each_refused_write_writes_exactly_one_refused_row`. A route belongs
there when it catches a refusal and answers the operator anyway, rather than letting it reach the
error handler unrecorded.

### 3. Slow calls

**An honest *still working* state. The timeout stays at 120 s and no job kind was added.**

* `app_api` raised one `AppUnreachable` for every `httpx.HTTPError`, and every route audited that
  as the application's refusal. A timeout is now `AppTimedOut` — a **subclass**, so every existing
  `except AppUnreachable` still catches it, carrying the **same `APP_UNREACHABLE` code**, so no
  client that branches on the code changes and spec §13's list is untouched. Its message says the
  console stopped waiting, that the work may still be running, and that nothing was cancelled and
  nothing was sent again.
* `outcome_of(exc)` decides the audit outcome: **`pending`** for a timeout — the vocabulary's word
  for *no state moved that we know of* — and `refused` for everything the application said no to.
  It is used at the 32 sites in `freeweight.py`, `freeweight_goals.py`, `loadcoach.py`,
  `ideapress.py` and `promptcadence.py` where a route audits a failed application call. The
  `outcome="failed"` of a grade FreeWeight did not answer is deliberately left alone: WP4 designed
  that path to re-read what FreeWeight holds, which is already the honest recovery.
* **A longer timeout was rejected**: FreeWeight's own re-hash of every GGUF on each pass is what
  makes discovery slow, and that is WPF2's (WP6 finding 9). The console cannot make FreeWeight
  faster; it can stop claiming FreeWeight refused. **A `model_refresh` job was rejected** for this
  row: the job kind exists, but moving the page's button onto the queue is a change to how the
  operator works, not a fix for a mislabelled outcome.
* **The catalog's discover call**, which the kickoff asked be checked: `_refresh_after_dropin`
  named every application as `refreshed` whether or not its discovery pass answered — `_call`
  swallows every error and returns `None`. It now names only the ones that answered. The catalog's
  other calls raise its own `CatalogRefused` on any `httpx` error; they are short calls, WP6 found
  nothing there, and they are left for whoever needs them (§7 item 3).

## 3. What the live proof found, and this row fixed

1. **The raw editor rewrote every line of the file it saved.** Restoring FreeWeight's own
   `config.toml` through the editor, unedited, came back CRLF: a browser posts a `textarea`'s value
   with CRLF endings whatever it was given. Valid TOML, so the application's validation passed and
   nothing warned — and every line of the operator's file changed. The editor normalises to `\n`
   before it validates and writes. Caught by `cmp` against the copy this session took before
   touching anything; the operator's file is byte-identical to how the row found it.
2. **A secret whose value is empty was written back on every save.** `save_settings` skipped the
   *unchanged* comparison for any secret-shaped key, because a secret renders as `********`. But
   `REDACTED` stands in only for a value there *is* one of: FreeWeight's `auth.tokens = []` rendered
   in the clear, came back as itself, and was written on every save. Found because the first
   untouched-form test still wrote one key.
3. **A `settings.write` row named the whole model.** The page posts every field, so the row's
   target carried all 85 of FreeWeight's keys and a refusal's message repeated the same sentence 85
   times. The target is now what the write did (or *n keys, none changed*), a refusal names the
   keys the operator asked to change, and `params` still carries each list in full.
4. **`app.capitalize()`** in the timeout's sentence produced *Freeweight*, which is not the name of
   anything.

## 4. Demonstration on the reference machine

A **throwaway** console (`https://127.0.0.1:8779`, its own XDG tree and database in the session
scratchpad, open loopback, pointed at the operator's four applications and their token files read
in place), driven with Playwright and the system Chrome. `weightroom.service` was not touched until
§8. The audit ids below are that console's; its database goes with the session.

**No provider switch, and no model load.** The kickoff asks for FreeWeight on `provider.kind =
"ollama"`. The reference machine's FreeWeight is on `llamacpp` with `[adapters] directory` set,
which is the combination WP6 finding 9 records FreeWeight as rewriting its file over *before*
refusing — WPF2's row, unfixed. Switching to show a refusal would have run the operator's live
configuration through a known file-damaging defect for no gain: every part of the gate can be shown
where the machine already is, and none of it needs a model resident (a llama.cpp discovery pass
hashes files; it starts no server), so ADR-0119's one-load rule never came into it.

1. **The form renders *unset*.** `/apps/freeweight/settings`:
   `runtime.flash_attention` posts `''` with options `unset · true · false`;
   `runtime.kv_cache_precision` posts `''` with `unset · f16 · q8_0 · q4_0`. `runtime.fit_to_device`
   posts `false` with `true · false`, which is correct — it is a plain `bool = False`, not nullable
   (§6 item 2).
2. **The whole form posted back untouched writes nothing.** *Nothing changed.*
   (`01M29EY0FQ98SAVBVW2RFNSKM8`, `ok`, `written: []`), and `config.toml` byte-identical. This is
   the save that could not succeed at all before the row.
3. **One key saved.** `benchmarks.long_context_max_tokens` 32000 → 30000:
   *1 written to the file* (`01M29EYGRD2P533ZZ29AGWPZT2`, `written:
   ['benchmarks.long_context_max_tokens']`). The file gained `[benchmarks] long_context_max_tokens
   = 30000` and **nothing else** — no `flash_attention`, no `kv_cache_precision`.
4. **FreeWeight restarted from the page.** The settings page showed *pending restart*, and its
   button ran the unit verb (`01M29F1WADRV2R5PMY4WQGFDMG`, `unit.restart`, `ok`); FreeWeight came
   back `active` on the new file, `1.2.1`.
5. **A refused save, and its audit row.** `benchmarks.long_context_max_tokens = -1`:
   *Refused. freeweight refused the new configuration: … benchmarks.long_context_max_tokens: Input
   should be greater than or equal to 1000 (got -1)*. The row is
   **`01M29F5AKE2SKM7C7NF32RHZ0J`, outcome `refused`**, target `benchmarks.long_context_max_tokens`,
   message FreeWeight's own. `config.toml` unchanged and no `.bak` written. WP6's two refusals left
   **no row at all**. (`01M29F2M1HAQG6RWGNM60HTSJR` is the same refusal a few minutes earlier,
   before §3 item 3 trimmed the target: it is the 85-key row, kept here as the evidence for that
   fix.)
6. **A llamacpp refresh that is not reported as refused.** *Refresh from provider* at 17:09:49 PDT.
   The console stopped waiting after **120.8 s** and rendered *freeweight has not answered POST
   /api/v1/models/discover within 120 s, so the console stopped waiting. The work may still be
   running — nothing was cancelled and nothing was sent again.* The row is
   **`01M29F9J0X0ZNZPVMKD5H9ATT8`, outcome `pending`** (WP6's was `refused`). FreeWeight went on
   hashing: its 27 `llamacpp` models were persisted between 17:14:00 and 17:14:20 PDT, **two and a
   half minutes after the console gave up**, each stamped `last_seen_at 2026-09-12T00:09:50.586Z` —
   the instant the pass began. The work succeeded; the console said so honestly.
7. **The file put back.** The raw editor, with the operator's original text
   (`01M29FE7FS1CMA0WCC469YNT60`, `raw_editor: true`); `cmp` against the copy taken before any of
   this: **identical**. (`01M29FC1GZD8VPD656KF71JTQ7` is the attempt before §3 item 1 was fixed —
   the one that came back CRLF.)
8. **Phone width**, 412 × 915, both themes, nine pages: every one fits. Before the `.mono` rule,
   FreeWeight's machine page scrolled to 550 px (the 64-hex `machine_fingerprint` in a `p.mono`)
   and its adapter page to 508 px (`llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:…+terse@sha256:…` in
   a `span.mono`, 496 px of unbroken text in a 388 px column). **LoadCoach's Database page does not
   reproduce**: it measured 412 vs 412 before the change as well as after.

**Left on the machine:** `config.toml.bak` beside FreeWeight's configuration (every write keeps
one, by design); FreeWeight's model rows re-stamped by the discovery pass; the throwaway console's
XDG tree and the Playwright scripts in the session scratchpad, which go with the session.

## 5. What the kickoff got wrong

1. **"A call … takes longer than the console's client timeout … after the client's 10 s default."**
   Discovery has carried its own 120 s timeout since row WP3 (`freeweight_actions`
   `_DISCOVER_TIMEOUT_SECONDS`, `8cc25ca`, in place at WP6's commit `9c6ace1`). WP6's refresh timed
   out at 120 s, not 10 s, and so did this row's live one — 120.8 s. `DEFAULT_TIMEOUT_SECONDS` is
   10 s, but no discovery call has ever used it.
2. **"`runtime.fit_to_device` renders the same way"** (WP6 finding 1). It does not: it is
   `bool = False`, not `bool | None`, so its select is correct and posting `false` is `unchanged`.
   The nullable leaf beside `flash_attention` is `runtime.kv_cache_precision`, an **enum**, which
   rendered its first choice `f16` — so every FreeWeight save wrote *two* keys the operator never
   touched, not one.
3. **"LoadCoach, IdeaPress and PromptCadence publish no nullable boolean."** LoadCoach's
   `RuntimeModelOverride` carries `flash_attention: bool | None` and `kv_cache_precision`, under
   the keyed table `runtime.models.<model>`; FreeWeight and LoadCoach both publish the nullable
   enum. The rule is the generator's either way, but the fix reaches two applications, not one.
4. **"Tests first, against a schema golden with a nullable boolean."** No new golden was needed:
   `tests/fixtures/schemas/freeweight.json` is the reference machine's own document and already
   carries `runtime.flash_attention` and `runtime.kv_cache_precision`. What was missing was a test
   that reads the **rendered markup** — every settings test built its post by hand, which is why no
   test could see a select that posts `false`. `_as_a_browser_would_post()` in
   `tests/integration/test_settings_routes.py` now serialises a page the way a browser would.
5. **"With FreeWeight on `provider.kind = "ollama"`."** The machine is on `llamacpp` with adapters,
   and switching would run WPF2's unfixed finding 9 (§4).
6. **"The probe did not locate the element"** (WP6 §4). It is locatable: walk the DOM for the
   deepest box whose right edge passes `document.documentElement.clientWidth`, and for elements
   whose `scrollWidth` exceeds their `clientWidth` — the second is what finds a `p.mono`, whose own
   box fits while its min-content width stretches the page.

## 6. For the operator

1. **FreeWeight's `config.toml` is as this session found it** (`cmp`-identical), and FreeWeight is
   running on it. A `config.toml.bak` sits beside it from the last write.
2. **WPF2 inherits two things from here.** Its demonstration saves FreeWeight's settings through
   the form, which now works; and finding 9's write-then-refuse is still there, so a provider
   switch on this machine is still the hazard it was.
3. **The catalog's own error family was left alone.** `services/catalog.py` raises `CatalogRefused`
   for any `httpx` error including a timeout, so a slow `set_enabled` or `pull` would still be
   audited `refused`. They are short calls and WP6 saw nothing there; a later row can give them
   `app_api`'s distinction if it matters.
4. **The audit row's `target` changed shape.** A settings write now names what it did rather than
   every key on the form. Anything reading `target` as *the submitted set* should read
   `params.written` / `params.applied` / `params.refused` instead, which are unchanged.

## 7. What runs next

Wave 1's other rows (WPF3, WPF7, WPF8) are independent of this one and touch different files;
WPF7 and WPF8 had already merged into `main`, and `main` merged cleanly into this branch
(`aea1b93`). **WPF2 runs after this row**, as the roadmap says, and starts from a form that saves.
