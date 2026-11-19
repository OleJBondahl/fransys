"""Field case: a unit whose boundary is a bridged 24V run and GND run, fed by a DC supply inside it, inside a container with lamps.
The bug: layout raised LayoutError (a unit's boundary names a function that has no spec), since layout read dropped the rail terminal (V3).
Fixed by layout-0120, the container's page draws the child's boundary terminal as its black-box terminal, one data and two views."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages, markers_in, ref_texts, tag_texts

from electrical_symbols import power_symbol_key
from fransys_model.derive import boundary_rail_wires, conductor_ends, item_of_port, item_unit, rail_source_unit
from fransys_model.derive import unit_system_designation as tag
from fransys_model.derive.stands import stands
from fransys_model.layout import DrawingSet, Page, PowerSymbol, layout_of
from fransys_model.vocab.tables import ports, unit_releases, units

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]


@fr.unit("demo-rail-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    lamp = u.device("P1", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", interface=True)
    plus, minus = x1.run("24V", 2, bridged=True, rail=True), x1.run("GND", 2, bridged=True, rail=True)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.series(dc.plus.pin, plus[1].inner, wire=("RD", 0.75))
    u.series(dc.minus.pin, minus[1].inner, wire=("BK", 0.75))
    u.series(plus[1].inner, lamp.lamp["1"], wire=("RD", 0.75))
    u.series(minus[1].inner, lamp.lamp["2"], wire=("BK", 0.75))
    return _Io((plus[1], plus[2], minus[1], minus[2]))


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    lamps = (d.device("H1", "DEMO-LAMP-24"), d.device("H2", "DEMO-LAMP-24"))
    for pair, pole in ((io.rail[:2], "1"), (io.rail[2:], "2")):
        for terminal, lamp in zip(pair, lamps, strict=True):
            d.series(terminal.outer, lamp.lamp[pole], wire=("RD", 0.75))
    (tmp_path / "own.md").write_text("# Rail box\n", encoding="utf-8")
    (tmp_path / "box.md").write_text("# Container\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-rail-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "box.md"))


def _set_unit_names(model: Any) -> dict[Any, str | None]:
    """The unit release name of each page's drawing set (`None`: the container's own set)."""
    sets = layout_of(model, DrawingSet)
    named = {}
    for page in layout_of(model, Page).values():
        unit = sets[page.drawing_set].unit
        named[page.id] = None if unit is None else unit_releases(model)[units(model)[unit].release].name
    return named


def test_the_container_draws_the_boundary_terminal_and_the_unit_its_power_symbol(
    tmp_path: Path,
) -> None:
    """No LayoutError, 0 ERROR; `-U1-X1:24V:1` is on the container's page with its wire; the
    unit's own pages hold the rail's power symbol."""
    result = _build(tmp_path)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    model = result.model
    owner = _set_unit_names(model)
    pages = drawn_pages(model)
    designation = "-U1-X1:24V:1"
    tagged = {owner[page] for page, d in pages.items() if tag_texts(d, designation)}
    assert tagged == {None}  # the unit's own pages draw it as no terminal
    # the container draws the boundary strip itself, wired to the lamp: no stub names the terminal (R729)
    assert not any(designation in text for d in pages.values() for m in markers_in(d) for text in ref_texts(m))
    assert "demo-rail-box" in {owner[s.page] for s in layout_of(model, PowerSymbol).values()}


def test_the_wires_into_the_boundary_rail_terminals_are_the_four_lamp_wires(tmp_path: Path) -> None:
    """The container's four lamp wires end on a rail terminal of the unit boundary; the unit's inner wires do not."""
    model = _build(tmp_path).model
    assert len(boundary_rail_wires(model)) == 4


def test_no_function_is_left_unwired_and_no_connection_undrawn(tmp_path: Path) -> None:
    """DS2 part 7: the lamp wires into the boundary rail terminals are nets, so every terminal is wired and drawn."""
    codes = [f.code for f in fr.check(_build(tmp_path))]
    assert "FUNCTION_NOT_WIRED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes


def test_a_pin_wired_to_a_boundary_rail_terminal_stands_no_power_symbol(tmp_path: Path) -> None:
    """R868: the four lamp pins are drawn by their wires, so no anchor stands on them; the unit's own rail pins still do."""
    model = _build(tmp_path).model
    wired = {p for w in boundary_rail_wires(model) for p in conductor_ends(model, w)}
    stood = stands(model)
    assert wired
    assert not wired & stood.keys()
    assert stood  # the unit's own lamp and supply pins stand their rails


# Second case (KI-1095, R2589): two unbonded 0 V sources in one cabinet raised RAIL_IDENTITY_SHARED; each ground now prints its unit's tag.
class _Gnd(NamedTuple):
    out: fr.Terminal


