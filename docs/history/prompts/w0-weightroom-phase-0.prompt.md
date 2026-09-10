# Kickoff — W0: WeightRoom Phase 0 — the ADRs, the spec, the plan, the repo

**Row:** W0 (Fable 5.1 · attended) — indexed from [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md)
§1 today, and the first row of `docs/roadmap/weightroom-work.md`, the arc's own file this row
creates (§7.1) — the fifth application. Interview of 2026-09-09; every decision below is the operator's and is
not re-opened here. Rows W1+ (agentic, unattended allowed) build what W0's plan says.
**Ships:** no code. ADRs 0123+, `apps/weightroom/{spec,development-plan,api,data-model,risks}.md`,
the restructured repository, updated references, a MirrorWall 0.3 design brief, and the W1+ rows
written into `roadmap/weightroom-work.md` with their kickoff prompts.
**Component:** the repository at `~/ai/suite/docs` (remote `JPKell/OpenWeight-Gym`), which this
row turns into `~/ai/suite/WeightRoom` with the documentation under `WeightRoom/docs/`.

---

## Standing preamble

* Read first: [`architecture/master-architecture.md`](../../architecture/master-architecture.md)
  §§1–3, [`architecture/dependency-and-boundary-rules.md`](../../architecture/dependency-and-boundary-rules.md),
  [`standards/gold-standards.md`](../../standards/gold-standards.md), ADR-0020, ADR-0026, ADR-0038,
  ADR-0045, ADR-0100, ADR-0117, ADR-0118, ADR-0119; then every `apps/*/spec.md` §§7 and 12 (the
  surfaces WeightRoom re-implements) and every app's `docs/security.md`; then
  [`MEMORY_SAFETY.md`](../../MEMORY_SAFETY.md) and [`LAN_ACCESS.md`](../../LAN_ACCESS.md) (both change
  here). **All of it before the first edit.**
* House method for the documents: the spec follows the 21-section shape every other app uses
  (`apps/ideapress/spec.md` is the freshest); the plan follows `apps/promptcadence/development-plan.md`
  (phases with demonstrable acceptance criteria, "what to run and what a person sees"); ADRs are
  the ADR-0118 shape (Status, Relates to, Source, Context, Decision as numbered rules,
  Consequences, Alternatives, Revisit when). ADRs are never edited, only superseded.
* Documentation is mirrored: after the move, `WeightRoom/docs/` **is** the canonical tree; the
  four app repos keep their byte-identical mirrors. Nothing in this row changes a mirrored file's
  content except where §4 says so.
* **Do not push, do not tag, do not publish.** Commit at each gate; never `git add -A`;
  `git status --short` at start and end in every repository touched.

---

## 1. What WeightRoom is — decided

**A host operator tool above the layer rules, not a fifth peer app.** Package `weightroom`, CLI
`weightroom`, port **8769**, repository `OpenWeight-Gym`, PyPI distribution **`openweight-gym`**
(`weightroom` is taken on PyPI by an unrelated 0.0.1; the import name and CLI stay `weightroom` —
confirm with the operator at the first gate, it is the one assumption in this prompt).

It may: read every app's database directly; edit every app's `config.toml`; start, stop, restart
and read the logs of every app through `systemd --user`; run every app's CLI as a subprocess;
call every app's HTTP API; import the **packages** (`sweatmeter`, `mirrorwall`, `weightsdb`,
`setspec`, `baseaicore`) like any app. It may **not** import an application. Writes to another
app's database are the one place the boundary is crossed on purpose, and §3's guard is the price.

## 2. Decisions from the interview — each becomes an ADR or a spec section

