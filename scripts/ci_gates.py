"""`just ci`: the gates run side by side, each gate's output prints as one block, in order (AW14).

The groups run at once: `check`, `dead-code`, `cov` then the coverage floors, and the lean checks.
Output is captured per gate and printed in the serial order (check, dead-code, cov, cov_floors,
lean hard, enforce, report), so a log reads as before. The exit code is the first failing
gate's; a failure never hides a later gate's block.

`--testmon [-- PYTEST ARGS]` (TESTMON-AWS) swaps the `cov` group for pytest under pytest-testmon,
with no coverage: only the tests that testmon selects run, plus `ALWAYS_RUN`. Everything testmon
cannot see forces a full run (`DATA_GLOBS`, `NON_PY_UNDER`). The last line is `TESTMON: ...`.
"""

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

_GROUPS: tuple[tuple[tuple[str, ...], ...], ...] = (
    (("just", "check"),),
    (("just", "dead-code"),),
    (
        ("just", "cov"),
        (
            "uv",
            "run",
            "python",
            "scripts/cov_floors.py",
            "check",
            ".fransys/coverage.json",
            "coverage-floors.toml",
        ),
    ),
    (
        ("uv", "run", "python", "scripts/lean_check.py", "hard"),
        ("uv", "run", "python", "scripts/lean_check.py", "enforce"),
        ("uv", "run", "python", "scripts/lean_check.py", "report"),
    ),
)

Block = tuple[int, bytes]
Groups = tuple[tuple[tuple[str, ...], ...], ...]
Runner = Callable[[list[str], dict[str, str]], tuple[int, str]]

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ".fransys/testmon"
DATAFILE = "testmon.sqlite"
MANIFEST = "manifest.json"
NOTHING_COLLECTED = 5  # pytest exit code

# Tracked files a test reads as data or at import only, which testmon does not see (TM5).
DATA_GLOBS: tuple[str, ...] = (
    "packages/electrical-symbols/symbols/**",
    "packages/electrical-symbols/build/**",
    "examples/**",
    "**/pyproject.toml",
    "uv.lock",
    "ceilings.toml",
    "packages/*/src/*/conventions/**",  # module-level tables are read at import only
    "packages/fransys-model/src/fransys_model/derive/rows.py",  # the same, for the row shapes
)
# Every non-.py file under these is data too (bundle.json, guide pages, fonts, fixtures).
NON_PY_UNDER: tuple[str, ...] = ("packages/*/src/**", "packages/*/tests/**", "tests/**")
# Tests that read tracked source, docs or config as text: testmon cannot see their input.
ALWAYS_RUN: tuple[tuple[str, str], ...] = (
    ("tests/test_boundaries.py", "ast of every packages/*/src .py"),
    ("tests/test_declared_dependencies.py", "src imports against pyproject"),
    ("tests/test_guide_examples.py", "ast of the examples"),
    ("tests/test_guide_findings_codes.py", "ast of packages/*/src"),
    ("tests/test_lean_check.py", "lean sites over the real layout src and tests"),
    ("tests/test_lean_code_shape.py", "a real src module"),
    ("tests/test_names.py", "text of every tracked file"),
    ("tests/test_no_second_cable_predicate.py", "ast of packages/*/src"),
    ("tests/test_public_toml.py", "public.toml and git ls-files"),
    ("tests/test_readme_example.py", "README.md and website/example.py"),
    ("tests/test_site_banner.py", "website/mkdocs.yml and overrides"),
    ("tests/test_site_nav.py", "website/roadmap.md"),
    ("tests/test_spec_links.py", "links in tracked docs"),
    ("tests/test_vulture_whitelist.py", "whitelist and ast of src"),
    ("tests/test_website_example.py", "website/example.py"),
    ("tests/test_wire_label_one_home.py", "ast of packages/*/src"),
    ("packages/electrical-symbols/tests/test_decisions_hygiene.py", "decision records text"),
    ("packages/electrical-symbols/tests/test_hygiene.py", "git ls-files text"),
    ("packages/electrical-symbols/tests/test_text.py", "ast of geometry/text*.py"),
    ("packages/fransys-layout/tests/conventions/test_facts.py", "ast of layout src"),
    ("packages/fransys-layout/tests/engines/test_adjacent_cell_wire.py", "ast of layout src"),
    ("packages/fransys-layout/tests/lint/test_fan_out_exempt.py", "text of lint/*.py"),
    ("packages/fransys-layout/tests/lint/test_geometric.py", "regex over layout src"),
    ("packages/fransys-layout/tests/stages/test_grid_path_home.py", "ast of layout src"),
    ("packages/fransys-layout/tests/test_design_map.py", "rules/*.md and stages src"),
    ("packages/fransys-layout/tests/test_layering.py", "ast of layout src"),
    ("packages/fransys-layout/tests/test_one_port_exit.py", "layout src text"),
    ("packages/fransys-layout/tests/test_one_port_position.py", "layout src text"),
    ("packages/fransys-layout/tests/test_purity.py", "ast of layout src"),
    ("packages/fransys-layout/tests/test_samples.py", "text of its own tests"),
    ("packages/fransys-layout/tests/test_stage_vocabulary.py", "stages and conventions src"),
    ("packages/fransys-layout/tests/test_suppressions.py", "noqa scan of layout src"),
    ("packages/fransys-model/tests/test_layering.py", "ast of model src"),
    ("packages/fransys-overview/tests/test_vendor.py", "generated _vendor_cytoscape.py"),
    ("packages/fransys/tests/test_api.py", "ast of src, docs and examples"),
    ("packages/fransys/tests/test_release_reads_one_place.py", "ast of fransys src"),
)

