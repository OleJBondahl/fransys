"""One text for every lifted line, and one merge of the stubs per far end (OVERVIEW-VIEWS R2)."""

from derive_helpers import house_record
from overview_builders import item_id, unit_plant

from fransys_model.derive import OverviewLinkKind, overview_lifted_text, stub_ends
from fransys_model.derive.overview_text import overview_member_text
from fransys_model.derive.rows import OverviewStub
from fransys_model.layout import OverviewRef, OverviewRefKind, StubText

WIRE, CABLE = OverviewLinkKind.WIRE, OverviewLinkKind.CABLE


def _stub(box: str, far: str, ports: str, *, kind=WIRE, count=1) -> OverviewStub:
    end = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id(far))
    return OverviewStub(
        box=item_id(box), kind=kind, via=None, far=f"-{far}", ports=ports, end=end, count=count
    )


def test_a_lifted_line_prints_its_one_cable_several_as_a_count_or_the_count_text() -> None:
    """Breaks if a level prints a lifted line by its own rule: one cable names itself."""
    assert overview_lifted_text(CABLE, ("-W1",), 5) == "-W1"
    assert overview_lifted_text(CABLE, ("-W1", "-W2"), 5) == "x 2"
    assert overview_lifted_text(WIRE, (), 3) == "x 3"
    assert overview_lifted_text(WIRE, (), 1) == ""
    assert overview_lifted_text(CABLE, (), 4) == ""


def test_stubs_to_one_far_end_at_one_box_are_one_box_with_each_port_tail_once() -> None:
    """Breaks if two stubs to one far end draw two boxes, or a tail twice, or a count is lost."""
    model, unit, _ = unit_plant()
    at = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("k1"))
    other = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("k2"))
    placed = [
        (at, _stub("k1", "b1", ":1")),
        (at, _stub("k1", "b1", ":2", count=2)),
        (at, _stub("k1", "b1", ":1")),
        (other, _stub("k2", "b1", ":9")),
    ]
    boxes, lines = stub_ends(model, unit, placed)
    assert [(b.at, b.lines) for b in boxes] == [(at, ("-b1", ":1", ":2")), (other, ("-b1", ":9"))]
    assert [(ln.at, ln.kind, ln.count, ln.text) for ln in lines] == [
        (at, WIRE, 4, "x 4"),
        (other, WIRE, 1, ""),
    ]


def test_stubs_of_one_far_end_with_two_kinds_are_one_box_and_two_lines() -> None:
    """Breaks if a second kind to the same far end adds a box instead of a line."""
    model, unit, _ = unit_plant()
    at = OverviewRef(kind=OverviewRefKind.ITEM, item=item_id("k1"))
    placed = [(at, _stub("k1", "b1", "")), (at, _stub("k1", "b1", "", kind=OverviewLinkKind.MATE))]
    boxes, lines = stub_ends(model, unit, placed)
    assert len(boxes) == 1
    assert [ln.kind for ln in lines] == [WIRE, OverviewLinkKind.MATE]


def test_a_member_row_is_the_stub_label_with_the_carrier_first() -> None:
    """Breaks if the row joins box text and carrier with a dash, or loses the port tails."""
    assert (
        overview_member_text(house_record(StubText), ("+EXT-M1", ":PE"), "-W11")
        == "-W11 → +EXT-M1:PE"
    )
    assert overview_member_text(house_record(StubText), ("+EXT-M1",), "") == "→ +EXT-M1"
