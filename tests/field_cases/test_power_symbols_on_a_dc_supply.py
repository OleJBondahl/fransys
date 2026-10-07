"""Field case: the supply, 0 V and earth pins of a PLC input module, its loads and a PSU, on a
declared DC supply, are drawn with power symbols and not with `#n` references.

The engineering shape: a 24 V DC supply with rails 24 V and 0 V, a PSU, PLC input channels, lamps
on the same two rails and motors whose earth pins sit on a PE net. Every pin is wired to its
rail's hub, so on a plant this size a page of pins is cut from its hub and each cut end, today,
is a reference box with a `#n` digit, and the rails run as horizontal bands.

The rule (decisions model-0117, layout-0094, render-0005; spec LD4, LD8, D5): an end that would be
a reference on a DC supply's rail takes a symbol instead: a bar for a rail above or below 0 V,
the ground symbol for 0 V, protective earth for a PE net. Only the bar prints a text, the net's
name (else the potential); ground and PE print none. The symbol continues its pin's direction,
turned as needed. An AC supply keeps its references (LD8). Owner's A4-A6, 2026-10-02: A4 is
supply-only text, A5 and A6 confirmed.

Bars: a symbol per cut end and none per joined run, no `#n` and no `CONNECTION_NOT_DRAWN`, the
member check and the nowhere guard count each symbol as a draw, and AC ends stay references.
"""

import dataclasses
from collections import Counter
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import overlaps, translate
from fransys_layout.lint import check_members, check_nowhere
from fransys_layout.stages import pagerun
from fransys_layout.stages.texts.power import power_places
from fransys_layout.stages.types import NetGroup, Role
from fransys_model.derive import port_power_text
from fransys_model.layout import (
    Label,
    LinkMarker,
    Orientation,
    Page,
    PowerSymbol,
    layout_of,
)
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from pathlib import Path

_LOADS = 5
_P0_PIN_2 = ("B/P0", "fn", "lamp", "port", "2")
_P4_PIN_2 = ("B/P4", "fn", "lamp", "port", "2")
_PSU_PLUS = ("B/T1", "fn", "output", "port", "+")
_PSU_MINUS = ("B/T1", "fn", "output", "port", "-")


def _build(tmp_path: Path, plant) -> fr.BuildResult:
    """A cabinet with `plant(d)`'s devices in function block B, one document."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _hub(d, hub, members) -> None:
    """Every pin of `members` wired to the rail's `hub` pin."""
    for pin in members:
        d.wire(hub, pin, wire=(BU, 0.5))


def _dc_plant(  # noqa: PLR0913 - one keyword per plant variation, all keyword-only
    *,
    loads=_LOADS,
    motor_on_24: bool = False,
    earth: bool = True,
    gnd: bool = False,
    ac=False,
    block: str = "B",
):
    """A PSU, PLC input channels and lamps on a supply S; the PSU's `L` and `N` on an AC supply.

    `gnd` puts every second lamp's 0 V pin on the 0 V rail of a second supply (a second PSU).
    `ac` makes S the three-phase supply of the PSU's own input and a terminal strip: the plant
    stands on its rails L2 and L3, so the references of an AC supply stay.
    """

    def plant(d) -> None:
        with d.function(block, "Group"):
            psu = d.device("T1", "DEMO-PSU-24")
            loads_ = [
                (d.device(f"K{i}", "DEMO-PLC-DI-2"), d.device(f"P{i}", "DEMO-LAMP-24"))
                for i in range(loads)
            ]
            motors = [d.device(f"M{i}", "DEMO-MOTOR-4KW") for i in range(3)]
            other = d.device("T2", "DEMO-PSU-24") if gnd else None
            strip = d.terminal_strip("X1", "DEMO-TB-2.5", 3) if ac else None
        plus, zero = psu.output["+"], psu.output["-"]
        if strip is not None:
            d.ac_supply("S", 230, psu.input["L"], strip[2], strip[3], n=psu.input["N"])
            plus, zero = strip[2], strip[3]
        else:
            d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
            d.dc_supply("S", psu)
        if other is not None:
            d.dc_supply("S2", other, names=("24V2", "GND"))
        members = [psu.output["+"]] if strip is not None else []
        zeros = [psu.output["-"]] if strip is not None else []
        for i, (di, lamp) in enumerate(loads_):
            members += [di.di_1["1"], lamp["1"]]
            if other is not None and i % 2:
                _hub(d, other.output["-"], [lamp["2"]])
            else:
                zeros.append(lamp["2"])
        if motor_on_24:
            members.append(motors[0].motor["U"])
        _hub(d, plus, members)
        _hub(d, zero, zeros)
        if earth:
            pe = [m.motor["PE"] for m in motors]
            _hub(d, pe[0], pe[1:])
            d.earth(*pe)

    return plant