_COUNTED = re.compile(r"(\d+) (passed|failed|skipped|xfailed|xpassed|errors?)")


def run_group(group: tuple[tuple[str, ...], ...]) -> list[Block]:
    """Run one group's commands in order; stop the group at its first failure."""
    blocks: list[Block] = []
    for argv in group:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)  # noqa: S603 -- fixed argv
        blocks.append((done.returncode, done.stdout))
        if done.returncode:
            break
    return blocks


def run_all(groups: Groups = _GROUPS) -> int:
    """Run `groups` at once, print every block in group order, return the first failing code."""
    with ThreadPoolExecutor(len(groups)) as pool:
        results = list(pool.map(run_group, groups))
    code = 0
    for blocks in results:
        for returncode, output in blocks:
            sys.stdout.flush()
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
            code = code or returncode
    return code


# --- testmon (TESTMON-AWS) --------------------------------------------------------------------


def is_data(path: str) -> bool:
    """Whether a tracked path is a file whose change testmon cannot see."""
    pure = PurePosixPath(path)
    if any(pure.full_match(glob) for glob in DATA_GLOBS):
        return True
    return pure.suffix != ".py" and any(pure.full_match(glob) for glob in NON_PY_UNDER)


def tracked_files(root: Path) -> list[str]:
    done = subprocess.run(  # noqa: S603 -- fixed argv
        ["git", "-C", str(root), "ls-files", "-z"],  # noqa: S607 -- git is on PATH by design
        capture_output=True,
        check=True,
    )
    return [p.decode() for p in done.stdout.split(b"\0") if p]


