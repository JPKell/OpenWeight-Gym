# W4 Handoff — WeightRoomGym Phase 4: settings forms over the schema verbs, the doctor, tokens

**Row:** W4 of [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md) (Opus 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`w4-weightroom-p4-settings-doctor.prompt.md`](w4-weightroom-p4-settings-doctor.prompt.md).
**Ships:** `wr-gym 0.4.0`, **prepared, not tagged, not pushed, not published.** One new record,
[ADR-0130](../adr/0130-weightroomgyms-application-tokens-carry-admin-scope.md).

> **Read §2 before anything else.** This row did **not** run in `~/ai/suite/WeightRoom`. Row W5
> was already executing in that working tree when this session started, so W4 was moved to a
> git worktree at the operator's instruction and its three commits are on a branch that is not
> yet merged.

## 1. What was built, by commit

Branch `row/w4-settings-doctor`, worktree `~/ai/worktrees/weightroom-w4`, based on `e02ad4f`.

| Commit | Gate | What |
|---|---|---|
| `bfb3e02` | A | `services/settings_forms.py` — the schema-document reader (`<app> config schema --json`; in process for WeightRoomGym's own), the 60-second `SchemaCache`, the form model (`FormField`/`FormSection`/`SettingsForm`), `source`/`shadowed`/`live`, the secret rule, the derived *pending restart*; goldens over the four real documents; 34 tests |
| `162c1bb` | B | `services/config_files.py` (`tomlkit` round-trip, `base_mtime` race, validate-before-write, `.bak`, `fsync`+rename), `save_settings` with per-key outcomes, `web/routes/settings.py` (four JSON routes, five pages, the raw editor on its own page), `FormField.parse`, `domain/audit.py`'s three new actions, `web/rendering.py`'s side nav; 37 tests over a real executable |
| `37b22dc` | C | `services/doctor.py` + `wr-gym doctor` + `/doctor`, `services/tokens.py` + the Tokens pages, ADR-0130 and the scope change, four defects found while demonstrating, `CHANGELOG.md`, `README.md`, `0.4.0`; 25 tests |

Full local gate, in the worktree, Python **3.14.4** (`~/ai/suite/WeightRoom/.venv`, invoked as
`PYTHONPATH=$PWD/src /home/jpk/ai/suite/WeightRoom/.venv/bin/python -m pytest`, see §2.2):
`ruff format --check .` (125 files), `ruff check .` clean, `mypy src tests` clean (119 files,
strict), `lint-imports` **5 contracts kept**, `wr-gym config reference --check` matches,
`pytest -m "not live and not performance"` **757 passed, 1 skipped**, coverage **90.42 %**
(floor 85 %).

## 2. The thing the next row most needs to know: this ran in a worktree

### 2.1 Why, and what is where

Seventeen minutes into this session, `git status` in `~/ai/suite/WeightRoom` showed files
changing under it: `services/docs.py` written seconds earlier, `web/app.py` and
`web/static/vendor/` two minutes earlier, and commits `4afb0db`/`523a962` landing mid-session.
That is **row W5** (the docs viewer), running in the same tree. Both rows must edit
`web/app.py`, `web/rendering.py`, `CHANGELOG.md` and `__about__.py`, and both bump the version;
CLAUDE.md's working-tree rule is explicit that a tree with a run in progress is not to be worked.
The operator chose the worktree option.

* **Branch:** `row/w4-settings-doctor`, three commits, based on `e02ad4f` (`main` at the time).
* **Worktree:** `~/ai/worktrees/weightroom-w4`. Created with
  `git worktree add -b row/w4-settings-doctor ~/ai/worktrees/weightroom-w4 HEAD`.
* **Not merged.** `main` does not have W4. Merging is the operator's, after W5 lands.

### 2.2 The worktree has no virtualenv of its own

Every gate command above was run as:

```bash
cd ~/ai/worktrees/weightroom-w4
V=/home/jpk/ai/suite/WeightRoom/.venv/bin
PYTHONPATH=$PWD/src $V/python -m pytest -q          # and -m weightroom for the CLI
$V/ruff check . && $V/mypy src tests && $V/lint-imports
```

The main tree's venv is an editable install whose `_editable_impl_wr_gym.pth` is the plain path
`~/ai/suite/WeightRoom/src`, so `PYTHONPATH` shadows it cleanly — verified by asserting
`weightroom.__file__` resolves inside the worktree. `ruff`, `mypy` and `lint-imports` read the
worktree's own config and need nothing.

### 2.3 What the merge will conflict on

W5 touches, and W4 also touches:

| File | W4's change |
|---|---|
| `src/weightroom/web/app.py` | three router imports and their four `include_router` lines; `app.state.schemas = SchemaCache()`; `CONFIG_CHANGED_ON_DISK`/`CONFIG_VALIDATION_FAILED` in `STATUS_BY_CODE` |
| `src/weightroom/web/rendering.py` | `NAV_ITEMS` gains `doctor` and `settings`; `_PAGE_PHASE` shrinks to `Database`; `_PAGE_ELSEWHERE`, `_PAGE_HREF`, `_NO_TOKENS`, `_built_pages`; `app_side_nav(selected=…)` |
| `CHANGELOG.md`, `README.md`, `__about__.py`, `tests/unit/test_about.py` | `0.4.0` — W5 will want `0.5.0` |
| `tests/security/test_audit_routes.py` | nine new `EXERCISES` entries and a `fake_application` fixture |
| `tests/integration/test_shell.py` | the side-nav test, rewritten for the pages this build now serves |

None of these are semantic conflicts; all are additive.

## 3. What this row was asked to decide, and what it decided

### 3.1 The re-authentication token's transport: **the session, not a token**

The kickoff asked for a pick between a header on the JSON write and a second cookie. Neither was
taken, and the third option is what W1 already built.

`POST /reauth` stamps `sessions.reauth_at` and
[`require_fresh_reauth`](../../src/weightroom/services/auth.py) checks it against
`auth.reauth_window_minutes`. **There is no token to transport.** The page posts the operator's
password in the same form as the change; the route opens the window and performs the write in one
request. api.md §2's sketched `"reauth": "<token from POST /reauth>"` field is gone, and
[`api.md`](../apps/weightroom/api.md) §2 and §9 are amended to say so.

Tested against the same-origin rules, which is where the argument for it actually lies. A JSON
write already passes `SameOriginMiddleware`; a form post already passes MirrorWall's
double-submit CSRF; the session cookie is already `__Host-`, `Secure`, `HttpOnly`,
`SameSite=strict`. A second credential would have to live somewhere a script can reach —
`localStorage`, a JS variable, a form field in the DOM — on a console that is **reachable from the
LAN by design** (ADR-0126). It would add an exfiltration target and defend against nothing the
three existing mechanisms do not already cover. A second cookie is the same object as the session
cookie with a shorter life, which `reauth_at` already is.

One thing this makes necessary, and it is easy to get wrong: **the principal must be restamped
inside the request**. The principal was resolved before the password arrived and still carries the
old `reauth_at`; handing it to `require_fresh_reauth` a moment later refuses a password that was
just accepted. `_reauthenticated()` returns a `dataclasses.replace`d principal, and the page tests
cover it.

### 3.2 A key whose document name and file spelling differ: **shown as the document names it**

LoadCoach's singular `[provider]` and plural `[providers.<name>]` (ADR-0077). The WS2 handoff says
the document carries `provider_form` — `"singular"` or `"plural"` — computed from the *effective*
settings after the full precedence chain, so it means "which form is live", not "which form is
written".

The form does not reconcile them, and does not try:

* Both `[provider]`'s leaves and `[providers]`' leaves are in the document's own key sets, so
  **both render**, each in its own section, each with its own `source`.
* A registration the operator typed (`[providers.local].kind`) is not in any key set, but the
  model still types it through `additionalProperties`; the form resolves it that way and renders
  it as a real field rather than as raw text.
* `provider_form` is carried on `SettingsForm` for a page that wants it.
* **A registration is not edited here.** ADR-0117 built a purpose-made admin form for it *inside
  LoadCoach*, which handles the singular-to-plural fold, the secret-by-reference rule and the
  registration lifecycle. A fifth copy of that in the console would be exactly the drift ADR-0127
  exists to prevent. The side nav says so: the `Provider`/`Providers` entries are inert and
  titled *edited on the application's own provider page (ADR-0117)* rather than naming a row.

The escape hatch the plan's *Known risks* names — the raw editor — is there and works.

### 3.3 Two decisions the kickoff did not anticipate

**The key list is the document's three sets, not a walk of `json_schema`.** Walking the schema is
the obvious implementation and it is wrong twice over against the real documents: it misses every
key that is not a model field (LoadCoach's database-only `queue.paused`/`queue.draining`,
IdeaPress's eleven `models.stages.<stage>` bindings, PromptCadence's `[tiers.<name>]` instances)
and it *double-counts* `approval.gate_step_cost`, once whole and once split into
`.currency`/`.nanos`, because the application's own `leaf_keys()` stops at the `Money` value
object and a walk does not. The application decides where a leaf ends. The schema walk survives
only to order the fields within a section in the model's own order. All five documents now render
with **zero undescribed keys** (§5).

**The raw TOML editor is its own page** (`/apps/{app}/settings/raw`), not a `<details>` beside the
form. It shows the file verbatim — that is what makes it useful — and FreeWeight's file carries
`auth.tokens`. A settings page with the editor inline would ship every application's bearer tokens
in every response, to a shoulder, a screenshot or a cached page, on a console reachable from the
LAN. The form redacts; the editor is asked for. `spec.md` §7.4 is amended from *beside the form*
to say this and why.

## 4. ADR-0130, and how it was found

Development plan Phase 4 criterion 1 — change LoadCoach's `routing.min_confidence` from the
console with LoadCoach running — **failed on the first attempt**, and the failure was correct:

```text
PUT /api/v1/apps/loadcoach/settings  {"changes": {"routing.min_confidence": 0.25}}
→ "outcome": "refused",
  "message": "loadcoach refused: 'weightroom' holds the 'write' scope; 'admin' is required.
              Scopes are cumulative: admin contains write contains read."
```

ADR-0126 rule 8 chose the console's token scopes — `write` for LoadCoach, `write,approve` for
PromptCadence — at row W1, before the settings page existed. ADR-0127 rule 4, decided later,
routes every runtime-changeable key through `PUT /api/v1/settings`, which **both** applications
require `admin` for. Two accepted records that do not compose is a documentation defect, and
CLAUDE.md says to close one with a record rather than a quiet one-line widening, so:
[**ADR-0130**](../adr/0130-weightroomgyms-application-tokens-carry-admin-scope.md), which amends
ADR-0126 rule 8 to `{"loadcoach": "admin", "promptcadence": "admin,approve"}` and states plainly
that this is a real widening — the privilege is not new, only its route is, since the same session
already edits the same application's `config.toml` in place, drives its unit, and from W7 writes
into its database.

**The reference machine's tokens were re-issued** as part of the demonstration (`token revoke
weightroom` then `token create weightroom --scope admin …`, the secret written back to
`~/.config/wr-gym/secrets/<app>.token` at `0600`). The old ones are revoked, not deleted, and
appear in each application's own `token list`. A `doctor` rule reports an install still on the
narrower scope and prints the two commands.

## 5. The demonstration — plan Phase 4 criteria 1–4, on the reference machine

Run against the four **real** applications (`freeweight` 1.2.1, `loadcoach` 1.3.1, `ideapress`
1.4.1, `promptcadence` 1.3.3, all `active` under `systemd --user`) and the real Ollama, from a
scratch console on `127.0.0.1:8779` with its own database and CA so the operator's own `wr-gym`
on `10.77.10.84:8769` was never touched.

### Criterion 1 — a runtime key, live, no restart ✅

```text
$ loadcoach config show | grep min_confidence
routing.min_confidence          0.05          (default)

PUT /api/v1/apps/loadcoach/settings  {"changes": {"routing.min_confidence": 0.25}}
→ {"outcomes": {"routing.min_confidence": {"outcome": "applied"}},
   "written": [], "pending_restart": false}

$ loadcoach config show | grep min_confidence          # one second later
routing.min_confidence          0.25          (database)

$ ls -A ~/.config/loadcoach/
(empty)                                                # the file was never touched (rule 4)
```

### Criterion 2 — a security key, the password, the comment, the restart ✅

Without a fresh `POST /reauth`:

```text
→ 403 {"code": "REAUTH_REQUIRED",
       "message": "This action needs the password again (POST /reauth) within the last 5 minutes."}
```

After it, writing `server.port` (a security key) and `runtime.context_size` (which carries a
comment) together:

```text
$ diff config.toml config.toml.bak
3,6c3
< context_size = 4096   # MEMORY_SAFETY.md: never unset
<
< [server]
< port = 8775
---
> context_size = 8192   # MEMORY_SAFETY.md: never unset
```

The comment above the key is intact, the new `[server]` table is appended, nothing else moved,
and `freeweight config validate` accepts the result. The audit row:

```json
{"action": "settings.write", "app": "freeweight", "outcome": "ok", "security": true,
 "target": "runtime.context_size, server.port",
 "params": {"written": ["runtime.context_size", "server.port"], "touched_security": true}}
```

The page showed *pending restart*; the restart button
(`POST /apps/freeweight/restart-for-settings`, the ADR-0125 control path) returned `303`, the
unit came back `active running` **listening on 8775**, and `pending_restart` cleared to `false`.

**The reference machine was then restored**: `config.toml` back to its original two lines,
`config.toml.bak` removed, `freeweight` restarted and listening on 8765 again;
`routing.min_confidence` set back to `0.05`. One residue, deliberate: LoadCoach's `settings` row
still exists, so `config show` says `0.05 (database)` where it said `0.05 (default)`. The value
and the behaviour are identical; deleting the row is a raw write into another application's
database, which is ADR-0124's five-part guard and row W7's, not this row's.

### Criterion 3 — a field added to a fixture document appears, no code change ✅

`tests/unit/test_settings_forms.py::test_a_field_added_to_a_fixture_document_appears_with_no_code_change`
adds `server.invented_number` to LoadCoach's committed document exactly as an application that
grew a key would emit it — the field in `json_schema`, the key in `config_only` — and asserts the
rendered field carries its type, default, bounds and description. Passes.

### Criterion 4 — `wr-gym doctor` on the reference machine ✅

```text
WARN  token.scope.promptcadence  WeightRoomGym's token on promptcadence lacks admin; a runtime
                                 settings write is refused (ADR-0130).
        scope 'approve, write'  [ADR-0130]
        $ promptcadence token revoke weightroom
        $ promptcadence token create weightroom --scope admin,approve --json
note  lan.ollama_host  Ollama listens on the LAN, unauthenticated. That is the operator's daemon
                       and the operator's choice; it is the one thing besides this console that
                       answers from another room.
        OLLAMA_HOST=0.0.0.0:11434  [LAN_ACCESS.md §5]
        $ # LAN_ACCESS.md §5: set OLLAMA_HOST=127.0.0.1:11434 in the override, then
        $ sudo systemctl edit ollama.service && sudo systemctl restart ollama.service
?     polkit.ollama_restart  Whether the console may restart Ollama is not yet known — nothing
                             has been tried, and polkit will not answer the question in advance.
        $ sudo install -m 0644 <the file printed above> /etc/polkit-1/rules.d/50-weightroom-ollama.rules

warning 1  notice 1  unknown 1  ok 25
```

After re-issuing PromptCadence's token, **27 pass, one notice, one unknown, exit 0**. Every
`MEMORY_SAFETY.md` §2.1 line passes (the operator applied §2.1 after W0) and both §2.2 units carry
their caps, so the memory-safety half is green rather than the red the W0 checklist expected.
`--all` prints the passing rules.

### The pages, against the real documents

All eleven render `200`; **zero undescribed keys** on any of the five:

| Application | Sections | Fields | live | security |
|---|---:|---:|---:|---:|
| freeweight | 17 | 84 | 12 | 14 |
| loadcoach | 13 | 66 | 7 | 15 |
| ideapress | 11 | 65 | 19 | 6 |
| promptcadence | 12 | 72 | 5 | 57 |
| weightroom | 12 | 50 | 6 | 33 |

## 6. Four defects the demonstration found, all fixed here

Each of these is a thing no unit test over a fixture would have caught, which is the argument for
the criterion being "on the reference machine" rather than "covered".

1. **ADR-0130** — §4 above.
2. **The §2.2 memory rule checked all four units.** `MEMORY_SAFETY.md` §2.2 and ADR-0125 rule 1
   cap the two that launch `llama-server`; IdeaPress and PromptCadence hold no model in their own
   cgroup. Two permanent `FAIL` lines the operator would be right to ignore, which is how a
   checklist stops being read. Now `MEMORY_CAPPED` only.
3. **IdeaPress spells `config show --json`'s block `settings`**, where FreeWeight, LoadCoach and
   PromptCadence spell it `values`. W3's `services/overview.py` reads `values` only, so
   **IdeaPress's Overview page has been falling back to dashed figures since W3** and the doctor's
   revision rule could not find its database. Both spellings are read now; IdeaPress's revision
   `0010` is recognised.
4. **The token-list envelope and the *revoked* field differ too** — LoadCoach `{"tokens": …}` with
   `revoked_at`, PromptCadence `{"items": …}` with `active` and a `scopes` list. Reading one shape
   reported every revoked token as live, which is the wrong way round for a credential.

A fifth, minor: the `settings.write` audit row's flag is `touched_security`, not `security_key` —
the redactor blanks any parameter whose name matches `key`, and a redacted boolean reads like a
caught leak rather than a flag.

## 7. Decisions inside the implementation worth knowing

* **`base_mtime` is `st_mtime_ns`.** api.md's field name is kept; nanoseconds are exact in a JSON
  integer where float seconds are not. LoadCoach's own ADR-0117 implementation uses a content
  digest instead — either closes rule 7's race; this one is cheaper and the console reads the
  mtime in the same request that renders the form.
* ***Pending restart* is derived, not stored**: the file's mtime against the unit's uptime. A
  stored flag is wrong after a restart made from a terminal and lost when the console itself
  restarts; the two timestamps are the fact.
* **The file half of a write is one transaction, and goes first.** It is the only half that can be
  refused wholesale (a stale base, the application's validation), so a refusal there must leave
  nothing applied anywhere. Runtime keys follow, each with its own outcome.
* **A runtime key on a stopped application is refused by name** (`APP_STOPPED`, naming the file),
  never quietly written as configuration. The page offers *to file* per key, which writes it as
  configuration explicitly.
* **The form's secret rule is narrower than the audit trail's.** `redact_params` matches `key` and
  `token` anywhere, which here would blank `api_key_file` and `api_key_env` — the references
  ADR-0126 rule 8 configures *instead of* the secret, which the operator must be able to edit —
  and PromptCadence's `tiers.<name>.*_tokens`, which are token counts. The form matches the last
  segment only; redaction of the trail stays deliberately over-broad.
* **An empty box is not an empty value.** A submitted empty string on a field whose value is
  `None` means *leave it unset*; otherwise submitting an untouched form would write
  `database_url = ""` over every optional path in the file. Where the value already *is* `""`,
  that is a real value and emptying stays an edit. Clearing a key is a deletion and belongs to the
  raw editor. Verified: every field of all four real documents round-trips
  `value_text → parse → value` unchanged.
* **`POST /settings/validate` writes an audit row** (`settings.validate`, outcome `pending`). No
  state moves, but a loader is launched over operator-supplied text; the security suite's
  route registry demands an entry for every state-changing route, and exempting this one would
  have weakened the test rather than the route.
* **`services/doctor.py` joined `INSTRUCTION_MODULES`** in the `sudo` grep test. Its whole purpose
  is printing fixes it must not run.

## 8. What is deliberately not here

* **Provider registration forms.** §3.2 — they stay in the application's own ADR-0117 admin page,
  and the side nav says where.
* **A Tokens page for FreeWeight and IdeaPress as a *table*.** FreeWeight's bearer tokens are
  `auth.tokens`, a security key on its own settings page, and its Tokens page says so and links
  there. IdeaPress has no token surface at all and its page says that. Neither invents one.
* **WeightRoomGym restarting itself** from its own settings page. It says so and prints
  `systemctl --user restart weightroom`.
* **A doctor rule for `MEMORY_SAFETY.md` §2.3** (fire the guard once on purpose). It is an action,
  not a reading, and the doctor only reads.

## 9. For the operator

1. **Merge `row/w4-settings-doctor` after W5 lands.** §2.3 lists the overlap. The worktree at
   `~/ai/worktrees/weightroom-w4` can be removed with `git worktree remove` once merged.
2. **The two application tokens were re-issued at `admin` scope** (ADR-0130) on this machine, and
   the old ones revoked. Nothing else about them changed.
3. `wr-gym doctor` is green apart from the `OLLAMA_HOST=0.0.0.0` notice — still the open question
   in `weightroom-work.md` §4 — and the polkit rule, still not installed.
4. **IdeaPress's Overview page was wrong since W3** (§6 item 3) and is fixed on this branch.
5. Nothing was pushed, tagged or published.

## 10. Open for later rows

* **W6 and W7 read this row's output**: the application tokens (now `admin`, ADR-0130) and the
  connection strings, which come from each application's schema document through
  `SettingsForm.field_for("storage.database_url")`.
* **W7's guarded write** will want the same `_reauthenticated` restamp §3.1 describes; it is in
  `web/routes/settings.py` and should move beside `require_fresh_reauth` when the second caller
  arrives rather than being copied.
* **W10** should decide whether `provider_form` and the `[provider]`/`[providers]` duplication is
  worth a note in the generated configuration reference, or whether ADR-0077's fold should finally
  happen in LoadCoach.

## 11. Addendum — operator decisions after the row (2026-09-09, same session)

An interview after the row settled four open items:

* **ADR-0130 confirmed** as written; the re-issued `admin` tokens stand.
* **The `MEMORY_SAFETY.md` §2.1 checklist item** in `weightroom-work.md` §4 is struck — the
  doctor shows all seven lines passing (`a9fb1e3`).
* **The two CLI JSON divergences of §6 were converged at the source, now**:
  [ADR-0131](../adr/0131-cli-json-shapes-converge-on-values-and-items.md). IdeaPress `1.5.0`
  prints `values` (was `settings`); LoadCoach `1.4.0` prints `{"items": …}` (was `tokens`); both
  shapes are written into CLI Standards §9 and §11. Both are **renames shipped as minors** — an
  operator exception to packaging and release standards §3.2, recorded in the ADR with its reason
  (no users of either output yet). This console keeps reading the old names for one major.
* **The merge** was to wait for W5. It was performed by another session at `c425489`, which
  includes this branch through `a9fb1e3` but **not** this addendum, ADR-0131 or the CLI Standards
  amendment — those are a second, small merge of this branch.