def _symbols(model, name: str | None = None) -> list[PowerSymbol]:
    found = layout_of(model, PowerSymbol).values()
    return [one for one in found if name is None or one.symbol == name]


def _text_of(model, symbol: PowerSymbol) -> str | None:
    return port_power_text(model, symbol.port)


def _codes(result: fr.BuildResult) -> Counter:
    return Counter(f.code for f in fr.check(result))


def _no_error_codes(result: fr.BuildResult) -> set[str]:
    return {f.code for f in fr.check(result) if f.severity is fr.Severity.ERROR}


def _stage_run(model):
    inputs = read_inputs(model)
    results, _ = stage_results(model, inputs)
    return inputs, results


def _lint(results, inputs, layout) -> list:
    # V3: the rail nets leave `net_groups` (their wires are not drawn): one group of the rail ends
    ends = inputs.rail_ends
    rail = NetGroup(
        net=ends[0].connection,
        physical_net=ends[0].connection,
        role=Role.POWER,
        ports=tuple(one.ref for one in ends),
    )
    args = (layout, inputs.connections, (*inputs.net_groups, rail), results.drawn)
    return [*check_members(*args), *check_nowhere(*args)]


@pytest.fixture(scope="module")
def main(tmp_path_factory) -> fr.BuildResult:
    """The main plant, built once for every test that only reads it."""
    return _build(tmp_path_factory.mktemp("main"), _dc_plant(motor_on_24=True))


@pytest.fixture(scope="module")
def main_staged(main) -> tuple:
    """The main plant's inputs and staged results, run once; tests only read them."""
    return _stage_run(main.model)


def test_each_cut_24v_end_is_a_bar_and_each_cut_0v_end_a_ground(main) -> None:
    model = main.model
    assert Counter(one.symbol for one in _symbols(model)) == Counter(
        {"power-supply": 12, "ground": 6, "protective-earth": 3}
    )  # the PSU's 0 V and the last lamp's 0 V are a fallen-back join, two grounds (D5, step 6)
    # 12 bars, not 11: the fixture declares T1's AC side (MAINS on L1 and N), so T1:+ no longer
    # shares a wire with P4:1 and each gets its own bar (D5, designer's ruling of 2026-10-02)
    # one symbol per port and page, never two at a pin
    assert len({(one.port, one.page) for one in _symbols(model)}) == len(_symbols(model))
    # the fixture spans three sheets of schematic
    assert len(layout_of(model, Page)) == 3


def test_power_ends_print_the_net_name_and_no_hash_reference(main) -> None:
    model = main.model
    names = {"power-supply": "24V", "ground": None, "protective-earth": None}
    for one in _symbols(model):
        assert _text_of(model, one) == names[one.symbol]
    power_ports = {one.port for one in _symbols(model)}
    named = {one.port for one in _symbols(model) if one.symbol == "power-supply"}
    labelled = {one.port for one in layout_of(model, Label).values() if one.slot == "power"}
    assert labelled == named
    assert power_ports.isdisjoint(one.port for one in layout_of(model, LinkMarker).values())


