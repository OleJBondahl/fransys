"""`import fransys_layout.core` loads no engine, stage or lint module (layout-0358, DEL-2)."""

import subprocess
import sys

_PROBE = (
    "import sys, fransys_layout.core\n"
    "print(sorted(m for m in sys.modules if m.startswith('fransys_layout.')"
    " and m.split('.')[1] in ('engines', 'stages', 'lint')))\n"
)


def test_the_core_import_loads_no_old_engine_module():
    out = subprocess.run(  # noqa: S603 - fixed argv, our own interpreter
        [sys.executable, "-c", _PROBE], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "[]"


def test_every_lazy_name_resolves_on_first_use():
    import fransys_layout

    for name in (
        "lay_out_cables",
        "lay_out_diagrams",
        "lay_out_overview",
    ):
        assert getattr(fransys_layout, name) is not None, name
    assert fransys_layout.FINDING_CODES
