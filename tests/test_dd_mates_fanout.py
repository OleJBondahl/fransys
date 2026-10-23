"""One undo test per ruling for connectors and mated pairs and for fan-out nets, built
through the `fransys` facade from `examples/demo-parts` and read from
the page Drawings only (the Drawing carries no star kind and no port: R243).

Not covered: the cross-unit mate with its boundary pin as a replica cell under the parent-side
pin (needs the units worked example's fixture, which other tests own).
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _dd_core import pages_with, set_of
from _dd_core_b import is_stub, marker_strings, markers, symbols_of, tags_of
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.derive import item_designation
from fransys_model.derive.designation import port_designation
from fransys_model.vocab.tables import functions

_PROJECT: dict[str, Any] = {
    "title": "Mates and fan-out",
    "number": "P-1004",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _design():
    parts = fransys_parts.load("demo_parts")
    design = fransys_author.Design(parts)
    design.project(**_PROJECT)
    design.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, design, design.location("C1", "Cabinet"), design.group("A", "A")


def _placements(model, item, _function=None):
    """Every symbol drawn for the item authored as `item`, ordered by page, x and y.

    `_function` is not carried by the Drawing: the symbols beside the item's tags.
    """
    return [symbol for _, symbol in symbols_of(model, item)]


# -- connectors and mated pairs --------------------------------------------------------


def test_a_connector_is_one_view_per_wired_pin_and_an_idle_one_is_not_drawn() -> None:
    """Two wired pins are two views (mated pins too), and a connector with no wire is absent."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:pin_views
    #     keeps a connector as one view (no pin views)
    # UNDO: fransys_layout/engines/schematic/read/views.py:without_idle_pins
    #     keeps every pin (`kept = set(pin_of)`)
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", name="k2", at=c1, group=grp)
    plug = d.item("DEMO-CONN-2P", tag="J1", name="j1", at=c1, group=grp)
    socket = d.item("DEMO-CONN-2P", tag="J2", name="j2", at=c1, group=grp)
    d.item("DEMO-CONN-2P", tag="J7", name="j7", at=c1, group=grp)
    wire(k1.fn("co_1")["14"], plug["1"])
    wire(k2.fn("co_1")["14"], plug["2"])
    d.mate(plug, socket)
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    wired, mated = _placements(model, "j1", "x1"), _placements(model, "j2", "x1")
    assert len(wired) == 2
    assert {p.x for p in wired} == {p.x for p in mated}
    assert len({p.x for p in wired}) == 2
    assert _placements(model, "j7", "x1") == []


