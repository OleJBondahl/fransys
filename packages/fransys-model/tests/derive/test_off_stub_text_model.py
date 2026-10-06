"""F1 (layout deep dive, D10): `stub_far_end` and `off_stub_text`, the one text of an off stub.

Hand-built plant: a strip `X1` at `+C1` with three terminals, a motor `M1` at `+EXT` with ports
`U1`, `V1`, `W1`, `X1`, and a cable `W3`. `stub_far_end` splits what the layout engine's
`_full_port` joined at `|` (its own test pins `+C1-K1|:1`); `off_stub_text` is what layout sizes a
stub's box from and render prints.
"""

from typing import TYPE_CHECKING

import pytest
from plant import Plant
from query_builders import make_node, make_placement, make_terminal

from fransys_model.derive.drawing_text import off_stub_line, off_stub_text, stub_far_end
from fransys_model.kernel import Id, Model, make_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    PageRole,
    Side,
    StarKind,
    layout_of,
)

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item, Port

PRODUCED_BY = "test-engine 0.0.0"
_DEVICE_PORTS = ("U1", "V1", "W1", "X1")
_MARKER_COUNT = 16


class _Stubs:
    """The plant plus the layout records the tests add stub by stub."""

    def __init__(self) -> None:
        plant = Plant()
        c1, ext = make_node("c1", None), make_node("ext", None)
        plant.add(c1, ext)
        strip = plant.item("x1", designation="X1")
        plant.add(make_placement("x1-loc", strip, c1.id))
        self.terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
        motor = plant.item("m1", designation="M1")
        motor_function = plant.function(motor, "f")
        self.device: dict[str, Id[Port]] = {
            name: plant.port(motor_function, name) for name in _DEVICE_PORTS
        }
        plant.add(make_placement("m1-loc", motor, ext.id))
        self.cable: Id[Item] = plant.item("w3", designation="W3")
        near_function = plant.function(plant.item("k1", designation="K1"), "f")
        self.near = [plant.port(near_function, f"p{n}") for n in range(_MARKER_COUNT)]
        drawing_set = DrawingSet(
            id=make_id(DrawingSet, ("set",)),
            key=("set",),
            location=None,
            number=1,
            produced_by=PRODUCED_BY,
        )
        self.pages = [
            Page(
                id=make_id(Page, (f"page{n}",)),
                key=(f"page{n}",),
                drawing_set=drawing_set.id,
                number=n,
                role=PageRole.CONTROL,
                sheet_format=None,
                groups=(),
                produced_by=PRODUCED_BY,
            )
            for n in (1, 2)
        ]
        plant.add(drawing_set, *self.pages)
        self.plant = plant
        self.count = 0

    def stub(  # noqa: PLR0913 -- one param per LinkMarker field the tests vary
        self,
        far: str,
        *,
        x: int = 0,
        y: int = 0,
        box_x: int | None = None,
        page: int = 0,
        facing: Side = Side.S,
        carrier: bool = True,
    ) -> LinkMarker:
        """Add an off stub naming the device port `far`, with its unpaired partner marker."""
        n = self.count
        self.count += 1
        stub_id = make_id(LinkMarker, (f"stub{n}",))
        partner_id = make_id(LinkMarker, (f"partner{n}",))
        stub = LinkMarker(
            id=stub_id,
            key=(f"stub{n}",),
            page=self.pages[page].id,
            port=self.near[n],
            side=MarkerSide.OWNER,
            partner=partner_id,
            x=x,
            y=y,
            width=13,
            height=8,
            produced_by=PRODUCED_BY,
            box_x=box_x,
            star=StarKind.OFF,
            far=self.device[far],
            carrier=self.cable if carrier else None,
            facing=facing,
        )
        partner = LinkMarker(
            id=partner_id,
            key=(f"partner{n}",),
            page=self.pages[1].id,
            port=self.near[n],
            side=MarkerSide.USER,
            partner=stub_id,
            x=0,
            y=0,
            width=13,
            height=8,
            produced_by=PRODUCED_BY,
        )
        self.plant.add(stub, partner)
        return stub

    def model(self) -> Model:
        return self.plant.model()


def _stored(model: Model, marker: LinkMarker) -> LinkMarker:
    return layout_of(model, LinkMarker)[marker.id]


def test_stub_far_end_of_a_device_port_is_its_product_designation_and_port_suffix() -> None:
    """A motor port at `EXT` reads head `+EXT-M1`, tail `:U1`; `_full_port` joined them at `|`."""
    stubs = _Stubs()
    model = stubs.model()
    assert stub_far_end(model, stubs.device["U1"]) == ("+EXT-M1", ":U1")


def test_stub_far_end_of_a_terminal_is_headed_by_its_strip() -> None:
    """A strip's terminal: the strip heads the designation, the terminal position is the tail."""
    stubs = _Stubs()
    model = stubs.model()
    assert stub_far_end(model, stubs.terminal.external) == ("+C1-X1", ":L:1")


