"""layout-0244: a marker's sideways stub run may not cross another marked port's lane."""

from typing import Any

from fransys_el import TEXTS
from samples import hid

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.space import Space
from fransys_layout.stages.texts.candidates import TextKind
from fransys_layout.stages.texts.marker_lanes import Lane, crosses_shut
from fransys_layout.stages.texts.marker_row import _place
from fransys_layout.stages.texts.place_texts import Place, TextToPlace, place_texts

OWN: Any = "own-port"
OTHER: Any = "other-port"
F: Any = "f"
LANE = Lane(function=F, port=OTHER, x=48, y=144, facing=Facing.S, end=240)
# a lead marker at (40, 100): its stub runs down to y 148, then east along y 148 across x 48
_LEAD = LinkMarker(
    connection=hid("conductor", 5),
    port=hid("port", 7),
    side=MarkerSide.OWNER,
    drawing_set=1,
    page=1,
    at=Point(x=40, y=100),
    box=Box(x=56, y=148, width=24, height=8),
    partner_page=2,
    shared_box=True,
    lead=True,
)


def test_a_sideways_run_across_another_ports_lane_crosses_it() -> None:
    rail = Box(x=40, y=151, width=24, height=2)
    assert crosses_shut((rail,), OWN, (LANE,))


def test_its_own_lane_an_upright_run_or_a_run_past_the_lane_does_not() -> None:
    rail = Box(x=40, y=151, width=24, height=2)
    assert not crosses_shut((rail,), OTHER, (LANE,))
    assert not crosses_shut((Box(x=47, y=150, width=2, height=24),), OWN, (LANE,))
    assert not crosses_shut((Box(x=56, y=151, width=24, height=2),), OWN, (LANE,))
    assert not crosses_shut((Box(x=40, y=260, width=24, height=2),), OWN, (LANE,))


def test_a_marker_place_whose_lead_crosses_a_shut_lane_says_so() -> None:
    """UNDO: `_place` sets `crosses=False`, and the lead across the lane is not marked."""
    assert _place(_LEAD, (), shut=(LANE,))[1].crosses
    assert not _place(_LEAD, (), shut=())[1].crosses


def _chosen(crossing: tuple[bool, ...]) -> int:
    """The place index `place_texts` takes from same-sized, free places with these `crosses`."""
    places = tuple(
        Place(box=Box(x=200 + 40 * i, y=0, width=24, height=8), crosses=one)
        for i, one in enumerate(crossing)
    )
    text = TextToPlace(
        kind=TextKind.REFERENCE,
        handle=hid("port", 7),
        slot="000000",
        position=Point(x=200, y=0),
        width=24,
        height=8,
        anchors=(),
        own=(),
        places=places,
    )
    space = Space(shapes=(), content=Box(x=0, y=-1000, width=1000, height=2000))
    done, findings = place_texts((text,), space, TEXTS)
    assert findings == ()
    return done[0].index


def test_a_place_off_every_lane_is_taken_before_one_that_crosses() -> None:
    """UNDO: `_fitting` ignores `strict`, and the first, crossing place is taken."""
    assert _chosen((True, False)) == 1


def test_a_row_whose_every_place_crosses_keeps_the_old_rule() -> None:
    """UNDO: the second, non-strict pass is dropped, and the text is not placed."""
    assert _chosen((True, True)) == 0
