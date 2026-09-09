# W0 Handoff — WeightRoomGym Phase 0: the ADRs, the spec, the plan, the repository

**Row:** W0 of [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md) (Fable 5.1 · attended).
**Date:** 2026-09-09. **Kickoff:** [`w0-weightroom-phase-0.prompt.md`](w0-weightroom-phase-0.prompt.md).
**Ships:** no code. Six ADRs (0123–0128), six `apps/weightroom/` documents, the repository move and
skeleton, the architecture amendments, the arc's work file, fifteen kickoff prompts.

## 1. What was built, by commit

| Repository | Commit | What |
|---|---|---|
| `WeightRoomGym` (was `docs`) | `5af4603` | `git mv` of every top-level file and directory into `docs/`; checkout renamed `~/ai/suite/WeightRoom`; `~/ai/suite/docs → WeightRoom/docs` symlink; skeleton (`pyproject.toml` dist `wr-gym`, `src/weightroom/__about__.py` `0.0.0`, one test, `.importlinter`, CI, `release.lock`, README, CHANGELOG, SECURITY, CONTRIBUTING, LICENSE); `compatibility-matrix.yml` and `finish_n_rows.sh` follow the new depth |
| | `7aa5da2` | ADRs 0123–0127; index; *Amended by* notes on ADR-0014 and ADR-0026 |
| | `6a46772` | `apps/weightroom/{spec,api,data-model,design,risks,development-plan}.md` |
| | `031d283` | Master architecture (§1.1, §2, §3, §8.2.2, §11 items 22–24), executive summary, boundary rules §3.2, gold standards (§1.1 row, §2 section), traceability matrix, risk register (S14, S15), master roadmap §9, docs README; `MEMORY_SAFETY.md` §2.2; `LAN_ACCESS.md` rewritten; `scripts/expose_on_lan.sh` deleted |
| | `5dd75ee` | `roadmap/weightroom-work.md`, `roadmap/README.md`, `outstanding-work.md` §1.2 + convention; prompts `w1`–`w10`, `ws1`–`ws4`, `wm` |
| `FreeWeight` | `e125dee` | `scripts/sync_docs.py` reads `WeightRoom/docs` |
| `FreeWeight`, `LoadCoach`, `IdeaPress`, `PromptCadence` | `eddb2d3`, `45bde87`, `8ff3969`, `4ffe113` | `docs/LAN_ACCESS.md` and `docs/MEMORY_SAFETY.md` re-mirrored byte-identically (they were mirrors; the workspace `CLAUDE.md` named only `LLAMACPP_SETUP.md`, which was wrong — corrected in the root `CLAUDE.md` text below) |
| workspace root (unversioned) | — | `CLAUDE.md` updated (tree, mirror rule, the exception, the per-arc convention); the pre-edit copy is in this session's scratchpad |

Nothing pushed, tagged or published. Gate on the empty package: `ruff format --check .`,
`ruff check .`, `mypy src tests`, `lint-imports` (3 contracts kept), `pytest` (1 passed) — all
green on **Python 3.14.4** (`WeightRoom/.venv`); `pip-audit` on `release.lock` clean.

## 2. Decisions taken in this row (beyond the interview's)

The interview's D1–D16 landed where the kickoff §2 table said. What the spec and ADRs had to
settle on top:

* **Names, decided by the operator at the close of the row:** product **WeightRoomGym**,
  distribution and CLI **`wr-gym`**, import name `weightroom`, env prefix `WEIGHTROOM_`, config
  and data roots `wr-gym`, checkout `~/ai/suite/WeightRoom`, GitHub remote still
  `OpenWeight-Gym`. The row had proposed `openweight-gym` (free on PyPI; `weightroom` is taken by
  an unrelated `0.0.1`); the operator chose otherwise after the §5 incident.
* **"htmx" — decided at the close of the row: the library.** The row first read D2 as the
  patterns only (ADR-0020 had rejected htmx as a dependency); the operator, given the trade-offs,
  chose adoption. ADR-0128: MirrorWall 0.3 vendors htmx and its SSE extension, opt-in per page,
  behaviour still in modules; ADR-0020 and ADR-0123 rule 7 carry *Amended by* notes.
