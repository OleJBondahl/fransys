"""D1 (EF-D part 1): a directed pole against its chain is drawn turned; a vote tie has a rule.

The running-lamp column: a `+` point, a changeover contact fed at its COM (11), a breaker
standing for the lamp, a `0V` point. The contact stands R0 with 11 on top, so a chain fed at 11
enters it along its direction. Fed at 14 instead, the chain enters it against its direction;
the breaker points the chain's way, so the vote is one to one.
"""

import itertools
from typing import TYPE_CHECKING

import pytest
from dd_chain_fixtures import MCB, TERMINAL, build, design, placed, terminal_key
from test_dd_chains import _strip_of_terminals

from fransys_layout import geometry as library
from fransys_model.layout import Orientation, Route, layout_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import SymbolPlacement

TOP, BOTTOM = terminal_key("XA", 1), terminal_key("XA", 2)
CONTACT, LAMP = ("K1", "fn", "co_1"), ("Q1", "fn", "element")
_BAD = {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}


def _lamp_column(*, plus_first: bool = True, fed_at: str = "11"):
    """XA:1 -> K1:co_1 (11, then 14) -> Q1 (1, then 2) -> XA:2; `+` on XA:1, else on XA:2.

    With `fed_at="14"` the contact is entered at 14 and left at 11 instead.

    Q1, a breaker, stands for the lamp: the demo lamp has no symbol and so no pole, and a
    breaker is the demo part with a directed pole that the chain enters at its input.
    """
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    first, second = (strip.terminal(TERMINAL, group=g) for _ in range(2))
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c, group=g)
    q1 = d.item(MCB, tag="Q1", at=c, group=g)
    wire = d.wiring(colour="BU", gauge="0.5")
    out_at = "14" if fed_at == "11" else "11"
    wire(first.outer, k1.fn("co_1")[fed_at])
    wire(k1.fn("co_1")[out_at], q1["1"])
    wire(q1["2"], second.inner)
    plus, zero = (first, second) if plus_first else (second, first)
    # an AC supply keeps references (LD8): a DC one would draw power symbols and move the column
    d.supply("S", current="ac", rails={"+": ("24", 0), "0V": ("0", None)})
    d.net("PLUS", plus.inner, cls="power", potential="+")
    d.net("ZERO", zero.inner, cls="power", potential="0V")
    return build(parts, d)


def _port_at(placement: SymbolPlacement, name: str) -> tuple[int, int]:
    """The page position of the symbol port `name` of a drawn placement."""
    geometry = library.symbol_geometry(
        placement.symbol,
        poles=placement.poles,
        orientation=library.Orientation(placement.orientation.value),
    )
    at = next(p.at for p in geometry.ports if p.name == name)
    return placement.x + at.x, placement.y + at.y


def _port_y(placement: SymbolPlacement, name: str) -> int:
    """The y of the symbol port `name` of a drawn placement."""
    return _port_at(placement, name)[1]


def test_a_changeover_fed_at_11_stands_r0_with_11_on_top_and_the_feed_runs_straight() -> None:
    """D1: the contact fed at 11 points with its chain, so it is drawn R0, 11 on top; the
    column has no failed connection.
    """
    # UNDO: stages/_chain_walk.py `_note_turns`, swap the branches of `elif pole.inn == e`
    result = _lamp_column()
    model = result.model
    contact = placed(model, *CONTACT)
    assert contact.orientation is Orientation.R0
    # R0: 11 (com) on top, 14 (no) and 12 (nc) below it, 12 on the left
    assert _port_y(contact, "com") < _port_y(contact, "nc") == _port_y(contact, "no")
    assert _port_at(contact, "nc")[0] < _port_at(contact, "no")[0]
    assert placed(model, *TOP).y < contact.y < placed(model, *LAMP).y < placed(model, *BOTTOM).y
    assert len({placed(model, *key).x for key in (TOP, CONTACT, LAMP, BOTTOM)}) == 1
    assert not {f.code for f in result.findings} & _BAD


