# WPF2 Handoff — a refused provider write changes nothing, adapters are inert not fatal, and the console starts an adapter run

**Row:** WPF2 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, wave 2 ·
**Model:** Claude Opus 5 · **Kickoff:**
`history/prompts/wpf2-freeweight-adapter-run-from-the-console.prompt.md`
(wave note `history/prompts/wave2-wpf2-summary.md`) · **Branches:** `row/wpf2-adapter-run` at
`~/ai/worktrees/freeweight-wpf2` and `~/ai/worktrees/weightroom-wpf2`, **neither merged** ·
**Ships:** unreleased, no version bump in either repository.

**Gates A and B are built, green and committed. Gate C — the live proof — is the operator's, and
§6 lists it command by command.** This session ran nothing that loads a model onto the GPU, and
touched none of the operator's units. It did measure the llama.cpp refresh on the reference
machine's real 195 GB directory, which loads no model (§4).

## 1. What shipped

| Repository · commit | Gate | What |
|---|---|---|
| FreeWeight `8fc9325` | A + B | The five defects below, `POST /runs`' `adapter`, `provider_can_serve`, and the tests for each |
| WeightRoomGym `842d254` | B | The Runs page's adapter field, the job parameter, the argv, the Adapters page's *inert* notice, ADR-0140, the api.md and spec amendments |
| WeightRoomGym (this commit) | — | This handoff; the row marked done |

### FreeWeight (`8fc9325`)

1. **A provider write refused at the re-open now writes nothing.** `save_provider` takes a `probe`
   and runs it against the settings the candidate file loads to, before the rename; the Provider
   route's probe builds the provider that configuration names and drops it. Everything
   `build_provider` refuses is therefore refused with `config.toml` untouched and no `.bak`
   written (ADR-0117 rule 2).
2. **A configured `[adapters] directory` under a provider that cannot serve one is inert, not
   fatal** (**ADR-0140**, new). `register_configured_adapters` asks
   `capabilities().adapter_hot_swap` instead of testing for the *presence* of
   `register_adapters` — which `OllamaProvider` has, and which always raises. The directory is
   still read (a typo is still refused on every kind), nothing is offered, a run naming an adapter
   is still refused by name, and `GET /adapters` plus `freeweight adapters list` carry
   `provider_can_serve`.
3. **A run claimed after a provider edit reaches the new provider.** `RunScheduler` takes a
   `provider_source` and reads it before each run, exactly as it already read `registry_source`
   and the stored settings; the web lifespan passes `lambda: app.state.provider`. The closed
   handle is never asked anything, so the *Cannot send a request, as the client has been closed*
   failures cannot recur and nothing launches a `llama-server` it cannot then talk to.
