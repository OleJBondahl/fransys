"""`cores.csv` lists every core of every cable with its ends, pair and spare mark (reports-0005).

The worked example, a paired cable with a one-ended screen, and a unit's cable that stays in the
unit's own build.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.vocab.tables import units as units_table

_HEADER = "cable,core,colour,pair,end_a,end_b,note"


def _cores_csv(written: tuple[Path, ...]) -> str:
    (csv,) = [p for p in written if p.name.endswith("cores.csv")]
    return csv.read_text(encoding="utf-8").replace("\r\n", "\n")


def _lines(text: str) -> list[str]:
    return text.strip().split("\n")


@cache
def _worked() -> fr.BuildResult:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
    w1.core(1, x1[1], h1[1])
    w1.core(2, x1[2], h1[2])
    w1.spare(3, at=x1[7])
    w1.spare()
    return fr.build(d)


@cache
def _paired() -> fr.BuildResult:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w1.core(1, x1[1], h1[1])
    w1.core(2, x1[2], h1[2])
    w1.spare(3, at=x1[7])
    w1.core(5, x1[8])
    w1.spare()
    return fr.build(d)


class _Open(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, k1.coil["A1"], k2.coil["A1"])
    cable.core(2, k1.coil["A2"], k2.coil["A2"])
    return _Open()


@cache
def _with_unit() -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cabinet\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.location("CAB", "Cabinet")
        d.add(_cab, "U1", place="CAB")
        schematic = fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            "demo-cab",
            cover=cover,
            add=(fr.PageKind.CABLE_LIST,),
        )
        return fr.build(d, schematic)


def test_the_worked_example_lists_every_core_with_its_ends(tmp_path: Path) -> None:
    text = _cores_csv(fr.write(_worked(), tmp_path))
    assert text == (
        f"{_HEADER}\n"
        "-W1,1,BN,,-H1:1,-X1:1,\n"
        "-W1,2,BK,,-H1:2,-X1:2,\n"
        "-W1,3,GY,,-X1:7,,spare\n"
        "-W1,4,GNYE,,,,spare\n"
    )


def test_a_paired_cable_prints_pairs_screens_and_the_earthed_end(tmp_path: Path) -> None:
    lines = _lines(_cores_csv(fr.write(_paired(), tmp_path)))
    assert lines[0] == _HEADER
    assert "-W1,5,SH,screen P1,-X1:8,," in lines
    assert "-W1,6,SH,screen P2,,," in lines
    assert "-W1,3,WH,P2,-X1:7,,spare" in lines


def test_a_units_cable_is_in_the_units_cores_csv_only(tmp_path: Path) -> None:
    assert units_table(_with_unit().model)
    system = _lines(_cores_csv(fr.write(_with_unit(), tmp_path / "system")))
    assert system == [_HEADER]
    own = _lines(_cores_csv(fr.write(_with_unit(), tmp_path / "unit", unit="demo-cab")))
    assert [row.split(",")[:2] for row in own[1:]] == [["-W1", "1"], ["-W1", "2"]]
