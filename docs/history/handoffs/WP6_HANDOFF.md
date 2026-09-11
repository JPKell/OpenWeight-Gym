# WP6 Handoff — verification: every application tab, fully operating

**Row:** WP6 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended, one sitting ·
**Model:** Claude Opus 5 · **Kickoff:** `history/prompts/wp6-weightroom-app-pages-verification.prompt.md`
(arc index `history/prompts/wp-app-pages-arc.prompt.md`) · **Ships:** no code

## Verdict

**not ready**

Most of what WP1–WP5 built works, and works live:
* every application's menu is complete;
* every page of every tab renders from the database, with a working *Start*, while its application
  is stopped;
* an unknown schema or an out-of-range version degrades only that application's pages, and names
  the cause;
* the injection corpus renders inert wherever it was put, and no page shows a secret;
* every action PromptCadence's, LoadCoach's and IdeaPress's own interfaces offer was done from the
  console.

It is **not ready**, because an operator who has only the console still meets things that do not
work:
* FreeWeight's Settings form cannot save a file key on FreeWeight's default provider, and a refused
  write leaves no audit row (findings 1 and 2);
* nothing in the console can start an adapter run. FreeWeight's own provider switch writes its file
  before refusing, then leaves its scheduler broken until a restart (findings 4 and 9);
* a cancelled PromptCadence trajectory leaves an approval nobody can decide (finding 5);
* restarting LoadCoach while the console's streams are open ends in a SIGKILL, which the console
  audits as a failure (finding 6);
* all four Overviews miss spec §15's budget by about half a second (finding 7);
* IdeaPress ignores a cancel across its retry, and its configured model cannot finish a project
  without a per-run override (finding 8).

Two smaller findings in FreeWeight's calibration report (10 and 11) go with them. The phone criterion
was met only on an emulated device, at the operator's choice. Rows **WPF1–WPF8** carry the fixes;
WPF5 adds the pages the operator asked this row to judge.

## 1. How the run was done

* **The console under test was the operator's own**: `weightroom.service` serving WeightRoom `main`
  at `9c6ace1` (`wr-gym 1.0.0`) on `https://10.77.10.84:8769`, the LAN address, not loopback. The host
  had rebooted at 10:20 PDT. At 12:01 only `freeweight.service` was running (FreeWeight 1.2.1).
  This session started `loadcoach.service` (1.5.0), `ideapress.service` (1.5.0) and
  `promptcadence.service` (1.3.3), then `weightroom.service`. The certificate verifies with the
  console's CA (`curl --cacert ~/.config/wr-gym/tls/ca.crt …/api/v1/version` → `1.0.0`).
* **Login.** At the operator's choice, the operator password of `jpk` was reset to a value kept in
  the session scratchpad (`wr-gym operator password jpk --password-stdin`; audit
  `01M28XXMV27TB2362NKGF9Y5M5`, one session revoked). The login is `01M28Y3Q3BRYM5GD9DJXSY6VYC`,
  from `10.77.10.84`. **Set your own password again** (§7).
* **Devices.** Playwright 1.62.0 drove the system Google Chrome, headless: a desktop at 1440 × 900
  and an **emulated** Pixel 7 profile (viewport, touch, user agent), both against the LAN address. The
  themes were set through the console's own theme key (`weightroom-theme`). **No physical phone was
  used.** The operator chose emulation (2026-09-11). The kickoff's "from a phone on the LAN" is
  therefore demonstrated only as an emulation.
* **The applications' own interfaces** were opened over loopback beside the console: FreeWeight
  (`:8765`) and IdeaPress (`:8767`) as they serve, and LoadCoach (`:8766`) and PromptCadence (`:8768`)
  with the console's own bearer tokens. Each was crawled for every form and button it offers:
  FreeWeight 31 pages, LoadCoach 18, PromptCadence 12, and IdeaPress 5, plus 10 opened by URL
  because its project page links nothing. The console's four tabs were crawled the same way:
  FreeWeight 93 pages, LoadCoach 68, IdeaPress 53 and PromptCadence 40.
* **One live model load at a time** throughout: PromptCadence and LoadCoach first, then IdeaPress on
  `qwen3.5:9b-q8_0`, then FreeWeight's llamacpp measurement, then the goal's jury. Before each load,
  Ollama's `/api/ps` was empty and no `llama-server` was running.
* **A throwaway console** (`127.0.0.1:8781`, its own XDG tree, open loopback) was used for check 4
  only, and was stopped afterwards. The operator's console configuration was not changed.
* **The console's audit-route test** ran first: `.venv/bin/pytest tests/security/test_audit_routes.py`,
  Python 3.14.4 → **111 passed**.
* The scripts, their JSON logs and **621 screenshots** (261 MB, every page in both themes at desktop
  and phone width, and every action step) are in the session scratchpad (`wp6/`); they go with the
  session.

## 2. The checks

### Check 1 — Menu

**Passed.** Every application's left menu was read in all four combinations of desktop or phone
and dark or light, and every entry was followed on the desktop and on the phone.

| Application | Entries | Inert entries | Every linked page |
|---|---|---|---|
| FreeWeight | 13: Overview, Models, Runs, Results, Evidence, Goals, Adapters · Prompts, Settings, Provider, Tokens, Logs, Database | none | `200`, no refusal |
| LoadCoach | 12: Overview, Models, Routing, Queue, Evidence, Adapters, Reliability · Settings, Providers, Tokens, Logs, Database | none | `200`, no refusal |
| IdeaPress | 9: Overview, Projects, Units, Workflows, Backends · Prompts, Settings, Logs, Database | none | `200`, no refusal |
| PromptCadence | 12: Overview, Trajectories, Approvals, Tiers, Tools, Ledger, Egress · System, Settings, Tokens, Logs, Database | none | `200`, no refusal |

IdeaPress has no *Tokens* entry at all, so the kickoff's one allowed exception does not arise (WP5
§6 said so). At phone width, one page scrolls sideways: LoadCoach's **Database** page, by 19 px in
both themes (a W7 page, not a WP page). It goes into WPF1's polish.

### Check 2 — Parity

For each application, the table lists what its own interface offers, where the console offers the
same, and what was done live from the console with its audit row. Rows marked *console only* are
actions the application's own interface has no form for. The console's audit ids are in the
`audit_log` of `weightroom.service`, and each application's own trail is named beside them.