def _source_unit(key: str, names: tuple[str, str] | None) -> Any:
    """A source unit: a supply feeding a lamp, its minus pole on an interface strip; `names` renames its rails as `dc_supply(names=)` does."""

    @fr.unit(key, revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def make(u: fr.Design) -> _Gnd:
        psu = u.device("T1", "DEMO-PSU-24")
        lamp = u.device("P1", "DEMO-LAMP-24")
        strip = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", interface=True).run("GND", 1)
        dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24, names=names)
        u.series(dc.plus.pin, lamp.lamp["1"], wire=("RD", 0.75))
        u.series(dc.minus.pin, lamp.lamp["2"], wire=("BK", 0.75))
        u.series(lamp.lamp["2"], strip[1].inner, wire=("BK", 0.75))
        return _Gnd(strip[1])

    return make


_gnd_source = _source_unit("demo-gnd-src", None)
_named_source = _source_unit("demo-gnd-src-named", ("24V", "GND"))


class _Recv(NamedTuple):
    ground: fr.Run


@fr.unit("demo-gnd-recv", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _gnd_receiver(u: fr.Design) -> _Recv:
    return _Recv(u.terminal_strip("XR", "DEMO-TB-2.5", interface=True).run("G", 2))


class _Top(NamedTuple):
    pass


def _gnd_top(*, bonded: bool, unit: Any) -> Any:
    """A parent unit holding two source instances and the receiver (the reported shape); `bonded` adds the bond wire between the sources."""

    @fr.unit("demo-gnd-top", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def top(u: fr.Design) -> _Top:
        first, second, recv = u.add(unit, "J1"), u.add(unit, "J2"), u.add(_gnd_receiver, "R1")
        u.series(first.out.outer, recv.ground[1].outer, wire=("BK", 0.75))
        u.series(second.out.outer, recv.ground[2].outer, wire=("BK", 0.75))
        if bonded:
            u.series(first.out.outer, second.out.outer, wire=("BK", 0.75))
        return _Top()

    return top


def _build_receiver(tmp_path: Path, *, bonded: bool, unit: Any = _gnd_source) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    top = d.add(_gnd_top(bonded=bonded, unit=unit), "U1")
    (tmp_path / "cover.md").write_text("# Cover\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, top, cover=tmp_path / "cover.md"))


def _ground_texts(model: Any) -> set[str]:
    """The text every drawn ground symbol prints."""
    ground = power_symbol_key("ground")
    return {text for page in drawn_pages(model).values() for sym in page.symbols if sym.key == ground for _, text in sym.slots}


def test_two_unbonded_ground_sources_print_their_unit_tags_and_raise_no_identity_finding(tmp_path: Path) -> None:
    """R2589: each ground symbol of the receiving cabinet prints its source unit's tag, and no RAIL_IDENTITY_SHARED."""
    result = _build_receiver(tmp_path, bonded=False)
    assert "RAIL_IDENTITY_SHARED" not in [f.code for f in fr.check(result)]
    assert {"0V -U1-J1", "0V -U1-J2"} <= _ground_texts(result.model)


def test_a_qualified_ground_prints_the_declared_minus_pole_name(tmp_path: Path) -> None:
    """R2592: with `names=("24V", "GND")` the receiving cabinet's grounds print `GND -U1-J1` and `GND -U1-J2`, the rail's declared name."""
    model = _build_receiver(tmp_path, bonded=False, unit=_named_source).model
    assert {"GND -U1-J1", "GND -U1-J2"} <= _ground_texts(model)


def test_two_bonded_ground_sources_print_no_ground_text_and_raise_no_identity_finding(tmp_path: Path) -> None:
    """V3: a bond wire between the two sources is one supply to the cabinet: nothing changes, ground prints no text."""
    result = _build_receiver(tmp_path, bonded=True)
    assert "RAIL_IDENTITY_SHARED" not in [f.code for f in fr.check(result)]
    assert _ground_texts(result.model) == set()


def test_rail_source_unit_names_the_declaring_unit_of_each_unbonded_source_and_nothing_else(tmp_path: Path) -> None:
    """R2589: in the receiving cabinet the fact is the unit of each source; in a source's own cabinet, and when bonded, it is None."""
    for bonded in (False, True):
        model = _build_receiver(tmp_path, bonded=bonded).model
        found = set()
        for p in ports(model):
            source, cabinet = rail_source_unit(model, p), item_unit(model, item_of_port(model, p))
            if source is not None and cabinet is not None:
                found.add((tag(model, cabinet), tag(model, source)))
        assert found == (set() if bonded else {("-U1-R1", "-U1-J1"), ("-U1-R1", "-U1-J2")})


def test_a_fused_supply_in_a_qualified_cabinet_prints_the_device_then_the_source_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2591: a supply text that carries its protective device's tag takes the declaring unit's tag last: `24V -F2 -U1`."""
    from fransys_model.derive import power
    from fransys_model.vocab import PowerKind

    monkeypatch.setattr(power, "rail_source_unit", lambda _m, _port: "unit")
    monkeypatch.setattr(power, "unit_system_designation", lambda _m, _unit: "-U1")
    assert power._printed(None, "24V -F2", PowerKind.SUPPLY, "port") == "24V -F2 -U1"  # ty: ignore[invalid-argument-type] patched reads
