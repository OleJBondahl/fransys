"""`website/example.py`, the home page's script, still builds and writes its PDF (FS3).

One full build, and the only one in this module, so it takes the few seconds a layout and a PDF
cost: the test would prove nothing with a stubbed build, since a name the surface lost only
fails when the script really calls it.
"""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "website" / "example.py"
MAX_LINES = 30


def test_example_stays_short():
    """FS3 keeps the home example at 30 lines or fewer."""
    assert len(EXAMPLE.read_text(encoding="utf-8").splitlines()) <= MAX_LINES


def test_example_writes_a_pdf_into_out(tmp_path):
    """Run in a fresh folder, the script exits 0 and leaves a PDF under `out/`."""
    run = subprocess.run(  # noqa: S603  runs the repo's own example script
        [sys.executable, str(EXAMPLE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert list((tmp_path / "out").glob("*.pdf"))
