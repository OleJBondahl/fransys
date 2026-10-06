"""EF-C part 6 review (layout-0057): the n-th stub of one port stands n boxes out, counting the
markers the port already carries and the stubs before it, so no two boxes of one port overlap.

Can-fail, checked by hand: `stages/references/off_stubs.py` `off_markers` shifting a busy row by
one box height once (not `n` of them, `out`) puts the third stub on the second, and both tests
fail.
"""

import itertools

from samples import PROFILE, SHEET, built, connection, drawn, hid, placed, standing

from fransys_layout.stages.references.off_stubs import _off_markers
from fransys_layout.stages.references.types import MarkerScene, OffStubs
from fransys_layout.stages.types import StubText

_PORT = hid("port", 12)  # port `14` of function 1: three conductors leave it


def _stubs(*, busy: dict) -> list:
    """Three conductors from one port to three far ends of their own, three stubs on it."""
    numbers = (1, 2, 3)
    scene = MarkerScene((placed(1, x=64, y=160),), (drawn(1),), SHEET, PROFILE)
    off = OffStubs(
        tuple(connection(n, 1, 90 + n) for n in numbers),
        off_texts={_PORT: [StubText(cable="-W1", far=f"+DB-X{n}", port=":1") for n in numbers]},
        busy=busy,
    )
    found = built(scene, _off_markers(scene, standing(scene, off)))
    assert len(found) == 3
    return sorted(found, key=lambda m: m.stub_extra)


def _apart(stubs: list) -> None:
    for near, far in itertools.pairwise(stubs):
        assert near.stub_extra + near.box.height <= far.stub_extra


def test_three_stubs_on_one_port_stand_one_two_and_three_boxes_apart() -> None:
    # UNDO: stages/references/off_stubs.py: off_markers `out = lift + max(...) * size[1]` ->
    #     `out = lift + min(1, max(...)) * size[1]` (the third stub lands on the second)
    stubs = _stubs(busy={})
    assert stubs[0].stub_extra == 0
    _apart(stubs)


def test_a_port_that_already_carries_a_marker_starts_its_stubs_one_box_out() -> None:
    # UNDO: stages/references/off_stubs.py: off_markers `max(busy[key] ...)` -> `min(1, max(...))`
    #     (the first and second stub of a port with a marker take one offset)
    stubs = _stubs(busy={(_PORT, 1, 1): 1})
    assert stubs[0].stub_extra >= stubs[0].box.height
    _apart(stubs)