def _mated_pair(*, coil=None, contact=None):
    """J-A and J-B mated; relay K2's coil and relay K1's first contact wire the named halves."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", name="k2", at=c1, group=grp)
    pair = {
        name: d.item("DEMO-CONN-2P", tag=name, name=name.lower(), at=c1, group=grp)
        for name in ("JA", "JB")
    }
    if contact is not None:
        wire(k1.fn("co_1")["11"], pair[contact]["1"])  # 11 faces N: the pair stands above K1
    if coil is not None:
        wire(pair[coil]["1"], k2.fn("coil")["A1"])
    d.mate(pair["JA"], pair["JB"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _one(model, item, name="x1"):
    """The one placement of function `name` of `item` (a connector with one wired pin)."""
    (found,) = _placements(model, item, name)
    return found


@pytest.mark.parametrize("wired", ["ja", "jb"])
def test_the_half_a_chain_enters_first_stands_on_top(wired) -> None:
    """The pair stands face to face, the wired half nearest the relay it is wired to."""
    # UNDO: fransys_layout/stages/chains.py:discover_chains
    #     `upper_of[p] = poles[p].functions[1 - index]` (the OTHER function of the pair)
    model = _mated_pair(contact=wired.upper())
    (relay,) = _placements(model, "k1", "co_1")
    halves = {name: _one(model, name) for name in ("ja", "jb")}
    other = "jb" if wired == "ja" else "ja"
    assert halves["ja"].x == halves["jb"].x == relay.x
    assert halves[other].y < halves[wired].y < relay.y  # the entered-first (unwired) half on top


@pytest.mark.parametrize("coil", ["JA", "JB"])
def test_a_pair_between_two_relays_faces_each_half_to_the_item_it_is_wired_to(coil) -> None:
    """With both halves wired, each half stands next to its own relay, none crossing."""
    # UNDO: fransys_layout/stages/chains.py:discover_chains
    #     `upper_of[p] = poles[p].functions[1 - index]` (the OTHER function of the pair)
    contact = "JB" if coil == "JA" else "JA"
    model = _mated_pair(coil=coil, contact=contact)
    at_coil = _one(model, coil.lower())
    at_contact = _one(model, contact.lower())
    (relay,) = _placements(model, "k1", "co_1")
    (drive,) = _placements(model, "k2", "coil")
    assert drive.x == relay.x == at_coil.x == at_contact.x
    upper, lower = sorted((at_coil, at_contact), key=lambda p: p.y)
    ends = sorted((drive, relay), key=lambda p: p.y)
    assert ends[0].y < upper.y < lower.y < ends[1].y
    assert (upper is at_coil) is (ends[0] is drive)


def test_a_pair_in_no_chain_keeps_the_plug_on_top() -> None:
    """A harness plug over the device connector it mates, whatever the two keys say."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:_lower_rank
    #     `not _on_cable(...)` becomes `True`
    parts, d, c1, grp = _design()
    far, field = d.location("FLD", "Field"), d.group("F", "Field")
    harness = d.harness(name="w3", tag="W3", at=c1, group=field)
    plug = d.item("DEMO-CONN-2P", tag="P9", name="p9", parent=harness, at=c1, group=field)
    end = d.item("DEMO-CONN-2P", tag="PZ", name="pz", parent=harness, at=far, group=field)
    d.cable("DEMO-CBL-4G1.5", name="w3c", parent=harness, at=c1).core(1, plug["2"], end["2"])
    d.mate(plug, d.item("DEMO-CONN-2P", tag="J0", name="j0", at=c1, group=grp))
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    (upper,) = _placements(model, "p9", "x1")
    (lower,) = _placements(model, "j0", "x1")
    assert upper.x == lower.x
    assert upper.y < lower.y


# -- fan-out nets ----------------------------------------------------------------------