* **`modelrack` is imported** (read-only: residency, discovery) despite the kickoff §1 listing
  five packages: the gold standard "one Ollama client in the suite" outranks a sixth-package
  omission in a prompt; `generate` is never called and a grep test says so. `loadledger[sql]`
  is imported for the mounted ledger tables' shapes. `toolyard`/`cutctx`/`commissioner` are
  forbidden by import-linter (ADR-0123 rule 4).
* **Dependency set = FreeWeight's ten + `cryptography` + `mistune`** (12). No `argon2`
  (`hashlib.scrypt`), no `python-systemd` (`journalctl -o json`), no markdown-it, no `psutil`
  (`sweatmeter`), no cron library (stdlib parser), FTS5 for search.
* **Auth:** one account, scrypt (`n=2**15, r=8, p=1`, params stored), server-side sessions,
  `__Host-` cookie `Strict`, 12 h idle / 7 d absolute, 5 logins/min/address, `POST /reauth`
  with a 5-minute window for security keys and guarded writes; **no bearer tokens, no roles**.
* **CA:** `$XDG_CONFIG_HOME/wr-gym/tls/`, ECDSA P-256, root 10 y, leaf 398 d renewed under
  30 d, SANs = hostname/.local/LAN IPs/localhost; **no plain HTTP on 8769**; a trust listener on
  **8770** serving exactly `/root.crt` and `/trust`; `tls init|renew|rotate|show`, `trust`.
* **Ollama restart = polkit rule**, printed by the wizard, installed by the operator with
  `sudo`; WeightRoomGym never runs `sudo`; without the rule the restart is the printed command.
  Sudoers rejected (grants a command; polkit grants a unit + verb).
* **Unit files carry the memory cap** for `freeweight` and `loadcoach` (ADR-0125 rule 1);
  `MEMORY_SAFETY.md` §2.2's `systemd-run` wrapper stays for shell runs.
* **App tokens:** `write` on LoadCoach, `write,approve` on PromptCadence (approvals are their own
  scope, ADR-0049), stored under `<config>/secrets/` by file reference.
* **Schema document** (ADR-0127): `config schema --json` + `config validate --file`;
  `security_keys` editable from WeightRoomGym after re-authentication (ADR-0117's "browser session
  cannot move the boundary" is kept for the applications and consciously not for the operator's
  console — rule 6 says why).
* **Never-writable tables**, by name per application (ADR-0124's table): migration state,
  credentials, runtime-settings rows, hashed identity (`machines`, `models`, `runtime_profiles`,
  `adapters`, `model_descriptors`), queue/lease state, governance records, money, event logs.
* **Jobs:** ADR-0010/0029 shape, one worker thread, six kinds; **alerts:** five sources, one open
  per subject, no outbound channel; **DB viewer:** SQLite and PostgreSQL from each application's
  own `storage.database_url` read out of its schema document.
* **Out of scope for 1.0:** multiple users, internet exposure, in-browser docs editing, providers
  for chat, replacing any app's UI, a second host, a WeightRoomGym API token for automation.
* **Row models:** W1/W6/W7/W10 Opus and never overnight; W2/W4/W9 Opus; W3/W5/W8/WM/WS1–4
  Sonnet high.

## 3. What the kickoff got wrong, or did not know

1. **§4.1 was self-contradictory** ("except … `README.md`" and then "`README.md → docs/README.md`").
   Read as: move it, write a new root `README.md` for the application repository. Done.
2. **`suite-flowchart.drawio`** was not in §4.1's list; moved with everything else.
3. **`import-linter` cannot declare a contract over a module that does not exist.** The layers
   contract is written with optional (parenthesised) layers; `web-cli-independence` and
   `domain-purity` are deferred to W1 with the exact text to restore in `.importlinter`'s comments.
4. **`LAN_ACCESS.md` and `MEMORY_SAFETY.md` are mirrored into all four application repositories**
   (byte-identical, proven with `cmp` against the pre-rewrite copies). The workspace `CLAUDE.md`
   said only `LLAMACPP_SETUP.md` was; it now says otherwise.
5. **FreeWeight's `sync_docs.py --check` was already failing before this row** (its mirror keeps
   links the script's `delink` would strip — a pre-existing inconsistency between the script's
   convention and the byte-identical rule). Not touched here; a FreeWeight housekeeping item.