def test_a_stub_with_a_carrier_names_the_cable_the_arrow_and_the_far_end() -> None:
    """Cable, arrow (`→` unless the stub faces north), then head and port."""
    stubs = _Stubs()
    marker = stubs.stub("U1")
    assert off_stub_text(stubs.model(), marker) == "-W3 → +EXT-M1:U1"


def test_a_stub_without_a_carrier_has_no_cable_part() -> None:
    """No carrier: the text starts at the arrow."""
    stubs = _Stubs()
    marker = stubs.stub("U1", carrier=False)
    assert off_stub_text(stubs.model(), marker) == "→ +EXT-M1:U1"


def test_a_stub_facing_north_points_its_arrow_back() -> None:
    """`Side.N` reads `←`; every other side reads `→`."""
    stubs = _Stubs()
    north = stubs.stub("U1", facing=Side.N)
    south = stubs.stub("V1", facing=Side.S)
    model = stubs.model()
    assert off_stub_text(model, north) == "-W3 ← +EXT-M1:U1"
    assert off_stub_text(model, south) == "-W3 → +EXT-M1:V1"


def test_a_shared_box_run_lists_its_tails_in_x_order_and_reads_the_same_from_each_stub() -> None:
    """Three stubs of one row: one text, tails ordered by `x` and not by creation order."""
    stubs = _Stubs()
    run = [
        stubs.stub("W1", x=30, y=50, box_x=100),
        stubs.stub("U1", x=10, y=50, box_x=100),
        stubs.stub("V1", x=20, y=50, box_x=100),
    ]
    model = stubs.model()
    texts = {off_stub_text(model, _stored(model, marker)) for marker in run}
    assert texts == {"-W3 → +EXT-M1:U1 V1 W1"}


def test_two_rows_that_share_a_box_x_are_two_runs() -> None:
    """Same page and `box_x`, different `y`: each row reads its own text (grouping by `box_x`
    alone would merge them).
    """
    stubs = _Stubs()
    upper = [stubs.stub("U1", x=10, y=50, box_x=100), stubs.stub("V1", x=20, y=50, box_x=100)]
    lower = stubs.stub("W1", x=10, y=90, box_x=100)
    model = stubs.model()
    assert {off_stub_text(model, marker) for marker in upper} == {"-W3 → +EXT-M1:U1 V1"}
    assert off_stub_text(model, lower) == "-W3 → +EXT-M1:W1"


def test_stubs_of_two_cables_in_one_box_read_their_own_texts() -> None:
    """Layout's row key is cable and far device: two stubs of one box that differ in either are
    two texts (a box bundling them must not merge their tails).
    """
    stubs = _Stubs()
    cabled = stubs.stub("U1", x=10, y=50, box_x=100)
    bare = stubs.stub("V1", x=20, y=50, box_x=100, carrier=False)
    model = stubs.model()
    assert off_stub_text(model, cabled) == "-W3 → +EXT-M1:U1"
    assert off_stub_text(model, bare) == "→ +EXT-M1:V1"


def test_a_boxless_stub_and_a_stub_of_another_page_do_not_join_a_run() -> None:
    """`box_x=None` is a run of one, and a run stays on its page."""
    stubs = _Stubs()
    lead = stubs.stub("U1", x=10, y=50, box_x=100)
    boxless = stubs.stub("X1", x=20, y=50)
    elsewhere = stubs.stub("V1", x=30, y=50, box_x=100, page=1)
    model = stubs.model()
    assert off_stub_text(model, lead) == "-W3 → +EXT-M1:U1"
    assert off_stub_text(model, boxless) == "-W3 → +EXT-M1:X1"
    assert off_stub_text(model, elsewhere) == "-W3 → +EXT-M1:V1"


def test_a_marker_that_is_no_off_stub_is_refused() -> None:
    """A programming error, not a model error: the text of a reference or branch is not this."""
    stubs = _Stubs()
    stubs.stub("U1")
    model = stubs.model()
    partner = next(m for m in layout_of(model, LinkMarker).values() if m.star is None)
    with pytest.raises(ValueError, match="off stub"):
        off_stub_text(model, partner)


def test_off_stub_line_is_cable_arrow_far_end_and_its_ports() -> None:
    """The one line layout measures and derive prints: arrow by facing, cable optional, ports
    with or without a leading `:`, in the order given."""
    # UNDO: derive/drawing_text.py: `off_stub_line` `"←" if north else "→"` -> `"→"` (a north
    #   stub prints the arrow of a south one); a dropped `removeprefix(":")` fails the last two
    assert off_stub_line("-W3", north=True, far="+EXT-M1", ports=["U1"]) == "-W3 ← +EXT-M1:U1"
    assert off_stub_line("-W3", north=False, far="+EXT-M1", ports=["U1"]) == "-W3 → +EXT-M1:U1"
    assert off_stub_line("", north=False, far="+EXT-M1", ports=["U1"]) == "→ +EXT-M1:U1"
    assert off_stub_line("-W3", north=True, far="+EXT-M1", ports=["U1", "V1"]) == (
        "-W3 ← +EXT-M1:U1 V1"
    )
    assert off_stub_line("-W3", north=True, far="+EXT-M1", ports=[":U1", ":V1"]) == (
        "-W3 ← +EXT-M1:U1 V1"
    )
