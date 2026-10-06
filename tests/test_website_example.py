"""`website/example.py`, the home page's script, still builds and writes its PDF (FS3).

One full build, and the only one in this module, so it takes the few seconds a layout and a PDF
cost: the test would prove nothing with a stubbed build, since a name the surface lost only
fails when the script really calls it.
"""

import csv
import runpy
import subprocess
import sys
from pathlib import Path

import fransys as fr

EXAMPLE = Path(__file__).resolve().parents[1] / "website" / "example.py"
MAX_LINES = 50


def test_example_stays_short():
    """FS3 keeps the home example at 50 lines or fewer (CABINET-UNIT raised it from 30)."""
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


def test_example_builds_with_no_error_and_no_warning(tmp_path, monkeypatch):
    """The cabinet unit has its title and number, so the build holds no ERROR or WARNING."""
    monkeypatch.chdir(tmp_path)
    result = runpy.run_path(str(EXAMPLE))["result"]
    severe = [
        f.code for f in fr.check(result) if f.severity in (fr.Severity.ERROR, fr.Severity.WARNING)
    ]
    assert severe == []


def test_cabinet_bom_holds_no_field_device_and_x1_rows_end_in_pe(tmp_path, monkeypatch):
    """The motor and cable stand in the top design (CU3); X1 ends in a PE run and part (acc 8)."""
    monkeypatch.chdir(tmp_path)
    result = runpy.run_path(str(EXAMPLE))["result"]
    out = tmp_path / "unit"
    fr.write(result, out, unit="motor-starter")
    bom = (out / "motor-starter-v1.1-bom.csv").read_text(encoding="utf-8")
    assert "-M1" not in bom
    assert "-W1" not in bom
    rows = (out / "motor-starter-v1.1-terminals-X1.csv").read_text(encoding="utf-8")
    assert [line.split(",")[0] for line in rows.splitlines()[1:]] == [
        "-X1:1",
        "-X1:2",
        "-X1:3",
        "-X1:PE:1",
    ]
    counts = {r[0]: r[4] for r in list(csv.reader(bom.splitlines()))[1:]}
    assert counts["DEMO-TB-2.5"] == "6"
    assert counts["DEMO-TB-PE-2.5"] == "1"
