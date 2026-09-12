# Kickoff — Wave 4, the orchestrating session: WPF10 ∥ WPF11 ∥ WPF12

**You are the wave's orchestrator.** Fable 5.1 · high. You do not write the three rows — three
agents do, one per row, each in its own worktree. You own the four things an agent must never
touch: **the GPU, the operator's shared units, `main` in every repository, and the merge**. You
also own the judgement calls the rows raise, because WPF10 is a **never overnight** row and this
session attending is what satisfies that rule.

**Working directory:** `~/ai/suite` (the workspace; each repository is its own git repo — never run
git from the workspace root). **Date this was written:** 2026-09-12.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and
[`weightroom-work.md` §2](../../roadmap/weightroom-work.md), which every agent gets by reference in
its brief. Two rules of the W arc that this wave is still under, and that you enforce on every
agent's commit:

* **Nothing is pushed, tagged or published**, by you or by any agent. Ever. Standing instruction.
* **No version bumps.** Every change goes under `## [Unreleased]` even if a kickoff names a
  version. The W arc ends at the operator's WR-1.0 declaration, not before.

## 1. The three rows

| Row | Repository | Kickoff | Gate B needs |
|---|---|---|---|
| **WPF10** — a launch path that loses the runtime profile | FreeWeight | [`wpf10-freeweight-a-launch-path-that-loses-the-runtime-profile.prompt.md`](wpf10-freeweight-a-launch-path-that-loses-the-runtime-profile.prompt.md) | **GPU** — real `llama-server` launches |
| **WPF11** — a catalog call slower than the client is not a refusal | WeightRoomGym | [`wpf11-weightroom-catalog-calls-slower-than-the-client.prompt.md`](wpf11-weightroom-catalog-calls-slower-than-the-client.prompt.md) | `ollama.service` + a real pull |
| **WPF12** — the attempts table names the transport call | WeightRoomGym | [`wpf12-weightroom-the-attempts-table-names-the-transport-call.prompt.md`](wpf12-weightroom-the-attempts-table-names-the-transport-call.prompt.md) | a browser; a real retry only if you make one |

