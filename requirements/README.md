# Lockfiles

Exact, hash-verified pins for this repository's **own** CI and release pipeline, required by
Packaging and Release Standards §4 and Security Standards §11.

| File | Contents | Used by |
|---|---|---|
| `release.in` / `release.lock` | The build and publish chain (`build`, `hatchling`, `twine`) | `release.yml`, and CI's `build` job |
| `ci.lock` | Runtime dependencies plus the `dev` and `postgres` extras | Every CI job that installs this package |

`release.lock` is committed at W0 so the `security` job has something to audit; `ci.lock` is cut
at **row W1**, when the package first imports a dependency, and CI switches from `pip install -e
".[dev]"` to `pip install --require-hashes -r requirements/ci.lock` at the same time. Regenerate
either after any change to `pyproject.toml`'s dependencies or extras:

```bash
pip install "pip-tools==7.6.1"
pip-compile --generate-hashes --extra dev --extra postgres -o requirements/ci.lock pyproject.toml
pip-compile --generate-hashes -o requirements/release.lock requirements/release.in
```

They do **not** define what a consumer installs: `pip install openweight-gym` resolves the ranges in
`pyproject.toml`.
