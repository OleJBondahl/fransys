"""Each convention `Options` carries gives another result when the caller passes another value."""

from dataclasses import replace

from fransys_layout.core import PinRef, Size
from fransys_layout.core.geometry import marker_box_at
from fransys_layout.core.outputs import Trunk
from fransys_layout.core.pack_sep import separation
from fransys_layout.core.text_ends import MarkEnv, end_stand
from fransys_layout.core.values import Box, Fan, Ref, RefEnd, RefKind, Side

from .conftest import MARKER
from .flow_builders import OPTIONS
from .order_fixtures import block, fan, flow, ordered
from .pack_fixtures import elem, placed


def test_driver_first_false_leaves_the_driver_column_in_natural_order() -> None:
    blk = block(["c1", "c2", "c3", "c4"], "f")
    fl = flow([fan("f", ["c1", "c2", "c4"], ["c3"])])
    assert ordered(blk, fl, replace(OPTIONS, driver_first=True)) == ["c3", "c1", "c2", "c4"]
    assert ordered(blk, fl, replace(OPTIONS, driver_first=False)) == ["c1", "c2", "c3", "c4"]


def test_tag_stagger_false_counts_the_text_slots_as_hard() -> None:
    syms = {"e": elem("e", footprint=Box(-20, -16, 40, 32))}
    a, b = placed("a", "e"), placed("b", "e")
    on = replace(OPTIONS, tag_stagger=True)
    off = replace(OPTIONS, tag_stagger=False)
    assert separation(a, b, syms, frozenset(), on) == 40
    assert separation(a, b, syms, frozenset(), off) == 48


def test_arrow_sides_choose_the_side_each_arrow_end_stands_on() -> None:
    pin = PinRef("S", "p")
    ref = Ref("f", RefKind.ARROW, (RefEnd(1, "c1", pin, 0), RefEnd(1, "c2", pin, 0)))
    trunks = {(1, "f"): (Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),)),)}
    fans = {"f": Fan("f", ("fa", "fb"), (), (), "H", 1, "S")}

    def stood(sides: tuple[Side, Side]) -> list[tuple[str, Box]]:
        options = replace(OPTIONS, marker=MARKER, arrow_sides=sides)
        env = MarkEnv(options, Size(1312, 854), {}, {}, trunks, fans)
        stands = [end_stand(env, ref, e, i) for i, e in enumerate(ref.ends)]
        return [(s.orient, marker_box_at(s.x, s.y, options, s.orient)) for s in stands]

    east_west = stood(("E", "W"))
    west_east = stood(("W", "E"))
    assert [o for o, _ in east_west] == ["R0", "R180"]
    assert [o for o, _ in west_east] == ["R180", "R0"]
    assert east_west[0][1].x == 500  # the first end's near edge at the trunk's right end
    assert west_east[0][1].x + west_east[0][1].w == 40  # now at its left end
