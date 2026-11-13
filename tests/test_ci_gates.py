"""`scripts/ci_gates.py`: gates run side by side, print as ordered blocks.

Synthetic one-liner gates stand in for the real ones; the real `just ci` wiring is proved by the
probe (a lint error fails it with ruff's block printed).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fransys_ci_gates", ROOT / "scripts" / "ci_gates.py")
assert _spec is not None
assert _spec.loader is not None
ci_gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci_gates)


def _gate(code: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code)


def test_exit_code_is_the_first_failing_gate_and_later_blocks_still_print(capfd):
    groups = (
        (_gate("import time; time.sleep(0.5); print('ok')"),),  # finishes last, prints first
        (_gate("print('ruff block'); raise SystemExit(4)"),),
        (_gate("print('cov block'); raise SystemExit(5)"),),
    )
    assert ci_gates.run_all(groups) == 4
    out = capfd.readouterr().out
    assert out.index("ok") < out.index("ruff block") < out.index("cov block")


def test_a_group_stops_at_its_first_failure(capfd):
    group = (_gate("raise SystemExit(2)"), _gate("print('never')"))
    assert ci_gates.run_all((group,)) == 2
    assert "never" not in capfd.readouterr().out


@pytest.mark.parametrize(
    ("env", "load", "cpus", "want"),
    [({}, 4.4, 32, "6"), ({}, 30.0, 8, "2"), ({}, 1.0, 5, "4"), ({"PYTEST_WORKERS": "3"}, 30.0, 32, "3")],
)
def test_the_workers_follow_the_load_unless_set(monkeypatch, env, load, cpus, want) -> None:
    """R2270: max(2, min(6, cpus - load)); an explicit PYTEST_WORKERS wins; the line names the load."""
    monkeypatch.setattr(ci_gates.os, "getloadavg", lambda: (load, 0.0, 0.0), raising=False)
    monkeypatch.setattr(ci_gates.os, "cpu_count", lambda: cpus)
    why = "PYTEST_WORKERS set" if env else f"load {load:.1f}"
    assert ci_gates.pytest_workers(env) == f"pytest workers: {want} ({why})"
    assert env["PYTEST_WORKERS"] == want
    monkeypatch.delattr(ci_gates.os, "getloadavg")
    assert ci_gates.pytest_workers({}) == "pytest workers: 6 (no load average on this platform)"


def test_the_internal_gate_joins_only_where_the_full_repo_has_its_recipes(tmp_path: Path) -> None:
    """R1348: the export has no internal/internal.just and runs the public groups alone."""
    assert ci_gates.all_groups(tmp_path) == ci_gates._GROUPS
    (tmp_path / "internal").mkdir()
    (tmp_path / "internal" / "internal.just").write_text("", encoding="utf-8")
    assert ci_gates.all_groups(tmp_path) == (*ci_gates._GROUPS, (("just", "internal-gate"),))
    assert not ci_gates.runs_pytest((ci_gates._RATCHETS,))  # R2270: the ratchets run in the cheap phase


def test_the_pytest_group_starts_only_after_the_cheap_gates_are_green(tmp_path: Path, capfd) -> None:
    """AWS-COST-1: a lint failure ends the run before pytest starts; a green lint runs every group, blocks in group order."""
    started = tmp_path / "pytest-started"
    pytest_group = ((*_gate(f"open({str(started)!r}, 'w').close(); print('pytest block')"), "cov"),)
    lint_red = (_gate("print('ruff block'); raise SystemExit(4)"),)
    assert ci_gates.run_all((pytest_group, lint_red)) == 4
    out = capfd.readouterr().out
    assert not started.exists()
    assert "ruff block" in out
    assert "pytest not started" in out
    assert ci_gates.run_all((pytest_group, (_gate("print('ruff block')"),))) == 0
    out = capfd.readouterr().out
    assert started.exists()
    assert out.index("pytest block") < out.index("ruff block")
