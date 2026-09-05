# M5 re-verification — LoadCoach 1.0.0, after the closeout

You are Fable 5, re-verifying the M5 closeout that acted on your fourteen findings of 2026-08-30.
You must still be able to say **not ready**. Verify, do not trust: reproduce each closed finding's
original failure mode and confirm it no longer reproduces, then check nothing you previously
confirmed has moved. The closeout's full record is `~/ai/suite/M4_HANDOFF.md`, section
`# M5 Closeout — verification findings (LoadCoach 1.0.0)`, entries `M5C-1` … `M5C-15`.

## Ground state you should find

```
cd ~/ai/suite/LoadCoach && git log --oneline -1     # eeef0f4 fix(db): migration 0006 is valid on PostgreSQL …
git status --short                                  # clean
cat src/loadcoach/__about__.py                      # __version__ = "1.0.0"
.venv/bin/python --version                          # 3.14.4 (the interpreter is named on purpose — F13)
.venv/bin/pytest -q -m "not live and not performance"   # 807 passed, 2 skipped  ← the BARE console script
.venv/bin/pytest -q -m contract                     # 25 passed
```

The runner: run id **33334510805** on `eeef0f4` — **every job `success`**, the
`continue-on-error` `tests-314-early-warning` included. Check it yourself:
`curl -s https://api.github.com/repos/JPKell/LoadCoach/actions/runs/33334510805/jobs`.

The tag has NOT been laid; `TAG_APPROVED: no` still stands.

## Per finding: repeat your reproduction, expect it closed

**F1** — run the bare console script (above) and your Docker line:

```
docker run --rm -v ~/ai/suite/LoadCoach:/src:ro python:3.12-slim bash -c \
 "cp -r /src /work && cd /work && pip install -q --require-hashes -r requirements/ci.lock && pip install -q . --no-deps \
  && pytest -q -m contract && pytest -q -m 'not live and not performance'"
```

Expect 25 contract and **807 passed / 2 skipped** (not 796: eleven closeout tests were added, and
your Docker line first exposed a GPU-dependent accessibility fixture — M5C-14 — that is now
pinned). Two findings of the closeout's own are worth your falsification too: M5C-14, and
M5C-15 — migration 0006's `reliability_stats` CHECK constraint left the reserved word `window`
unquoted, a PostgreSQL syntax error no SQLite run could see; reproduce with a real
`postgres:16` (`WEIGHTSDB_REQUIRE_POSTGRES=1`,
`WEIGHTSDB_POSTGRES_URL=postgresql+psycopg://weightsdb:weightsdb@localhost:5432/weightsdb_test`,
`pytest -m 'not live and not performance' tests/integration` → 232 passed).

**F2** — your arrangement is now a permanent test:
`.venv/bin/pytest -q tests/integration/test_breaker_probe.py` (3 tests). To re-falsify, revert the
gate (`git revert --no-commit 7d5b032` or stub `CircuitBreakers.probe_busy` to return `False`) and
watch `test_a_half_open_model_admits_exactly_one_probe_across_two_workers` fail with `assert 2 <= 1`.
Also check the deferral half: the losing job must end `COMPLETED` via `PROBE_IN_FLIGHT` /
`waiting_resources`, never `FAILED`.

**F3** — open the breaker on the only model through `app.state.queue_runtime.breakers.update`, then:
`POST /route` and `POST /generate` must both answer 422 `NO_ELIGIBLE_MODEL` with the candidate's
reason `recently_failing` (tests: `tests/integration/test_breaker_sync_path.py`, 5 of them, including
probe marking observed mid-flight from `on_chunk` and a foreign probe refused with the provider never
called). `loadcoach route explain --json` must carry `breaker_state_unavailable` in `flags`.

**F4** — on a real socket if you wish: spend the failure budget through forged
`X-Forwarded-For` from an untrusted peer — the header must be ignored (correct token from the same
peer gets 429). Then with `[server] trusted_proxies = ["<peer's network>"]`: the forged client is
braked, its neighbour with a correct token is not, chains resolve to the last untrusted hop
(tests: `tests/security/test_rate_limit.py`, 9). The keying decision (per address, never per
credential) is recorded in M5C-4 and api.md §11.

**F5** — nothing was weakened: confirm the cookie flags are unchanged, then check the three
disclosures — api.md §11, `docs/security.md`, and the 401 page itself ("This form needs HTTPS or
loopback") — and that `bootstrap()` on a non-loopback bind without `trusted_proxies` logs
`server.plain_http_exposure` (test: `test_a_non_loopback_bind_without_a_proxy_warns_at_startup`).
Your Chromium reproduction on a plain-HTTP LAN bind should behave identically to before — that is
now the documented contract, not a defect.

**F6** — `/jobs/{id}` for a completed job: the Explanation paragraph holds real
`<a href="/routing/…">` and `<a href="/api/v1/jobs/…/explanation">` anchors; `&lt;a href=` appears
nowhere in the page. At 375 px neither `/jobs/{id}` nor `/system` scrolls horizontally
(`document.documentElement.scrollWidth <= window.innerWidth`) — the fix is a stopgap
`.kv-list dd { overflow-wrap: anywhere; }` in both pages' heads, recorded as a MirrorWall 0.2.1 item.

**F7** — routing §5.1 (both copies, `cmp` them): the production-evidence row says *never a
capability score*, the closing sentence says *guarded rather than self-improving*, and
`docs/adr/0037-production-evidence-never-raises-capability-scores.md` exists, is indexed in the ADR
README, and records M5-1's three reasons plus the exploration-routing deferral.

**F8–F11** — `discover_models(…, principal=WRITER)` raises `InsufficientScope` before any write
(the scope list in `test_scopes.py` is nine); a scrubbed job's page and document say "content
removed by retention" and spec §14 states the 24-hour default; spec §17, api.md §1 and
`GET /api/v1/health` agree on five components (`test_the_documented_health_component_lists_match_the_endpoint`
parses the documents); the F11 wrap rule is asserted on both pages.

**F12** — re-measure over a real socket:
`.venv/bin/pytest -m performance tests/performance/test_streaming_gap.py -s` serves the app under
uvicorn on loopback at a real 5 ms/token cadence. Expect added-latency p95 ≈ 1–3 ms (closeout
measured 1.29 ms; at the old 10 ms poll the same harness reproduced your 10.2 — it printed 10.34).

## What you previously confirmed — check it has not moved

Claims 1, 2, 4, 5, 7, 8, 9, 10, 11, 12, 13 as before. The closeout's evidence that nothing
regressed: 807 passed / 2 skipped under the bare `pytest` and `python -m pytest` alike, coverage
91.72 % (floor 85), 25 contract, 230/2 integration alone, the whole suite under `unshare -rn`, the
Docker 3.12 line, and the performance suite (13 passed) with warm routing 15.1 ms median / 32.0 ms
max against the 20 ms budget — the figure you flagged as tightest; re-measure it.

## Verdict

*Explainable*, *durable*, *secure*, and now *CI green on the real runner* — the remaining human
step is `TAG_APPROVED` and the `v1.0.0` tag. Say **ready** only if every reproduction above stays
closed and nothing confirmed has moved; otherwise say **not ready** and number your findings F1′,
F2′, …
