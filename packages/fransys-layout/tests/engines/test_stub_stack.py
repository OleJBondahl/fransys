"""Layout-0256: stubs whose boxes meet stand in a staircase, one tier each."""

from itertools import pairwise
from typing import Any

from fransys_layout.geometry import Box, Facing, Point, boxes_meet
from fransys_layout.stages.line_shapes import LineStub
from fransys_layout.stages.line_trunk import stub_edge
from fransys_layout.stages.stub_stack import stack_stubs
from fransys_layout.stages.texts.candidates import Candidate, box_of, stub_anchor
from fransys_model.kernel import Id, Severity

CONTENT = Box(x=0, y=0, width=400, height=400)
WIDTH, HEIGHT = 250, 12


def _stub(name: str, x: int, facing: Facing = Facing.S) -> LineStub:
    at = Point(x=x, y=224)
    box = box_of(Candidate(side=facing, offset=0), stub_anchor(at), (WIDTH, HEIGHT))
    name_id: Id[Any] = Id(kind="harness", value=name)
    return LineStub(
        harness=name_id,
        branch=0,
        drawing_set=0,
        page=0,
        port=name_id,
        far=name_id,
        at=at,
        facing=facing,
        box=box,
    )


def _path(stub: LineStub) -> tuple[Id[Any], int, tuple[Point, ...]]:
    return (stub.harness, 0, (Point(x=stub.at.x, y=176), stub_edge(stub.at, stub.facing)))


def _row() -> tuple[list[LineStub], list[tuple[Id[Any], int, tuple[Point, ...]]]]:
    stubs = [_stub("a", 56), _stub("b", 88), _stub("c", 152)]
    return stubs, [_path(s) for s in stubs]


def test_three_stubs_in_one_row_stand_on_three_tiers_apart() -> None:
    stubs, paths = _row()
    assert all(boxes_meet(a.box, b.box, closed=False) for a, b in pairwise(stubs))
    done, _, _ = stack_stubs(stubs, paths, [], CONTENT)
    assert [s.at.y for s in done] == [224 + 48, 224 + 24, 224]
    assert not any(
        boxes_meet(a.box, b.box, closed=False) for n, a in enumerate(done) for b in done[n + 1 :]
    )


def test_each_line_runs_on_to_its_stubs_new_edge() -> None:
    stubs, paths = _row()
    done, carried, _ = stack_stubs(stubs, paths, [], CONTENT)
    assert [p[2][-1] for p in carried] == [stub_edge(s.at, s.facing) for s in done]
    assert all(p[2][0].x == q[2][0].x for p, q in zip(paths, carried, strict=True))


def test_a_lone_stub_stays() -> None:
    stub = _stub("a", 56)
    assert stack_stubs([stub], [_path(stub)], [], CONTENT)[0] == (stub,)


def test_a_row_with_no_room_for_a_tier_stays_as_it_stands() -> None:
    stubs, paths = _row()
    block = [Box(x=0, y=250, width=400, height=400)]
    assert stack_stubs(stubs, paths, block, CONTENT)[0] == tuple(stubs)


def test_a_staircase_too_wide_for_the_content_stays_as_it_stands() -> None:
    stubs, paths = _row()
    narrow = Box(x=0, y=0, width=260, height=400)
    assert stack_stubs(stubs, paths, [], narrow)[0] == tuple(stubs)


def test_a_cluster_with_no_free_staircase_is_named_in_a_note() -> None:
    stubs, paths = _row()
    block = [Box(x=0, y=250, width=400, height=400)]
    _, _, notes = stack_stubs(stubs, paths, block, CONTENT)
    (note,) = notes
    assert (note.code, note.severity) == ("STUBS_NOT_STACKED", Severity.INFO)
    assert [i.value for i in note.subjects] == ["a", "b", "c"]
    assert note.message.startswith(
        "p0.0: Fransys could not draw this cleanly; please report it with the smallest model"
    )


def test_a_stacked_cluster_gets_no_note() -> None:
    stubs, paths = _row()
    assert stack_stubs(stubs, paths, [], CONTENT)[2] == ()