@pytest.mark.parametrize("plus_first", [True, False])
def test_a_vote_tie_puts_the_higher_potential_on_top_whatever_the_walk_order(
    plus_first: bool,  # noqa: FBT001 -- a parametrized flag, one case per value
) -> None:
    """D1: one pole each way is a tie (the contact is fed at 14, against its chain, Q1 along);
    `+` is on top with `+` on XA:1 (walk order) or on XA:2.
    """
    # UNDO: _chain_walk.py `_vote_direction`, its returned `directed`: mark a tied chain as directed
    model = _lamp_column(plus_first=plus_first, fed_at="14").model
    plus, zero = (TOP, BOTTOM) if plus_first else (BOTTOM, TOP)
    assert placed(model, *plus).y < placed(model, *CONTACT).y
    assert placed(model, *CONTACT).y < placed(model, *zero).y


def test_a_changeover_fed_at_14_is_drawn_turned_so_the_feed_runs_straight() -> None:
    """D1: fed at 14 the chain enters the contact at its S-facing port, against its direction:
    the contact is drawn MR180, 14 on top, 11 and 12 below, and nothing loops round it.
    """
    # UNDO: stages/_chain_walk.py `walk_chains`, `out.flipped |= out.turned`: drop it
    result = _lamp_column(fed_at="14")
    model = result.model
    contact = placed(model, *CONTACT)
    assert contact.orientation is Orientation.MR180
    assert _port_y(contact, "no") < _port_y(contact, "com")
    assert placed(model, *TOP).y < contact.y < placed(model, *LAMP).y < placed(model, *BOTTOM).y
    assert len({placed(model, *key).x for key in (TOP, CONTACT, LAMP, BOTTOM)}) == 1
    assert not {f.code for f in result.findings} & _BAD


def test_a_function_with_a_pole_that_points_with_its_chain_is_not_turned() -> None:
    """D1: a turn is per function, so a 3P contactor whose pole 1-2 points with chain A and
    whose pole 4-3 points against chain B (a tie there) stays upright: the pole that points
    with its chain would be drawn against it, and the chain-A wire would loop round the symbol.
    """
    # UNDO: stages/_chain_walk.py `walk_chains`, drop the veto `out.against - out.along`
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    t1, t2, t3, t4 = (strip.terminal(TERMINAL, group=g) for _ in range(4))
    q1 = d.item(MCB, tag="Q1", at=c, group=g)
    k1 = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g).fn("main")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, k1["1"])  # chain A: XA:1 -> K1 pole 1-2 (with its direction) -> XA:2
    wire(k1["2"], t2.inner)
    wire(t3.outer, q1["1"])  # chain B: XA:3 -> Q1 -> K1 pole 4-3 (against) -> XA:4
    wire(q1["2"], k1["4"])
    wire(k1["3"], t4.inner)
    model = build(parts, d).model
    assert placed(model, "K1", "fn", "main").orientation is Orientation.R0
    chain_a = [
        route
        for route in layout_of(model, Route).values()
        if {functions(model)[ports(model)[end].function].key for end in (route.a, route.b)}
        & {terminal_key("XA", 1), terminal_key("XA", 2)}
    ]
    assert len(chain_a) == 2
    assert all(len(route.points) == 2 for route in chain_a)


def test_a_pole_pin_turns_back_only_past_its_devices_edge() -> None:
    """S20 M12: K1:4 (a bottom pin) to Q1:2 stands no higher than K1's top edge, so it is a
    drawn wire; K1:3 (a top pin) to XA:4, which stands below the contactor, is a reference pair.
    """
    # UNDO: stages/references/turned.py `_turns_back`: `own.body[0]` -> `own.end.offset`
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    t1, t2, t3, t4 = (strip.terminal(TERMINAL, group=g) for _ in range(4))
    q1 = d.item(MCB, tag="Q1", at=c, group=g)
    k1 = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g).fn("main")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, q1["1"])
    wire(q1["2"], k1["4"])
    wire(k1["3"], t4.inner)
    model = build(parts, d).model
    table = ports(model)
    drawn = {
        frozenset((table[r.a].key[-3:], table[r.b].key[-3:]))
        for r in layout_of(model, Route).values()
    }
    assert frozenset({("main", "port", "4"), ("element", "port", "2")}) in drawn
    assert not any(("main", "port", "3") in pair for pair in drawn)


