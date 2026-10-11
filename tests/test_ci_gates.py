"""`scripts/ci_gates.py` (AW14, GATE-SPEED): gates run side by side, print as ordered blocks.

Synthetic one-liner gates stand in for the real ones; the real `just ci` wiring is proved by the
GATE-SPEED probe (a lint error fails it with ruff's block printed).
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fransys_ci_gates", ROOT / "scripts" / "ci_gates.py")
assert _spec is not None
assert _spec.loader is not None
ci_gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci_gates)


def _gate(code: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code)


def test_blocks_print_in_group_order_not_finish_order(capfd):
    slow = _gate("import time; time.sleep(0.5); print('first block')")
    fast = _gate("print('second block')")
    assert ci_gates.run_all(((slow,), (fast,))) == 0
    out = capfd.readouterr().out
    assert out.index("first block") < out.index("second block")


def test_exit_code_is_the_first_failing_gate_and_later_blocks_still_print(capfd):
    groups = (
        (_gate("print('ok')"),),
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


def test_a_lint_error_fails_the_gate_with_ruffs_block_printed(tmp_path, capfd):
    bad = tmp_path / "bad.py"
    bad.write_text("import os\n", encoding="utf-8")
    ruff = ("uv", "run", "ruff", "check", "--isolated", "--no-cache", str(bad))
    assert ci_gates.run_all(((ruff,), (_gate("print('later block')"),))) != 0
    out = capfd.readouterr().out
    assert "F401" in out
    assert out.index("F401") < out.index("later block")
