# Kickoff — W10: WeightRoomGym Phase 10 — hardening, performance, documentation, `1.0.0`

**Row:** W10 (Opus 5 · xhigh · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W9; the last row of the arc's `1.0.0`.
**Ships:** `wr-gym 1.0.0` prepared (the tag and the `pypi` approval are the operator's);
the operator documentation set; the OpenAPI snapshot; the workspace `docs` symlink removed;
the kickoff prompt for WM2.
**Component:** `~/ai/suite/WeightRoom`; the workspace root for the symlink and `CLAUDE.md`
(unversioned — copy it before overwriting, per the workspace `CLAUDE.md`).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../../apps/weightroom/spec.md) §§14–20 in full; [`development-plan.md`](../../apps/weightroom/development-plan.md)
Phase 10; `standards/security-standards.md` §14; `standards/testing-standards.md`;
`standards/packaging-and-release-standards.md` §4–§6, §10; `standards/gold-standards.md` §2
WeightRoomGym and §4; `history/handoffs/M7_HANDOFF.md` and `history/prompts/m7-verification.prompt.md` (the
verification precedent: an independent run with permission to say *not ready*); every
`W*_HANDOFF.md` and `WS*_HANDOFF.md` (what each row deferred); `history/handoffs/W0_HANDOFF.md` §"The
symlink" (what still resolves through `~/ai/suite/docs`).

## Decisions already taken — do not reopen

* One release, `1.0.0`, over everything W1–W9 built (interview D15); nothing is cut to make the
  date — a criterion that fails is reported, not waived.
* The verification is run **on an independent device** against the reference machine, by a
  session with explicit permission to say *not ready*, and its verdict is recorded verbatim.
* The `docs` symlink at the workspace root is removed by this row; every `~/ai/suite/docs`
  reference in scripts, prompts, `pyproject.toml` comments and the workspace `CLAUDE.md` is
  rewritten to `WeightRoom/docs` (the W0 handoff lists them); the operator confirms nothing else
  on the machine resolves through it before the `rm`.
* Carried from W6 (operator, 2026-09-10; `history/handoffs/W6_HANDOFF.md` §8): PromptCadence's
  `trajectory show` names the approver by its token's name, in text and `--json`, so plan Phase 6
  criterion 2 passes as written; PromptCadence emits `egress.evaluated` when it records an egress
  decision; `promptcadence doctor` checks that LoadCoach answers and accepts the configured token,
  and WeightRoomGym's doctor shows that check on PromptCadence's card. These ride a PromptCadence
  minor released with the arc.
* **The mirror rule is settled by this row** (operator, 2026-09-10; `history/handoffs/W7_HANDOFF.md`
  §8). The workspace `CLAUDE.md` says a component's mirror is byte-identical to `WeightRoom/docs`
  and names `FreeWeight/scripts/sync_docs.py --check` as the executable form of that rule; but
  since 2026-08-28 the script rewrites links that leave FreeWeight's copy into plain text, so
  byte-identical copies report *stale* (seven at W7, all `cmp`-identical). No CI job runs the
  script and no other repository has one. While rewriting the `docs` references, pick one rule,
  make the script and `CLAUDE.md` say the same thing, and leave every mirror passing it.

## Gates

**Gate A — security.** Security Standards §14 item by item in `tests/security/`, plus spec §14's
own rows (session fixation, idle and absolute expiry, logout, `Sec-Fetch-Site`, the trust
listener's refusal of every other route, the guard's five conditions in isolation, the
never-writable list, redaction over every audited action, `sudo` absent); the injection corpus
against chat; a network-isolation e2e. Commit.

**Gate B — performance and degradation.** Every spec §15 budget measured on the reference
machine and asserted under `-m performance`; every degradation the spec names (no systemd, an
application stopped, an unknown revision, no FTS5, no GPU) with a test; the upgrade test from
`0.9.0`. Commit.

**Gate C — documentation and release.** `docs/security.md`, `docs/configuration.md` (generated,
diff-checked), `docs/setup.md`, `docs/troubleshooting.md` aligned with `doctor`, backup/restore,
the local `docs/README.md`; the OpenAPI snapshot committed and byte-tested; `api.md` regenerated
to match it; `CHANGELOG.md` for `1.0.0`; `__about__` `1.0.0`; the release commit. The symlink and
the references. The WM2 kickoff prompt written into `history/` from `design.md` §6 and the row's
line in `weightroom-work.md`. Commit.

**Gate D — verification.** The independent-device run over spec §20; its verdict into
`docs/history/handoffs/W10_HANDOFF.md` and, if *not ready*, the findings as new rows in
`weightroom-work.md` rather than as fixes squeezed into this row.

## Finish line

Gate green, coverage held, `pip-audit` and `gitleaks` clean, `pipx install dist/*.whl &&
wr-gym --version`, one commit per gate, `docs/history/handoffs/W10_HANDOFF.md`, the row marked done,
`roadmap/README.md` and `outstanding-work.md` §1.2 updated with the arc's status. Never overnight.