def test_no_connection_is_undrawn_and_the_build_has_no_error(main) -> None:
    result = main
    assert _no_error_codes(result) == set()
    assert "CONNECTION_NOT_DRAWN" not in _codes(result)
    assert "TEXT_OVERLAP" not in _codes(result)
    assert "LABEL_UNPLACED" not in _codes(result)


def test_the_lint_counts_each_symbol_as_a_draw(main_staged) -> None:
    """Drop one symbol's marker from the layout copy and the member check names its port."""
    inputs, results = main_staged
    layout = results.layout
    ends = [one for one in layout.markers if one.symbol]
    assert _lint(results, inputs, layout) == []
    bare = dataclasses.replace(layout, markers=tuple(m for m in layout.markers if not m.symbol))
    reported = {s for f in _lint(results, inputs, bare) for s in f.subjects}
    # V3: no rail wire is drawn, so a symbol is the only cover of its pin and every end is named
    bare_ends = [one for one in ends if one.port in reported]
    assert len(bare_ends) == len(ends)
    one = bare_ends[0]
    kept = tuple(m for m in layout.markers if m is not one)
    found = _lint(results, inputs, dataclasses.replace(layout, markers=kept))
    assert {f.code for f in found} == {"CONNECTION_NOT_DRAWN"}
    assert one.port in {s for f in found for s in f.subjects}


@pytest.mark.parametrize("loads", [5, 8])
def test_no_power_text_stands_on_a_symbol_body(tmp_path, loads: int) -> None:
    """A power text stands on no placed function's body, its own function's included.

    The power ends' reserved reference boxes (drawn as no box) block no text: a lamp's pin 1
    text once fell to the lamp's top edge for want of room beside the bar.
    """
    _, results = _stage_run(_build(tmp_path, _dc_plant(loads=loads)).model)
    layout = results.layout
    texts = [one for one in layout.labels if one.slot == "power"]
    assert texts
    bodies = {
        (one.port, one.drawing_set, one.page): one.body for one in power_places(layout.markers)
    }
    for text in texts:
        body = bodies[text.subject, text.drawing_set, text.page]
        # past its symbol (layout-0114), not pushed down its lead by the end's unused box
        above = body.y - text.box.height - 4 <= text.box.y <= body.y - text.box.height
        below = body.y + body.height <= text.box.y <= body.y + body.height + 4
        assert above or below
    for text in texts:
        for one in layout.placed:
            if (one.drawing_set, one.page) == (text.drawing_set, text.page):
                body = translate(one.geometry.body, dx=one.at.x, dy=one.at.y)
                assert not overlaps(text.box, body)


def _key5(model, port) -> tuple:
    """The last five parts of `port`'s key: item tag, `fn`, function, `port`, name."""
    return ports(model)[port].key[-5:]


def test_a_power_text_stands_on_no_symbols_lead_or_body(main, main_staged) -> None:
    """D5, step 6: "24V" at the PSU's `+` stood on its `-`'s lead; it now takes its free side.

    Every power symbol's lead and body are in the placer's `Space` for every text, not only for
    its own: no power text overlaps any symbol's lead or body on its page, and the `+` text
    stands past its bar (layout-0114), below the bar hung under the PSU's `+` pin.
    """
    model = main.model
    _, results = main_staged
    layout = results.layout
    places = power_places(layout.markers)
    texts = [one for one in layout.labels if one.slot == "power"]
    assert texts
    for text in texts:
        for place in places:
            if (place.drawing_set, place.page) == (text.drawing_set, text.page):
                assert not overlaps(text.box, place.lead), (text.subject, place.port)
                assert not overlaps(text.box, place.body), (text.subject, place.port)
    (plus,) = (one for one in places if _key5(model, one.port) == _PSU_PLUS)
    (label,) = (one for one in texts if one.subject == plus.port)
    assert label.box.y >= plus.body.y + plus.body.height  # a bar hung below its pin: text below


