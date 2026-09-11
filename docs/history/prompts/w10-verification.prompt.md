# Verification — WeightRoomGym `1.0.0` against spec §20, from an independent device

Verify `wr-gym 1.0.0` (WeightRoom `6b1b290`, row W10) against
[`apps/weightroom/spec.md`](../../apps/weightroom/spec.md) §20 and decide whether it is **ready**
or **not ready**. Run from a device that is **not** the reference machine — a laptop or a phone
on the same LAN — against the reference machine (`jordan-main`, `10.77.10.84`), where the
console runs as `weightroom.service` and the four applications as their units. You may read
anything, run anything against the console, open a browser, and stop and start applications from
the console; you may **not** edit code, commit, push, tag or publish, and you may not change the
reference machine's configuration except through the console's own pages. If a claim below is
false, that is a finding, not something to fix.

**Model:** Fable 5.1, max effort. Nobody is available to answer a question: decide, and say what
you assumed. **Reporting *not ready* is a success if it is true.** The implementer's report
(`history/handoffs/W10_HANDOFF.md`) says every local gate is green; a passing suite is weak
evidence, and the highest-value thing you can do is find the criterion the local evidence never
reached — the ones §20 states for a client that is not the host.

## The eleven criteria, and what the local run could not show

| # | Criterion | Local evidence (W10 handoff §4) | What only this run can show |
|---|---|---|---|
| 1 | `pip install wr-gym && wr-gym setup && wr-gym serve` → an HTTPS console on the LAN, a trusted certificate on **one client device**, a login, four applications as units | Clean-venv install of the wheel; the console live as `weightroom.service`; `curl --cacert` from the host | **The phone step**: `http://10.77.10.84:8770/trust` on the device, the root installed in the *CA* store, `https://jordan-main.local:8769` with the padlock, the login, the shell — this is also **WR-α** (`history/handoffs/W1_HANDOFF.md` §7 item 1) |
| 2 | Every state-changing action writes an `audit_log` row | `tests/security/test_audit_routes.py` enumerates the routes | Do three things from the device (start an application, save a setting, acknowledge an alert) and find each on the Audit page with your operator's name |
| 3 | A raw write fails on each guard condition alone and succeeds with all five | `tests/integration/test_db_guard.py`, unit tests | One dry run and one refused write (the application running) from the device's browser; the refusal names condition 1 |
| 4 | A runtime key takes effect without a restart; a file key round-trips with comments intact; a security key re-authenticates | `tests/integration/test_settings_routes.py` | Change `alerts.interval_seconds` on the console's own page (live), a LoadCoach file key (the `.bak` and the comment), and watch a security key ask for the password |
| 5 | The forms contain no hardcoded key | `tests/unit/test_settings_forms.py` over each schema golden | Read one page against the application's `config schema --json` from the host and confirm a field you pick at random is there |
| 6 | Chat streams from LoadCoach and PromptCadence, thinking collapses, routing and cost under each reply, an inline PromptCadence approval; no provider contacted | `tests/security/test_chat_isolation.py`; the W6 demonstration | One conversation per backend from the device; the thinking fold; the routing decision; an approval granted inline (a hybrid trajectory needs a remote tier configured — say so if none is) |
| 7 | Stopping every application leaves the console serving, each page *stopped* with a start button | `tests/integration/test_apps_routes.py` | Stop all four from the device; walk the four tabs; start them again — **then leave them running** |
| 8 | An unknown `alembic_version` degrades that application's pages by name and nothing else | The `loadcoach-unknown-9999` fixture | Not demonstrable live without corrupting a database — record it as fixture-only |
| 9 | The trust listener serves `/root.crt` and the instructions and nothing else; the console port serves no plain HTTP | `curl` from the host (handoff §4) | The same from the device, including `http://10.77.10.84:8770/login` → `404` |
| 10 | The full suite passes with no application, no systemd, no GPU and no network | `unshare -rn pytest` on the host; the fake `systemctl`; the network-isolation e2e | Run the suite on your device in a clean venv from the wheel's `[dev]` extra if you have one; otherwise record the host run |
| 11 | Every WeightRoomGym gold standard (`standards/gold-standards.md` §2) is met | `tests/unit/test_packaging.py`, `.importlinter`, the registries | Read §2's bullets against what you saw |

## Ground state

```bash
cd ~/ai/suite/WeightRoom && git log --oneline -1          # 6b1b290
cat src/weightroom/__about__.py                           # 1.0.0
systemctl --user status weightroom.service                # active, ExecStart .venv/bin/wr-gym serve
~/ai/suite/WeightRoom/.venv/bin/wr-gym trust              # the root fingerprint to compare on the device
~/ai/suite/WeightRoom/.venv/bin/wr-gym doctor             # 1 notice, 1 unknown, 27 ok at W10
```

The operator's account and password are the operator's. `docs/setup.md` §4 and
`docs/LAN_ACCESS.md` §3 are the trust steps per OS; `docs/troubleshooting.md` §3 is what to do
when the padlock does not appear.

## The verdict

Write it **verbatim** into `history/handoffs/W10_HANDOFF.md` §5 — `ready` or `not ready`, the
device (make, OS, browser), the date, and for each criterion what you saw. A *not ready* is
followed by one new row per finding in `roadmap/weightroom-work.md`, never by a fix in this run.
WR-α and WR-1.0 (`weightroom-work.md` §5) are declared by the operator on a *ready*.
