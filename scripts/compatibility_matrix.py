#!/usr/bin/env python3
"""Cross-repository compatibility matrix cell runner.

Proves packaging-and-release-standards.md §7's compatibility matrix at one cell: pin an
application at its latest PyPI release plus every suite package it declares, at either the
**lowest** or **highest** version each of its dependency ranges admits, into a clean venv, and
report whether the install and (where the sdist ships them) the contract/e2e tests pass.

Pins are derived from the application's *published sdist* on PyPI, never from a local checkout
(``pip download --no-deps --no-binary :all: <app>==<version>`` then read ``pyproject.toml``) --
the whole point of the matrix is to test what a `pip install` actually gets a consumer, not what
this workspace happens to have checked out.

Stdlib + ``pip`` subprocess only, by design (no ``packaging``, no ``requests``): this script must
run standalone in a bare ``python -m venv`` with nothing pre-installed, exactly like the consumer
it is impersonating.

Usage:
    python scripts/compatibility_matrix.py <app> <lowest|highest> [--workdir DIR] [--keep]

Exit code is 0 if the cell resolves, installs and (when tests ship) passes; 1 otherwise. A cell
that cannot even be pinned (no published version satisfies a declared range) is reported as a
failure with the reason, never silently skipped -- that is the finding this script exists to
surface, per row L6's instructions.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
from pathlib import Path

APPLICATIONS = ("freeweight", "loadcoach", "ideapress", "promptcadence")

# The ten suite packages a dependency line might name. Distribution names, lowercase.
SUITE_PACKAGES = frozenset(
    {
        "baseaicore",
        "setspec",
        "modelrack",
        "sweatmeter",
        "weightsdb",
        "mirrorwall",
        "loadledger",
        "cutctx",
        "toolyard",
        "commissioner",
    }
)

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(\[[^\]]*\])?\s*(.*)$")
SPEC_RE = re.compile(r"(>=|<=|==|!=|>|<)\s*([0-9][0-9A-Za-z.\-+_]*)")


def pypi_metadata(name: str) -> dict[str, object]:
    """Fetch a package's PyPI JSON API document.

    Args:
        name: PyPI distribution name.

    Returns:
        The parsed JSON document.

    Raises:
        urllib.error.HTTPError: if the package does not exist on PyPI.
    """
    with urllib.request.urlopen(PYPI_JSON.format(name=name), timeout=30) as resp:
        return json.load(resp)


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted-numeric version prefix into a comparable tuple.

    # ponytail: this is not PEP 440 (no pre/post/dev ordering, no epochs). The suite's own
    # convention is MAJOR.MINOR.PATCH with no pre-release identifiers on a published version
    # (packaging §3), so a leading numeric run is enough. Upgrade to stdlib `packaging` -- allowed
    # once this script may depend on more than pip -- if a suite package ever ships an rc on PyPI.

    Args:
        version: A version string, e.g. "0.7.1".

    Returns:
        The leading dotted-integer run as a tuple, e.g. (0, 7, 1).
    """
    m = re.match(r"^\d+(?:\.\d+)*", version)
    if not m:
        return (0,)
    return tuple(int(p) for p in m.group(0).split("."))


def published_versions(name: str) -> list[str]:
    """List a package's non-yanked published versions, ascending.

    Args:
        name: PyPI distribution name.

    Returns:
        Version strings sorted ascending by `version_tuple`.
    """
    meta = pypi_metadata(name)
    releases = meta["releases"]  # type: ignore[index]
    out = []
    for v, files in releases.items():  # type: ignore[union-attr]
        if not files:
            continue
        if all(f.get("yanked") for f in files):
            continue
        out.append(v)
    return sorted(out, key=version_tuple)


def latest_version(name: str) -> str:
    """Return an application's or package's current PyPI release.

    Args:
        name: PyPI distribution name.

    Returns:
        `info.version` from the PyPI JSON API.
    """
    return str(pypi_metadata(name)["info"]["version"])  # type: ignore[index]


def download_sdist(name: str, version: str, dest_dir: Path) -> Path:
    """Download a package's source distribution via pip, without building or installing it.

    Args:
        name: PyPI distribution name.
        version: Exact version to fetch.
        dest_dir: Directory to download into.

    Returns:
        Path to the downloaded sdist archive.

    Raises:
        RuntimeError: if pip did not leave exactly one archive behind.
    """
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--no-deps",
            "--no-binary",
            ":all:",
            f"{name}=={version}",
            "-d",
            str(dest_dir),
            "-q",
        ],
        check=True,
    )
    found = list(dest_dir.glob(f"{name}-{version}.tar.gz")) or list(dest_dir.glob("*.tar.gz"))
    if len(found) != 1:
        raise RuntimeError(f"expected one sdist for {name}=={version}, found {found}")
    return found[0]