def test_the_slot_label_placer_holds_every_power_lead_and_body(main, monkeypatch) -> None:
    """D5, step 6: the text placer's `Space` holds the power leads and bodies, not only power's.

    The second slot call's `occupied` is recorded: each page's call holds every power symbol's
    lead and body.
    """
    seen: list[set] = []
    slot_placer = pagerun.place_slot_labels

    def slot(*args, occupied, **kwargs):
        seen.append(set(occupied))
        return slot_placer(*args, occupied=occupied, **kwargs)

    monkeypatch.setattr(pagerun, "place_slot_labels", slot)
    _, results = _stage_run(main.model)  # run again: the patched placer must be called
    power = {(one.drawing_set, one.page): [] for one in power_places(results.layout.markers)}
    for one in power_places(results.layout.markers):
        power[one.drawing_set, one.page] += [one.body, one.lead]
    # `seen` is the second slot call only (the first one is not patched here), so dropping the
    # power shapes from that call fails this loop; every page's power boxes are in one call
    assert seen
    for boxes in power.values():
        assert any(set(boxes) <= held for held in seen)


def test_a_conductor_between_two_0v_pins_is_two_grounds_and_no_join(main, main_staged) -> None:
    """V3: `-P4:2` to `-T1:-` is two grounds, no route, and no join is tried: no `JOIN_UNALIGNED`.

    Both pins are on the 0 V rail, so the conductor between them is not drawn (it was a join
    that fell back to symbols with `JOIN_UNALIGNED`, D1 and D5 step 6).
    """
    result = main
    model = result.model
    _, results = main_staged
    ends = {_P4_PIN_2, _PSU_MINUS}
    grounds = {_key5(model, one.port) for one in _symbols(model, "ground")}
    assert ends <= grounds
    assert results.layout.routes == ()
    assert [f for f in fr.check(result) if f.code == "JOIN_UNALIGNED"] == []


def test_a_power_supply_has_ac_pins_on_top_and_dc_pins_at_the_bottom(main_staged) -> None:
    """The PSU's `L` and `N` stand on the AC supply, so they sit above its `+` and `-` (D5)."""
    _, results = main_staged
    (psu,) = (one for one in results.layout.placed if one.column[0] == "B/T1")
    side = {g.name: g.facing.value for g in psu.geometry.ports}
    assert side == {"input.L": "n", "input.N": "n", "output.+": "s", "output.-": "s"}


def test_the_build_is_the_same_every_time(main, tmp_path) -> None:
    first = main.model  # the shared build against one fresh build: the fresh one cannot be shared
    second = _build(tmp_path, _dc_plant(motor_on_24=True)).model
    assert layout_of(first, PowerSymbol) == layout_of(second, PowerSymbol)


def test_a_pin_facing_south_gets_a_symbol_hung_below_it(main) -> None:
    """A lamp's 0 V pin stands on the lower edge (D5): its ground hangs below, its bar is above."""
    model = main.model
    table = ports(model)
    lamp_0v = [one for one in _symbols(model) if table[one.port].key[-5:] == _P0_PIN_2]
    assert [(one.symbol, one.orientation) for one in lamp_0v] == [("ground", Orientation.R0)]
    north = [one for one in _symbols(model, "power-supply") if table[one.port].key[-5] == "B/P0"]
    assert {one.orientation for one in north} == {Orientation.R0}


def test_pe_prints_no_text_and_takes_protective_earth(main) -> None:
    model = main.model
    earth = _symbols(model, "protective-earth")
    assert all(_text_of(model, one) is None for one in earth)
    assert {one.symbol for one in _symbols(model)} <= {"power-supply", "ground", "protective-earth"}


def test_a_0v_net_and_a_gnd_net_both_print_no_text(tmp_path) -> None:
    result = _build(tmp_path, _dc_plant(loads=6, gnd=True))
    model = result.model
    grounds = _symbols(model, "ground")
    # 6 before V3; the 7th: a conductor between two 0 V pins is two grounds, not a fallback join;
    # the 8th: the second PSU's `-` is the GND rail's own pin, a ground of its own
    assert Counter(_text_of(model, one) for one in grounds) == {None: 8}
    assert _no_error_codes(result) == set()


