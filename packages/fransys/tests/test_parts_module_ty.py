"""EA4 ty proof: a circuit on the generated demo module type-checks; three slips, one error each.

The module is generated and ty run once for the whole file (a module fixture), not per test.
"""

import re
import subprocess
from pathlib import Path

import pytest
from fransys.parts_module import parts_module

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "uv.lock").is_file())
HEAD = """from typing import NamedTuple

import fransys as fr
from fransys import colours, design, unit

import gparts as P


class Cab(NamedTuple):
    X1: fr.Device
    L1: fr.Run


@unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def cab_unit(d: fr.Design) -> Cab:
    strip = d.terminal_strip("X3", P.DEMO_TB_2_5, 3, interface=True)
    return Cab(d.device("X1", P.DEMO_CONN_2P, interface=True), strip.run("L1", 2))


def circuit() -> None:
    d = design(P, place="C1")
    Q0 = d.device("Q0", P.DEMO_MCB_3P)
    K1 = d.device("K1", P.DEMO_CTR_3P_24)
    F1 = d.device("F1", P.DEMO_OVERLOAD_3P)
    S1 = d.device("S1", P.DEMO_PB_NC)
"""
GOOD = """    d.wire(Q0[2], K1.main[1], wire=(colours.BK, 2.5))
    d.wire(F1.main[2], K1[3], wire=("BK", 2.5))
    d.wire(S1.sw.A, F1.aux[95], wire=("BU", 0.75))
    d.wire(K1.coil.A1, S1.sw["B"], wire=("BU", 0.75))
"""
ADDED = '    cab = d.add(cab_unit, "CAB")\n    cab.X1\n    cab.L1[1]\n'
PLANTS = {
    "good": GOOD,
    "bad_pin": f'{GOOD}    d.wire(Q0[7], K1.main[1], wire=("BK", 2.5))\n',
    "bad_function": f'{GOOD}    d.wire(F1.mian[2], K1[3], wire=("BK", 2.5))\n',
    "bad_part": f'{GOOD}    d.device("Q9", P.MCB_9P)\n',
    "good_unit": ADDED,
    "bad_field": f"{ADDED}    cab.L11\n",
    "good_interface": (
        '    d.device("K2", P.DEMO_CTR_3P_24, interface=("main",), unused=("aux",))\n'
    ),
    "bad_interface": '    d.device("K2", P.DEMO_CTR_3P_24, interface=("main", "mian"))\n',
}


@pytest.fixture(scope="module")
def errors(tmp_path_factory) -> dict[str, int]:
    """Error count per planted file, from one ty run over all four."""
    folder = tmp_path_factory.mktemp("ty")
    (folder / "gparts.py").write_text(parts_module("demo_parts"), encoding="utf-8")
    for name, body in PLANTS.items():
        (folder / f"{name}.py").write_text(HEAD + body, encoding="utf-8")
    run = subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run", "ty", "check", "--project", str(ROOT)),
            *("--extra-search-path", str(folder), "--output-format", "concise"),
            *(str(folder / f"{n}.py") for n in PLANTS),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1, run.stdout + run.stderr  # ty ran and found the planted slips
    counts = dict.fromkeys(PLANTS, 0)
    for match in re.finditer(r"[\\/](\w+)\.py:\d+:\d+: error", run.stdout):
        counts[match.group(1)] += 1
    return counts


def test_a_typed_circuit_on_the_demo_module_passes(errors) -> None:
    assert errors["good"] == 0
    assert errors["good_interface"] == 0
    assert errors["good_unit"] == 0


def test_a_misspelt_unit_field_gives_one_error(errors) -> None:
    assert errors["bad_field"] == 1


def test_an_interface_name_the_part_lacks_gives_one_error(errors) -> None:
    assert errors["bad_interface"] == 1


@pytest.mark.parametrize("name", ["bad_pin", "bad_function", "bad_part"])
def test_each_slip_gives_exactly_one_error(errors, name) -> None:
    assert errors[name] == 1