#### PromptCadence

| PromptCadence's own UI | Console | Done live from the console |
|---|---|---|
| Trajectories: list, filter by state | Trajectories: list, filter | listed |
| — (API only) submit | the New-trajectory form | T1 `01M28YRAS1Y1K89NCTC6J5HR9R` "State in one sentence what 9 + 4 is.", `internal`, bypass planning, token budget 1 (audit `01M28YRASB67ZSAGHCFN3BFP28`); T2 `01M28YRRF5BBKP5PNMS49FRCY8` the same shape (`01M28YRRF92RP2S3CEQC2KM0DK`); T3 `01M28YRSS9C6KZQDP6MA9WETWR`, the injection corpus (`01M28YRSSD6MGFYJ2ARDK3HS2D`) |
| Approvals: **Grant**, **Deny** with a reason | Approvals: Grant with new ceilings, Deny with a reason | T1's `ceiling_raise` `01M28YRAT8966CCXY4F0X34GKZ` granted with a token ceiling of 50 000 (audit `01M28YRBZNZZWSKJ6N3GHHXK6N`, `security: true`, `raised: true`) → T1 **completed**. PromptCadence's events: `approval.requested`, `approval.granted`, `turn.started`, `budget.debited`, `trajectory.completed`; approver `approver:weightroom` |
| — (API only) cancel | Cancel on the record | T2 cancelled while awaiting its approval (audit `01M28YRRZB79RQCN8Z3W6SC8DP`) → **cancelled**; events end `approval.requested`, `trajectory.cancelled`. **Its request stayed `pending`** (finding 5) |
| Trajectory record | the record, the whole explanation, the live pane | T1–T3 opened; T3 streamed and completed |
| Egress filter (verdict, trajectory) | Egress filter | T3's decisions |
| Ledger filter (trajectory) | Ledger filter (trajectory, tag) | T3's debit |
| Tiers, Tools, System | Tiers, Tools, System (WPC1) | read |
| Settings (five runtime keys) | Settings (generated, runtime and file keys) | not changed at WP6 (W10 §5 criterion 4 proved it) |

**PromptCadence parity: met.** PromptCadence's own UI shows Grant and Deny only while a request is
pending, and its record page has no form. Every PromptCadence page in the console did what the
application's own page does, and more. One defect is PromptCadence's: finding 5.

#### LoadCoach

