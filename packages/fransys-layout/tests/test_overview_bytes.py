"""P7-8A: the overview HTML of the demo-parts system is the same bytes after the module move.

The hash is the one written on the base commit, before `engines/diagram` modules moved under
`engines/overview/`. A layout change that moves any overview box or line changes it.
"""

import hashlib
from pathlib import Path

import fransys as fr
import fransys_parts
from test_units_worked_example import _system_design

_GOLDEN = Path(__file__).resolve().parent / "golden" / "overview_html_sha256.txt"


def _overview_html(out: Path) -> bytes:
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    written = fr.write(fr.build(parts, design.draft()), out)
    return next(p for p in written if p.name.endswith("overview.html")).read_bytes()


def test_the_overview_html_of_the_demo_cabinet_keeps_its_bytes(tmp_path: Path) -> None:
    """Breaks if any overview placement, route or label moves."""
    digest = hashlib.sha256(_overview_html(tmp_path)).hexdigest()
    assert digest == _GOLDEN.read_text(encoding="utf-8").strip()
