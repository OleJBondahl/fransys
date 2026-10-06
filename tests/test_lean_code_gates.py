"""`scripts/lean_code_gates.py`: the ruff-measured sections and the noqa/ty:ignore reason rule.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. `measure_ruff_sections`'s own test runs a
real `ruff` subprocess against a `tmp_path` fixture -- never mocked, since the point is to catch
a change in ruff's own message format or JSON shape. `report_unreasoned`'s exempt honoring and
the `check`-wiring probe use plain in-memory data, no subprocess needed for those.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_code_gates", ROOT / "scripts" / "lean_code_gates.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_code_gates.py"
    raise ImportError(msg)
lean_code_gates = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_code_gates
_spec.loader.exec_module(lean_code_gates)

lean_ceilings = lean_code_gates.lean_ceilings


def _write(path: Path, content: str) -> None:
    """Write `content` to `path`, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _statement_function(name: str, count: int, indent: str = "", params: str = "") -> str:
    """Source text for a `def name(params):` with exactly `count` ruff-counted statements.

    A docstring plus `count - 1` assignments plus a `return` -- confirmed against real ruff
    (`sample16.py`/`sample.py` probes) to measure as exactly `count` statements, regardless of
    the docstring line.
    """
    lines = [f"{indent}def {name}({params}):", f'{indent}    """Docstring."""']
    lines += [f"{indent}    x = {i}" for i in range(1, count)]
    lines.append(f"{indent}    return x")
    return "\n".join(lines) + "\n"


# --- Check 1: ruff-measured statements/complexity/branches ---------------------------------


def test_measure_ruff_sections_maps_qualnames_without_collision(tmp_path: Path) -> None:
    """A module-level function and a method, each over the statements threshold, resolve to
    their own distinct qualnames -- never the same one, never swapped.
    """
    module = tmp_path / "packages" / "fakepkg" / "src" / "mod.py"
    _write(
        module,
        '"""Fixture module."""\n\n\n'
        + _statement_function("plain_function", 17)
        + "\n\n"
        + 'class Foo:\n    """Fixture class."""\n\n'
        + _statement_function("method", 17, indent="    ", params="self"),
    )
    sections = lean_code_gates.measure_ruff_sections(tmp_path)
    measured = sections["statements"]

    assert measured == {
        "packages/fakepkg/src/mod.py::plain_function": 17,
        "packages/fakepkg/src/mod.py::Foo.method": 17,
    }


def test_measure_ruff_sections_wired_through_check(tmp_path: Path) -> None:
    """Acceptance 1: a 16-statement fixture function, unlisted, fails `lean_ceilings.check`
    through `measure_ruff_sections`'s own qualname wiring -- not just `lean_ceilings`'s
    already-proven core.
    """
    module = tmp_path / "packages" / "fakepkg" / "src" / "mod.py"
    _write(module, '"""Fixture module."""\n\n\n' + _statement_function("over_limit", 16))

    measured = lean_code_gates.measure_ruff_sections(tmp_path)["statements"]
    assert measured == {"packages/fakepkg/src/mod.py::over_limit": 16}

    violations = lean_ceilings.check(measured, ceilings={}, limit=15)
    assert violations == (
        lean_ceilings.Violation(
            site="packages/fakepkg/src/mod.py::over_limit", measured=16, limit=15, listed=False
        ),
    )


def _complexity_function(name: str, branches: int) -> str:
    """Source text for a `def` with cyclomatic complexity `branches + 1` and few statements."""
    body = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(branches))
    return f'def {name}(x):\n    """Docstring."""\n{body}    return -1\n'


def test_measure_ruff_sections_ignores_the_projects_per_file_ignores(tmp_path: Path) -> None:
    """LEAN-GATE-FIX (decision 0114): the real root `pyproject.toml` ignores C901, PLR0912 and
    PLR0915 under `packages/*/src/**`; the gate still measures a 16-statement and a complexity-9
    function there.
    """
    shutil.copy(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    src = tmp_path / "packages" / "fakepkg" / "src"
    _write(src / "stmts.py", '"""Fixture."""\n\n\n' + _statement_function("long_one", 16))
    _write(src / "cx.py", '"""Fixture."""\n\n\n' + _complexity_function("branchy", 8))

    sections = lean_code_gates.measure_ruff_sections(tmp_path)

    assert sections["statements"] == {"packages/fakepkg/src/stmts.py::long_one": 16}
    assert sections["complexity"] == {"packages/fakepkg/src/cx.py::branchy": 9}


def test_measure_ruff_sections_fails_when_the_call_fails_without_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LEAN-GATE-FIX: a uv or ruff failure (exit 1, empty stdout, an error on stderr) is not
    "no findings"; the gate raises instead of passing clean.
    """
    _write(
        tmp_path / "packages" / "fakepkg" / "src" / "mod.py",
        '"""Fixture."""\n\n\n' + _statement_function("over_limit", 16),
    )
    failed = subprocess.CompletedProcess([], 1, stdout="", stderr="error: Failed to build")
    monkeypatch.setattr(lean_code_gates.subprocess, "run", lambda *_a, **_k: failed)

    with pytest.raises(RuntimeError, match="no parsed finding"):
        lean_code_gates.measure_ruff_sections(tmp_path)


# --- Check 2: the noqa/ty:ignore reason rule ------------------------------------------------


def test_unreasoned_bare_noqa_detected(tmp_path: Path) -> None:
    """Acceptance 4a: a bare `# noqa: C901` (no reason) is an `unreasoned_sites` hit."""
    module = tmp_path / "pkgtree" / "src" / "mod.py"
    _write(module, "x = 1  # noqa: C901\n")

    sites = lean_code_gates.unreasoned_sites([tmp_path / "pkgtree" / "src"], tmp_path)

    assert sites == (
        lean_code_gates.UnreasonedSite(path="pkgtree/src/mod.py", line=1, text="# noqa: C901"),
    )


def test_reasoned_noqa_passes(tmp_path: Path) -> None:
    """Acceptance 4b: the identical line with `-- reason text` is not a hit."""
    module = tmp_path / "pkgtree" / "src" / "mod.py"
    _write(module, "x = 1  # noqa: C901 -- reason text\n")

    sites = lean_code_gates.unreasoned_sites([tmp_path / "pkgtree" / "src"], tmp_path)

    assert sites == ()


def test_report_unreasoned_honors_directory_exempt() -> None:
    """A site under an `[exempt]` directory entry is dropped; a sibling package's site is not."""
    sites = (
        lean_code_gates.UnreasonedSite(
            path="packages/fake-layout/src/x.py", line=1, text="# noqa: C901"
        ),
        lean_code_gates.UnreasonedSite(
            path="packages/fake-render/src/y.py", line=2, text="# noqa: C901"
        ),
    )
    exempt = {"packages/fake-layout": "dated exemption (owner-0001)"}

    kept = lean_code_gates.report_unreasoned(sites, exempt)

    assert kept == (sites[1],)