def _negative_plant(d) -> None:
    with d.function("B", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(3 * _LOADS)]  # cut across pages
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
    # the PSU's `+` is the 0 V mid, its `-` the -15 V rail; the strip pin is the unused +15 V
    d.dc_supply("S", plus=strip[1], mid=psu.output["+"], minus=psu.output["-"], voltage=15)
    _hub(d, psu.output["-"], [lamp["1"] for lamp in lamps])
    _hub(d, psu.output["+"], [lamp["2"] for lamp in lamps])


def test_a_negative_dc_rail_is_a_supply_printing_its_name_with_the_sign(tmp_path) -> None:
    """Owner's A6, confirmed 2026-10-02: any DC rail that is not 0 V is a supply, sign included."""
    result = _build(tmp_path, _negative_plant)
    model = result.model
    bars = _symbols(model, "power-supply")
    assert bars
    assert {_text_of(model, one) for one in bars} == {"-15V"}
    assert _no_error_codes(result) == set()


def test_an_ac_supply_keeps_its_references(tmp_path) -> None:
    """LD8: the same plant on L2 and L3 of an AC supply: no symbol, references as before."""
    plant = _dc_plant(motor_on_24=True, earth=False, ac=True)
    model = _build(tmp_path, plant).model
    assert _symbols(model) == []
    assert layout_of(model, LinkMarker)


def _shape(model, results) -> dict:
    """Every power symbol's origin and orientation and every power text's box, by pin and page."""
    layout = results.layout
    texts = {(one.subject, one.page): one.box for one in layout.labels if one.slot == "power"}
    return {
        ((_key5(model, one.port)[0].split("/")[1], *_key5(model, one.port)[1:]), one.page): (
            one.at,
            one.orientation,
            texts.get((one.port, one.page)),
        )
        for one in power_places(layout.markers)
    }


def test_the_power_shape_does_not_depend_on_the_name_of_the_block(
    main, main_staged, tmp_path
) -> None:
    """Step 5 (i): the same circuit under any block name draws every symbol and text alike.

    The PSU's `+` and `-` stand on one side and take their leads in turn; which one took the
    first free lead was the order of their port ids, a hash of the block's name.
    """
    shapes = [_shape(main.model, main_staged[1])]  # block B is the shared main plant
    for block in ("A", "C", "D"):
        model = _build(tmp_path, _dc_plant(motor_on_24=True, block=block)).model
        shapes.append(_shape(model, _stage_run(model)[1]))
    assert shapes[1:] == shapes[:1] * 3


def _adjacent_pins_plant(d) -> None:
    with d.function("B", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        plc = d.device("K1", "DEMO-PLC-DI-16")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    _hub(d, psu.output["+"], [plc[str(i)] for i in range(1, 5)])


def test_a_supply_bars_text_sits_past_its_bar_and_crosses_no_lead(tmp_path) -> None:
    """Step 5 (ii), owner 2026-10-05: the text of a supply bar stands past the bar, upright.

    Four pins of one module on one rail: the text of each bar stands above it (the pin faces
    north), centred on its lead; the PSU's bar hangs below its pin and its text below it. It
    never stands beside the bar: a text beside the third bar ran through the fourth bar's lead.
    Decision layout-0114.
    """
    _, results = _stage_run(_build(tmp_path, _adjacent_pins_plant).model)
    layout = results.layout
    places = power_places(layout.markers)
    texts = [one for one in layout.labels if one.slot == "power"]
    assert len(texts) == 5  # the four pins and the PSU`s +
    assert not [one for one in texts if one.unplaced]
    for text in texts:
        (own,) = (one for one in places if one.port == text.subject)
        if own.lead.y < own.body.y:  # a bar hung under its pin: the text goes below it
            assert text.box.y >= own.body.y + own.body.height
        else:
            assert text.box.y + text.box.height <= own.body.y
        assert abs(text.box.x + text.box.width // 2 - (own.lead.x + own.lead.width // 2)) <= 1
        for other in places:
            assert not overlaps(text.box, other.lead), (text.subject, other.port)
