# W6 Handoff — WeightRoomGym Phase 6: chat

**Row:** W6 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Opus 5 · high;
attended). **Date:** 2026-09-10. **Kickoff:**
[`w6-weightroom-p6-chat.prompt.md`](../prompts/w6-weightroom-p6-chat.prompt.md) (the path
after the merge; on the branch it is still `docs/history/`).
**Ships:** `wr-gym 0.6.0`, **prepared, not tagged, not pushed, not published**. Built on branch
`row/w6-chat` in the worktree `~/ai/worktrees/weightroom-w6`, because another session held
`WeightRoom`'s working tree. **Not merged.** While this row ran, `main` moved every handoff under
`docs/history/handoffs/`, so this file is written there. The roadmap row edit sits on the line
next to `main`'s own W4/W5 row edits, so the merge may need that one table row resolved by hand.

## 1. What was built, by commit

| Repository | Commit | Gate | What |
|---|---|---|---|
| WeightRoom | `401b52d` | A | `domain/chat.py` (backends, event kinds, `Chunk`, `ThinkingState` and `advance`/`fold`, `cost_cell`, `sanitise_filename`); migration `0004` (`conversations`, `messages`, `message_events`, `attachments`); unit tests of the state machine |
| WeightRoom | `37148cb` | — | ADR-0132 and the amendment to `apps/loadcoach/api.md` §4/§5 |
| LoadCoach | `40d8845` | — | `feat(stream)`: each `ThinkingDelta` is forwarded live as an enveloped `thinking` frame, with its own index, from both stream routes |
| LoadCoach | `6f5d3db` | — | `chore(release)`: `loadcoach 1.5.0`, prepared, untagged |
| LoadCoach | `29a12a2` | — | api.md mirror of ADR-0132 (the first commit's heredoc had dropped it) |
| MirrorWall | `4aedf6f` | — | `fix(csrf)`: read the token from a `multipart/form-data` body. Under `[Unreleased]` |
| WeightRoom | `cedcafc` | B | `services/chat_loadcoach.py`, `services/chat.py` (conversations, attachments, the runner, the recorder, completion, recovery, SSE), `web/routes/chat.py`, three templates, the audit actions, recorded 1.3.1 and 1.5.0 streams |
| WeightRoom | `13b29bb` | C | `services/chat_promptcadence.py` (trajectory submit, event cards, answer, egress, approvals under the `approve` token); the injection-corpus and network-isolation tests; `0.6.0`, CHANGELOG |
| WeightRoom | `00aa5d6` | — | README status line (`13b29bb` replaced a version string that was not there) |
| WeightRoom | `f051652` | demo | The three defects the live demonstration found, and a test that reached the real host (§4.1) |

Full local gate after `f051652`, run from the worktree with `PYTHONPATH=$PWD/src` and
`WeightRoom/.venv` (Python 3.14.4): `ruff format --check .` (144 files), `ruff check .` clean,
`mypy src tests` clean (138 files, strict), `lint-imports` 5 contracts kept,
`pytest -m "not live and not performance"` **945 passed, 1 skipped** (the PostgreSQL migration
test; no server here), coverage **90.28 %** (floor 85 %; W5 closed at 90.12 %).

## 2. What this row was asked to decide: how LoadCoach's stream marks thinking

**Before this row, LoadCoach's stream did not mark thinking at all.** A capture of
`POST /generate/stream` on `general.chat` (routed to `ollama/gpt-oss:20b`) carried 1 `routing`,
60 `token` and 1 `result` frames. Every `token` was answer text, and the reasoning arrived only as
`result.reasoning.summary`, after the answer. ModelRack's Ollama and llama.cpp providers do yield a
`ThinkingDelta` per piece. LoadCoach's executor received them and forwarded only `token` chunks.

Decided with the operator (option "Add a `thinking` frame to LoadCoach") and recorded as
**ADR-0132**:

| Provider kind (reference machine) | What LoadCoach 1.5.0 sends | What the chat shows |
|---|---|---|
| `ollama` (gpt-oss:20b and other thinking models) | `event: thinking` per delta, enveloped, own index from 0; then `token` frames | Block opens on the first thinking delta, streams, collapses on the first non-whitespace text delta |
| `llamacpp` (`reasoning_content`) | Same as Ollama | Same |
| `openai_compatible` | No thinking frames, never an empty one (ADR-0016) | No block, unless `result.reasoning.summary` is present, which fills a collapsed block at the end |
| Any provider through LoadCoach ≤ 1.4 | Thinking only in `result.reasoning` | Collapsed block filled from `result` at `done` |

Also, for a model that emits no thinking: `advance` never opens a block, and `done`/`halt` closes
the phase with nothing to show. The collapse never reopens. Thinking frames are live-only, like
`token`. A reply's deltas are dropped when it completes and the text is kept on `messages.thinking`,
so a reload shows the collapsed block from the database.

## 3. Other decisions taken in this row

1. **The tool allowlist is always sent to PromptCadence.** An omitted `tools` field means *every
   configured tool* to PromptCadence, so a blank field in the form is sent as `[]`.
2. **One trajectory per message.** Each follow-up is a new trajectory, with the conversation so far
   as context in the task. PromptCadence has no conversation object to continue.
3. **Attachments are fenced context.** Text and markdown only, capped, stored `0600` under a
   generated name. Each is wrapped in a tilde fence longer than any tilde run inside it, so a file
   cannot close its own fence. The blocks are prepended to the first user message of every request.
4. **A reply interrupted by a console restart** is closed at startup as a named `halt`, never left
   `in_progress`.
5. **Model text reaches the page two ways only.** Live deltas go in as `textContent`. The finished
   answer is re-fetched as server-rendered HTML from an escape-on mistune renderer: http(s) links
   only, images reduced to alt text so nothing a model wrote is fetched. It reaches Jinja through
   `SafeReplyHtml.__html__`, and no chat template uses `| safe`.
6. **Approvals never show a button that would fail.** The console reads its own PromptCadence
   token's scopes (cached 60 s). Without `approve`, the card says *No approve scope* and gives the
   CLI command. Each tap writes a `chat.approve`/`chat.deny` audit row with `security=True`.
7. **Egress cards come from PromptCadence's recorded decisions**, fetched when the trajectory ends,
   because the stream never carries them (§4.4).

## 4. What the kickoff got wrong, or did not know

### 4.1 Found by the live demonstration, fixed in `f051652`

Every test replayed a *finished* stream, so these three were invisible until a real browser
watched a real reply:

1. **The console buffered LoadCoach's whole reply.** `iter_frames` began with
   `for line in [*lines, ""]`, which drains the iterator first. Direct measurement: LoadCoach
   delivered its first thinking frame at 0.48 s and its result at 12.6 s, while `stream_reply`
   yielded everything at 22.5 s. Fixed with `itertools.chain`. A test raises on the input after
   the first frame.
2. **`done` was invisible to an open page.** `message_events.id` had no `AUTOINCREMENT`. When
   `_complete` deleted the delta rows, SQLite gave `done` the highest *remaining* rowid plus one:
   in the first run, `thinking_done` 174 and `done` 175, below text-delta ids the page had already
   received. The SSE loop reads `id > last`, so the page stayed "streaming" until reloaded. Fixed
   with `sqlite_autoincrement` on the model and in migration `0004`, which is unreleased and was
   edited in place. The downgrade test now ignores `sqlite_sequence`. PostgreSQL sequences never
   reuse ids, so only SQLite was affected.
3. **Every role line was sticky.** The shell styles `header { position: sticky; top: 0 }`, and
   each message's "You"/"Reply" label was a `<header>`. On a phone, the labels pinned over the top
   bar as the thread scrolled. The label is now a `div`. The same trap waits for any later
   template that uses `<header>`.
4. **A W3 test reached the real host.**
   `test_resident_reports_a_source_and_an_error_for_each_unreachable_side` used the default
   Ollama and LoadCoach URLs. It passed only while Ollama had no model loaded, and failed the gate
   after the demonstration loaded one. Both sides now point at a refused port.

### 4.2 Found while building, fixed where they live

* **LoadCoach dropped thinking deltas**: §2, ADR-0132, LoadCoach 1.5.0.
* **MirrorWall's CSRF middleware refused every multipart form** (`CSRF_FAILED` on any upload)
  because it looked for the token only in urlencoded bodies. Fixed in MirrorWall `4aedf6f`,
  **unreleased**. `wr-gym 0.6.0`'s attachment upload needs that MirrorWall release before
  publishing.
* **The security checklist's Phase 1 test** (`test_no_route_accepts_a_body_file`) is now an
  explicit `UPLOAD_ROUTES` allowlist.

### 4.3 Host: PromptCadence had never reached LoadCoach

Every trajectory on the reference machine failed with
`LoadCoach refused /api/v1/generate with UNAUTHORIZED (LOADCOACH_ERROR)`, and had since W1:
PromptCadence had no LoadCoach token. Fixed on the host, with the operator's choice ("Mint a
token, configure PromptCadence"): a LoadCoach token named `promptcadence` (write), stored at
`~/.config/promptcadence/secrets/loadcoach.token`; `~/.config/promptcadence/config.toml` created
with `[loadcoach] api_key_file`; `promptcadence.service` restarted. That failure is recorded as a
fixture (`promptcadence-1.3.3-failed-unauthorized.sse`). **The doctor has no rule for it**; see §7.

### 4.4 PromptCadence facts the plan assumed otherwise

1. **`egress.evaluated` is never emitted** on PromptCadence's event stream, although its API lists
   it. The console maps the event if it ever arrives, and meanwhile reads the recorded decisions
   at the end (§3.7).
2. **`[approval] mode = "hybrid"` never gates on this machine.** Hybrid pauses for egress at or
   above `gate_egress_at` or a step above `gate_step_cost`. Every tier here is local, so the policy
   approves every step with `target_not_remote`. A hybrid run (`01M2564V6DNCRBZ1FRAX9C5J03`) went
   plan → approved → tool → answer with no request. The demonstration used `manual`, which holds
   the plan on one request. Plan criterion 2 names hybrid, which is only reachable with a remote
   tier.
3. **`promptcadence trajectory show` does not name the approver**, in text or `--json`. The
   approver is in the explanation (`GET /api/v1/trajectories/{id}/explanation`) as the token *id*:
   `intents[0].minted_by = "approver:<token id>"`, and `approvals[0].approver_token_id`. So the
   plan's `approver:weightroom` should read `approver:<id of the token named weightroom>`.

### 4.5 "From a phone"

The demonstration ran in headless Google Chrome with mobile emulation (390 × 844 CSS px, device
scale 3, an Android user agent) on the reference machine, driven over the DevTools protocol. It
was **not a physical phone**. The phone trust step is still the operator's (W1).

## 5. Demonstration (Phase 6 acceptance criteria)

Run on the reference machine: LoadCoach 1.5.0 and PromptCadence 1.3.3 under their
`systemd --user` units, Ollama serving `gpt-oss:20b`. The W6 console ran from the worktree on a
scratch HTTPS port (8779), with a scratch config and database (W4's demo database, migrated
0002 → 0004), using the `~/.config/wr-gym/secrets` application tokens.
Screenshots are kept **outside git**, at `/home/jpk/ai/evidence/W6/` on the reference machine
(operator, 2026-09-10); the file names below are theirs.

**Criterion 1: LoadCoach on `general.chat`, thinking streams then collapses.** Conversation
`01M25600G9E1XQE07GSYKR0C5E` asked a two-step arithmetic question. The page's own event log
recorded:

```text
delta.thinking: 128 frames, 0 ms to 1350 ms
thinking_done:    1 frame,  1453 ms
delta.text:      63 frames, 1453 ms to 2076 ms
done:             1 frame,  2128 ms   → finished message re-fetched, 200
thinking 411 chars · answer "… 9 + 18 = 27 sheep in total."
decision: ollama/gpt-oss:20b@sha256:17052f91a42e · 1 candidates · 15 rejected · in 105 · out 201
          · cache read 0 · cache write 0 · thinking — · — · local
```

`1-thinking-streaming-expanded.png` shows the block open mid-thought. `1-thinking-collapsed.png`
and `1-thinking-expanded.png` show the finished message collapsed, then opened by a tap. The
`thinking —` is correct: Ollama does not report reasoning tokens, which is unavailable, not zero.

**Criterion 2: PromptCadence with `read_file`, an approval the tap grants.** Temporarily, with the
operator's choice ("Set for the demo, restore after"), PromptCadence ran with
`[approval] mode = "manual"` and `[tools] read_roots = ["/home/jpk/ai/suite/WeightRoom/docs"]`.
Conversation `01M2565ZS5MX0H2ERMSTB39QS0` asked for ADR-0128's decision, which became trajectory
**`01M256601QYN4AVJCB8ZZSSQ7G`**:

```text
cards: Plan · plan.drafted | Approval pending · approval.requested · requested   ← Approve tapped
     | Approval pending · approval.granted · granted | Step · step.started · s1 | Step · turn.completed
     | Tool call · tool.call.started · read_file | Tool call · tool.call.completed · read_file · ok
     | Step · turn.completed | Step · step.completed · s1 | Egress decision | Egress decision
answer: MirrorWall 0.3 will vendor and serve a pinned htmx library and its SSE extension …
decision: ollama/gpt-oss:20b@sha256:17052f91a42e · tier local_fast · 1 candidates · 15 rejected
          · in 2,553 · out 205 · …
```

`promptcadence trajectory show 01M256601QYN4AVJCB8ZZSSQ7G` (with `PROMPTCADENCE_API_TOKEN` from
the console's token file):

```text
trajectory   01M256601QYN4AVJCB8ZZSSQ7G
state        completed
class        confidential
bypass       False
cause        the provider declared finish_reason=stop
```

It names no approver (§4.4.3). The explanation for the same trajectory does:

```text
approvals[0].approver_token_id  "01M24Y8TKHE7DK5346QV3MMBB4"
intents[0].minted_by            "approver:01M24Y8TKHE7DK5346QV3MMBB4"
intents[0].approved_tools       ["read_file"]
```

and `promptcadence token list --json` shows `01M24Y8TKHE7DK5346QV3MMBB4` is the active token named
**`weightroom`**, scopes `admin` and `approve`. Evidence: `2-approval-pending.png` (before the tap)
and `2-approval-granted-tool-ok.png`. The pending shot was taken before `f051652`, so its role
labels still overlap the top bar. An earlier manual run (`01M2561BSKNATQ3T4TP2EV1QCB`) also granted
by tap, but its `read_file` correctly returned `file_not_found`: it asked for ADR-0132, which
exists only on this branch. The PromptCadence config was then restored byte-identical (`auto`,
`[]`) and the service restarted.

**Criterion 3: both applications stopped.** With `loadcoach.service` and
`promptcadence.service` stopped, both old threads still rendered every message: one answer and a
thinking block in the LoadCoach thread, one answer and 11 cards in the PromptCadence thread. In
both, the textarea and Send were disabled and titled with the reason:

```text
loadcoach      "Sending is off. LoadCoach is stopped. Start it on its Overview page; this conversation still reads."
promptcadence  "Sending is off. PromptCadence is stopped. Start it on its Overview page; this conversation still reads."
POST /api/v1/chat/conversations/{id}/messages → {"error":{"code":"CHAT_BACKEND_UNAVAILABLE", …}} (both)
```

Evidence: `3-loadcoach-stopped-send-off.png`. Both units were started again and report `active`.

## 6. Verification a reviewer can repeat

```bash
cd ~/ai/worktrees/weightroom-w6        # or WeightRoom after the merge, with its venv active
export PYTHONPATH=$PWD/src; PY=~/ai/suite/WeightRoom/.venv/bin
$PY/ruff format --check . && $PY/ruff check . && $PY/mypy src tests && $PY/lint-imports
$PY/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing
# 945 passed, 1 skipped, coverage 90.28%
$PY/python -m pytest tests/integration/test_chat_loadcoach.py -k "as_they_arrive or live_reader"
cd ~/ai/suite/LoadCoach && .venv/bin/pytest tests/integration/test_streaming.py
```

The live half: start the console, open a LoadCoach conversation on a thinking model, and watch
the block open, stream and fold. The page must finish without a reload.

## 7. What is deferred

* **Merging** `row/w6-chat` into `main`: the operator merges it (§8), resolving the one roadmap
  row that conflicts.
* **Releases**, held until the W arc ends (operator, 2026-09-09): `wr-gym 0.6.0`,
  `loadcoach 1.5.0`, and a MirrorWall release carrying `4aedf6f`, which 0.6.0's uploads need.
* **A doctor rule** for "PromptCadence has no LoadCoach token" (§4.3), the PromptCadence gaps of
  §4.4 and the approver in `trajectory show`: all moved to row W10 (§8).
* Unchanged from the kickoff: the database viewer (W7), catalog and costs (W8), jobs (W9).

## 8. Decisions taken after the row (operator interview, 2026-09-10)

1. **The operator merges `row/w6-chat`.** No session merges it.
2. **Plan Phase 6 criterion 2 keeps its wording; PromptCadence changes instead.**
   `promptcadence trajectory show` is to name the approver by its token's name, in text and
   `--json`, so `approver:weightroom` appears as the plan says. Hybrid approval still only gates
   egress to a remote tier, so demonstrating the criterion as written needs one configured.
3. **The PromptCadence gaps fold into W10**: the approver in `trajectory show`, and
   `egress.evaluated` emitted on the stream when a decision is recorded (it is in
   `domain/events.py` and the API document but never sent).
4. **The token check lives in both doctors**, also in W10: `promptcadence doctor` checks that
   LoadCoach answers and accepts the configured token; WeightRoomGym's doctor shows that result on
   PromptCadence's card.
5. **The shell's sticky rule is scoped** to MirrorWall's page header (`body > header`), so a
   `<header>` inside page content is no longer sticky. Done on this branch; the chat role line
   stays a `div`.
6. **Screenshots stay out of git.** They were removed from the handoff commit and kept at
   `/home/jpk/ai/evidence/W6/`.
