"""layout-0230: the overview's reader order has one home, `reader_rank`; its two readers use it."""

from fransys_layout.engines.diagram.values import DiagramFacts
from fransys_layout.engines.overview.lanes.plan import make_plan
from fransys_layout.engines.overview.read.lanes import inner_keys, reader_rank
from fransys_layout.engines.overview.read.values import BoxSpec, ViewFacts, box_ident
from fransys_model.derive import ViewBox
from fransys_model.kernel import Id
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind


def _ref(token: str) -> OverviewRef:
    return OverviewRef(kind=OverviewRefKind.ITEM, item=Id(kind="item", value=token))


def _key(token: str, at: str | None = None) -> BoxKey:
    return BoxKey(ref=_ref(token), at=None if at is None else _ref(at))


def _boxes(*lines: str, stub: tuple[int, ...] = ()) -> list[ViewBox]:
    return [
        ViewBox(key=_key(f"b{n}", "x" if n in stub else None), lines=(text,), dashed=False)
        for n, text in enumerate(lines)
    ]


def test_the_rank_is_the_natural_order_of_each_boxs_first_line() -> None:
    """Breaks if A10 sorts before A2, or the rank follows the input order."""
    assert reader_rank(_boxes("A10", "A2", "A1")) == (2, 1, 0)


def test_a_box_with_no_line_ranks_first() -> None:
    """Breaks if a lineless box is skipped or ranked by something other than the empty text."""
    boxes = [*_boxes("B"), ViewBox(key=_key("none"), lines=(), dashed=False)]
    assert reader_rank(boxes) == (1, 0)


def test_the_inner_keys_leave_out_stubs_and_follow_the_rank() -> None:
    """Breaks if lane_plan's inner boxes stop following reader_rank, or a stub is kept."""
    boxes = _boxes("A10", "A2", "A5", stub=(2,))
    assert inner_keys(boxes, reader_rank(boxes)) == [boxes[1].key, boxes[0].key]


def test_a_cell_stacks_its_boxes_in_the_rank_the_reader_gave() -> None:
    """Breaks if make_plan picks its source or orders a cell by anything but `facts.rank`."""
    specs = tuple(
        BoxSpec(box=box_ident(b.key), key=b.key, lines=b.lines, dashed=False)
        for b in _boxes("A10", "A2", "A1")
    )
    facts = ViewFacts(
        unit=None,
        level=None,
        mode=OverviewMode.LANES,
        open=None,
        boxes=specs,
        lines=(),
        diagram=DiagramFacts(
            unit=None,
            boxes=(),
            lines=(),
            text_height=1,
            turn_penalty=1,
            crossing_penalty=1,
            width=9,
            height=9,
        ),
        lanes=(0, 0, 0),
        west=(False, False, False),
        power=(),
        join=(-1, -1, -1),
        rank=reader_rank(_boxes("A10", "A2", "A1")),
    )
    plan = make_plan(facts)
    assert plan.stage[specs[2].box] == 0  # the first box in reader order is the source
    assert plan.cells[0, 1] == [specs[1].box, specs[0].box]
