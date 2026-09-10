# Lockfiles

Exact, hash-verified pins for this repository's **own** CI and release pipeline, required by
Packaging and Release Standards §4 and Security Standards §11.

| File | Contents | Used by |
|---|---|---|
| `ci.lock` | Runtime dependencies plus the `dev` and `postgres` extras: the whole test, lint, type and boundary toolchain | Every CI job that installs this package |
| `release.in` / `release.lock` | The build and publish chain (`build`, `hatchling`, `twine`) | `release.yml`, and CI's `build` job |

They do **not** define what a consumer installs: `pip install wr-gym` resolves the ranges in
`pyproject.toml`. They exist so a green build stays green and `pip-audit` audits what the build
actually used.

## Regenerating

Run after any change to `pyproject.toml`'s dependencies or extras, and commit the result:

```bash
python3.13 -m venv /tmp/lock && /tmp/lock/bin/pip install "pip-tools==7.6.1"
/tmp/lock/bin/pip-compile --generate-hashes --extra dev --extra postgres -o requirements/ci.lock pyproject.toml
/tmp/lock/bin/pip-compile --generate-hashes -o requirements/release.lock requirements/release.in
```

## Interpreter

Both locks were cut at row W1 (2026-09-09) on **Python 3.13** with pip-tools 7.6.1 — the CI
resolution interpreter, as the sibling repositories do. Every pin's `requires-python` admits
3.12, and no pin is CPython-ABI-specific, so the same lock installs on both supported versions;
the 3.14 early-warning job resolves from ranges instead. (`release.lock` was first cut at W0 on
the local 3.14; W1 re-cut it.)

## The PostgreSQL driver is in `ci.lock`

`psycopg[binary]` is the optional `postgres` extra a consumer installs to talk to a real server;
it is locked here so the `db-matrix` job needs no extra install on top of the lock.

## Coverage measures the installed package, not the checkout

CI installs the built distribution (`pip install . --no-deps`), not an editable checkout, so
`[tool.coverage.run] source` in `pyproject.toml` names the importable package `weightroom`, and
`[tool.coverage.paths]` maps `src/weightroom` and the site-packages copy together.
