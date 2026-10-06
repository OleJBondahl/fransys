"""`texts.clear_bodies.place_clear_of_bodies`: a marker's place whose stub runs through a foreign
symbol is not taken, though its box stands clear (M9, layout-0093).

The own function's N port is at (104, 88). Another function stands above it, body x 96..112,
y 24..56. The first place is a box above that body, its stub up through the body; the second is
a box to the east, its stub along y 88.
"""

from samples import hid, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages.texts.candidates import TextKind
from fransys_layout.stages.texts.clear_bodies import place_clear_of_bodies
from fransys_layout.stages.texts.marker_row import stub_boxes
from fransys_layout.stages.texts.place_texts import Place, TextToPlace

_OWN, _ABOVE = placed(1, x=104, y=104), placed(2, x=104, y=40)
_CONTENT = Box(x=0, y=-1000, width=400, height=2000)


def _marker(box: Box) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 5),
        port=hid("port", 7),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=104, y=88),
        box=box,
        partner_page=2,
    )


def test_a_place_whose_stub_runs_through_a_foreign_symbol_is_not_taken() -> None:
    """UNDO: `stub_clear` returned unchanged in `place_clear_of_bodies`, and place 0 is taken."""
    markers = [
        _marker(Box(x=92, y=0, width=24, height=8)),
        _marker(Box(x=130, y=84, width=24, height=8)),
    ]
    row = [(m, Place(box=m.box, stub=stub_boxes(m))) for m in markers]
    text = TextToPlace(
        kind=TextKind.REFERENCE,
        handle=markers[0].port,
        slot="000000",
        position=markers[0].at,
        width=24,
        height=8,
        anchors=(),
        own=(_OWN.function,),
        places=tuple(place for _, place in row),
    )
    done, findings = place_clear_of_bodies((text,), {0: row}, (_OWN, _ABOVE), (), _CONTENT)
    assert findings == ()
    assert [one.index for one in done] == [1]