| # | Decision | Where it lands |
|---|---|---|
| D1 | WeightRoom is a host operator tool; direct DB reads, config edits, process control are in scope; apps stay untouched | **ADR-0123** (supersedes nothing; declares the exception to CLAUDE.md's "no app reads another's DB" for this one component and names why: the operator's tool is the operator) |
| D2 | Server-rendered + htmx + SSE; ADR-0020 kept | spec §7, §11; a line in ADR-0123 that ADR-0020 applies |
| D3 | DB viewer: read + guarded writes; app-owned maintenance operations first, raw SQL behind a triple guard | **ADR-0124** — the guard (§3 below) |
| D4 | Processes via `systemd --user` units WeightRoom writes and drives; Ollama stays a system unit (read status; restart only if a polkit rule allows it — decide, write it down) | spec §5, ADR-0125 if a rule is needed |
| D5 | Chat talks to LoadCoach and PromptCadence only, never a provider directly; conversations in WeightRoom's DB | spec §7; ADR-0045's spirit, cite it |
| D6 | Telemetry: `sweatmeter` in-process, 1 s SSE; resident models from Ollama `/api/ps` and LoadCoach residency; click → history page | spec §7 |
| D7 | **WeightRoom is the only thing on the LAN.** Built-in TLS (own CA), HTTPS in uvicorn, session login; `/trust` page serving `root.crt` with the per-OS steps from `LAN_ACCESS.md` §3; apps stay loopback; `expose_on_lan.sh` is deleted and `LAN_ACCESS.md` rewritten around WeightRoom | **ADR-0126**; `LAN_ACCESS.md` |
| D8 | WeightRoom re-implements every app's control surface natively; app UIs stay loopback-only | spec §4, §7 |
| D9 | Settings: generated forms from each app's settings schema; TOML edited in place with comments kept (tomlkit); validated with the app's own `config validate`; restart offered; runtime-changeable keys through the app API without restart | spec §7, §12; needs a `config schema --json` verb in each app (row per app, W-side) |
| D10 | Docs viewer: render, tree, ADR index, full-text search, mermaid, link rewriting; read-only | spec §7 |
| D11 | v1 feature set (one release): setup wizard + cross-app doctor; unified logs + audit trail; model catalog + downloads (ollama pull, GGUF drop-in, enable/disable, evidence summary, delete-with-cleanup); cost + budget dashboard (LoadLedger balances, ceilings editable); backups + migrations; scheduled jobs (DB-backed, ADR-0010); prompt library editor (ADR-0012 records, diff); alerts (banner only, no outbound channel) | spec §2, §7; plan phases |
| D12 | Look: **dense dark console** (the left artboard of the 2026-09-09 canvas), light toggle; MirrorWall 0.3 carries the new tokens/components and the four apps adopt them in later rows | design brief (§5); MirrorWall row |
| D13 | Chat extras: markdown + code blocks with copy, streamed; routing decision + cost under each reply; PromptCadence tool calls, egress decisions and approve/deny inline; text/markdown attachments as context; **thinking streams while thinking, then collapses; collapsed thinking, decisions and plans expand on click** | spec §7 |
| D14 | Checkout renamed `~/ai/suite/WeightRoom`; docs under `WeightRoom/docs/` | §4 below |
| D15 | Everything in one `1.0.0`; internal phases still gated | plan |
| D16 | W0 on Fable 5.1 attended; W1+ agentic, unattended allowed | roadmap rows |

## 3. The write guard (ADR-0124) — what it must say

Curated maintenance actions come first and call the owning app: `freeweight db delete --model`,
each app's retention settings, `db backup`, `db upgrade`. A raw write (SQL console, row edit,
row delete) is allowed only when **all** of:

1. the owning app is stopped (or, if the ADR finds a read-only mode, in it) — WeightRoom checks
   the unit, not a checkbox;
2. an automatic backup of that database was taken first, named in the audit row;
3. a dry run reported the affected row count and the statement was shown back;
4. the operator typed the table name to confirm;
5. an `audit_log` row in WeightRoom's own DB records who, when, which database, the statement,
   the row count and the backup path.

Also decide: which tables are **never** writable from here (migration tables, lease/queue tables
of a running app, `runtime_profiles`, anything hashed into a fingerprint), and say so by name.

## 4. The repository move — do this first, as its own gate