4. **A llama.cpp refresh reuses ADR-0071's digest store.** `discover_models` no longer passes
   `refresh=True` to a provider that keeps a content-digest cache (`_ignores_caches_for`, which
   tests for `clear_digest_cache`, ADR-0071's own public surface). An HTTP provider is still
   refreshed past its five-minute metadata cache. Measured on the reference machine: **6.1 s warm,
   against 254 s for the same directory with the same warm cache under `main`** (§4).
5. **`POST /runs/{id}/repeat` keeps the original run's adapter** — it measured the bare base while
   reusing the original's adapter-bearing runtime profile and calling itself *repeat of …*. A
   repeat whose adapter is no longer servable is refused by name (ADR-0058).
6. **Both web start paths build the runtime profile `run start` builds.** FreeWeight's own Runs
   form built **none at all**, so a run started there sent no `--ctx-size` while recording the
   configured context as a fact, and recorded `adapters_registered` as unstated on a server
   launched with the operator's adapters registered — which silently excludes that run's evidence
   (row H5's I18). `POST /runs` gained the serving mode and an `adapter` field.
7. **`served_context_assumed_incorrectly` no longer contradicts the configuration in front of it**
   (WP6 finding 4): a *configured* context that disagrees with the provider's reading says so, and
   says what the disagreement can mean. What it cannot say is which side is wrong — see §5 item 4.

### WeightRoomGym

* **The Runs page starts a run under an adapter.** A `<select>` of the available entries from
  FreeWeight's `GET /adapters`, rendered only where FreeWeight reports `provider_can_serve: true`;
  `adapter` as a `freeweight_suite_run` parameter, checked against
  `^[a-z][a-z0-9_-]{1,63}$` because it becomes a child's argv; `--adapter` appended to the same
  capped command. **Repeat** needs no console change — it calls FreeWeight's own repeat, which now
  keeps the adapter.
* **The Adapters page names an inert directory**, with the key that fixes it and a link to the
  Provider page.
* `spec.md` §7.10 and `apps/freeweight/api.md` §2a and §4 amended; ADR-0140 written and indexed;
  ADR-0061 carries its *Amended by* note.

## 2. The five decisions this row was asked to make

### 1. Adapters with a provider that cannot hot-swap → **configured and inert, and said so**

ADR-0140, in full there. In short: refusing the combination keeps a legal configuration the
application cannot start on, makes an operator edit two blocks to change one, and would put a
capability check inside the configuration loader, which reads no provider. Inert moves the refusal
to the only place it changes an answer — a run that names an adapter — which ADR-0058 already
governs. The state is named on `GET /adapters`, in `freeweight adapters list`, and on the console's
Adapters page.

The behaviour was already **documented** as this: `register_configured_adapters`' docstring says "a
provider that cannot register adapters is left alone". Only the test was wrong — presence of the
method rather than the capability — so ADR-0140 mostly writes down an intention the code had and
did not keep. ADR-0061 rule 2 is amended, not superseded.

### 2. The digest cache → **reused, keyed by exactly what ADR-0071 already keys it by**

Nothing in the cache needed changing. `JsonFileDigestStore` is already durable, already keyed by
path + size + mtime + inode, already atomic, already pruning. The defect was one argument in
FreeWeight: `discover_models` asked `list_models(refresh=True)`, and for llama.cpp that flag
discards the digest store as well as the header cache. The rule now is: **a provider whose
identities come from hashing file content is refreshed without the flag** — its directory is
re-globbed on every call and its header cache is stamp-checked on every hit, so a model added,
replaced or removed is still found, and only changed bytes are hashed. An operator who wants a
re-hash has `clear_digest_cache` (and deleting the file).

### 3. The Start form's adapter field → **only where it can be served, and listed, not typed**

Rendered only when FreeWeight answers `provider_can_serve: true`, and then as a select of the
entries FreeWeight reports `available` and `in_directory`, with *none — the bare base* first. An
unavailable entry is left out: it is refused for a reason the operator fixes in the directory, not
in this form, and the Adapters page already names it. **Compatibility with the chosen base stays
FreeWeight's** — the console never filters by base and never pre-judges a pairing; it renders
FreeWeight's refusal. The name is still validated for *shape*, because it reaches a child process's
argv.

### 4. `POST /api/v1/runs` → **yes to the API, no to FreeWeight's own HTML form**

The API gained `adapter` (three lines, once the start path had to read the directory anyway for the
serving mode), which closes a real asymmetry: `GET /runs?adapter=` could filter by adapter while
nothing over HTTP could create one. `api.md` §4 was edited first and mirrored.

FreeWeight's **Runs form** deliberately did *not* gain a field. The console is the operator's
interface for FreeWeight after W10, its Start goes through the capped job (ADR-0119), and a second
select on a page nobody is asked to use is work with no reader. The kickoff's phrasing — "so that
FreeWeight's own UI can start one too" — conflates the two; the API is not the UI.

### 5. Repeat → **it did not keep the adapter; fixed**

`repeat_run` never read the original's `adapter_id`, so a repeat of an adapter run measured the
**bare base** — and, because it faithfully reuses the original's *runtime profile*, recorded
`adapters_registered = true` while doing so. The wrong subject and a profile hash asserting a
serving mode that did not happen, under the label *repeat of …*. It now reads the stored row (by
row, so a renamed manifest still resolves) and passes it to `create_run`; its two callers pass the
directory. A repeat whose adapter has left the directory is refused by name rather than falling
back.

## 3. The gates

| Gate | Repository | Result |
|---|---|---|
| A | FreeWeight | green (§7) |
| B | FreeWeight + WeightRoomGym | green (§7) |
| C | — | **the operator's** (§6) |

Every Gate A and Gate B bullet of the kickoff has a test:

* *a provider write refused at the re-open leaves the file byte-identical* —
  `tests/unit/test_provider_admin.py` (the probe, and that the probe sees the candidate's
  settings), `tests/integration/test_provider_admin_api.py` (both `PUT` and the page's form, the
  file and its `.bak`);
* *`config validate` agrees with the running application on the adapters combination* —
  `tests/unit/test_provider_factory.py::…::test_the_running_application_and_config_validate_agree_on_the_combination`,
  plus the inert-registration and `CapabilityUnsupported` tests beside it;
* *a second refresh of an unchanged directory hashes nothing* —
  `tests/unit/test_model_discovery.py::TestDigestCacheReuse`, whose first test runs the second pass
  through a **new provider** over the same `state_dir` with the hasher rigged to fail (a restart),
  with a changed-file test and an HTTP-provider test beside it. Reverting the one-line change makes
  it fail, which was checked;
* *a run the scheduler claims after `PUT /provider` reaches the new provider* —
  `tests/unit/test_scheduler.py::TestProviderEdits`, where the old handle raises on **any**
  attribute access, so "never asked" is asserted rather than hoped for; the orphaned
  `llama-server` was a consequence of that same closed handle;
* *a llama.cpp run with a configured context launches with `--ctx-size`, with and without adapters
  registered* — `tests/unit/test_runtime_profile.py::TestTheContextSurvivesTheServingMode`
  (parametrised over `None`/`False`/`True`, asserted on ModelRack's own `launch_flags`) and
  `tests/e2e/test_run_journey.py::TestTheConfiguredContextReachesTheServer` (the page's form and
  the API, each to `--ctx-size 8192` from the run's **stored** profile);
* *the job's argv carries `--adapter`; an unknown adapter is refused in FreeWeight's own words; the
  run's subject names the adapter* — `tests/integration/test_job_kinds.py` (argv, and no flag when
  no adapter), `tests/e2e/test_run_journey.py` (the API refuses `terse` on a provider that cannot
  serve it, and creates no run), `tests/integration/test_adapter_subjects.py::TestARepeatRepeatsTheSubject`
  (the subject), `tests/integration/test_freeweight_pages.py` (the field's presence and absence,
  the parameter, and a name the console will not spell).

## 4. The refresh, measured on the reference machine

No model is loaded by a llama.cpp discovery pass — it reads GGUF headers and hashes files — so this
was measured in this session, with a throwaway FreeWeight (its own XDG tree, its own database, its
own `state_dir` seeded with a **copy** of the operator's `digests.json`, 27 entries), read-only over
`~/ai/models/llm` (23 files, 195 GB).

| | `models refresh --json` | digest file |
|---|---|---|
| **`main`** (`FreeWeight/.venv`, 1.2.1) | **254.03 s** | rewritten |
| **this branch** (`freeweight-wpf2/.venv`) | **6.13 s** first pass, **6.02 s** second | **byte-identical** (md5 unchanged) |

Both passes on this branch stored all 27 models (`added 27` then `unchanged 27`). WP6 measured 2–4
minutes per refresh on this directory and the digest file rewritten each time; the console's 10 s
client timeout (WPF1's half) is no longer anywhere near the warm figure.

## 5. What the kickoff got wrong

1. **"A llama.cpp refresh reuses its digest cache"** reads as FreeWeight's cache needing work,
   keyed by "what ADR-0071 names". The cache is ModelRack's, and it was already correct and already
   durable; the bug was FreeWeight *asking for it to be ignored*. One argument, not a mechanism.
2. **"The combination of adapters and a provider that cannot serve them is settled by decision"** —
   true, but the code already declared the answer this row chose, in the docstring of the function
   that got it wrong. The decision was cheaper than the kickoff implies, and ADR-0061 needed an
   amendment note rather than a replacement.
3. **"`config validate` agrees with what the running application accepts"** is written as if
   `config validate` had to change. It did not: once startup stops refusing the combination, the
   loader and the application agree by construction. Nothing was added to the loader, and nothing
   should be — it reads no provider.
4. **"Either the `/props` reading is wrong, or those launches lost the flag" (finding 4) — neither
   explanation fits the two runs WP6 read, and this row could not settle it.** Both of those runs
   carried a profile with `context_size = 8192`: one was a CLI `run start` (which builds the
   profile from `[runtime]`) and one was a **repeat** (which reuses the original's stored profile),
   and `launch_flags` adds `--ctx-size` whenever the profile has one, independently of `--lora`.
   `fit_to_device` defaults to `False`, so both also carried `--fit off`. So the flag was almost
   certainly sent, which leaves ModelRack's `read_served_context` — it reads
   `default_generation_settings.n_ctx` from `/props`, and 32 768 is exactly
   `Qwen2.5-1.5B-Instruct`'s trained context — as the suspect. **That is ModelRack's code, in
   neither of this row's two repositories, and deciding it needs a live `llama-server`.** §6 item 2
   is the probe; if it confirms the reading, the fix is a ModelRack row and this row's degradation
   text is already honest about not knowing.
   What this row *did* find in the same area is a real lost flag on a different path: FreeWeight's
   own Runs form built no runtime profile at all (§1 item 6).
5. **Decision 5's "confirm … or fix it"** understates it: the repeat dropped the adapter *and* kept
   the profile that claimed the adapter was registered, so the record was wrong in two directions
   at once.
6. **"Runs after WPF1, whose fixed Settings form this row's demonstration uses."** It does not need
   to: `[adapters] directory` is already set on the reference machine — the operator left it there
   on 2026-09-11 — so nothing in Gate C writes a settings key. WPF1 is still a merge-order
   dependency, and its timeout fix is what makes the refresh in §6 item 1 read as `ok`.
7. **The kickoff's Gate C asks for "a refused provider switch".** After ADR-0140 the switch WP6
   used (`llamacpp` → `ollama` with adapters on) is **no longer a refusal** — that is the decision.
   The refusal that remains, and the one §6 item 3 uses, is a kind this build cannot construct.

## 6. Gate C — the live proof, for the operator

**It needs both branches running**, because the console reads `provider_can_serve` from FreeWeight
and starts the run through FreeWeight's CLI. Against the operator's unpatched FreeWeight 1.2.1 the
Start form shows no adapter field at all, correctly (the key is absent, so the console does not
assume `true`).

Ordered. Steps 1–3 load no model; step 4 does. One live load at a time (ADR-0119); nothing else in
wave 2 should be mid-call.

**0. Put the branches where the services run.** Either merge both `row/wpf2-adapter-run` branches
first (this row's merge order is *first* in both repositories, per the wave note), or run
FreeWeight from the worktree for the demonstration. Restarting `freeweight.service` is the
operator's call — this session did not touch it.

```bash
# after merging, in the operator's own checkouts:
systemctl --user restart freeweight.service && systemctl --user status freeweight.service
curl -sk https://127.0.0.1:8766/api/v1/adapters | python3 -m json.tool | head -20   # provider_can_serve: true
```

**1. A refresh inside the console's timeout** (no model): *Models → Refresh from provider* on
FreeWeight's page in the console. Pass: the audit row's outcome is `ok`, not `refused`, the page
shows 27 `llamacpp` models, and `~/.local/share/freeweight/llamacpp/digests.json` keeps its mtime.
The same, from the CLI, for a number:

```bash
cd /home/jpk/ai/suite/FreeWeight && /usr/bin/time -f "%e s" .venv/bin/freeweight models refresh --json
```

**2. Which side of finding 4 is wrong** (needs a `llama-server`, so one model load). Start any
llama.cpp run with `[runtime] context_size = 8192` set — step 4's bare-base run will do — and while
it is resident:

```bash
pid=$(pgrep -x llama-server) && tr '\0' ' ' < /proc/$pid/cmdline; echo
port=$(ss -ltnp 2>/dev/null | grep "pid=$pid" | grep -oP '127.0.0.1:\K[0-9]+' | head -1)
curl -s "http://127.0.0.1:$port/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); g=d.get("default_generation_settings",{}); print("n_ctx", g.get("n_ctx"), "| total_slots", d.get("total_slots"), "| keys", sorted(g)[:12])'
```

Pass, either way, is an answer: `--ctx-size 8192` present in the argv **and** `n_ctx` 32 768 means
ModelRack's reading is wrong and needs its own row; `--ctx-size` absent means a launch path still
loses it and this row missed it.

**3. A refused provider switch that changes nothing** (no model). On the console's Provider page,
with the password, save `kind = vllm` — a real `ProviderKind` this build cannot construct:

```bash
sha256sum ~/.config/freeweight/config.toml
# … save on the page, read the refusal, then …
sha256sum ~/.config/freeweight/config.toml   # identical
ls -la ~/.config/freeweight/config.toml.bak  # unchanged mtime, or still absent
systemctl --user is-active freeweight.service
```

Pass: the page renders FreeWeight's own refusal naming `vllm`, the digest is identical, no new
`.bak`, and the running provider is still `llamacpp` (`GET /api/v1/provider`). Then, for ADR-0140's
half: saving `kind = "ollama"` with `[adapters] directory` set is now **accepted**, FreeWeight
re-opens on Ollama, and its Adapters page says the directory is inert. Put `llamacpp` back
afterwards — the operator's chosen configuration (2026-09-11).

**4. The two runs, from the Runs page** (each loads a model; one at a time). Bare base first, then
`terse`, both on `native.structured_output`, both followed from the Starting page:

* the Start form shows *Adapter* with `terse · base Qwen2.5-1.5B-Instruct.Q8_0` and *none — the
  bare base*;
* the job's output line begins `$ … freeweight run start --model … --suite … --adapter terse
  --json`;
* the adapter run's subject reads `…Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5` — the
  argument reached the wire, which is H6's lesson and the thing to check;
* *Repeat* on the adapter run queues a run whose subject names `terse` too (this is decision 5's
  proof, and it is new behaviour);
* the adapter's page shows its deltas against the bare base, and Compare reads the two runs.

Pass for §1 item 7: neither run carries `served_context_assumed_incorrectly` **or** it carries the
new wording, which names both possibilities instead of claiming an assumption. Screenshots in both
themes, as the kickoff asks.

## 7. The gate, with the interpreter named

**FreeWeight** — `~/ai/worktrees/freeweight-wpf2/.venv/bin/python`, **CPython 3.14.4**
(`mirrorwall 0.3.1`, `setspec 0.6.0` and `sweatmeter 0.4.0` installed from the workspace checkouts,
since 0.3.1 is prepared and unpublished):

```text
ruff format --check .   355 files already formatted
ruff check .            All checks passed!
mypy src tests          Success: no issues found in 324 source files
lint-imports            Contracts: 4 kept, 0 broken
pytest -m "not live and not performance" --cov
                        2751 passed, 30 skipped, 31 deselected in 268 s
                        Total coverage 89.65% (floor 85%)
```

**WeightRoomGym** — `~/ai/worktrees/weightroom-wpf2/.venv/bin/python`, **CPython 3.14.4**:

```text
ruff format --check .   233 files already formatted
ruff check .            All checks passed!
mypy src tests          Success: no issues found in 226 source files
lint-imports            Contracts: 5 kept, 0 broken
pytest -m "not live and not performance" --cov
                        1872 passed, 3 skipped, 10 deselected in 159 s
                        Total coverage 90.45% (floor 85%)
```

`git status --short` clean in both worktrees at the start and the end.

## 8. For the operator

1. **Nothing is pushed, tagged or merged**, and no version moved. FreeWeight's commit is `8fc9325`;
   the console's are `842d254` and this handoff's commit.
2. **Two canonical documents were edited in my worktree's `docs/`, not in `~/ai/suite/WeightRoom`**:
   `adr/0140-…md` (new), `adr/README.md`, `adr/0061-…md` (an *Amended by* line),
   `apps/freeweight/api.md`, `apps/weightroom/spec.md`, `roadmap/weightroom-work.md`, and this
   handoff. `api.md`'s mirror in FreeWeight was copied with `cp` and verified with `cmp`
   (`scripts/sync_docs.py` resolves the canonical tree as `../WeightRoom/docs`, which does not
   exist beside a worktree, so it cannot be run from there).
3. **ADR-0140 may collide.** WPF4 and WPF5 are writing in the same wave; 0139 was the highest
   number on `main` when this row started. If another row also took 0140, renumber at merge.
4. **`docs/openapi.json` was regenerated** (`scripts/generate_openapi_snapshot.py`) because the
   docstrings FastAPI publishes changed. WPF5 adds a FreeWeight route this wave, so expect a
   conflict in that file; regenerate rather than resolve it by hand.
5. **A provider edit still interrupts a run in flight** — `_reload` closes the handle the running
   run holds, which the code says is the honest reading of changing the provider under a
   measurement. Unchanged by this row, and worth an operator's eyebrow before saving that page
   while a run is live.
6. **The reproducibility fingerprint still does not name the adapter**, so `check_repeatable`
   cannot notice that a repeat's adapter changed identity — only that it is missing from the
   directory. A candidate for its own row if adapter subjects are ever repeated across machines.
