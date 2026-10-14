"""`scripts/regen_goldens.py` lists exactly the layout test files that read `--regenerate-golden`.

A missing file would leave its golden stale after `just regen-goldens layout`; an extra one would
only cost time. The set is found by scanning, so a new golden test fails here until it is listed.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_regen_goldens", ROOT / "scripts" / "regen_goldens.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/regen_goldens.py"
    raise ImportError(msg)
regen_goldens = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = regen_goldens
_spec.loader.exec_module(regen_goldens)


def test_layout_golden_list_is_the_set_of_files_that_read_the_option() -> None:
    root = ROOT / regen_goldens.LAYOUT_DIR
    readers = {
        path.relative_to(ROOT).as_posix()
        for path in root.rglob("test_*.py")
        if 'getoption("--regenerate-golden")' in path.read_text(encoding="utf-8")
    }
    assert readers, "the scan found no test reading the option"
    assert set(regen_goldens.LAYOUT_GOLDEN_TESTS) == readers
    assert list(regen_goldens.LAYOUT_GOLDEN_TESTS) == sorted(regen_goldens.LAYOUT_GOLDEN_TESTS)