def test_a_mated_pin_view_turned_face_to_face_stays_r180() -> None:
    """D1: only a turned directed pole is MR180; the device pin view under its plug is R180."""
    # UNDO: stages/place.py _cells, `Orientation.MR180 if cell.mirror` -> `if cell.flip`
    parts, d = design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    far, field = d.location("FLD", "Field"), d.group("F", "Field")
    harness = d.harness(name="w3", tag="W3", at=c1, group=field)
    plug = d.item("DEMO-CONN-2P", tag="P9", name="p9", parent=harness, at=c1, group=field)
    end = d.item("DEMO-CONN-2P", tag="PZ", name="pz", parent=harness, at=far, group=field)
    d.cable("DEMO-CBL-4G1.5", name="w3c", parent=harness, at=c1).core(1, plug["2"], end["2"])
    d.mate(plug, d.item("DEMO-CONN-2P", tag="J0", name="j0", at=c1, group=grp))
    model = build(parts, d).model
    assert placed(model, "j0", "fn", "x1").orientation is Orientation.R180
    assert placed(model, "p9", "fn", "x1").orientation is Orientation.R0


def _crossings(model: Model) -> int:
    """How many times two routes cross: a horizontal and a vertical segment of two different
    routes meeting inside both. Touching at an end, at a port or at a bend, is no crossing.
    """
    segments = [
        (route.id, a, b)
        for route in layout_of(model, Route).values()
        for a, b in itertools.pairwise(route.points)
    ]
    count = 0
    for (id_a, a1, a2), (id_b, b1, b2) in itertools.combinations(segments, 2):
        if id_a == id_b:
            continue
        for h1, h2, v1, v2 in ((a1, a2, b1, b2), (b1, b2, a1, a2)):
            if h1.y == h2.y and v1.x == v2.x:
                x_in = min(h1.x, h2.x) < v1.x < max(h1.x, h2.x)
                y_in = min(v1.y, v2.y) < h1.y < max(v1.y, v2.y)
                count += x_in and y_in
    return count


def test_two_contactors_in_series_draw_no_crossed_phase_wires() -> None:
    """D1 (MR180): K1 is entered at its outputs, so it is turned; a turned three-pole device
    keeps its lanes left to right (a plain R180 mirrors them), so the phases run straight
    from K2 down to K1 without crossing.
    """
    # UNDO: stages/place.py _cells, draw a turned non-terminal function at R180 again
    parts, d, c, g, ts, wire = _strip_of_terminals(6)
    k1 = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g).fn("main")
    k2 = d.item("DEMO-CTR-3P-24", tag="K2", at=c, group=g).fn("main")
    for i in range(3):
        wire(ts[i].outer, k2[str(2 * i + 1)])
        wire(k2[str(2 * i + 2)], k1[str(2 * i + 2)])
        wire(k1[str(2 * i + 1)], ts[3 + i].inner)
    result = build(parts, d)
    model = result.model
    assert _crossings(model) == 0
    upper, turned = placed(model, "K2", "fn", "main"), placed(model, "K1", "fn", "main")
    assert upper.orientation is Orientation.R0
    assert turned.orientation is Orientation.MR180
    for pole in ("1", "2", "3"):
        assert _port_y(turned, f"{pole}.out") < _port_y(turned, f"{pole}.in")  # 2, 4, 6 on top
    for side, name in ((upper, "in"), (upper, "out"), (turned, "in"), (turned, "out")):
        xs = [_port_at(side, f"{pole}.{name}")[0] for pole in ("1", "2", "3")]
        assert xs == sorted(xs)
        assert len(set(xs)) == 3
    assert _port_at(upper, "1.out")[0] == _port_at(turned, "1.out")[0]  # phase 1 stays put
    assert not {f.code for f in result.findings} & _BAD