WPF13 (ModelRack counts Ollama's thinking tokens) is **not in this wave** — it needs the GPU for
its own Gate B and it changes a package every application reads. It runs after this wave merges.

## 2. What each agent may do, and what only you may do

Put this verbatim in every agent's brief.

**The agent may:** work only inside its own worktree; create commits on its own branch; run the
full gate in its own repository's venv; start and stop **its own** throwaway servers on **its own**
ports with **its own** XDG tree; read the operator's running applications over HTTP.

**The agent may never:**

* touch the GPU — no model load, no `llama-server`, no Ollama generate, no `pytest -m live`;
* run `systemctl --user` against any of `weightroom freeweight loadcoach ideapress promptcadence
  ollama` — start, stop, restart or edit;
* write to the operator's config or data trees (`~/.config/<app>`, `~/.local/share/<app>`) —
  reads over HTTP are fine, files are not;
* merge, rebase onto a moving `main`, `git push`, tag, or `git add -A`;
* work in another row's worktree, or on `main` in any repository.

**Only you:** every GPU run, every unit verb, every merge, every `main` commit, and any decision
that changes a document under `WeightRoom/docs/` that two rows both touch
(`roadmap/weightroom-work.md` above all).

## 3. Branches, worktrees, ports

Create the worktrees yourself before dispatching, so an agent never runs `git worktree add`:

```bash
git -C ~/ai/suite/FreeWeight  worktree add ~/ai/worktrees/freeweight-wpf10  -b row/wpf10-runtime-profile
git -C ~/ai/suite/WeightRoom  worktree add ~/ai/worktrees/weightroom-wpf11 -b row/wpf11-catalog-pending
git -C ~/ai/suite/WeightRoom  worktree add ~/ai/worktrees/weightroom-wpf12 -b row/wpf12-transport-call
```

Each worktree needs its own venv (`python -m venv .venv && .venv/bin/pip install -e ".[dev]"`)
— the main checkout's `.venv` is an editable install of the main checkout and will import the
wrong tree. Tell each agent which interpreter it is naming in its gate report.

| Row | Worktree | Throwaway console | XDG tree |
|---|---|---|---|
| WPF10 | `~/ai/worktrees/freeweight-wpf10` | none (FreeWeight `serve` on `18765` if it wants one) | its own scratchpad |
| WPF11 | `~/ai/worktrees/weightroom-wpf11` | `127.0.0.1:8779` / trust `8780` | its own scratchpad |
| WPF12 | `~/ai/worktrees/weightroom-wpf12` | `127.0.0.1:8789` / trust `8790` | its own scratchpad |

Check `ss -ltnp` before handing a port out — another session may hold it. Kill a throwaway by pid
after verifying `/proc/<pid>/environ` carries that row's `WEIGHTROOM_SERVER__PORT`; **never
`pkill -f`** (it has matched and killed the invoking shell here before).

## 4. The collision map

* **WPF11 and WPF12 share WeightRoomGym** and are otherwise disjoint: WPF11 is
  `services/catalog.py` plus the catalog routes and their audit; WPF12 is the stage-run page's
  attempts table (`web/routes/ideapress.py`'s stage-run route and its template) plus
  `tests/fixtures/ideapress/`. Neither should need `services/app_api.py` — WPF11 **reads**
  `outcome_of` and reuses it; if it finds itself editing that function, it must say so in its
  handoff, because that is WPF1's shared code and WPF12 renders audit outcomes too.
* **`CHANGELOG.md` and `docs/roadmap/weightroom-work.md`** are the guaranteed textual conflicts.
  Tell both WeightRoomGym agents to write their `## [Unreleased]` entry as a **single contiguous
  block** at the top of its section and to leave the roadmap row alone entirely — **you** mark
  both rows done, in one commit on `main`, after both merges.
* **`docs/openapi.json`** — if a row changes a published docstring, it is **regenerated**
  (`scripts/generate_openapi_snapshot.py`), never hand-merged. Same for FreeWeight's `api.md`
  mirror: edit `WeightRoom/docs/apps/freeweight/api.md`, then `FreeWeight/scripts/sync_docs.py`,
  then `cmp`.
* **WPF10 is alone in FreeWeight** this wave. No collision; merge it whenever it is green.

## 5. The GPU protocol — you are the only holder

ADR-0119 and `MEMORY_SAFETY.md`: **one live model load at a time on this machine.** The host has
16.3 GB of VRAM and 30 GB of RAM, and has been driven into swap by exactly this mistake before.

Before any live run:

```bash
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
pgrep -x llama-server ; systemctl --user is-active ollama.service
```

`pgrep -x`, not `pgrep -f` — the one-load rule has been broken by a pattern that matched a
shell. If another session holds the card, wait; do not evict it.

Your three live windows, run **one at a time**, never overlapping:

1. **WPF10 Gate B** (the big one). Restart `freeweight.service` onto the merged fix first, then a
   run, a repeat of it, and a second run while the first server is warm. Pass is every
   `llama-server` in `ps` carrying `--ctx-size` and `--fit off`, `/props` answering the profile's
   `n_ctx`, and no served-context degradation on any of the three runs.
2. **WPF11 Gate B**. `ollama.service` is **inactive** right now — you start it, pull
   `smollm2:135m` from the console, watch the audit row go `pending` then the model appear, check
   Ollama's own log for a second pull, and stop the unit again if it was not running when you
   began. Leave the host as you found it.
3. **WPF12's live evidence, only if you choose to make one** — see §6.

After each window: confirm no `llama-server` survives, VRAM back to idle, and the unit states are
what they were before.

## 6. Corrections to the kickoffs, from this session (2026-09-12)

Give these to the agents; a kickoff that is wrong about the machine wastes a whole session.

* **WPF12's live evidence is gone.** Its kickoff says WPF7's Gate C left a retried attempt in the
  operator's IdeaPress database. Those two projects (`01M29FZG…`, `01M29HZ6…`) were **deleted on
  2026-09-12** at the operator's instruction, and `project delete` takes the rows with it. What
  survives: `WeightRoom/tests/fixtures/ideapress/unit.json` and `task-cancelled.json` carry the
  `transport_call` field, but **every attempt in them is `transport_call: 0, completed`** — there
  is no retry example in the fixtures either. So WPF12 must (a) author a fixture with a discarded
  call (`transport_call: 0, provider_error`) followed by its retry (`transport_call: 1,
  completed`), recorded from IdeaPress's own API shape, and (b) take its screenshots against that.
  A *live* retry needs a model call that returns empty — **your** GPU window if you want one, and
  it is not worth a window on its own. Say in the wave handoff which of the two the row proved.
* **FreeWeight `main` has moved** since WPF9's handoff: `ed58b44` adds the truncation warning that
  names the setting that bounded the juror (`runtime.context_size` when no `[judge]
  max_output_tokens` is set) and logs `goal.juror_truncated`. WPF10 branches from that, not from
  `c215e32`.
* **WPF11's kickoff asks whether `pull` moves onto the job queue.** WPF1 rejected the queue for
  FreeWeight's model refresh because it changed how the operator works. A multi-minute download is
  not the same case. The row decides; you review the decision before its merge, because it is the
  kind of choice a row should not make alone.
* **Unpushed work exists** on `WeightRoom` main (5 commits) and `FreeWeight` main (2). That is
  normal here. It is not yours to push and not a reason to rebase anything onto origin.

## 7. The agent brief — what you paste

One agent per row. Each brief is: *the row's kickoff file path* + *§2's may/may-never list* +
*that row's line from §3's table* + *the relevant bullets of §6* + this closing:

> Work only on your branch in your worktree. Run the full gate in your own venv and name the
> interpreter. Commit at each phase boundary with Conventional Commits, never `git add -A`, and
> leave `git status --short` clean. Write
> `WeightRoom/docs/history/handoffs/<ROW>_HANDOFF.md` — the decisions you took, the numbers you
> measured, and what the kickoff got wrong — but **do not** edit `docs/roadmap/weightroom-work.md`
> and **do not** merge. Report back: the branch head, the gate line, what is left for the GPU, and
> any decision you want reviewed before merge. If you find yourself needing the GPU, a shared
> systemd unit, or another row's files, **stop and say so** — that is the orchestrator's, not
> yours.

Dispatch all three at once; they do not depend on one another. Check in on them rather than
waiting idle — your GPU windows and their work do not overlap until their gates are green.

## 8. Merging — your job, in this order

1. **Read the diff.** A Fable session attending is the whole reason WPF10 may run at all. Review
   each row's diff against its kickoff's decisions before merging it, and reject a row that
   widened its scope.
2. **FreeWeight: merge WPF10** whenever green. Nothing else touches that repository.
3. **WeightRoomGym: merge whichever of WPF11/WPF12 is green first**, then tell the other agent
   to merge the new `main` **into its branch** (not rebase — these branches have real history and
   a rebase mid-review loses the review), resolve `CHANGELOG.md` by keeping both blocks, and
   regenerate `docs/openapi.json` if it moved. Then merge the second.
4. **Re-read the branch head immediately before writing each merge commit.** A session has
   committed underneath a merge in this repository before (W6, 2026-09-10) and the merge recorded
   the wrong parent.
5. **Restart the units the merges affect** so the operator's running applications are the merged
   code: `freeweight.service` after WPF10, `weightroom.service` after each WeightRoomGym merge.
   A fix that has not reached a running process has not reached the operator.
6. **Then run the live gates** of §5, in their windows, and record them in the rows' handoffs
   (a `## Gate B, on the reference machine` section, as WPF2 §6a and WPF9 §4 do).
7. **One roadmap commit** at the end marking WPF10, WPF11 and WPF12 done, each with its handoff
   link, its branch head, and the live figures in the status cell — the shape every other row in
   that table uses.

## 9. Working-tree integrity

`git status --short` in every repository you touch at the start and the end. `git checkout --`
anything modified that neither you nor an agent edited — **except `py/BaseAiCore`**, whose
uncommitted docstring edits are the operator's and stay. Nothing at the workspace root is
versioned: copy before overwriting. Do not hand-edit the tree while an agent is mid-run.

## 10. When to stop and ask

Stop, and put the question to the operator, if: a row's decision changes a released contract or a
frozen SetSpec payload; a live run would need more than one model resident; a merge conflict is a
logic conflict rather than textual proximity; an agent reports the host in swap or a GPU it did
not ask for; or WPF10's cause turns out to be in ModelRack rather than FreeWeight (its kickoff
says to say so before touching that package — that is a different arc's repository and WPF13 is
about to edit it).

Everything else is yours to decide, and to write down.

## Finish line

* Three green gates, each with its interpreter named; three handoffs; the live proofs recorded
  where the row can be read, not only here.
* Three rows marked done in `docs/roadmap/weightroom-work.md`, in one commit.
* `docs/history/handoffs/WAVE4_HANDOFF.md`: what each agent built, what you reviewed and changed,
  the GPU windows and what they measured, what this prompt got wrong, and what the next wave
  (WPF13, then the WP6 re-verification) inherits.
* Every worktree removed, every merged branch deleted, `git status --short` clean everywhere,
  the five units active, the GPU idle, `ollama.service` as you found it.
* **Nothing pushed. Nothing tagged. No version moved.**
