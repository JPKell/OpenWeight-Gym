# N1 handoff — dependency diagrams reconciled, `pydantic-settings` dropped from four specs

**Row:** N1 of [outstanding work §1](../roadmap/outstanding-work.md), from M1's findings 2 and 3.
**Run:** 2026-09-09, attended. Documentation only; no package or application code moved.

## What changed

* `architecture/master-architecture.md` §2: `IP --> MR & WD & MW & SS & CC & LL & SC & TY`. The
  frozen document gained a **Reconciled 2026-09-09** line in its header naming the records that
  declare each new arrow (J1/J2's ADRs for `cutctx`, `loadledger`, `commissioner`; ADR-0116 for
  `toolyard`) and ADR-0114 as the rule the arrows were checked against. Additive, per the
  ADR-0038 amendment precedent.
* `architecture/executive-summary.md` dependency graph: `TY` added to IdeaPress's arrow.
* `apps/{freeweight,loadcoach,ideapress,promptcadence}/spec.md` §5: `pydantic-settings` removed
  (ADR-0114 decision 4). One word in each.
* All four `spec.md` mirrors re-copied, byte-identical (`cmp`).

## Checked against `pyproject.toml`

Every application's arrows match its runtime set: FreeWeight and LoadCoach → ModelRack,
SweatMeter, WeightsDB, MirrorWall, SetSpec; IdeaPress → those minus SweatMeter, plus CutCtx,
LoadLedger, Commissioner, ToolYard; PromptCadence → WeightsDB, MirrorWall, SetSpec, CutCtx,
ToolYard, LoadLedger, Commissioner and deliberately not ModelRack/SweatMeter (ADR-0045).

## Found, not done

* `FreeWeight/scripts/sync_docs.py --check` reports all seven `apps/freeweight/*.md` mirrors stale,
  including six this row did not touch, while `cmp` finds every one byte-identical to the
  canonical copy. The script's rendering (link flattening) and the suite's byte-identical mirror
  rule disagree; pre-existing, not introduced here. Worth one small row: either the script mirrors
  verbatim or the rule changes.
* The specs' third-party lists are still not the full enumerated set of ADR-0114 — FreeWeight's
  omits `tomlkit`, `python-multipart`, `httpx`; LoadCoach's omits `tomlkit`. Outside this row's
  one-word brief; a follow-up if ADR-0114 is to be read strictly.