1. In the checkout: `git mv` every top-level directory and file except `.git`, `.github`,
   `README.md`, `.gitignore` into `docs/` (`adr/`, `apps/`, `architecture/`, `history/`,
   `inventory/`, `packages/`, `reviews/`, `roadmap/`, `standards/`, `scripts/`,
   `LLAMACPP_SETUP.md`, `MEMORY_SAFETY.md`, `LAN_ACCESS.md`, `LEARNING_PLAN.md`,
   `WALKTHROUGH.md`, `CODE_REVIEW_PLAN.md`, `README.md` → `docs/README.md`). History follows.
2. Rename the checkout directory to `~/ai/suite/WeightRoom`. Leave a symlink
   `~/ai/suite/docs → WeightRoom/docs` for one transition (say so in the handoff; the row that
   removes it is named in `outstanding-work.md`).
3. Fix every reference to the old path: `~/ai/suite/CLAUDE.md` (the tree, "docs/ holds", the
   mirror rule), `FreeWeight/scripts/sync_docs.py` (its canonical source path),
   `docs/scripts/*.sh` (`SUITE`-relative paths), `.github/workflows/compatibility-matrix.yml`,
   the ADR/handoff links that are repo-relative (they are `../adr/…` from `history/`; they keep
   working because the whole tree moved together — verify with a link check).
4. Add the standard app skeleton beside `docs/`: `pyproject.toml` (hatchling; dist
   `openweight-gym`, package `weightroom`, script `weightroom`), `src/weightroom/__about__.py`
   at `0.0.0`, `tests/`, `.importlinter`, `.pre-commit-config.yaml`, `requirements/`, the
   fourteen-repo CI workflow shape. **No application code** — W1 writes the first line.
5. Commit: `chore(repo): OpenWeight-Gym becomes the WeightRoom repository; docs move under docs/`.

## 5. The MirrorWall 0.3 design brief (`docs/apps/weightroom/design.md`)

From the chosen artboard, write down the system so the four apps can adopt it later: the token
deltas against `mirrorwall/static/css/tokens.css` (dark-first values, the 13 px base, 32 px rows,
the status-dot vocabulary — `ok`, `degraded`, `stopped`, `unknown` — the telemetry strip at 34 px,
the top-bar app tabs, the left menu), the components WeightRoom needs that MirrorWall lacks (app
tab, status dot, telemetry meter, log pane, DB grid, chat thread with collapsible thinking,
markdown article), and which of them are generic enough to live in MirrorWall 0.3 versus in
WeightRoom. One page; the MirrorWall row builds from it.

## 6. What the spec must settle that the interview did not

Decide these in the spec and cite the decision; if any needs an ADR, write it:

* **Auth model:** one operator account (username + password hash in WeightRoom's DB), sessions,
  CSRF via MirrorWall's double-submit; no roles in v1. The `weightroom setup` wizard creates it.
* **The CA:** where the key lives (`~/.config/weightroom/tls/`, mode 0600), lifetime, leaf
  renewal, what `weightroom trust` prints, rotation (`weightroom tls rotate`).
* **Ollama control:** WeightRoom is not root. Status and `ollama ps` are readable; restart needs a
  polkit rule or a `sudoers` line the wizard offers to write — pick one, or decide restart is
  shown as a command to run.
* **App tokens:** while the four apps bind loopback none is required; the wizard still creates a
  `write` token for LoadCoach and PromptCadence and stores them in WeightRoom's config so chat
  keeps working if an app is ever moved off loopback.
* **Settings schema source:** each app gains `config schema --json` (a pydantic JSON schema plus
  the runtime-changeable and config-only key sets); WeightRoom generates forms from it and never
  hardcodes a key. Name the four rows.
* **The DB viewer's SQLite and PostgreSQL support**, connection strings taken from each app's
  effective config, never typed twice.
* **Scheduled jobs:** WeightRoom's own DB-backed queue with leases (ADR-0010/0029 shape), job
  kinds in v1: FreeWeight suite run, retention trim, backup, model refresh.
* **Alerts:** sources (app down, OOM cap fired — journal match on the ADR-0119 kill, GPU thermal,
  budget ceiling, breaker open), banner, acknowledge, history; no outbound channel.
* **What is out of scope for 1.0:** multiple users, internet exposure, editing docs in the
  browser, providers WeightRoom talks to directly, replacing any app's own UI.

## 7. The plan (`apps/weightroom/development-plan.md`)

Phases with gates; every acceptance criterion demonstrable. Suggested spine — reshape freely,
keep the gates:

0. this row · 1. skeleton, config, DB, TLS + login, `setup` wizard · 2. process control + unified
logs + audit log · 3. telemetry strip + shell (top bar, menus, status) · 4. settings forms over
the schema verbs + doctor · 5. docs viewer · 6. chat (LoadCoach, then PromptCadence, thinking
collapse) · 7. DB viewer + guard · 8. model catalog + costs + backups/migrations · 9. jobs +
alerts + prompt editor · 10. hardening, performance, docs, `1.0.0`.

Then write rows **W1–W10** — plus the four `config schema --json` rows and the MirrorWall 0.3
row, ordered so W4 has the schemas it needs — into **a new roadmap file of their own**,
`docs/roadmap/weightroom-work.md` (§7.1), and one kickoff prompt per row under
`docs/history/prompts/w<N>-….prompt.md`.

### 7.1 One outstanding-work file per arc — a new convention, started here

`outstanding-work.md` has carried every row since A1 and is now ~300 lines of mixed arcs. From
this row on, **each arc the operator starts gets its own file**, same master-table shape:

* Create `docs/roadmap/weightroom-work.md` with the same section skeleton as
  `outstanding-work.md` (§1 master table, §2 standing preamble — link to the original's rather
  than copying it, §3 load-bearing orderings, §4 the human/ops checklist, §5 milestone map) and
  the columns `# | Phase → ships | Model · effort | Runs after | Work overview — and required
  reading | Why this model`. Row W0 moves there from `outstanding-work.md` (marked done with its
  handoff when this row finishes); W1+ are written there and nowhere else.
* In `outstanding-work.md`: replace the W0 row with one line under a new §1.2 "Arcs with their
  own file" — `**WeightRoom** → roadmap/weightroom-work.md (rows W0–W10; started 2026-09-09)` —
  and add the convention sentence to its preamble: a new arc starts a new
  `roadmap/<arc>-work.md`; `outstanding-work.md` keeps only the pre-existing rows and the index of
  arc files.
* `docs/roadmap/README.md` (create if absent) lists every work file with its status line and the
  date it started, so a person opening `roadmap/` sees the arcs first.
* Status marks, handoff links and the `docs/history/handoffs/<ROW>_HANDOFF.md` rule are identical in the
  new file; a kickoff prompt's **Row:** line names the file it lives in.

## 8. Finish line for this row

* ADR-0123 … 012x accepted and indexed; `apps/weightroom/*` written and mirrored to nowhere
  else (WeightRoom is its own canonical home); `architecture/master-architecture.md` amended
  with the fifth application (additive, ADR-0038 precedent); `executive-summary.md` and the
  dependency diagrams show it; `MEMORY_SAFETY.md` §2.2 and `LAN_ACCESS.md` rewritten;
  `expose_on_lan.sh` deleted; `CLAUDE.md` at the workspace root updated for the new paths.
* The repository moved, skeleton in place, `ruff`/`mypy`/`lint-imports` green on the empty
  package, CI workflow present.
* `docs/roadmap/weightroom-work.md` exists with W0 (done) and W1+ (open); `outstanding-work.md`
  §1.2 indexes it; `docs/roadmap/README.md` lists the arc files.
* `docs/history/handoffs/W0_HANDOFF.md`: decisions taken, the PyPI-name confirmation, the symlink, what
  the interview left open and how it was closed.
