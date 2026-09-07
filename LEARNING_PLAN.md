# Local AI Suite — Learning Plan

A guided path through the four applications: **FreeWeight** (measure), **LoadCoach** (manage),
**IdeaPress** (apply) and **PromptCadence** (harness). The goal is to understand what each one
does, how it works, and how to get the most out of it — first standalone, then composed.

Each module ends with a checkpoint: something you can show, not just something you have read.
Do the modules in order; later ones assume the earlier ones are running.

Rough budget: **five half-days**, one per module, plus a half-day for the composed run.

---

## Before you start

**You need**

* Python 3.12 or 3.13 and a shell.
* [Ollama](https://ollama.com) running on `127.0.0.1:11434`. It is the default provider for every
  application. A GPU with 12–16 GB of VRAM makes the model steps pleasant; without one, use a
  small model (`llama3.2:3b`) and expect slower runs.
* About 20 GB of disk for the models the quickstarts pull.

**Set up once**

```bash
mkdir -p ~/suite-learning && cd ~/suite-learning
python -m venv .venv && source .venv/bin/activate
pip install freeweight loadcoach ideapress promptcadence
ollama pull llama3.1:8b          # FreeWeight and LoadCoach quickstarts
ollama pull qwen3.5:9b-q8_0      # IdeaPress structured work
ollama pull gemma4:12b           # IdeaPress prose
```

Each application starts with zero configuration, binds to loopback only, and owns its own port
and its own SQLite database:

| Application | Port | Answers |
|---|---:|---|
| FreeWeight | 8765 | How well does this model perform on this machine, for this capability? |
| LoadCoach | 8766 | Given this task and this machine right now, which model should run it, and how? |
| IdeaPress | 8767 | How do I turn this idea into finished content? |
| PromptCadence | 8768 | How do I let an agent loop run tools and models under a plan, a budget and a policy? |

Every application has the same three diagnostic commands. Learn them first; you will use them in
every module:

```bash
<app> doctor          # every known failure mode, ✓ / ! / ✗, with what to do about it
<app> health --json   # the same component list the API reports
<app> version
```

**Two ideas that run through everything**

1. *Nothing is fabricated.* A missing GPU, an absent provider, a sensor that cannot be read or
   stale evidence produces an explicit state — never a zero, never a crash. When you see
   "unsupported" or "degraded", that is the application being honest, not broken.
2. *Python decides, models perform.* No application lets a model choose control flow. Models do
   bounded, validated tasks; the application checks the result and decides what happens next.

**Read** (30 minutes): `docs/architecture/executive-summary.md`. Skim the dependency diagram and the
"independent deployment" table. That table is the map for this whole plan.

---

## Module 1 — FreeWeight: measure

**What it is.** A benchmark runner for local models that records enough provenance (model digest,
runtime profile, machine fingerprint, benchmark version, dataset hashes) that a result can be
reproduced, compared and invalidated. It refuses to collapse a model into one universal number.

**Read first**: `FreeWeight/docs/quickstart.md`, then `FreeWeight/docs/benchmarks.md`.

### 1.1 First run (45 min)

```bash
freeweight serve &                  # http://127.0.0.1:8765
freeweight doctor
freeweight models refresh           # discover what Ollama has
freeweight models list
freeweight benchmarks list          # the native suites
freeweight run start --model <ref> --suite native.performance
freeweight run list
freeweight run wait <run-id>
freeweight results show <run-id>
```

Open the web UI. Walk the **Dashboard → Runs → Results** pages for the run you just made. On
the result page find the *provenance* block and check each field against the list above. Note
which measurements are marked unsupported on your machine, and why.

Try the **wizard** once — it is the guided way to start a run and shows every choice
the CLI makes silently.

### 1.2 The native suites (1 h)

Run one model through `native.echo`, `native.reliability`, `native.structured_output`,
`native.tool_use` and `native.long_context`. For each, read the benchmark's entry in
`docs/benchmarks.md` and answer: *what does this suite actually measure, and how is it scored?*
Keep the run ids; you will compare them next.

Then run `native.performance` a second time on the same model:

```bash
freeweight run repeat <run-id>
```

Compare the two. This is the point of provenance — the second run should be attributable to the
same model, machine and runtime profile.

### 1.3 Comparing and exporting (30 min)

```bash
freeweight results compare <run-a> <run-b>
freeweight results export <run-id> --format json > result.json
```

Pull a second model (`ollama pull llama3.2:3b`), run it through the same suites, and use the
**Compare** page. Read the statistics section of a comparison: sample counts, confidence, and
whether a difference is called significant or not.

### 1.4 Goals and calibration — the part most people miss (1.5 h)

Native suites measure generic capabilities. **Goals** are *your* criteria for *your* task, scored
by rules and by model judges that FreeWeight first calibrates against your own grading.

```bash
freeweight goals starters           # shipped examples
freeweight goals init                # interviews you, writes a goal pack
freeweight goals validate <slug>
freeweight goals suggest <slug>      # a model proposes criteria from a sample; you keep or drop
freeweight judges list              # which models are eligible to judge, and why not
freeweight judges validate
```

Then in the UI: **Goals → Calibrate**. Grade a handful of samples yourself (the anchors), then
`freeweight goals calibrate <slug>` scores the holdout with the jury and reports the *agreement*.
A judge that disagrees with you is excluded from the panel. Run the goal as a suite and read the
result.

Read `docs/apps/freeweight/subjective-goals.md` (in `docs/`) for why calibration exists.

### 1.5 Evidence (20 min)

```bash
freeweight evidence show --model <ref>
freeweight evidence export > evidence.json
```

This bundle is what LoadCoach consumes. Open it: one `capability.evidence` record per model,
runtime profile, machine and capability, with a confidence and an expiry beside each score.

### 1.6 Adapters (optional, 30 min)

If you have LoRA adapters in a directory: `freeweight adapters list`. A run can be pinned to an
adapter, and the evidence then carries the adapter identity. Skip if you have none.

**Checkpoint.** Two models measured across five native suites and one goal you authored and
calibrated; a comparison you can explain; an exported evidence bundle on disk.

**Making the most of it**

* Measure on the machine you will run on. Evidence is keyed by machine fingerprint for a reason.
* Re-run `native.performance` after changing a runtime setting (context length, quantisation).
  That is what the runtime profile in the provenance is for.
* Write goals with checkable criteria. "Sounds professional" cannot be calibrated;
  "never uses the first person" can.
* `freeweight db backup` before an upgrade. `docs/backup-restore.md`.

---

## Module 2 — LoadCoach: manage

**What it is.** A router, queue and executor. Given a task profile, it scores the installed models
on evidence (FreeWeight's or declared), adjusts for live hardware and production reliability,
picks one, runs it with validation and retries, and keeps a full explanation of the decision.

**Read first**: `LoadCoach/docs/quickstart.md`, then `LoadCoach/docs/routing.md` (all of it; it
is the heart of the application).

### 2.1 First request (30 min)

```bash
loadcoach serve &                   # http://127.0.0.1:8766
loadcoach doctor
loadcoach tasks list                # the twenty shipped task profiles
loadcoach tasks show general.chat
loadcoach route explain --task general.chat     # decide, but do not run
loadcoach generate --task general.chat --prompt 'hello'
```

Read the explanation `route explain` prints before you run anything else. It names the winner,
the margin over the runner-up, what carried the score, and why every other candidate was set
aside. With no evidence imported yet, every score comes from declared capabilities and priors, and
the explanation says so.

### 2.2 Jobs and the queue (45 min)

```bash
loadcoach job submit --task general.chat --prompt 'hello'
loadcoach job wait <job-id>
loadcoach job show <job-id>
loadcoach job submit --task content.article_draft --prompt-file brief.txt --class background
loadcoach queue status
loadcoach queue pause; loadcoach queue resume
```

Open **Jobs** in the UI, then **Queue** (it is a live SSE view). Submit several jobs at different
priority classes and watch the ordering. Cancel one mid-flight. Read `docs/operations.md`
"queue controls" while you do this.

Kill the server while a job is running, restart it, and check the job. Nothing is lost or
duplicated — that is the lease-based recovery.

### 2.3 Evidence in, routing changes (45 min)

With FreeWeight still running from Module 1:

```bash
loadcoach evidence import --url http://127.0.0.1:8765
loadcoach evidence sources
loadcoach evidence show --model <ref>
loadcoach route explain --task code.review
```

Compare this explanation with the one from 2.1. Scores now carry a *source* and an *age*. Find
the freshness and confidence weighting in `docs/routing.md` "the four factors" and locate each
factor's inputs in the explanation.

Open **Routing** in the UI and use the "what if" form to change the task and see the decision move.

### 2.4 Production feedback and reliability (30 min)

```bash
loadcoach job feedback <job-id> --accepted --quality 0.8
loadcoach reliability show
```

Give bad feedback to several jobs on one model and watch its reliability factor fall in the next
explanation. Read about the circuit breaker in `docs/routing.md` and `docs/operations.md`; the
**Reliability** page shows the breaker state and the re-probe.

### 2.5 Residency and adapters (30 min)

```bash
loadcoach models residency          # what is loaded, and VRAM-aware admission
loadcoach adapters scan; loadcoach adapters list
```

LoadCoach manages which model is resident and refuses to admit a job that would not fit. If you
have adapters, pin a task profile to one and route again.

### 2.6 Exposing it on a LAN (30 min, optional)

Read `docs/security.md` end to end first. Then:

```bash
loadcoach token create --scope write --expires-days 30
loadcoach token list
```

Bind to a LAN address in config, and use the token from another machine. Watch `doctor` tell you
what is missing (Host allow-list, rate limits) before it lets you.

**Checkpoint.** Two routing explanations for the same task — one on priors, one on evidence — and
you can point to the line that changed the winner. A queue you have paused, drained and recovered.

**Making the most of it**

* Write your own task profile (`loadcoach tasks validate`). Routing quality is bounded by how
  well the profile names the capabilities the task needs.
* Import evidence on a schedule and set `evidence.max_age` deliberately. Stale evidence is
  discounted, not ignored; decide how fast you want that discount to bite.
* Always give feedback from callers. Reliability without feedback only sees failures, not
  disappointments.
* Use `route explain` as the first debugging step whenever a model choice surprises you.

---

## Module 3 — IdeaPress: apply

**What it is.** Turns a brief into finished content through a fixed workflow of sixteen stages,
where Python owns the control flow and models do bounded jobs (compile requirements, draft a unit,
audit it, critique it, revise it). Every unit is validated before it is committed, and every
committed unit carries provenance back to the brief.

**Read first**: `IdeaPress/docs/quickstart.md`, then `IdeaPress/docs/workflows.md`.

### 3.1 A brief that can be checked (20 min)

The quickstart is emphatic about this and it is right: the quality of everything downstream is
decided by whether your brief compiles into *checkable* requirements. Write a brief for a short
article about something you know, with three or four sentences of the form "it must state X" and
"it must not do Y".

### 3.2 Plan (30 min)

```bash
ideapress serve &                    # http://127.0.0.1:8767
ideapress doctor
ideapress backend list; ideapress backend test
ideapress project create "My article" --brief-file brief.md
ideapress plan build <project-id>
ideapress plan show <project-id>
```

Open the **Plan** page. Every requirement sits beside the span of your brief it came from. Find one
that the brief does not really support and fix the brief, then rebuild. Try the plan editor.

### 3.3 Draft, review, commit (1 h)

```bash
ideapress stage run <project-id> draft
ideapress stage status <project-id>
ideapress unit list <project-id>
ideapress unit show <unit-id>
ideapress unit history <unit-id>
```

Watch the **Workspace** page while the stage runs. For one unit, read the whole history: draft,
validator results, audit, critique, revision, commit. Read `docs/workflows.md` "the bounded loops"
and match each loop iteration to what you see.

If a unit pauses, read its page. The reason and the fix are there. The common one — a reasoning
model spending its output budget on thinking — is fixed by raising
`[workflow] structured_output_tokens` and running with `--resume`.

### 3.4 Requirements, validators and content types (45 min)

```bash
ideapress workflow list; ideapress workflow show article
ideapress unit revise <unit-id> --instructions "..."
```

Read `docs/content-types.md`. Note which validators are structural (Python checks: length,
formatting, references) and which are judged (a model audits against a requirement). Change a
requirement to one that the structural validators can enforce and watch the difference on revision.

### 3.5 Export (15 min)

```bash
ideapress export formats
ideapress export run <project-id> --format markdown
ideapress project export <project-id>      # the archive, with provenance
```

### 3.6 Switch the backend to LoadCoach (30 min)

With LoadCoach running:

```bash
ideapress backend switch loadcoach
ideapress backend test
ideapress stage run <project-id> draft
```

Now open LoadCoach's **Jobs** page. Each IdeaPress stage became a LoadCoach job with a task
profile and an explanation. No workflow code changed — that is the composition promise from the
executive summary, and this is the moment you see it.

**Checkpoint.** One committed, exported article whose every unit you can trace to a requirement
and to the sentence in your brief that produced it; the same project drafted once through Ollama
directly and once through LoadCoach.

**Making the most of it**

* Spend your time on the brief and the plan, not on the draft. Fixing structure before drafting
  is cheap; fixing it after is a revision loop.
* Use two models (structured vs prose) as the defaults do. They reward different things.
* Read `docs/backends.md` before switching to a remote OpenAI-compatible endpoint; the UI marks
  that as egress for a reason.

---

## Module 4 — PromptCadence: harness

**What it is.** An agent loop with governance. A request becomes a *trajectory*: a model proposes a
plan of steps, the plan is approved (by policy, by budget, and where required by a person), and
each step then runs on a *tier* (a LoadCoach task profile with a price and a classification), with
sandboxed tools, a budget ledger with three ceilings, and an egress decision for every turn. The
whole trajectory is reconstructable afterwards.

**Read first**: `PromptCadence/docs/quickstart.md`, `PromptCadence/docs/tiers.md`, then
`docs/apps/promptcadence/lifecycle.md` (the state machine — keep it open in Module 4).

PromptCadence reaches models **only** through LoadCoach. Keep LoadCoach running.

### 4.1 Start and check the plumbing (20 min)

```bash
promptcadence serve &                # http://127.0.0.1:8768
promptcadence doctor                 # database, loadcoach, tiers, tools
promptcadence tiers list
promptcadence tiers check            # every tier's task profile exists in LoadCoach
promptcadence tools list             # the registry, and the isolation rung run_command has
```

Read what `tools list` says about isolation. ToolYard has a ladder with three rungs: container
(podman or docker), bubblewrap, and *unavailable*, which refuses rather than running unsandboxed.
`doctor` tells you which rung your machine reached and what would raise it.

### 4.2 First trajectory (45 min)

```bash
mkdir notes && echo "some text" > notes/a.md
promptcadence run "summarize the files in ./notes" --follow
promptcadence trajectory show <id>
promptcadence trajectory explain <id>
```

`explain` is the composed record: every model, tier, tool call, debit and egress verdict. Read it
once end to end. Then open the **Console** and the trajectory page in the UI and find the same
things.

Run the same request with `--bypass-planning --follow` and diff the two explanations. Read the
approval-mode section of the spec to understand when bypass is allowed at all.

### 4.3 Approvals (30 min)

Configure a policy that requires approval for `run_command` (see `docs/configuration.md`), then:

```bash
promptcadence run "list the files in ./notes with ls" --follow
promptcadence approvals list
promptcadence approve <id>           # or: promptcadence deny <id> --reason "..."
```

Watch the trajectory move through the awaiting-approval state in `lifecycle.md`. Try the same
from the **Approvals** page.

### 4.4 Budget (30 min)

```bash
promptcadence ledger show --scope day
```

Set a small per-trajectory ceiling in config and run something that needs several steps. Watch it
stop at the ceiling, read the deviation category it lands in (lifecycle.md), and see the reserved
versus debited figures in the ledger. Cost is re-derived from token usage and a pricing file, never
stored as money — `docs/tiers.md` explains where prices come from.

### 4.5 Egress (30 min)

```bash
promptcadence egress list
promptcadence egress list --denied-only
```

Tiers carry a classification; data classified above a tier's clearance is refused before the turn
runs. Configure a remote tier without a LoadCoach registration that declares `remote = true` and
watch it refuse honestly rather than silently route local.

### 4.6 Compaction and retention (20 min)

Run a long trajectory (many tool calls) and read the compaction section of its explanation. The
context the model saw is a *view* over the full record; the full record is kept. Read
`docs/operations.md` "retention" to see what the sweep removes and when.

**Checkpoint.** Three explained trajectories: one planned, one bypassed, one that stopped at a
budget ceiling; an approval you granted; an egress denial you can explain.

**Making the most of it**

* Design tiers before running anything. A tier is where cost, capability and classification meet;
  most surprises trace back to a tier that was priced or classified carelessly.
* Keep approval on for anything that writes or executes until you have read a dozen plans.
* Read the denied egress list weekly. It is the log of what the harness stopped.
* Use `trajectory explain` as your audit trail; it is designed to be handed to someone else.

---

## Module 5 — The composed suite (half day)

Run all four together and complete one end-to-end loop:

1. **Measure**: FreeWeight benchmarks two models on your machine and exports evidence.
2. **Manage**: LoadCoach imports that evidence; `route explain` now favours the measured winner
   for each task profile.
3. **Apply**: IdeaPress drafts an article through LoadCoach. Open each stage's LoadCoach job and
   read its explanation.
4. **Harness**: PromptCadence runs a trajectory whose steps land on tiers that map to LoadCoach
   task profiles; the explanation names the model LoadCoach chose for each step.
5. **Feed back**: give LoadCoach feedback on the IdeaPress jobs; check reliability; re-route.

Then break it on purpose. Stop FreeWeight — LoadCoach keeps routing on the evidence it has.
Stop LoadCoach — IdeaPress on the Ollama backend keeps working; PromptCadence reports `loadcoach`
degraded and refuses to execute, but stays up. Stop Ollama — every `doctor` names it.

**Final checkpoint.** You can draw the diagram from the executive summary from memory, say what
crosses each dotted line (a SetSpec payload over HTTP, never a database), and show one artefact
from each application that proves the composition: an evidence bundle, an explanation, an
exported article, a trajectory explanation.

---

## Where to go next

* `docs/architecture/master-architecture.md` — the design behind all of it.
* `docs/adr/` — one hundred decisions; read 0016 (unsupported is not zero), 0030 (cost is
  re-derived), 0045 (PromptCadence reaches models only through LoadCoach) first.
* The **Code Review Plan** beside this file, if you want to read the source.
