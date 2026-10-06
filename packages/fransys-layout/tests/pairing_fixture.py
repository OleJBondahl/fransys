"""Hand-made boxes for the layout-0107 pairing tests: one fed box and two feeders.

Box 1 has top pins `a1 a2` (fed by box 2) and `b1 b2` (box 3 feeds `b1`), a bottom pin `z`.
"""

from dataclasses import replace

from samples import drawn, hid

from fransys_layout.geometry import generic_box_geometry
from fransys_layout.stages import BoxFeed, DrawnFunction, DrawnPort, FedPin
from fransys_layout.stages.boxes import paired_boxes
from fransys_layout.stages.types import Profile


def port(box: int, name: str):
    return hid("port", box * 10000 + ord(name[0]) * 100 + ord(name[-1]))


def box(number: int, tops: tuple[str, ...], bottoms: tuple[str, ...]) -> DrawnFunction:
    names = (*tops, *bottoms)
    sides = ("n",) * len(tops) + ("s",) * len(bottoms)
    ports = tuple(DrawnPort(port=port(number, n), symbol_port=n) for n in names)
    geometry = generic_box_geometry(names, sides)
    return replace(drawn(number), geometry=geometry, ports=ports)


def feed(feeder: int, pairs: tuple[tuple[str, str], ...]) -> BoxFeed:
    return BoxFeed(
        fed=hid("function", 1),
        feeder=hid("function", feeder),
        ports=tuple(FedPin(fed=port(1, a), feeder=port(feeder, b)) for a, b in pairs),
    )


PROFILE = Profile(
    column_gap=32,
    row_gap=0,
    row_spacing=0,
    text_height=8,
    marker_padding=0,
    band_ranks=frozendict({}),
    group_ranks=frozendict({}),
    route_turn_penalty=0,
    route_crossing_penalty=0,
    route_margin=0,
)


def pair() -> tuple[DrawnFunction, ...]:
    boxes = (
        box(1, ("a1", "a2", "b1", "b2"), ("z",)),
        box(2, (), ("q2", "q1")),
        box(3, (), ("p",)),
    )
    feeds = (feed(2, (("a2", "q2"), ("a1", "q1"))), feed(3, (("b1", "p"),)))
    return paired_boxes(boxes, feeds, PROFILE)
