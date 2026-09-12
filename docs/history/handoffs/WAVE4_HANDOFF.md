# Wave 4 handoff — WPF10 ∥ WPF11 ∥ WPF12, one orchestrating session

**Ran:** 2026-09-12, ~01:55–02:35 PDT · **Orchestrator:** Fable 5.1 (attended; this is what
satisfies WPF10's *never overnight*) · **Agents:** WPF10 Opus 5, WPF11 Sonnet 5, WPF12 Sonnet 5,
one worktree each, dispatched at once · **Kickoff:**
`history/prompts/wave4-orchestrator-wpf10-wpf12.prompt.md`. **Ships:** unreleased; nothing pushed,
tagged or published; no version moved.

## 1. What landed

| Row | Repository | Branch head | Merge on `main` | Handoff |
|---|---|---|---|---|
| WPF10 | FreeWeight | `7156c20` | `c4dd2f4` | `WPF10_HANDOFF.md` (moved in from the worktree, Gate B §5 filled by this session) |
| WPF11 | WeightRoom | `47221d1` | `6f50fa8` | `WPF11_HANDOFF.md` (Gate B filled by this session) |
| WPF12 | WeightRoom | `de082e4` (after `main` merged in) | `624272f` | `WPF12_HANDOFF.md` |

Also on WeightRoom `main`: `b876a89` (FreeWeight `spec.md` mirror, byte-identical by `cmp`),
`b47e774` (the two Gate B sections), and the roadmap commit that marks all three rows done.

**Units restarted onto the merges:** `freeweight.service` after `c4dd2f4` (02:09:32 PDT, again at
02:12 to release the Gate B server), `weightroom.service` after `6f50fa8` (02:12:55) and after
`624272f` (02:20:23). All five application units active at the end; `ollama.service` active as
found; GPU idle (≈830–940 MiB).

## 2. What each agent built, and what was reviewed

**WPF10** (Opus 5) found the lost profile in neither of the kickoff's two candidates: the
interaction path's turn caller in `services/runs.py` built its own `GenerationRequest` without
`runtime_profile`, so every interactive suite (`structured_output`, `tool_use`, `tool_recovery`,
`agent`, the judge suite) asked ModelRack for a different launch key on its first measured turn and
ModelRack, correctly, restarted the server flagless. One builder, `_provider_request`, now serves
warm-up, single-call and every turn. Reviewed: the diff, the structural test
(`inspect.getsource(runs).count("GenerationRequest(") == 1` — crude, kept: it is the only check
that fires when a third builder appears), the spec paragraph. No ADR: a mismatched warm server was
already a required restart in ModelRack (`restart_reason="profile_change"`); the row was told to
stop if the cause was in ModelRack, and it was not. Coverage 89.68 %.

**WPF11** (Sonnet 5): `set_enabled`, `_ollama_tag_exists` and `_ollama_delete_tag` raise
`AppTimedOut` on a timeout; the catalog routes audit through `app_api.outcome_of`;
`services/app_api.py` read, not edited (its `_unreachable` wording is duplicated in
`catalog._timed_out` rather than exported — accepted, the collision map asked for exactly that).
The decision the kickoff flagged for review — does `pull` move onto the queue — was moot:
`catalog_pull` has been a queued job since W9. Endorsed the row's choice of **no ADR** over a
retroactive one.

**WPF12** (Sonnet 5): both the stage-run Attempts table and the unit page's Provenance table
render `attempt N · round R · call C` from the shared `_attempt_row`, with one line of copy above
each. The row widened from "the stage-run page's attempts table" to both tables because Gate B's
own text names the unit page and one function builds both rows — endorsed. One review catch
mid-run: the first copy said a `provider_error` "is that retry"; IdeaPress migration 0012 numbers
the **kept** call `0` and every **discarded** call `1+`, so the fix `d14c17d` names both
directions explicitly. Screenshots at 1440/412 px in both themes read by this session: the
authored pair renders as `1 · round 2 · call 1` `provider_error` beside `1 · round 2 · call 0`
`completed`, no sideways scroll.

## 3. The GPU windows

**Window 1 — WPF10 Gate B, PASS** (`WPF10_HANDOFF.md` §5). Three `--detach` runs through the
restarted unit on `llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b`:
`native.structured_output` `01M2AE305H0K52T6RR785VMNP8`, its repeat `01M2AE4CF0K2D1YRM47K95X397`,
then `native.tool_use` `01M2AE569AED5SPRXE3C2HE1CB` while the server was warm. **One
`llama-server` pid, 1811446, `lstart` 02:10:06, across all three**; argv `--ctx-size 8192 --fit
off`; `/props` `n_ctx 8192`, `total_slots 4`; each run `8192 configured []`,
`served_context_observed 8192`. VRAM 2 893–3 038 MiB resident; released by restarting
`freeweight.service`. Before the fix the pid changed between warm-up and first measured turn.

**Window 2 — WPF11 Gate B, PASS for the pull** (`WPF11_HANDOFF.md`, Gate B). `smollm2:135m`
removed from Ollama first, then pulled through a throwaway console on `127.0.0.1:8779` running the
merged checkout: job `01M2AEERDEGH8Z4ZX15QG0FFPB` `completed` in 10.95 s, audit
`01M2AEERDFBWD1HGQD2X2MKNR8 catalog.pull ok`, exactly one `POST /api/pull` in Ollama's journal,
the tag back in `/api/tags`, `/api/ps` empty throughout. The row's own change — a `pending` audit
on a hung application — was **not** made live; its tests are its proof.

**Window 3 — WPF12: not taken.** Proved on the authored fixture, as §6 of the kickoff allowed.

## 4. What this kickoff got wrong

1. **`ollama.service` is a system unit**, not a user unit, and it was **active** the whole time
   (since 2026-09-11 10:20 PDT, `MemoryMax` 24 GiB). `systemctl --user is-active ollama.service`
   answers `inactive` because no such user unit exists. Nothing was started or stopped.
2. **`smollm2:135m` was already pulled**; a real pull needed a `DELETE /api/delete` first.
3. **WPF12's numbering was backwards** in §6: call `0` is the kept answer, `1+` the discarded
   calls. The agent followed the code.
4. **WPF11's decision 2 was already closed at W9** — the kickoff (and this session's brief) read
   it as open.
