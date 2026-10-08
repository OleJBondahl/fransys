"""Field case: an assembly unit offers its board unit's connector as its own (author-0032).

The engineering shape: an assembly unit holds a board unit; the assembly's outside
connector is the board's, `X7`. The assembly returns the board's field, as the guide
promises ("the tuple the function returns names the devices a container can reach"). A
container mates a harness plug to that connector and wires the plug.

The bug: `write_boundaries` wrote a `Boundary` only for a device the scope's own `interface=True`
held, so the returned field made no boundary of the assembly, and the container's wire gave
`UNIT_BOUNDARY_BYPASSED`. The rule (decision author-0032, spec patch-0-13-1 P1 to P5): a field
that holds a boundary function of a directly nested unit makes it this unit's boundary too, one
level at a time; a field holding a function that is no boundary of the nested unit writes
nothing. The print is the real path from the document's unit: `-U1-U2-X7` on the
container's page, `-U2-X7` on the assembly's, `-X7` on the board's.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


def _board_fn(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    k1 = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.wire(x7[1], k1["1"], wire=(BK, 0.5))
    u.wire(x7[2], k1["2"], wire=(BK, 0.5))
    return _Io(x7)


_board = fr.unit(
    "demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)(_board_fn)


@fr.unit("demo-asm", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _asm(u: Any) -> _Io:
    return _Io(u.add(_board, "U2").X7)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    asm = u.add(_asm, "U1")
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    harness = u.harness("W5")
    plug = u.device("P5", "DEMO-HSG-4M", parent=harness, contacts="DEMO-CRIMP-M")
    u.mate(plug, asm.X7)
    u.wire(plug[1], psu.output["+"], wire=(BK, 0.5))
    u.wire(plug[2], psu.output["-"], wire=(BK, 0.5))
    return _Open()


def _errors(result: fr.BuildResult) -> list[str]:
    return [f.code for f in result.findings if f.severity.name == "ERROR"]


def test_the_assembly_returning_its_boards_connector_has_no_bypass() -> None:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    assert _errors(fr.build(d)) == []


class _Written(NamedTuple):
    board: list[str]
    asm: list[str]
    cab: list[str]


@pytest.fixture(scope="module")
def written() -> _Written:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    docs = []
    for stem, preset, name in (
        ("cab", fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab"),
        ("asm", fr.DocumentPreset.CABINET_SCHEMATIC, "demo-asm"),
        ("board", fr.DocumentPreset.PCB_SCHEMATIC, "demo-board"),
    ):
        (root / f"{stem}.md").write_text(f"# {stem}\n", encoding="utf-8")
        docs.append(fr.document(preset, name, cover=root / f"{stem}.md"))
    result = fr.build(d, *docs)
    assert _errors(result) == []
    fr.write(result, root / "out", intermediates=root / "inter")
    model = result.model
    names = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)

    def texts(name: str) -> list[str]:
        found: list[str] = []
        for page in layout_of(model, Page).values():
            if sets[page.drawing_set].unit == names[name]:
                svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
                found += re.findall(r">([^<>]+)</text>", svg)
        return found

    return _Written(texts("demo-board"), texts("demo-asm"), texts("demo-cab"))


def test_the_container_prints_the_real_path(written: _Written) -> None:
    assert "-U1-U2-X7" in written.cab
    assert "-U1-X7" not in written.cab


def test_the_assembly_prints_the_path_from_itself(written: _Written) -> None:
    assert "-U2-X7" in written.asm
    assert [t for t in written.asm if "U1" in t] == []  # its own tag


def test_the_board_prints_the_connector_locally(written: _Written) -> None:
    assert "-X7" in written.board
    assert [t for t in written.board if "U2" in t or "U1" in t or "C1" in t] == []


# -- P2 and P3 ------------------------------------------------------------------------------

_LEAK: dict[str, Any] = {}


@fr.unit("demo-inner", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _inner(u: Any) -> _Io:
    return _board_fn(u)


@fr.unit("demo-hides", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _hides(u: Any) -> _Open:
    _LEAK["io"] = u.add(_inner, "U2")
    return _Open()


@fr.unit("demo-skips", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _skips(u: Any) -> _Io:
    u.add(_hides, "U5")
    return _Io(_LEAK["io"].X7)


@fr.unit(
    "demo-two-levels", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
def _two_levels(u: Any) -> _Io:
    return _Io(u.add(_asm, "U5").X7)


def _container(unit: Any, plug_unit_field: str = "X7") -> list[str]:
    @fr.unit(
        "demo-outer", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
    )
    def outer(u: Any) -> _Open:
        nested = u.add(unit, "U3")
        psu = u.device("T1", "DEMO-PSU-24")
        u.dc_supply("S", psu)
        harness = u.harness("W5")
        plug = u.device("P5", "DEMO-HSG-4M", parent=harness, contacts="DEMO-CRIMP-M")
        u.mate(plug, getattr(nested, plug_unit_field))
        u.wire(plug[1], psu.output["+"], wire=(BK, 0.5))
        u.wire(plug[2], psu.output["-"], wire=(BK, 0.5))
        return _Open()

    d = fr.design("demo_parts")
    d.add(outer, "C1", place=None)
    return _errors(fr.build(d))


def test_a_grandchild_the_child_does_not_pass_through_still_bypasses() -> None:
    assert "UNIT_BOUNDARY_BYPASSED" in _container(_skips)


def test_both_levels_passing_through_is_clean() -> None:
    assert _container(_two_levels) == []


@fr.unit("demo-lampbox", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _lampbox(u: Any) -> _Io:
    return _Io(u.device("K1", "DEMO-LAMP-24"))  # no `interface=True`: no boundary


@fr.unit(
    "demo-offers-lamp", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
def _offers_lamp(u: Any) -> _Io:
    return _Io(u.add(_lampbox, "U2").X7)


def test_a_returned_non_boundary_function_still_bypasses() -> None:
    @fr.unit(
        "demo-outer", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
    )
    def outer(u: Any) -> _Open:
        offered = u.add(_offers_lamp, "U3")
        psu = u.device("T1", "DEMO-PSU-24")
        u.dc_supply("S", psu)
        u.wire(offered.X7["1"], psu.output["+"], wire=(BK, 0.5))
        return _Open()

    d = fr.design("demo_parts")
    d.add(outer, "C1", place=None)
    assert "UNIT_BOUNDARY_BYPASSED" in _errors(fr.build(d))


def test_the_container_draws_one_outline_titled_for_the_assembly(written: _Written) -> None:
    """P6: the board is hidden inside the assembly's black box, which is the one outline."""
    assert written.cab.count("demo-asm rev 1.1") == 1
    assert [t for t in written.cab if "demo-board" in t] == []
