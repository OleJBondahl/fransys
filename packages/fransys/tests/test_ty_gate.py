"""TY6: ty at the workspace pin finds nothing in the guide or the handle spellings.

One ty run for the whole module (a module fixture). The guide pages are cut into one file per
page, as `tests/test_guide_examples.py` runs them, and the generated `demo_typed` stub sits beside
them. No network is needed.
"""

import re
import subprocess
from importlib.resources import files
from pathlib import Path

import pytest
from fransys.parts_module import parts_module

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "uv.lock").is_file())
FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)
SPELLINGS = """
from typing import NamedTuple

import fransys as fr


class Cab(NamedTuple):
    X1: fr.Device
    L1: fr.Run


def cab_unit(revision: int) -> fr.UnitDef[Cab]:
    @fr.unit(
        "demo-cab", revision=revision, interface_version=1, date="2026-01-01", text="t", by="AB"
    )
    def build(d: fr.Design) -> Cab:
        strip = d.terminal_strip("X3", "DEMO-TB-2.5", 3, interface=True)
        x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
        return Cab(x1, strip.run("L1", 2, interface=(1,)))

    return build


def wire(
    d: fr.Design, k: fr.Device, cab: fr.Device, ac: fr.AcSupply, dc: fr.DcSupply, w: fr.Cable
) -> str | None:
    d.detail.wire(k.coil["A2"], cab.main["2"], wire=("BK", 2.5))
    d.detail.wire(k.coil.A1, k["0V"], wire=("BK", 2.5))
    d.series(ac.L1, k.co.no, k.co.nc, dc.plus, wire=("BK", 2.5))
    rail: fr.SupplyRail = dc.minus
    pin: fr.Pin = k.coil["A2"]
    fn: fr.Fn = k.coil
    return k.tag
"""

THROWS = """
import fransys as fr
from demo_typed import DEMO_RLY_2CO_24


def wire(d: fr.Design, ac: fr.AcSupply, dc: fr.DcSupply) -> None:
    k = d.device("K1", DEMO_RLY_2CO_24)
    d.series(ac.L1, k.co_1.no, dc.plus, wire=("BK", 2.5))
    d.series(ac.L1, k.co_1.nc, dc.plus, wire=("BK", 2.5))
    d.series(ac.L1, k.co_1.xx, dc.plus, wire=("BK", 2.5))
"""


def _guide_pages(folder: Path) -> None:
    for page in files("fransys").joinpath("guide").iterdir():
        blocks = (
            FENCE.findall(page.read_text(encoding="utf-8")) if page.name.endswith(".md") else []
        )
        if blocks:
            stem = page.name[:-3].replace("-", "_").replace(".", "_")
            (folder / f"guide_{stem}.py").write_text("\n".join(blocks), encoding="utf-8")


@pytest.fixture(scope="module")
def findings(tmp_path_factory) -> list[str]:
    """Every ty diagnostic line over the guide pages and the spellings."""
    folder = tmp_path_factory.mktemp("ty")
    (folder / "demo_typed.py").write_text(parts_module("demo_parts"), encoding="utf-8")
    (folder / "spellings.py").write_text(SPELLINGS, encoding="utf-8")
    (folder / "throws.py").write_text(THROWS, encoding="utf-8")
    _guide_pages(folder)
    run = subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run", "ty", "check", "--project", str(ROOT)),
            *("--extra-search-path", str(folder), "--output-format", "concise"),
            str(folder),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode in {0, 1}, run.stdout + run.stderr  # ty ran
    return [line for line in run.stdout.splitlines() if ": error[" in line or ": warning[" in line]


def _of(findings: list[str], needle: str) -> list[str]:
    return [line for line in findings if needle in line]


def test_the_handle_spellings_type_check(findings) -> None:
    assert _of(findings, "spellings.py") == []


def test_a_generated_changeover_types_its_throws(findings) -> None:
    """`k.co_1.no` and `.nc` type-check on a generated part; `.xx` stays a ty error (0203, 0206)."""
    lines = _of(findings, "throws.py")
    assert len(lines) == 1, lines
    assert "throws.py:10:" in lines[0], lines  # only the `.xx` line


def test_every_guide_example_type_checks(findings) -> None:
    assert _of(findings, "guide_") == []


def test_the_generated_demo_stub_type_checks(findings) -> None:
    assert _of(findings, "demo_typed.py") == []


def test_the_generated_demo_stub_type_checks_under_default_rules(tmp_path) -> None:
    """A consumer's ty has no project config: the stub alone, in a folder with none."""
    stub = tmp_path / "demo_typed.py"
    stub.write_text(parts_module("demo_parts"), encoding="utf-8")
    run = subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run", "ty", "check", "--project", str(tmp_path)),
            *("--output-format", "concise", str(stub)),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert run.returncode == 0, run.stdout + run.stderr


def test_the_gate_sees_a_finding_when_there_is_one(tmp_path) -> None:
    """The check can fail: a planted slip is reported."""
    bad = tmp_path / "bad.py"
    bad.write_text("import fransys as fr\n\nx: fr.Design = 1\n", encoding="utf-8")
    run = subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run"),
            "ty",
            "check",
            "--project",
            str(ROOT),
            "--output-format",
            "concise",
            str(bad),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1, run.stdout + run.stderr