def data_manifest(root: Path, paths: list[str]) -> dict[str, str]:
    """Each data file's path and content hash; a tracked file missing from disk is left out."""
    found: dict[str, str] = {}
    for path in sorted(paths):
        if is_data(path) and (root / path).is_file():
            found[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return found


def saved_manifest(manifest_file: Path) -> dict[str, str] | None:
    try:
        saved = json.loads(manifest_file.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return saved if isinstance(saved, dict) else None


def known_tests(datafile: Path) -> int | None:
    """How many tests the data knows; None when the file is missing or not a testmon database."""
    if not datafile.is_file():
        return None
    try:
        with sqlite3.connect(datafile) as db:
            row = db.execute("select count(*) from test_execution").fetchone()
    except sqlite3.Error:
        return None
    return int(row[0])


def full_run_reason(
    current: dict[str, str], saved: dict[str, str] | None, known: int | None
) -> str:
    """Why every test must run, or an empty string when testmon may select."""
    if saved is None or saved != current:
        return "data files changed"
    return "no testmon data" if known is None else ""


def counted(output: str) -> int:
    """Tests that ran, from pytest's last summary line (`no tests ran` is 0)."""
    lines = [line for line in output.splitlines() if line.startswith("=") and " in " in line]
    return sum(int(n) for n, _ in _COUNTED.findall(lines[-1])) if lines else 0


def pytest_argv(workers: str, *flags: str) -> list[str]:
    return ["uv", "run", "pytest", "-n", workers, "--dist", "worksteal", *flags]


def run_pytest(argv: list[str], env: dict[str, str]) -> tuple[int, str]:
    done = subprocess.run(  # noqa: S603 -- fixed argv
        argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    text = done.stdout.decode(errors="replace")
    sys.stdout.write(text)
    return done.returncode, text


def testmon_line(reason: str, ran: int, collected: int) -> str:
    counts = f"{ran} of {collected} tests"
    return f"TESTMON: all ({reason}), {counts}" if reason else f"TESTMON: {counts}"


def run_testmon(
    extra: list[str], root: Path = ROOT, run: Runner = run_pytest, workers: str = ""
) -> int:
    """Pytest under testmon, then the always-run tests without it; print the `TESTMON:` line."""
    workers = workers or os.environ.get("PYTEST_WORKERS", "6")
    state = root / STATE_DIR
    state.mkdir(parents=True, exist_ok=True)
    datafile = state / DATAFILE
    env = {**os.environ, "TESTMON_DATAFILE": str(datafile)}
    current = data_manifest(root, tracked_files(root))
    known = known_tests(datafile)
    if known is None:
        datafile.unlink(missing_ok=True)  # unreadable data is a full run, never an error
    reason = full_run_reason(current, saved_manifest(state / MANIFEST), known)
    always = [path for path, _ in ALWAYS_RUN]
    ignores = [f"--ignore={path}" for path in always]
    flags = ["--durations=20", "--testmon", *(["--testmon-noselect"] if reason else []), *ignores]
    code, text = run(pytest_argv(workers, *flags, *extra), env)
    if (
        code == NOTHING_COLLECTED
    ):  # pytest: nothing collected, which is what a testmon run with no change does
        code = 0
    if code in (0, 1):
        (state / MANIFEST).write_text(json.dumps(current, indent=1) + "\n", encoding="utf-8")
    ran, collected = counted(text), known_tests(datafile) or 0
    if ALWAYS_RUN:
        always_code, always_text = run(pytest_argv(workers, "-p", "no:testmon", *always), env)
        code = code or always_code
        ran, collected = ran + counted(always_text), collected + counted(always_text)
    sys.stdout.write(testmon_line(reason, ran, collected) + "\n")
    sys.stdout.flush()
    return code


def testmon_groups(extra: list[str]) -> Groups:
    """The gate groups with the `cov` group replaced by the testmon test run (TM2)."""
    tests = (("uv", "run", "python", "scripts/ci_gates.py", "--testmon-tests", *extra),)
    return tuple(tests if group[0] == ("just", "cov") else group for group in _GROUPS)


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("--testmon", "--testmon-tests"):
        extra = [word for i, word in enumerate(argv[1:]) if not (i == 0 and word == "--")]
        return (
            run_testmon(extra) if argv[0] == "--testmon-tests" else run_all(testmon_groups(extra))
        )
    return run_all()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