def _star_of_relays(*wires, strip=False):
    """Four relays K1..K4 whose coil pins `wires` join, each end a pin spec "K4.A2": the
    pins are mixed (A1 and A2) because same-side pins are joined by wires at any column distance,
    so a net of all-A1 pins is wires and no star; a star needs the pins on both sides."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {
        tag: d.item("DEMO-RLY-2CO-24", tag=tag, name=tag.lower(), at=c1, group=grp).fn("coil")
        for tag in ("K1", "K2", "K3", "K4")
    }

    def pin(spec):
        tag, name = spec.split(".")
        return relays[tag][name]

    if strip:
        terminal = d.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
        wire(terminal.outer, pin("K3.A1"))
    for first, second in wires:
        wire(pin(first), pin(second))
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _star(model):
    """The star's (reference marker, branch markers, text by marker).

    The Drawing carries no star kind (R243): the reference is the first marker drawn."""
    every = [m for _, m in markers(model)]
    text = {id(m): "\n".join(marker_strings(m)) for m in every}
    (ref, *branches) = every
    return ref, branches, text


def _named_by(model, marker) -> str:
    """The `-<tag>` of the item whose operating symbol stands nearest to `marker`."""
    candidates = [
        (abs(s.x - marker.x) + abs(s.y - marker.y), tag.text)
        for drawing in drawn_pages(model).values()
        if marker in drawing.markers
        for tag in drawing.texts
        for s in drawing.symbols
        if s.key == "operating-device" and abs(s.x - tag.box.x - 56) <= 2
    ]
    return min(candidates)[1]


_CHAIN = (("K4.A2", "K2.A1"), ("K2.A1", "K1.A2"), ("K1.A2", "K3.A1"))
_HUB_K3 = (("K3.A1", "K1.A2"), ("K3.A1", "K2.A2"), ("K3.A1", "K4.A2"))


def test_a_fanout_net_gets_one_marker_per_port_and_no_wires() -> None:
    """Four ports on one net that are not adjacent are four markers, none of them a route."""
    # UNDO: fransys_layout/stages/references/nets.py:star_nets
    #     returns `()` (wires drawn, no markers)
    model = _star_of_relays(*_CHAIN)
    drawn = markers(model)
    assert len(drawn) == 4
    assert not [w for d in drawn_pages(model).values() for w in d.wires]


def test_the_reference_is_the_hub_not_the_first_designation() -> None:
    """K3 carries three conductors, so K3 (not K1, first by designation) is the reference."""
    # UNDO: fransys_layout/stages/references/nets.py:star_nets
    #     drop `-degree[port]` from the `ref` sort key
    model = _star_of_relays(*_HUB_K3)
    ref, _, _ = _star(model)
    assert _named_by(model, ref) == "-K3"


def test_a_tie_for_hub_falls_to_the_port_whose_designation_sorts_first() -> None:
    """D9: K2.A1 and K1.A2 each carry two conductors; K1:A2 sorts first."""
    # UNDO: fransys_layout/stages/references/nets.py:star_nets
    #     reverse the designation in the `ref` sort key
    model = _star_of_relays(*_CHAIN)
    ref, _, _ = _star(model)
    assert _named_by(model, ref) == "-K1"


def test_a_single_terminal_point_is_the_reference_even_beside_a_bigger_hub() -> None:
    """X1:1 carries one conductor, K3 three; the terminal point still is the reference."""
    # UNDO: fransys_layout/stages/references/nets.py:star_nets
    #     `if len(points) == 1` becomes `if False`
    model = _star_of_relays(("K3.A1", "K1.A2"), ("K3.A1", "K2.A2"), strip=True)
    ref, _, _ = _star(model)
    assert any(t.text == "-X1:1" for _, t in tags_of(model, "X1"))
    assert _named_by(model, ref).startswith("-X1")


def test_the_reference_lists_its_branches_and_each_branch_names_the_reference() -> None:
    """The reference's and every branch's text is symmetric -- each of the star's
    four markers lists one line per OTHER end, so the reference lists its three branches and
    each branch's own text is the same shape, three lines, no duplicates. "Each branch names
    the reference" is the persisted `partner` link (unchanged by the text symmetry, a `star.py`
    rule), not a text-shape guess any more."""
    # UNDO: fransys_layout/stages/references/markers.py:star_markers
    #     builds each branch marker with itself as partner
    model = _star_of_relays(*_CHAIN)
    ref, branches, text = _star(model)
    assert len(branches) == 3
    for member in (ref, *branches):
        lines = text[id(member)].split("\n")
        assert len(branches) == 3
        assert len(lines) == 1  # three other ends print the first and a count
        assert lines[0].endswith(" +2")  # every OTHER member but the first, once each
    # each branch names the reference: its text lists the reference's end
    assert all(_named_by(model, ref).lstrip("-") in text[id(m)] for m in branches)


def test_a_black_box_pin_carries_no_star_marker() -> None:
    """Layout-0080: a unit's boundary terminal wired to two relays of the top level is no star.
    Each conductor leaving the unit is a stub, so there is no reference or branch marker anywhere:
    the pin's two off stubs stand in the unit's own set only, and the parent's page shows no marker
    of the pin (its black box hides its insides); each relay carries one mirror stub in the
    top-level set, naming the pin."""
    # UNDO: fransys_layout/stages/offstubs.py:ends_in_stubs
    #     `return any(...)` becomes `return False` (the wires are a star again: a reference
    #     and branch markers, no stub at the pin or at the relays)
    parts, d, c1, grp = _design()
    unit = d.scope("cab", at=c1).unit("demo-pump-cabinet", revision=2, interface="1")
    unit.revision(2, date="2026-01-01", text="First release", created="XX")
    terminal = unit.strip("X2").terminal("DEMO-TB-2.5", group=unit.group("FLD", "Field"))
    unit.boundary(terminal)
    wire = d.wiring(colour="BU", gauge="0.5")
    for tag in ("K1", "K2"):
        k = d.item("DEMO-RLY-2CO-24", tag=tag, name=tag.lower(), at=c1, group=grp)
        wire(terminal.outer, k.fn("coil")["A1"])
        wire(k.fn("co_1")["11"], k.fn("co_1")["14"])  # layout-0112: an unwired contact is not drawn
        wire(k.fn("co_2")["21"], k.fn("co_2")["24"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    pin = terminal.outer.id
    every = markers(model)
    assert all(is_stub(m) for _, m in every)  # no reference, no branch: no star
    on_pin = [(page, m) for page, m in every if set_of(model, page).unit is not None]
    tails = sorted(text.rsplit("-", 1)[1] for _, m in on_pin for text in marker_strings(m))
    assert tails == ["K1:A1", "K2:A1"]  # the unit's own set only
    terminal_item = functions(model)[terminal.function.id].item
    shown = set(pages_with(model, item_designation(model, terminal_item)))
    top = {page for page in drawn_pages(model) if set_of(model, page).unit is None}
    assert top <= shown  # the pin is drawn there
    mirrors = [(page, m) for page, m in every if set_of(model, page).unit is None]
    assert len(mirrors) == 2  # the top-level set
    assert all(
        text.endswith(port_designation(model, pin))
        for _, m in mirrors
        for text in marker_strings(m)
    )


def test_a_cross_unit_mate_stands_at_the_end_of_its_column_the_chain_enters_from() -> None:
    """Layout-0069 (amended) and layout-0155: the harness plug P1 and the boundary
    connector X1 it mates sit at a line's end, so on the parent page each draws as one box, no pin
    symbol, and the two boxes stand face to face, X1 above: the chain enters P1 from below."""
    # UNDO: fransys_layout/stages/box_views.py:_box
    #     `top = edge if down else edge - height` becomes `top = edge` (every box hangs down)
    parts, d, _, _ = _design()
    unit = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    unit.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = unit.location("C1", "Cabinet"), unit.group("NET", "Network")
    inner = unit.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    unit.boundary(inner)
    far, field = d.location("FLD", "Field"), d.group("NET", "Network")
    harness = d.harness(name="w3", tag="W3", at=c1, group=field)
    plug = d.item("DEMO-CONN-2P", tag="P1", parent=harness, at=c1, group=field)
    end = d.item("DEMO-CONN-2P", tag="P2", parent=harness, at=far, group=field)
    d.cable("DEMO-CBL-4G1.5", name="w3c", parent=harness, at=c1).core(2, plug["2"], end["2"])
    relay = d.item("DEMO-RLY-2CO-24", tag="Z9", at=c1, group=field)
    d.wiring(colour="BU", gauge="0.5")(plug["1"], relay.fn("coil")["A1"])
    d.mate(plug, inner)
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    parent = {page for page in drawn_pages(model) if set_of(model, page).unit is None}
    by_tag = {
        symbol.texts[0][0]: (page, symbol)
        for page, drawing in drawn_pages(model).items()
        for symbol in drawing.symbols
        if page in parent and symbol.texts
    }
    (plug_page, plug), (boundary_page, boundary) = by_tag["-W3-P1"], by_tag["-X1"]
    assert plug_page == boundary_page
    width, height = dict(boundary.stretch).get("x", 0), dict(boundary.stretch).get("y", 0)
    plug_width = dict(plug.stretch).get("x", 0)
    assert boundary.x < plug.x + plug_width
    assert plug.x < boundary.x + width
    # the chain runs on from P1 down to Z9, so X1 stands above and P1 below, face to face
    assert boundary.y + height == plug.y