5. **The FreeWeight API is plain HTTP on 8765** and needs no bearer token from localhost; the
   WPF10 handoff's first draft said `https://…:8766` with a token (8766 is LoadCoach) — corrected.
6. **A console JSON write needs `Sec-Fetch-Site: same-origin`** (ADR-0126 rule 5) — the first
   pull attempt was `403 CSRF_FAILED`. Not in any recipe yet; it is now.
7. **Worktree venvs cannot `pip install -e ".[dev]"` cold**: `mirrorwall>=0.3.1` is prepared, not
   published, so each worktree needed `pip install -e ~/ai/suite/py/MirrorWall` (and SetSpec,
   SweatMeter — the main checkouts carry them editable) first. The kickoff's one-line venv recipe
   fails until MirrorWall 0.3.1 is on PyPI.
8. **WPF10's fake `server_path` was unnecessary**: `launch_flags()` is a pure function of the
   profile, so recording the requests of an in-process run reproduces the defect with no process.
9. **A FreeWeight-row handoff has nowhere to go on the agent's branch** — it belongs in
   `WeightRoom/docs/history/handoffs/`, which is `main` of another repository. This wave had the
   agent leave it untracked at its worktree root and the orchestrator moved it; write that into the
   next FreeWeight row's brief rather than rediscovering it.

## 5. What the next wave inherits

* **WPF13** (ModelRack counts Ollama's thinking tokens) — next, alone, GPU-owning, *never
  overnight*. ModelRack `main` is untouched by this wave. WPF10's handoff §2 suggests promoting the
  launch-key/restart rule into `packages/modelrack/spec.md` as a numbered contract — that row is
  in the right repository to do it.
* **For the operator** (WPF10 §7 item 2): every adapter/context measurement taken on an
  interactive suite under llama.cpp *before* `c4dd2f4` was served at the model's trained context,
  not the recorded one — WP6's and WPF2 Gate C's runs included. They carry the degradation and
  the real `served_context_observed`, so they are readable, not silently wrong; whether to
  re-measure is the operator's call. Single-call suites (`max_context_fit`, `memory_kv`, echo,
  performance) were never affected.
* **The WP6 re-verification** now runs on a FreeWeight whose interactive runs are served at the
  configured context, a console whose catalog timeouts audit `pending`, and attempts tables that
  name the call — three of WP6's eleven findings closed here, WPF13 the last before the re-run.
* **Unpushed:** WeightRoom `main` is 11 commits ahead of origin, FreeWeight 2 (`7156c20`, `c4dd2f4`). The operator's,
  as always.
* Three things not proved live and left to tests: WPF11's `pending` on a hung endpoint, WPF12's
  live retry, and the catalog page listing a freshly pulled Ollama tag (needs LoadCoach or an
  Ollama-provider FreeWeight to refresh — W8's design, not a defect).

## 6. Working-tree state at the end

Worktrees removed, the three `row/*` branches deleted, `git status --short` clean in FreeWeight
and WeightRoom (`py/BaseAiCore` keeps the operator's uncommitted docstring edits, as instructed).
Gate on WeightRoom `main` at the roadmap commit, `.venv/bin/python` 3.14.4: see the roadmap
commit message for the line. FreeWeight `main` at `c4dd2f4` is the same tree WPF10's Gate A ran on
(`ed58b44` was its base and had not moved): 2767 passed, 30 skipped, 31 deselected, 89.68 %.
