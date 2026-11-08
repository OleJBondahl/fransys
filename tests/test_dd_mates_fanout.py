"""One undo test per ruling for connectors and for fan-out nets, built
through the `fransys` facade from `examples/demo-parts` and read from
the page Drawings only (the Drawing carries no star kind and no port: R243).
"""

from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _dd_core import pages_with, set_of
from _dd_core_b import is_stub, marker_strings, markers, symbols_of
from _dd_core_c import stands
from _drawn_pages import drawn_pages, markers_in
from _model_build_cover import cabinet_document
from _no_power_net import assert_no_power_net
from fransys_author.design import Design

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
    design = Design(parts)
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
    """Two wired pins are two views, and a connector with no wire is absent."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:pin_views
    #     keeps a connector as one view (no pin views)
    # UNDO: fransys_layout/engines/schematic/read/views.py:without_idle_pins
    #     keeps every pin (`kept = set(pin_of)`)
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", name="k2", at=c1, group=grp)
    plug = d.item("DEMO-CONN-2P", tag="J1", name="j1", at=c1, group=grp)
    d.item("DEMO-CONN-2P", tag="J7", name="j7", at=c1, group=grp)
    wire(k1.fn("co_1")["14"], plug["1"])
    wire(k2.fn("co_1")["14"], plug["2"])
    model = fr.build(parts, d.draft(), cabinet_document(c1)).model
    wired = _placements(model, "j1", "x1")
    assert len(wired) == 2
    assert len({p.x for p in wired}) == 2
    assert _placements(model, "j7", "x1") == []


# -- fan-out nets ----------------------------------------------------------------------


def _star_of_relays(*wires, strip=False):
    """Four relays K1..K4 whose coil pins `wires` join, each end a pin spec "K4.A2": the
    pins are mixed (A1 and A2) because same-side pins are joined by wires at any column distance,
    so a net of all-A1 pins is wires and no star; a star needs the pins on both sides."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {tag: d.item("DEMO-RLY-2CO-24", tag=tag, name=tag.lower(), at=c1, group=grp).fn("coil") for tag in ("K1", "K2", "K3", "K4")}

    def pin(spec):
        tag, name = spec.split(".")
        return relays[tag][name]

    if strip:
        terminal = d.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
        wire(terminal.outer, pin("K3.A1"))
    for first, second in wires:
        wire(pin(first), pin(second))
    used = {spec for pair in wires for spec in pair} | ({"K3.A1"} if strip else set())
    rest = [spec for tag in relays for spec in (f"{tag}.A1", f"{tag}.A2") if spec not in used]
    closing = d.strip("X2", at=c1)
    for spec in rest:
        wire(pin(spec), closing.terminal("DEMO-TB-2.5", group=grp).inner)
    return fr.build(parts, d.draft(), cabinet_document(c1)).model


def _trunk_shape(model) -> tuple[int, int, int, int]:
    """The page's (trunks, drops, junction dots, markers): a trunk runs level, a drop upright."""
    (drawing,) = drawn_pages(model).values()
    level = [w for w in drawing.wires if w.points[0][1] == w.points[-1][1]]
    trunk_nets = {w.net for w in level}  # the closing wires of the other pins are other nets
    upright = [w for w in drawing.wires if w.points[0][0] == w.points[-1][0] and w.net in trunk_nets]
    dots = [s for s in drawing.symbols if s.key == "junction-dot"]
    return len(level), len(upright), len(dots), len(markers_in(drawing))


_CHAIN = (("K4.A2", "K2.A1"), ("K2.A1", "K1.A2"), ("K1.A2", "K3.A1"))
_HUB_K3 = (("K3.A1", "K1.A2"), ("K3.A1", "K2.A2"), ("K3.A1", "K4.A2"))


@pytest.mark.rule("BUNDLE")
def test_a_fanout_net_is_one_trunk_with_a_drop_and_a_dot_per_port_and_no_marker() -> None:
    """Four coil ports on one non-power net: one trunk, a drop per port, a dot at each inner drop,
    no marker (ROUTING, BUNDLE, R467)."""
    # UNDO: fransys_layout/core/topology_nets.py:fans_of returns `()` (the net is link wires or
    #     markers again, not one trunk)
    model = _star_of_relays(*_CHAIN)
    assert_no_power_net(model)
    assert _trunk_shape(model) == (1, 4, 2, 0)


@pytest.mark.rule("BUNDLE")
def test_which_port_carries_most_conductors_changes_nothing_in_the_trunk() -> None:
    """A hub of three conductors draws the same trunk as a chain over four ports (BUNDLE, R467):
    no port is the reference, so a tie or a hub has nothing to decide."""
    # UNDO: as in the first fan-out test
    model = _star_of_relays(*_HUB_K3)
    assert_no_power_net(model)
    assert _trunk_shape(model) == (1, 4, 2, 0)


@pytest.mark.rule("BUNDLE")
def test_a_single_terminal_point_is_a_drop_of_the_trunk_beside_a_bigger_hub() -> None:
    """X1:1 carries one conductor, K3 three; the terminal stands once as one drop of the trunk
    over the four ports, one dot at the inner drop (ROUTING, BUNDLE, R467)."""
    # UNDO: as in the first fan-out test
    model = _star_of_relays(("K3.A1", "K1.A2"), ("K3.A1", "K2.A2"), strip=True)
    assert_no_power_net(model)
    assert stands(model, "-X1:1")
    (drawing,) = drawn_pages(model).values()
    # X1:1 once, plus the five terminals of X2 that close the relays' other coil pins
    assert len([s for s in drawing.symbols if s.key == "terminal"]) == 1 + 5
    assert _trunk_shape(model) == (1, 4, 1, 0)


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
    terminal = unit.strip("X2").terminal("DEMO-TB-2.5-TWIN", group=unit.group("FLD", "Field"))
    unit.boundary(terminal)
    wire = d.wiring(colour="BU", gauge="0.5")
    strip = d.strip("X1", at=c1)
    for tag in ("K1", "K2"):
        k = d.item("DEMO-RLY-2CO-24", tag=tag, name=tag.lower(), at=c1, group=grp)
        wire(terminal.outer, k.fn("coil")["A1"])
        wire(k.fn("co_1")["11"], k.fn("co_1")["14"])  # layout-0112: an unwired contact is not drawn
        wire(k.fn("co_2")["21"], k.fn("co_2")["24"])
        wire(k.fn("coil")["A2"], strip.terminal("DEMO-TB-2.5", group=grp).outer)
    model = fr.build(parts, d.draft(), cabinet_document(c1), cabinet_document(unit)).model
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
    assert all(text.endswith(port_designation(model, pin)) for _, m in mirrors for text in marker_strings(m))