| LoadCoach's own UI | Console | Done live from the console |
|---|---|---|
| Queue: **Pause dispatch**, **Resume**, **Drain** | Queue: the same three, each confirmed first | pause (`pending` `01M28Z22H43CB4KKVCRW25M8QX` → `ok` `01M28Z22Y8DHGDCMY1R3RA58VB`); resume (`01M28Z25TF19FV3D0JD3ZWM6ZK`); drain (`01M28Z986Q61N0W9VCTK3FQ0JA`) |
| — (API only) submit, cancel, feedback | Submit, Cancel, Give feedback | while paused, j1 `01M28Z23V0FTKCP9BAQN9HMPEQ` and j2 `01M28Z24KE09T2YBQ25DYFRDFS` stayed `queued`; j2 cancelled (`01M28Z24Y1FPXN8RHKRC6XASQ6`); j1 then failed `NO_ELIGIBLE_MODEL` (this session pinned `smollm2:135m`, which `general.chat` does not accept; the page rendered the failure in LoadCoach's words); j3 `01M28Z84QEDA8VJFHEY29CEFYY`, routed, **completed** on `gpt-oss:20b` (`01M28Z84QJPD6VAAW9RJPK9EDS`); feedback on j3 (`01M28Z97DWXCB0A9GQ9GH9K2GK`) |
| — restart (the kickoff's "undrained by restart") | Overview: Restart | restart pressed with the queue draining: LoadCoach was SIGKILLed at systemd's 90 s stop timeout, and the console audited **`failed`** (`01M28ZA6T3HHPBQK0SFQ8V9PQD`) although the unit came back (finding 6). **The drain survived the restart**, as LoadCoach's durable `queue.draining` flag is designed to; *Resume* clears it (its confirmation says so). It was cleared here through the runtime key on the Settings page (`01M28ZH1ZNADBH8TWSXPR8RJ70`, *1 applied live*) |
| Jobs: filter by state, class, task, source; job page; explanation | the Jobs section and the job page | j1–j3 and the warm job opened |
| Models: **Scan for models** | Models: Scan, Enable/Disable, Warm | scan (`01M28ZC61CS7YFEJ7GSNEGH7Q4`, *0 added, 11 updated*); `smollm2:135m` disabled (`01M28ZH3HVEYS20HWZ6MJBKFJ8`) and enabled (`01M28ZH40RB5QBYYEKR629P5FC`); warm (`01M28ZH4EGXMV1JA8PZBSR9QS1`) → job `01M28ZH4EA1TPVVS6VX8HMMT2Z` **completed** |
| Providers: **Save** a registration, **Remove**, **Add registration** | Providers: the same, re-authenticated | `timeout_seconds` 300 → 301 with no password: saved (`01M28ZC46KC881XZASYA4VW3CJ`); `base_url` → `http://localhost:11434` with no password: **`REAUTH_REQUIRED`**, nothing sent (`01M28ZC4M7NJYFKCD1FENG88RE`, `refused`, `security: true`); with the password: saved (`01M28ZC553757RXZZVZ093CW7E`); both reverted with the password (`01M28ZC5M8GEK6QSSZBNGWZSR9`). Registration `wp6probe` added (`01M290RCSBZY25T7HTW7VEZS42`, `security: true`) and removed after its preview, with the name typed and the password (`01M290X76JG1CBBZPPZX400M28` `pending`, `01M290X7KB68TNTDY68P8WBMAE` `ok`). LoadCoach's file ends as `[providers.ollama]` alone |
| Routing: decisions, one decision; Task profiles | Routing: explain (API), history, decisions, profiles | explain `general.chat` (`01M28ZHAWQRR02J0DNBHGVJ5MB`, decision `01M28ZHAW5K2YNP9TZPY6SHJBD`): candidates with their numbers, rejections by code, the stored explanation |
| Benchmarks (evidence) | Evidence, with import by file or FreeWeight pull | pulled from FreeWeight (`01M28ZNQRNHM799T1WCYW011F4`): *2 new, 0 updated, 2 bound, 0 unmatched* |
| Reliability | Reliability | read |
| — (CLI only) adapters | Adapters | read (*Adapters are off*: LoadCoach has no `[adapters] directory`) |
| Settings (runtime keys, the queue flags among them) | Settings | `queue.draining` → `false`, above |
| System | **no console page** | judged in §3 |

**LoadCoach parity: met**, except LoadCoach's System page (§3). Two things did not work as they
should: the restart (finding 6), and the job page, which says *Model: not yet routed* for a job
whose routing refused it (a wording note).

#### FreeWeight

| FreeWeight's own UI | Console | Done live from the console |
|---|---|---|
| Provider: **Save provider** | Provider, re-authenticated for `kind` and `base_url` | `kind` → `llamacpp`, `model_directory` → `~/ai/models/llm` (`01M28YT472HPE6X3RVG5BWRG67`, `security: true`, touched `kind`). Back to `ollama` with the password: **refused** in FreeWeight's words, *This provider does not declare 'adapter_hot_swap' and cannot register an adapter.* (`01M2963QF2PXQ3GEZ4N9T10BRY`). **FreeWeight had already rewritten its `config.toml` to `ollama`** while it kept running llama.cpp (finding 9). Put back to `llamacpp` with the password (`01M296S3H9P6YAWB4ZDSJHYBGE`): *FreeWeight wrote its [provider] block and re-opened its provider.* The operator chose to leave FreeWeight on llama.cpp with adapters on |
| Settings: **Save settings** (runtime keys) | Settings (runtime and file keys), and the raw editor | the form's save of `[adapters] directory` was **refused, with no audit row** (findings 1 and 2); the raw editor wrote it with the password (`01M28YZDTJSKWY8ZJZKGRJST77`, `raw_editor: true`) |
| Models: **Refresh from provider**, **Disable**/**Enable** | Models: the same, through the catalog call | the refresh on llamacpp was audited `refused` after 10 s (`01M28YXX7NRYPAB99Z97J8DGV4`, finding 3); FreeWeight finished it and stored 27 `llamacpp` models. `smollm2:135m` disabled (`01M291CD259FT53VZ5W7T0XXMV`) and enabled (`01M291CDE1RWVR83P4VQP6P55X`) |
| Runs: **Start run** (model, suite, label); a run; its tests | Runs: Start as the capped job and follow it, Cancel, Repeat | the bare base `llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b` on `native.structured_output`, started as job `01M2956RB194S5ENMBTH36TJQ7` (`job.enqueue` `01M2956RB3K5HXXZDQCG4G87QM`). The Starting page followed it to run `01M2956YG0KKH3FG6K2FS9RAWG`, which was **cancelled** from its page while `preparing` (`01M29574DKQJKJ1ZFFVHK9GG6Y`); the job then recorded *the run stopped on the operator's cancel* (`01M2956RBE8Y2FE8EAXPP0QY39`). **Repeated** with force and a label (`01M295750TPA0M7QC9JD65V9N1`) as run `01M295750S8VB88YFKW8JYDSTQ`, followed from `warming` to **completed** in about 25 s. Both llama.cpp runs, this one and the adapter's, carry FreeWeight's degradation `served_context_assumed_incorrectly`: 8 192 recorded as configured, 32 768 read from llama-server's `/props`. Its explanation says *nothing requested one*, although `[runtime] context_size = 8192` is set. ModelRack adds `--ctx-size` from the run's profile, and the goal jury's server shows `--ctx-size 8192`. Whether the reading or those two launches is wrong is left to WPF2 |
| Results: filters; samples | Results: every filter; **Export** | run `01M27N0XGKH7YG3MPZYCP37QNQ` exported as `freeweight-run.csv`, 3 518 bytes (a download writes no audit row) |
| Compare | Compare | the bare base `01M295750S8VB88YFKW8JYDSTQ` beside `terse`'s run `01M2976BG3DZ81BS97TMJD2TJR` under `native.structured_output`: *A direct across 2 run(s)* and *Nothing separates them: every metric row may be read across.* Every quality metric reads 1 on both. Energy was 422 J bare and 470.7 J with the adapter, peak VRAM 3.285 GB and 3.396 GB, mean GPU power 31.38 W and 26.12 W |
| Evidence: filter by capability, model, **stale** | Evidence: filter by capability, model, machine, runtime hash, minimum confidence; **the bundle** | `freeweight-evidence.json` downloaded, 14 415 bytes. The console has no filter by staleness; it shows each record's staleness (WP4). A small gap |
| Goals: starters (**Fork**, **Customise**), the wizard, grading, the report | Goals: all of that, plus import, edit, delete, both exports, calibration, judges | `technical_explanation` forked as **`wp6_goal`** (*badged unforked until its criteria or its tasks are edited*). Edited through the dry run — the corpus into `audience_fit`'s intent and a one-juror llama.cpp jury: the preview showed both hashes, *0 run(s)*, *What moved: judge* and the pack's lint, and the save rewrote `goal.json` (`sha256:3143423b…`). Twelve starter samples pasted; graded through the console, reloading after six, to FreeWeight's own *24 of 24, complete*, with no duplicate (it upserts). The first calibration was **refused** for having no variance, in FreeWeight's words. After a regrade, job `01M297EVXDF0N9SXPW09V2QG3W` ran 1 375 s in its capped scope with the jury on `llamacpp/Qwen3.5-9B-UD-Q8_K_XL`, judging 4 of 4 held-out samples. The report reads *Not measurable yet — and that is a useful answer*: gate not passed, κw 0.000, 8 anchors · 2 held out (finding 10), validity 0.550, each criterion with its lint and the worst disagreements with both rationales. Exports: the bundle (7 378 bytes), the goal pack (2 108 bytes) and the calibration report (761 bytes, finding 11), each an attachment |
| Database: backup, preview deletion, vacuum | Database (W7, ADR-0134) | not repeated here |
| — (CLI only) adapters | Adapters, and one adapter beside its base | the directory, written with the raw editor, applied at FreeWeight's next start. With the reviewed manifest in place, Adapters lists `terse` (base proven by its digest, declares none, `public`, available) and three unmanifested GGUFs. The console cannot start an adapter run (finding 4), so `freeweight run start --adapter terse` was launched inside the job's scope, and FreeWeight's own scheduler executed it. Two attempts failed with the closed client (finding 9). Run `01M2976BG3DZ81BS97TMJD2TJR` **completed** at 14:50:43. The adapter's page then showed the subject `…Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5`, its runs and results, and the delta beside the bare base: `structured_output` 1.000 with the adapter, 1.000 bare, **+0.000**. At phone width that page scrolls sideways by 96 px |
| Machines | Machines, reached from Runs and Results | read; at phone width the machine page scrolls sideways by 138 px |
| Dashboard, Sources, System | **no console page** | judged in §3 |

#### IdeaPress

IdeaPress's project page links nothing, so its plan, workspace, unit and export pages were opened by
URL. Every model call ran through IdeaPress's own `ollama` bindings, one load at a time.

| IdeaPress's own UI | Console | Done live from the console |
|---|---|---|
| Projects: **Create project** (title, brief); show archived | Projects: create (title, content type, workflow, brief, author material), filters | project `01M28ZYHH7GS9RGX5GR0JVEG3F`, *WP6 verification: keeping a local LLM box out of swap* (audit `01M28ZYHHCE1N1Y56W416ZYM9S`) |
| — (API only) run the plan | Project: **Run the plan** | task `01M28ZYHW81BZRNTWC7XWMM1JV` completed in 250 s, 5 units (`01M28ZYHXH0V65EEACR3B7DXBT`) |
| — (API only) stage runs | Project: the run form with overrides | `draft` with `max_revision_rounds` 1 (`01M2906EVSMQHJHMWDYHM7FD0E`), task `01M2906EVK9SZVR7WWT8DBJ6A7` completed in 2 657 s. U-01, U-02, U-04 and U-05 were committed. **U-03 was paused by IdeaPress**: *the model produced no text at all in 8192 output tokens, twice, for the 'critique' stage … Raise the stage's output budget.* The console's unit page shows the reason |
| — resume a paused unit | Unit: **Resume this unit**; the run form's `resume` | U-03 resumed through the run form with `model_hint` `ollama/gemma4:12b-it-q8_0` for that run alone (`01M29433R08WP7FMSXYE9W1F8Y`, overrides `[model_hint]`), task `01M29433QXSNNF9DFPMDQQA228`, 133 s → **all five units committed** |
| — (API only) revise | Unit: **Revise** with instructions | U-01, *Add one sentence telling the reader to run `ollama ps` …* (`01M292R2PXR4QCNBHQC759WJH4`), task `01M292R2PP990BDXPVN354N7VJ`, 821 s: the audit found 2 major issues and the critique was *materially_deficient*, then **IdeaPress paused U-01** (*no text at all in 8392 output tokens, twice, for the 'revise' stage*). A second revision, with the corpus as its instruction (`01M293H6Z2Z6RQWXGF5HPB18Q0`), committed version 2 (check 5). The history shows version 1 from `draft, audit_fast, audit_deep, critique, revise, audit_fast, critique` and version 2 from `revise, audit_fast, critique` |
| Export: **Write the export** (html, json, markdown) | Export: write; download each format | first write **refused**, in IdeaPress's words: *This project's plan is not fully committed: 3 of 5 units are committed, and U-01 (paused), U-03 (paused) are not …* (`01M293H56T10R693G7AZBTVD14`). After the resume: markdown written, 12 250 bytes, `sha256:bf4d3fb9…eda3`, 5 units (`01M29475XM213QNA39DSE3TKVP`). Downloaded through the console: `200`, `text/markdown`, `attachment; filename="01M28ZYHH7GS9RGX5GR0JVEG3F.md"`, byte-identical to the file IdeaPress wrote |
| Plan: **Merge**, **Move**, **Reassign**, **Set the goal**, **Split** | Plan: the same five edits | *Set the goal* of U-05: *Applied the goal edit; IdeaPress re-checked the whole plan.*; every unit stayed committed |
| Workspace: **Show the difference**, **Run research** | Workspace and Plan: the same | research, task `01M2947VG4J86272E7065Y7JPC`, completed at once (the brief names no source to fetch); the workspace read with `?unit=U-01` |
| — (API only) cancel | Task page: **Cancel** | a `project_review` run (`01M294G788QHTP8SR78R0KYFPB`, task `01M294G77WCS4NANGVCV9BJWSF`) was cancelled 3 s after it started (`01M294GAAYYE91ECHK56EASENP`). The page said *IdeaPress honours it at the next model-call boundary*. **IdeaPress then made a second 2 m 47 s model call and ended the run `failed`**, not `cancelled`, with 0 attempts recorded (finding 8) |
| — (API only) delete | Project: **Delete this project…**, previewed, archive-first | the preview only: *IdeaPress removes the project, its plan, its units and every version … (12250 bytes). It cannot be undone.*, with *Archive it first* and the typed title. Not confirmed: the operator keeps everything |
| Backends | Backends, with the round-trip **Test** | *Round trip: ollama ok*, 29.19 ms, Ollama 0.32.13, not remote, 11 models |
| — (API only) workflows | Workflows | read |
| System | **no console page** | not needed (§3) |

**IdeaPress parity: met.** The export refusal and both pauses are IdeaPress's own honest answers,
rendered in IdeaPress's words. The pauses come from `qwen3.5:9b-q8_0` spending its whole output
budget on thinking (`workflow.structured_output_tokens`, 8 192, config-only). That is a note for the
operator (§7), not a console defect. Neither IdeaPress's own export page nor the console offers
IdeaPress's `--allow-partial`.

#### From the phone

Every action above ran on the desktop profile. A second pass ran by touch on the emulated Pixel 7,
light theme, at 412 px:
* PromptCadence: T4 `01M29198VWM0E96AC5SXT2223P` was submitted with a one-token budget
  (`01M29198W55HCNCHQW05GHMZCC`) and **denied** with a reason (`01M29199XQHBAEMYFWXXF2NJ6M`,
  `security: true`). It **halted**, with the reason as its cause.
* LoadCoach: the queue was paused (`01M2919AQFVSZMT5ENY5R5VAKR` `pending`, then
  `01M2919C4FDKP29RR5KTS18ERJ`) and resumed (`01M2919CJKWTBKJ6NZXQ8D1FTD` `pending`, then
  `01M2919DW6M53QTAH8CFVENPE1`), each confirmation read on the phone.
* FreeWeight's Provider, Start and goal-draft forms, and IdeaPress's create form, were opened, not
  submitted.

No page scrolled sideways, and nothing raised a dialog or a `4xx`. WP4 had graded a goal from the
same phone profile, and WP5 created and planned a project from it.

### Check 3 — Stopped

Each application was stopped from its console Overview. Every page of its tab was loaded in the four
device and theme combinations, and it was started again from a page's own *Start*.

| Application | Stop → start (audit) | Renders | Result |
|---|---|---|---|
| PromptCadence | `unit.stop` `01M290BJ42GW09KSMACV0AA8P8` (1.0 s) → `unit.start` `01M290C6NBM5Y0ATF49G3S8P56` | 14 pages × 4 = 56, all `200` | **Passed.** Trajectories, the records, Approvals, Egress and Ledger read *from the database at revision 0011*. A record says it shows the database's rows rather than the explanation document. Tiers, Tools and System say they read only from the running API. *Start* is on every page, and no API-only action is offered. Every `0` is a real count (cache-read tokens, row counts), none an unread value |
| LoadCoach | `unit.stop` `01M290CDHVZ1J1DBYR7MQR0X3V` (0.7 s, no console stream open) → `unit.start` `01M290DP9E3C2VNYGKK4X9SRVM` | 38 pages × 4 = 152, all `200` | **Passed.** Overview, Models, the jobs list and pages, Routing, decisions, task profiles, Evidence and Adapters read the database at `0015`. Reliability shows the persisted counts and says the verdicts need the running API. The queue report and Providers read only the API. *Start* is everywhere. The `0`s are a GPU index, persisted counts, `min_context_tokens` and a temperature |
| FreeWeight | `unit.stop` `01M29166AVMEREGKMJG9WF33ME` (0.8 s) → `unit.start` `01M2917W3XZP3DH2PG0B0BCGBW` | 37 pages × 4 = 148, all `200` | **Passed.** The Overview, Models, a model, Runs, a run (its stored events instead of the pane), tests, samples, Machines, Adapters, Goals, a goal, validation, calibration and the report read the database at `0010`. Evidence, Results, Judges, Provider, the goal editor and grading say they read only the running API. *Start* is on every page. The zeros are real: scores, spreads, a GPU index, and `wp4_demo`'s calibration set, which WP4's delete and import emptied (the running API also answers `total: 0`). Polish: Compare keeps its query form enabled and names no source, and *Start grading* stays enabled |
| IdeaPress | `unit.stop` `01M294VQ19H63TF871W6PNEA23` (0.9 s) → `unit.start` `01M294WH48AV2T4P3STB5GEQBR` | 19 pages × 4 = 76, all `200` | **Passed.** The Overview, Projects, both projects, their plans, the tasks, Units and each unit read the database at `0011`. Backends, Workflows and the workspaces say they read only the running API. *Start* is on every page, and no page scrolled sideways. The zeros are real: a task's *Paused* count, and row counts |

The strip is one exception to "never `0` for `—`", and a small one. After LoadCoach was stopped
(`01M290HRZ2WGG0YNJFGXYWBY39`), a page's first paint still read **QUEUE 0 active**: the last
reading, until the sampler's next one. Within 5 s the stream showed **QUEUE — inactive**. It is in
WPF1's polish.

### Check 4 — Degradation

**Passed, on a throwaway console.** Putting an unknown revision under the operator's LoadCoach, or
replacing a running application, cannot be done on the operator's console without corrupting a
database or reconfiguring it. So a second console ran on the same machine (`127.0.0.1:8781`, its
own XDG tree), against the real applications, with two substitutions:

* **LoadCoach's database** was a copy of the fixture `loadcoach-unknown-9999.sqlite3`. A wrapper
  answered `config show --json` with its URL and passed every other verb to the real `loadcoach`.
* **IdeaPress's API** was a stub on `:8797` that answers `GET /api/v1/version` with `2.0.0`, outside
  the console's `>=1.0,<2.0`.

| | LoadCoach (unknown revision) | IdeaPress (version mismatch) | FreeWeight, PromptCadence |
|---|---|---|---|
| Variant A — LoadCoach's API live | Overview: *Figures from the API; table: schema at revision 9999 is not known*; Database: `SCHEMA_UNKNOWN`; every API page as normal | every IdeaPress page: *`APP_VERSION_MISMATCH` IdeaPress 2.0.0 is outside the range this console speaks to (>=1.0,<2.0); its pages are degraded by name rather than guessed at.* | every page `200`, as normal |
| Variant B — LoadCoach not answering | every database page: *`SCHEMA_UNKNOWN` loadcoach's schema at revision 9999 is not known to WeightRoomGym 1.0.0 (known: 0015); its database pages are degraded by name (ADR-0123 rule 3).*; Providers and the queue report: *LoadCoach is not answering, and this page reads only from its running API.* | unchanged | unchanged |

The console's own pages (`/`, Jobs, Catalog, Costs, Backups) rendered. Its Database index names
LoadCoach's `SCHEMA_UNKNOWN`. IdeaPress's Database page read IdeaPress's real database at `0011`,
a revision the console knows, which is right. The throwaway console and the stub were stopped.

### Check 5 — Safety

* **The injection corpus** (PromptCadence's `tests/security/test_injection_corpus.py`, as the
  console's chat test copies it):
  * *Trajectory prompt* — T3 `01M28YRSS9C6KZQDP6MA9WETWR` completed. Its record carries
    `&lt;script&gt;alert(1)&lt;/script&gt;` and `{{ 7 * 7 }}` as text, with no raw `<script>`, no
    `javascript:` link and no dialog. Its list, ledger, egress and approvals pages are the same.
  * *Goal criterion* — goal `wp6_goal` carries the corpus in the intent of its `audience_fit`
    criterion, saved through the editor's dry run (`goal_hash` `sha256:3143423b…`). The editor's
    textarea carries it escaped (`&lt;script&gt;…`). The goal page, the grading page, the report and
    the report export do not render a criterion's intent at all. The bundle is a JSON attachment in
    which the corpus is a JSON string. No raw `<script>` appeared, and no dialog was raised.
  * *Unit instruction* — IdeaPress revised U-01 of project `01M28ZYHH7GS9RGX5GR0JVEG3F` with the
    corpus as the author's instructions (task `01M293H6YMHA93TY88KBA32Y5N`, 285 s). Validation
    passed, the audit found nothing, and the critique said *leave_it_alone*, so version 2 was
    committed (47 words). The model did not echo the corpus. The task, the unit, the workspace and the
    project pages carry no corpus markup: the instruction is rendered nowhere, and the audit row
    records only `has_instructions`. No dialog was raised.
  * *Project brief* — project `01M293H5QSD42HDN2C03QJK5EM` has the corpus as its brief and as author
    material. Its page carries `&lt;script&gt;alert(1)&lt;/script&gt;` and `{{ 7 * 7 }}` as text,
    with no raw `<script>` and no `javascript:` link. The projects list, its plan page and the Units
    page are the same. No dialog was raised.
* **No page shows a secret.** 129 console pages and the four raw editors were compared against both
  application token files, PromptCadence's LoadCoach token and the operator's password. No value
  appears anywhere. The one match for the word `Bearer ` is a field description on FreeWeight's
  Settings page.
* **Every state-changing route has an audit exercise.** `test_every_state_changing_route_has_an_exercise`
  asserts the route set equals `EXERCISES` over every `APIRoute`, UI routes included, and it passes.
  **But a refused settings write leaves no row** (finding 2): the exercise covers only the success.
  Against spec §11 contract 2 this is a failure.

### Check 6 — Performance

**Failed for the Overviews, passed for every other page.** Spec §15 names one page budget,
*Application Overview page, application running ≤ 300 ms*, and it was applied to every page of
every tab. Each was measured on the reference machine through the LAN address, desktop profile, 3
loads per page, median of the browser's first contentful paint. Each application was running and
nothing else was loading the console.

| Pages | Within 300 ms | Slowest within budget | Over budget |
|---|---|---|---|
| PromptCadence 14, LoadCoach 38, FreeWeight 36 | 86 of 88 | LoadCoach Queue, 224 ms (time to first byte 184 ms) | **`/apps/promptcadence` 580 ms** (first byte 554 ms); **`/apps/loadcoach` 544 ms** (first byte 510 ms) |
| IdeaPress 19 | 18 of 19 | a unit page, 208 ms (first byte 168 ms) | **`/apps/ideapress` 520 ms** (first byte 484 ms) |
| FreeWeight 40, this run's pages included (the adapter, its run, the comparison, `wp6_goal` and its calibration) | 39 of 40 | the Database page, 188 ms | **`/apps/freeweight` 508 ms** (first byte 464 ms) |

**147 pages measured in all. Every page is inside the budget except the four Overviews**, which miss
it by about half a second each. The slowest page that is not an Overview is LoadCoach's Queue at
224 ms.

The half second is one process launch. Five server round trips per page (median): PromptCadence
Overview 662 ms, LoadCoach Overview 566 ms, IdeaPress Overview 468 ms, PromptCadence Trajectories
36 ms. Timed alone: `loadcoach config show --json` 576 ms, `promptcadence config show --json`
494 ms, `journalctl` 6 ms, `systemctl show` 5 ms. `services/overview.py` calls
`effective_database_url` on every render instead of the `DatabaseUrlCache` the other pages use
(finding 7).

## 3. Pages with no console home

Judged at the operator's request (2026-09-11). Each page was opened in its application beside the
console.

| Page | What it shows | Judgement |
|---|---|---|
| FreeWeight **Dashboard** | Filters by suite, model, machine and since. Summary figures: completed runs 11, models measured 6, samples 375, unsupported measurements 60, machines 3, the latest run. A model × suite heatmap of one headline metric, marking cells that span machines or suite versions as *separated* | **Needed.** No console page shows the cross-model view: Results is a metric query, Compare works per subject. It has no API route today. → **WPF5**, which amends spec §7.3 |
| FreeWeight **System** | Ten health components with details (database, provider, GPU telemetry, machine, evidence freshness, prompts, sandbox, external benchmarks, goals, judges) | **Needed.** The console shows only the Overview's status and a JSON link. PromptCadence's System page (WPC1) is the precedent. → **WPF5** |
| LoadCoach **System** | Version, fingerprint, workers, dispatch latency, starving, active jobs, dispatch state, five health components, telemetry, resident models, circuit breakers | **Needed.** Health components and workers appear nowhere in the console. → **WPF5** |
| FreeWeight **Sources** | Nine external benchmark adapters with source, pinned version, licence, sandbox and install state. None installed; the dataset pins are placeholders that refuse installation | **Not needed now.** It is a read-only credit list with nothing actionable from any interface. Revisit when an external benchmark can be installed, since install state is then worth seeing. Recorded in WPF5's spec amendment |
| IdeaPress **System** (not in the kickoff's list) | Three health components | **Not needed** (WP5 §4): the Overview and the doctor cover it |

## 4. Findings, and the rows they became

Each finding became a row in `roadmap/weightroom-work.md` §1, with a kickoff prompt under
`history/prompts/`. Nothing was fixed in this session.

| # | Severity | Finding | Evidence | Row |
|---|---|---|---|---|
| 1 | **major** | **FreeWeight's Settings form cannot save a file key while FreeWeight runs on Ollama**, its default provider. `runtime.flash_attention` is FreeWeight's one nullable boolean. The form renders it as a select with `false` preselected, so every save writes `flash_attention = false`, and FreeWeight refuses it: *runtime.flash_attention is not honoured by provider.kind = 'ollama'* | the save of `[adapters] directory` at 12:23:46 PDT; the field's markup; FreeWeight's file held only `[runtime] context_size`; the raw editor saved the same key (`01M28YZDTJSKWY8ZJZKGRJST77`) | **WPF1** |
| 2 | **major** | **A refused settings write leaves no audit row** (spec §11 contract 2). The audit test exercises each route's success only | two `POST /apps/freeweight/settings` in the console's journal (request ids `01M28YT24SABZ0WN7K7XCWPCK9`, `01M28YT2TPE2PZ8RVWR5PXP3GF`), no `settings.write` row; compare LoadCoach's audited provider refusal `01M28ZC4M7NJYFKCD1FENG88RE` | **WPF1** |
| 3 | minor | **A call slower than the console's 10 s client timeout is audited as the application's refusal.** *Refresh from provider* on llamacpp said *did not answer … timed out* while FreeWeight finished hashing 195 GB and stored 27 models | `01M28YXX7NRYPAB99Z97J8DGV4` (`refused`); FreeWeight's digest file written 12:27:50 | **WPF1** |
| 4 | **major** | **No adapter run can be started from the console**, so the operator's adapter step cannot be done there. The Start form and the `freeweight_suite_run` job carry no adapter. FreeWeight's own form and `POST /api/v1/runs` carry none either; only `freeweight run start --adapter` does | `services/job_kinds.py` argv; `apps/freeweight/api.md` §3; check 2's FreeWeight adapter step | **WPF2** |
| 5 | **major** | **A cancelled trajectory leaves its approval request pending.** The console's Approvals page offers Grant and Deny on it, and PromptCadence refuses both | T2 `01M28YRRF5BBKP5PNMS49FRCY8`, request `01M28YRRGKVNSZ03HZS5X3S3P1` still `pending`; deny refused `APPROVAL_INVALID_STATE` (`01M29025ZAC5SBAWK58GD92J8X`) | **WPF3** |
| 6 | **major** | **LoadCoach does not stop inside its unit's timeout while console streams are open**, and **the console audits a restart that succeeded as `failed`**. First seen at WP2 §7 item 4 | journal: `Waiting for connections to close`, then SIGKILL at 90 s, `Result=timeout`; `unit.restart` `failed` `01M28ZA6T3HHPBQK0SFQ8V9PQD`. With no stream open the stop took 0.7 s (`01M290CDHVZ1J1DBYR7MQR0X3V`) | **WPF4** |
| 7 | **major** | **Every application's Overview misses spec §15's ≤ 300 ms**, because each render launches `<app> config show --json` (about 0.5 s) instead of using the console's `DatabaseUrlCache`. W10's budget test measured 3.0 ms against fakes | first paint: PromptCadence 580 ms, LoadCoach 544 ms, IdeaPress 520 ms, FreeWeight 508 ms, against 224 ms for the slowest other page; `services/overview.py:290` | **WPF6** |
| 8 | **major** | **IdeaPress does not honour a cancel across its empty-generation retry, and its configured bindings cannot finish a project.** A `project_review` cancelled during its first call made a second model call afterwards and ended `failed`, not `cancelled`, with no attempt recorded. On `qwen3.5:9b-q8_0` the critique, the reviser and `project_review` each spent the whole 8 192-token output budget thinking: two units were paused and the review failed. The export was refused until a unit was resumed with another model | task `01M294G77WCS4NANGVCV9BJWSF` (`stage.started`, `stage.failed` only; `CONTEXT_LIMIT_EXCEEDED`); Ollama calls 14:03:15–14:06:09 and 14:06:10–14:08:57 around the cancel at 14:03:17; U-03 and U-01 pause reasons; export refusal `01M293H56T10R693G7AZBTVD14` | **WPF7** |
| 9 | **major** | **FreeWeight writes a provider change before refusing it, and cannot use adapters with Ollama.** With `[adapters] directory` set, the Provider page's switch to `ollama` was refused, yet `config.toml` was already rewritten to `ollama` while the running provider stayed llama.cpp. `freeweight config validate --file` called the file valid, so the next restart would have started FreeWeight on the refused combination. After the provider was put back, the next two runs FreeWeight's own scheduler claimed failed at once: *Cannot send a request, as the client has been closed*. The re-open had closed the client the scheduler still held, and the failed run left a `llama-server` running. Separately, every llama.cpp refresh hashed all 195 GB of GGUF files again (2–4 minutes), rewriting the digest cache each time | `01M2963QF2PXQ3GEZ4N9T10BRY` (`refused`); `config.toml` `kind = "ollama"` beside its `.bak`; FreeWeight's health `llama.cpp … 1 resident`; restored `01M296S3H9P6YAWB4ZDSJHYBGE`; runs `01M2970JAN5V8Q14D1Q531XRTQ` and `01M2970TDRQ5VJWYRQ1D19KXAC` failed at 14:47 PDT; `digests.json` rewritten 12:27:50 and 14:13:20 | **WPF2** |
| 10 | minor | **A calibration report counts fewer held-out samples than its jury judged**, and says nothing about the difference. WP4 saw it too (four judged, three counted) | job `01M297EVXDF0N9SXPW09V2QG3W` printed `anchors 8, holdout 4` and `sample_judged 1…4 of 4`; the page and `GET …/calibration/report` both say `n_holdout 2`, per criterion as well | **WPF8** |
| 11 | minor | **The exported calibration report carries no criteria.** `wp6_goal.calibration-report.json` (761 bytes, `benchmark.calibration_report 1.0`) has `"criteria": []`, while the page and the API carry both criteria with their coefficients, bias, validity, band, lint and worst disagreements | the export beside the report page and `GET …/calibration/report` | **WPF8** |
| — | decision | Pages with no console home (§3) | §3 | **WPF5** |

**Polish, carried in WPF1's kickoff:**
* at phone width, FreeWeight's machine page scrolls sideways by 138 px (550 px on a 412 px screen),
  FreeWeight's adapter page by 96 px, and LoadCoach's Database page by 19 px;
* the strip's QUEUE shows the last reading on the first paint after LoadCoach stops, for up to 5 s;
* a stopped FreeWeight's Compare keeps its query form enabled and names no source, and its
  calibration page keeps *Start grading* enabled, a link to a page that needs the API;
* after a grant, the Approvals page shows the new state but no notice;
* a job whose routing refused it reads *Model: not yet routed*.

## 5. What the kickoff got wrong

1. **"From a phone on the LAN."** No physical device was reachable from the session. The operator
   chose an emulated Pixel 7 over the LAN address, so the phone criterion is demonstrated only as an
   emulation.
2. **"The LoadCoach queue … drained, then undrained by restart."** A drain is LoadCoach's durable
   `queue.draining` flag, which it reads again at start, so a restart keeps it. *Resume* clears a
   drain, and the console's confirmation says so.
3. **"No inert entry except IdeaPress `Tokens`."** IdeaPress's menu has no *Tokens* entry at all.
4. **"From the console, set FreeWeight's `[adapters] directory` … Measure one adapter."**
   `~/ai/models/adapters/llm` held four GGUFs and no reviewed manifest, so FreeWeight could measure
   none until a person wrote one. The operator reviewed one drafted in this session. The Settings
   form could not save the key (finding 1), and nothing in the console can start an adapter run
   (finding 4).
5. **"Load an unknown `alembic_version` fixture and a version-mismatch application"** on the
   reference machine with all four applications running. The operator's console cannot do that
   without corrupting a database or replacing an application, so check 4 ran on a throwaway console
   on the same machine.
6. **"Every new page's first paint stays within spec §15's page budget."** §15 names one page budget,
   the Overview's ≤ 300 ms. It was applied to every page. The two pages that miss it are the
   Overviews, which are not new.
7. **"Record the application's audit trail."** Only the console keeps an audit log. For each
   application, its trail here is its own record of the action: PromptCadence's trajectory events,
   LoadCoach's job and provider state, FreeWeight's run events and IdeaPress's stage runs.

## 6. Left on the reference machine

Everything this run created was kept, at the operator's choice (2026-09-11).

* **The console (`weightroom.service`).** **141 audit rows** by `jpk` from 12:08 PDT, 8 of them
  refusals and 13 marked `security`; the operator password reset (§7 item 1); FreeWeight's start and
  calibration jobs in its jobs table. The *memory cap
  fired · ollama.service* alert from 09:14 PDT was left open and unacknowledged. A transient
  *application down · freeweight.service* alert (13:39, one health read timed out while IdeaPress
  held the GPU) cleared itself within a minute.
* **PromptCadence.**
  * Trajectories: T1 `01M28YRAS1Y1K89NCTC6J5HR9R` completed, with its debit; T2
    `01M28YRRF5BBKP5PNMS49FRCY8` cancelled; T3 `01M28YRSS9C6KZQDP6MA9WETWR` (the corpus) completed;
    T4 `01M29198VWM0E96AC5SXT2223P` halted by the phone's denial.
  * Request `01M28YRRGKVNSZ03HZS5X3S3P1` stays `pending` until it expires at 2026-09-12 12:23 PDT.
  * No configuration change.
* **LoadCoach.**
  * Jobs: j1 `01M28Z23V0FTKCP9BAQN9HMPEQ` failed, j2 `01M28Z24KE09T2YBQ25DYFRDFS` cancelled, j3
    `01M28Z84QEDA8VJFHEY29CEFYY` completed with feedback, and the warm job
    `01M28ZH4EA1TPVVS6VX8HMMT2Z` completed. Routing decision `01M28ZHAW5K2YNP9TZPY6SHJBD`.
  * Two evidence records imported from FreeWeight.
  * **`~/.config/loadcoach/config.toml` now exists**, holding the one default `ollama` registration
    (the provider edits created it; WP2 had removed its file), with `.bak`.
  * The stored `queue.draining` and `queue.paused` flags are both `false`.
  * `smollm2:135m` was disabled and enabled again.
  * The unit was restarted once (SIGKILLed at the stop timeout) and stopped and started three more
    times.
* **IdeaPress.**
  * Project `01M28ZYHH7GS9RGX5GR0JVEG3F`: five units committed, U-01 at version 2 from the corpus
    instruction, U-05's goal edited. Its stage runs include the failed `project_review`
    `01M294G77WCS4NANGVCV9BJWSF`.
  * Its markdown export: `~/.local/share/ideapress/projects/wp6-verification-keeping-a-local-llm-box-out-of-swap/wp6-verification-keeping-a-local-llm-box-out-of-swap.md`.
  * Project `01M293H5QSD42HDN2C03QJK5EM`: the corpus as its brief, no plan.
  * A delete preview that was never confirmed. The unit was stopped and started once.
* **FreeWeight.**
  * **`config.toml` now holds `[provider] kind = "llamacpp"`, `model_directory =
    "/home/jpk/ai/models/llm"` and `[adapters] directory = "/home/jpk/ai/models/adapters/llm"`**,
    with `.bak`: the operator's decision to stay on llama.cpp with adapters on.
  * **`~/ai/models/adapters/llm/qwen2.5-1.5b-instruct-terse.manifest.json`**, the operator-reviewed
    manifest (`public`).
  * 27 `llamacpp` model rows and `~/.local/share/freeweight/llamacpp/digests.json`.
  * Runs `01M2956YG0KKH3FG6K2FS9RAWG` (cancelled), `01M295750S8VB88YFKW8JYDSTQ` (the bare base),
    `01M2970JAN5V8Q14D1Q531XRTQ` and `01M2970TDRQ5VJWYRQ1D19KXAC` (the adapter, both failed with the
    closed client), and `01M2976BG3DZ81BS97TMJD2TJR` (the adapter, completed).
  * Goal **`wp6_goal`** (forked from `technical_explanation`, the corpus in one criterion's intent,
    a one-juror llama.cpp jury), its 12 calibration samples, 24 grades by `jpk`, and its stored
    calibration report of 2026-09-11T21:55Z.
  * `smollm2:135m` was disabled and enabled again. The unit was restarted twice and stopped and
    started once.
* **Throwaway files.** Check 4's console tree, fixture copy and stub are in the session scratchpad,
  all stopped.

## 7. For the operator

1. **Set your own operator password**: `wr-gym operator password jpk`. It was reset at the start of
   this row and its value sits in the session scratchpad.
2. **The verdict is *not ready*.** Rows WPF1–WPF7 carry the findings. WPF1 comes before WPF2. WPF3,
   WPF4, WPF6 and WPF7 are independent, and WPF5 fits in when convenient. WR-α and WR-1.0 remain
   undeclared: this row's phone was an emulation, and W10's independent-device verification still
   owns those milestones.
3. **FreeWeight is on llama.cpp with adapters on**, by your choice. Its Ollama models cannot be
   measured until you switch back. The switch is refused while `[adapters] directory` is set, and the
   refused switch still rewrites the file (finding 9). Until WPF2 lands, switch back in this order:
   empty `[adapters] directory` with the raw editor, then change the provider on the Provider page,
   then restart FreeWeight.
4. **IdeaPress on `qwen3.5:9b-q8_0` pauses units and fails project reviews** at its 8 192-token output
   budget (finding 8). Until WPF7 lands, a per-run model hint on the run form gets a unit through:
   `ollama/gemma4:12b-it-q8_0` committed U-03 in 133 s. A larger `workflow.structured_output_tokens`
   in IdeaPress's `config.toml` is the other way.
5. **Alerts.** *memory cap fired · ollama.service*, from 09:14 PDT on the WP4 crash morning, is still
   open on the banner.
6. **Nothing was pushed.** This row is one docs commit in WeightRoom.