def sdist_member_names(sdist_path: Path) -> list[str]:
    """List every path inside an sdist archive.

    Args:
        sdist_path: Path to a `.tar.gz` sdist.

    Returns:
        Archive member names.
    """
    with tarfile.open(sdist_path, "r:gz") as tf:
        return tf.getnames()


def read_pyproject(sdist_path: Path) -> dict[str, object]:
    """Parse the `pyproject.toml` shipped inside an sdist.

    Args:
        sdist_path: Path to a `.tar.gz` sdist.

    Returns:
        The parsed TOML document.

    Raises:
        FileNotFoundError: if no `pyproject.toml` is at the sdist's top level.
    """
    with tarfile.open(sdist_path, "r:gz") as tf:
        candidates = [n for n in tf.getnames() if n.count("/") == 1 and n.endswith("pyproject.toml")]
        if not candidates:
            raise FileNotFoundError(f"no top-level pyproject.toml in {sdist_path}")
        member = tf.extractfile(candidates[0])
        assert member is not None
        return tomllib.loads(member.read().decode("utf-8"))


def parse_requirement(req: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Split a PEP 508-ish requirement string into name, extras and specifiers.

    Args:
        req: A dependency string as it appears in `pyproject.toml`, e.g.
            `"modelrack>=0.7,<0.8"` or `"loadledger[sql]>=0.3,<0.4"`.

    Returns:
        `(lowercase_name, extras_suffix_or_empty, [(operator, version), ...])`.
    """
    m = REQ_RE.match(req)
    if not m:
        return req.lower(), "", []
    name = m.group(1).lower()
    extras = m.group(2) or ""
    specs = SPEC_RE.findall(m.group(3) or "")
    return name, extras, specs


def suite_dependency_ranges(pyproject: dict[str, object]) -> dict[str, tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]]:
    """Extract the floor/ceiling this application declares for each suite package it depends on.

    Args:
        pyproject: A parsed `pyproject.toml` document.

    Returns:
        Mapping of suite package name to `(extras_suffix, floor_tuple_or_None,
        ceiling_exclusive_tuple_or_None)`. Only `[project.dependencies]` is read -- optional
        extras (e.g. IdeaPress's `sweatmeter` under `[telemetry]`) are out of scope for this pass.
    """
    project = pyproject.get("project", {})
    deps = project.get("dependencies", []) if isinstance(project, dict) else []
    out: dict[str, tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]] = {}
    for req in deps:
        name, extras, specs = parse_requirement(req)
        if name not in SUITE_PACKAGES:
            continue
        floor = ceiling = None
        for op, ver in specs:
            t = version_tuple(ver)
            if op == ">=":
                floor = t
            elif op == "<":
                ceiling = t
            elif op == "==":
                floor = ceiling = t
        out[name] = (extras, floor, ceiling)
    return out


def resolve_pin(name: str, floor: tuple[int, ...] | None, ceiling: tuple[int, ...] | None, bound: str) -> str | None:
    """Pick the lowest or highest published version a declared range admits.

    Args:
        name: Suite package's PyPI distribution name.
        floor: Inclusive lower bound (from `>=`), or None.
        ceiling: Exclusive upper bound (from `<`), or None.
        bound: `"lowest"` or `"highest"`.

    Returns:
        A version string, or None if no published version satisfies the range -- an
        unresolvable cell, which the caller must report as a failure, not a skip.
    """
    candidates = [
        v for v in published_versions(name)
        if (floor is None or version_tuple(v) >= floor) and (ceiling is None or version_tuple(v) < ceiling)
    ]
    if not candidates:
        return None
    return candidates[0] if bound == "lowest" else candidates[-1]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run with captured output and no implicit raise, for readable failure reporting."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def cell_report(app: str, bound: str, workdir: Path) -> dict[str, object]:
    """Run one compatibility-matrix cell: resolve pins, install, prove, report.

    Args:
        app: One of `APPLICATIONS`.
        bound: `"lowest"` or `"highest"`.
        workdir: Scratch directory for the sdist download and the venv (not cleaned up here).

    Returns:
        A JSON-serializable report dict with at least `ok: bool` and `summary: str`, plus
        `pins`, `app_version`, `install`, and `tests` detail on success.
    """
    report: dict[str, object] = {"app": app, "bound": bound}

    app_version = latest_version(app)
    report["app_version"] = app_version

    sdist_dir = workdir / "sdist"
    sdist_dir.mkdir(parents=True, exist_ok=True)
    app_sdist = download_sdist(app, app_version, sdist_dir)
    pyproject = read_pyproject(app_sdist)
    ranges = suite_dependency_ranges(pyproject)

    pins: dict[str, str] = {}
    unresolved: list[str] = []
    for pkg, (extras, floor, ceiling) in ranges.items():
        chosen = resolve_pin(pkg, floor, ceiling, bound)
        if chosen is None:
            unresolved.append(
                f"{pkg}: no published version satisfies >={'.'.join(map(str, floor or ()))},"
                f"<{'.'.join(map(str, ceiling or ()))}"
            )
            continue
        pins[pkg] = f"{pkg}{extras}=={chosen}"
    report["pins"] = pins

    if unresolved:
        report["ok"] = False
        report["summary"] = "UNRESOLVABLE: " + "; ".join(unresolved)
        return report

    members = sdist_member_names(app_sdist)
    has_contract = any("/tests/contract/" in f"/{m}" for m in members)
    has_e2e = any("/tests/e2e/" in f"/{m}" for m in members)
    report["tests_in_sdist"] = has_contract or has_e2e

    venv_dir = workdir / "venv"
    run([sys.executable, "-m", "venv", str(venv_dir)])
    venv_python = venv_dir / "bin" / "python"

    # [dev] pulls in pytest plus whatever the test suite itself needs (respx, etc.) in the same
    # resolution as the suite-package pins, so a later separate `pip install pytest` cannot upgrade
    # something already pinned. Harmless when there is nothing to test either.
    app_spec = f"{app}[dev]=={app_version}" if (has_contract or has_e2e) else f"{app}=={app_version}"
    install_args = [app_spec, *pins.values()]
    install = run([str(venv_python), "-m", "pip", "install", "-q", *install_args])
    report["install"] = {
        "returncode": install.returncode,
        "stderr_tail": install.stderr[-2000:],
    }
    if install.returncode != 0:
        report["ok"] = False
        report["summary"] = "INSTALL FAILED: " + install.stderr.strip().splitlines()[-1] if install.stderr.strip() else "INSTALL FAILED"
        return report

    version_check = run([str(venv_python), "-m", app, "--version"])
    if version_check.returncode != 0:
        version_check = run([str(venv_python), "-c", f"import {app}; print(getattr({app}, '__version__', '?'))"])
    report["version_check"] = {
        "returncode": version_check.returncode,
        "stdout": version_check.stdout.strip(),
    }

    if not (has_contract or has_e2e):
        report["ok"] = version_check.returncode == 0
        report["summary"] = (
            "no tests/contract or tests/e2e in the sdist -- workflow strategy: clone the tag "
            f"({pyproject.get('project', {}).get('urls', {}).get('Homepage', '?')}) and run "
            "pytest -m \"contract or e2e\" from the checkout against the installed wheel"
        )
        return report

    extract_dir = workdir / "extracted"
    with tarfile.open(app_sdist, "r:gz") as tf:
        tf.extractall(extract_dir)  # noqa: S202 -- our own just-downloaded sdist
    top = next(extract_dir.iterdir())

    # Point pytest at only the contract/e2e directories rather than the whole `tests/` tree:
    # collection is eager regardless of `-m`, so a broken import anywhere under `tests/` (e.g. a
    # unit test needing a dev extra this cell does not install) would abort the run before the
    # marker filter ever applies.
    test_targets = [d for d in ("tests/contract", "tests/e2e") if (top / d).is_dir()]
    tests = run(
        [str(venv_python), "-m", "pytest", "-m", "contract or e2e", "-q", *test_targets],
        cwd=str(top),
    )
    report["tests"] = {
        "returncode": tests.returncode,
        "tail": "\n".join(tests.stdout.strip().splitlines()[-15:]),
    }
    report["ok"] = tests.returncode == 0
    report["summary"] = f"tests {'passed' if tests.returncode == 0 else 'FAILED'} (pytest exit {tests.returncode})"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=APPLICATIONS)
    parser.add_argument("bound", choices=("lowest", "highest"))
    parser.add_argument("--workdir", type=Path, default=None)
    parser.add_argument("--keep", action="store_true", help="do not delete a temp workdir")
    args = parser.parse_args(argv)

    owns_workdir = args.workdir is None
    workdir = args.workdir or Path(tempfile.mkdtemp(prefix=f"compat-{args.app}-{args.bound}-"))
    try:
        report = cell_report(args.app, args.bound, workdir)
    finally:
        if owns_workdir and not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    print(json.dumps(report, indent=2, default=str))

    summary_path = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            status = "PASS" if report.get("ok") else "**FAIL**"
            fh.write(f"| {args.app} | {args.bound} | {status} | {report.get('summary')} |\n")

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
