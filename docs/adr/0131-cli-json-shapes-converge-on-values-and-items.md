# ADR-0131 — Two CLI JSON shapes converge: `config show` says `values`, a listing says `items`

**Status:** Accepted (2026-09-09)
**Amends:** [CLI Standards](../standards/cli-standards.md) §9 and §11 (the shapes are now written
down); IdeaPress `config show --json`; LoadCoach `token list --json`.
**Relates to:** [ADR-0129](0129-weightroom-reads-both-version-payload-shapes.md) (the same kind of
divergence, on `/version`, and the recipe this record follows),
[Packaging and Release Standards](../standards/packaging-and-release-standards.md) §3.2 (which
this record makes a deliberate exception to), [API and Contract Standards](../standards/api-and-contract-standards.md)
(the collection envelope).
**Found:** row W4, on the reference machine — `wr-gym doctor` and IdeaPress's Overview page.
**Source:** operator decisions of 2026-09-09, after W4.

## Context

WeightRoomGym is the first program that reads every application's CLI output by machine, and at
row W4 it found two places where the applications disagree on a JSON shape no document had named:

| Output | FreeWeight | LoadCoach | IdeaPress | PromptCadence | WeightRoomGym |
|---|---|---|---|---|---|
| `config show --json`, the effective-configuration block | `values` | `values` | **`settings`** | `values` | `values` |
| `token list --json`, the list | — | **`{"tokens": […]}`** | — | `{"items": […]}` | — |

The first is not a breach of any written rule — CLI Standards §9 names the verb and not its
fields — but it is one application in five, and it had already cost something: IdeaPress's
Overview in WeightRoomGym read `values`, found nothing, and showed dashed figures from row W3 until
the doctor found it at W4.

The second **is** a breach. API and Contract Standards wraps every collection in `items`, and CLI
Standards §11 requires `--json` output to use the HTTP API's vocabulary. PromptCadence conforms;
LoadCoach does not.

Two neighbouring differences are **not** drift and are not changed here:

* **Revocation.** Both applications already carry `revoked_at` (a timestamp, `null` while
  active). PromptCadence also prints `active`. Nothing to converge.
* **`scope` against `scopes`.** LoadCoach's scopes are cumulative levels (`read` ⊂ `write` ⊂
  `admin`), so one string is the whole answer; PromptCadence's are an independent set (`write`,
  `approve`). Different models, correctly different fields.

## Decision

1. **`<app> config show --json` is `{"config_path", "sources", "values", …}`.** The effective
   configuration is `values`. Additional top-level fields (IdeaPress's `config_file_used`) are
   allowed. IdeaPress renames `settings` → `values`.
2. **Any `--json` listing is the collection envelope: `{"items": […]}`**, optionally with `page`
   and `total` as the HTTP API has them. LoadCoach's `token list --json` renames `tokens` →
   `items`. Record shapes inside `items` are unchanged.
3. **Both are written into CLI Standards** — §9 gains the `config show --json` shape, §11 gains
   the listing envelope — so the next application is checked against a sentence rather than
   against whichever neighbour it copied.
4. **Released as minor versions: IdeaPress `1.5.0`, LoadCoach `1.4.0`.** Packaging and Release
   Standards §3.2 counts "changing a serialized shape" as breaking, and §3 makes a post-1.0 break a
   **major**. The operator decided otherwise, explicitly, with the reason: *there are no users of
   these outputs yet*. That is recorded here as a deliberate, scoped exception — these two renames,
   in these two releases — and not as a change to §3.2, which stands for everything else.
5. **WeightRoomGym keeps reading both names for one console major**, as ADR-0129 rule 3 already
   requires of a convergence: an operator upgrades the console and the applications on different
   days. The two readers (`services/overview.py`, `services/tokens.py`) cite this record.

## Consequences

*Positive.* Every application's `config show --json` and every `--json` listing now has one shape,
and the shapes are written down. LoadCoach is back inside API and Contract Standards.

*Negative.* A script written against IdeaPress ≤ 1.4.1 or LoadCoach ≤ 1.3.1 breaks on a minor
upgrade, which semantic versioning says must not happen. The operator accepted that on the basis
that no such script exists. The next time this reasoning is offered it should be re-checked, not
cited: *no users yet* stops being true on a date nobody announces.

*Neutral.* ADR-0129 rule 3 said a convergence release would be "a minor release of each
application that changes". Against §3.2 that was wrong for any rename, and this record does not
make it right — it records the operator's exception for these two. A future convergence of the
`/version` shapes that ADR-0129 describes is a **major** unless the operator decides again.

## Alternatives considered

* **Additive minor: print both names, drop the old one at 2.0.** Conforming to §3.2 and offered.
  Declined by the operator: a duplicated key in every output until a major that is not planned.
* **Two majors, IdeaPress 2.0.0 and LoadCoach 2.0.0.** Conforming and offered. Declined: two
  application majors for two renames with one consumer, and WeightRoomGym's
  `SUPPORTED_VERSIONS` would have flagged both as a version mismatch until a console release.
* **Record only, converge at W10.** Offered. Declined in favour of fixing the source now.

## Revisit when

* **An application's CLI JSON gains a real external consumer** — a published script, a second
  console. From then on a rename is a major, with no exception available on this record's basis.
* **WeightRoomGym's next major.** Drop the `settings` and `tokens` readers.
