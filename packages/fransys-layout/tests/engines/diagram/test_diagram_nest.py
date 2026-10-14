"""Same-column lines nest (layout-0201): the order of their ends and the order of their tracks."""

from fransys_layout.engines.diagram.arrange import RawEnd, place_ends
from fransys_layout.engines.diagram.channels import same_tracks
from fransys_layout.geometry import Facing
from fransys_model.kernel import Id


def _id(name: str) -> Id:
    return Id(kind="item", value=name)


_Y = {_id(k): v for k, v in {"T": 0, "N": 100, "F": 200, "U": -100, "V": -200}.items()}
_H = dict.fromkeys(_Y, 400)


def _order(far: list[str], *, nest: bool) -> list[int]:
    ends = tuple(RawEnd(k, _id("T"), _id(f), Facing.E, None, same=True) for k, f in enumerate(far))
    placed = place_ends(ends, _Y, _H, 8, nest=nest)[(_id("T"), Facing.E)]
    return [e.line for e in sorted(placed, key=lambda e: e.y)]


def test_the_farther_box_below_takes_the_upper_end() -> None:
    assert _order(["N", "F"], nest=False) == [0, 1]
    assert _order(["N", "F"], nest=True) == [1, 0]


def test_lines_above_come_first_nearer_first_and_those_below_farther_first() -> None:
    assert _order(["F", "V", "N", "U"], nest=True) == [3, 1, 0, 2]


def test_a_longer_span_takes_the_outer_track_whatever_its_order() -> None:
    spans = [(0, 100), (10, 50)]
    assert same_tracks(spans, share=False) == (1, 2)
    assert same_tracks(spans, share=False, nest=True) == (2, 1)


def test_sharing_keeps_disjoint_spans_on_one_track_and_nests_the_rest() -> None:
    spans = [(0, 100), (10, 50), (200, 300)]
    assert same_tracks(spans, share=True, nest=True) == (2, 1, 1)