6. **430 links under `history/` were broken before the move and are unchanged by it** — kickoff
   prompts and handoffs written with workspace-relative `docs/…` targets. The move introduced no
   new broken link (checked before/after over 3 128 links). Left alone; they are history.
7. **The reference machine has not applied `MEMORY_SAFETY.md` §2.1**: `ollama.service`'s override
   still sets `OLLAMA_CONTEXT_LENGTH=112000`, `OLLAMA_HOST=0.0.0.0:11434`, and `MemoryMax=infinity`.
   No `systemd --user` units exist for any application; `Linger=yes`. ADR-0125 and the W2 prompt
   treat this as the failing fixture; `LAN_ACCESS.md` §5 names the `0.0.0.0` bind.
8. **Local Python is 3.14.4**; `release.lock` was cut on 3.14 (W1 re-cuts both locks on 3.13,
   the CI resolution interpreter, per the sibling repositories).
9. The design canvas's chosen artboard uses MirrorWall's **existing dark palette exactly**; the
   brief's deltas are scale, density, fonts and four status tokens, not colours.

## 4. The symlink, and what still resolves through it

`~/ai/suite/docs → WeightRoom/docs` stays until **row W10** removes it (named in
`weightroom-work.md` §4 and the W10 prompt). Still saying `~/ai/suite/docs` or `docs/` at the
workspace root, all harmless while the symlink exists: `IdeaPress/pyproject.toml` and
`PromptCadence/pyproject.toml` (ruff-exclude comments), `FreeWeight/PHASE11_ISSUES.md`, every
`history/*.prompt.md` before this row, and the paths line in `outstanding-work.md` (now says
both). `FreeWeight/scripts/sync_docs.py` and `docs/scripts/finish_n_rows.sh` were rewritten and
no longer need it. The root `install_local.sh`/`launch.sh` never referenced it.

## 5. The working tree at 15:14

While this session was writing the kickoff prompts, twelve files in `WeightRoomGym` and one or two
in each of the four application repositories were modified in place at **15:14:16 PDT** — a
mechanical substitution `openweight-gym → weightroom` and `OpenWeight-Gym → weightroom` (it
produces "`weightroom` because `weightroom` is taken on PyPI" in ADR-0123 rule 1, and rewrites a
historical GitHub URL in `IdeaPress/CHANGELOG.md` to `JPKell/weightroom`). The journal shows a
VS Code event at 15:14:15 and a Codex code-mode host running inside VS Code; it was not this
session. Files written before 15:14 and committed after it (`weightroom-work.md`, the first nine
prompts) carried the substitution into commit `5dd75ee`; the rest was reverted with
`git checkout --` in all five repositories once the operator had decided the names (§2), and the
patch is kept at `<scratchpad>/stray-rename-weightroom-2026-09-09T1514.patch`. This is the third
recorded instance of the pattern the workspace `CLAUDE.md` describes (interactive activity on a
tree a run holds).

## 6. Open for the operator

1. ~~The distribution name.~~ **Decided** (§2): WeightRoomGym / `wr-gym` / `weightroom`; applied in
   the row's closing commit across the five repositories.
2. ~~"htmx"~~ **Decided**: adopted (ADR-0128).
3. Apply `MEMORY_SAFETY.md` §2.1 on the host; decide whether Ollama stays on `0.0.0.0`.
4. Reserve the PyPI name before W1 publishes anything.

## 7. What runs next

W1 (Opus, attended-review, never overnight) can start now; **WS1–WS4 and WM are independent of
W1–W3 and can run in parallel on Sonnet** — all five are needed before W4 (WS) and W3 (WM).
Each application's head migration at this row, for `known_revisions`: FreeWeight `0009`,
LoadCoach `0015`, IdeaPress `0010`, PromptCadence `0011`.
