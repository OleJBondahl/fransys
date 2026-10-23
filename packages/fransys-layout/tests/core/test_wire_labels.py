"""Stage 8c: `label_along` and `label_nets` on hand-built pages (layout-0310)."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core import AnnexBox, CoreError, Net
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.outputs import Annotations, Marker
from fransys_layout.core.text_wires import label_along, label_nets
from fransys_layout.core.values import Box, PinRef, RefKind

from . import wire_label_fixtures as fx
from .wire_label_fixtures import LABEL, OPTIONS

SIDES = OPTIONS.wire_label_sides


def test_a_lone_vertical_wire_takes_the_middle_on_the_first_side() -> None:
    box = label_along(fx.lone().points, LABEL, SIDES, fx.grid((fx.lone(),)))
    assert box == Box(104, 80, 24, 8)


def test_a_blocked_first_side_takes_the_second() -> None:
    occ = fx.grid((fx.lone(),), fx.east_blocked())
    assert label_along(fx.lone().points, LABEL, SIDES, occ) == Box(72, 80, 24, 8)


def test_a_horizontal_run_tries_north_then_south() -> None:
    wire = fx.wire(((40, 104), (120, 104)))
    occ = fx.grid((wire,))
    assert label_along(wire.points, LABEL, SIDES, occ) == Box(64, 96, 24, 8)
    occ = fx.grid((wire,), (Box(40, 88, 100, 16),))
    assert label_along(wire.points, LABEL, SIDES, occ) == Box(64, 112, 24, 8)


@pytest.mark.parametrize(
    ("step", "earlier", "want"),
    [
        (8, Box(104, 80, 24, 8), Box(104, 88, 24, 8)),
        (4, Box(100, 84, 24, 4), Box(100, 88, 24, 8)),
    ],
)
def test_a_label_in_the_way_slides_by_one_grid_step(step: int, earlier: Box, want: Box) -> None:
    occ = fx.grid((fx.lone(),), (earlier,), step)
    assert label_along(fx.lone().points, LABEL, SIDES, occ) == want


def test_a_run_shorter_than_the_label_falls_through_to_the_next_run() -> None:
    occ = fx.grid((fx.bent(),))
    assert label_along(fx.bent().points, LABEL, SIDES, occ) == Box(64, 104, 24, 8)


def test_no_free_place_gives_none() -> None:
    occ = fx.grid((fx.lone(),), fx.walled())
    assert label_along(fx.lone().points, LABEL, SIDES, occ) is None


def test_a_direction_missing_from_the_sides_is_an_error_naming_the_fix() -> None:
    with pytest.raises(CoreError, match="no entry for 'vert'"):
        label_along(fx.lone().points, LABEL, (("horiz", "N"),), fx.grid())


def test_the_sides_are_read_from_the_options() -> None:
    only_west = (("vert", "W"), ("horiz", "N", "S"))
    assert label_along(fx.lone().points, LABEL, only_west, fx.grid()) == Box(72, 80, 24, 8)


def test_a_trunk_is_marked_lanes_wide_and_its_label_stands_outside_the_band() -> None:
    trunk = fx.trunk(3)
    occ = fx.grid(trunk)
    assert len({i for i, _ in occ.used}) == 3
    box = label_along(trunk[0].points, LABEL, SIDES, occ, 3)
    assert box == Box(120, 80, 24, 8)
    assert occ.free(box)


def test_a_trunk_label_on_the_other_side_stands_one_cell_off() -> None:
    trunk = fx.trunk(3)
    occ = fx.grid(trunk, (Box(120, 64, 40, 48),))
    assert label_along(trunk[0].points, LABEL, SIDES, occ, 3) == Box(72, 80, 24, 8)


def test_a_horizontal_trunk_stands_lanes_cells_below_or_one_cell_above() -> None:
    trunk = tuple(fx.wire(((40, 104 + 8 * k), (120, 104 + 8 * k))) for k in range(2))
    occ = fx.grid(trunk)
    assert label_along(trunk[0].points, LABEL, (("horiz", "S"),), occ, 2) == Box(64, 120, 24, 8)
    assert label_along(trunk[0].points, LABEL, (("horiz", "N"),), occ, 2) == Box(64, 96, 24, 8)


def test_a_one_lane_wire_gives_the_same_box_as_the_default() -> None:
    occ = fx.grid((fx.lone(),))
    assert label_along(fx.lone().points, LABEL, SIDES, occ, 1) == label_along(
        fx.lone().points, LABEL, SIDES, occ
    )


def _nets(*ids: str) -> tuple[Net, ...]:
    return tuple(Net(i, (), label=LABEL) for i in ids)


def test_one_wire_label_per_labelled_net() -> None:
    a = fx.wire(((96, 64), (96, 112)), "n1")
    b = fx.wire(((200, 64), (200, 112)), "n2")
    placement, routes, prob = fx.case((a, b), (*_nets("n1"), Net("n2", ())))
    labels, findings = label_nets(placement, routes, Annotations(), prob, OPTIONS)
    assert [(w.net, w.page, w.box) for w in labels] == [("n1", 1, Box(104, 80, 24, 8))]
    assert findings == ()


def test_a_blocked_net_gives_the_finding_and_no_label() -> None:
    placement, routes, prob = fx.case((fx.lone(),), _nets("n1"))
    wall = tuple(AnnexBox("S1", 1, b, "BL") for b in fx.walled())
    labels, findings = label_nets(placement, routes, Annotations(annexes=wall), prob, OPTIONS)
    assert labels == ()
    assert [(f.code, f.page, f.subject) for f in findings] == [("TEXT_OVERLAP", 1, "n1")]
    assert "net n1" in findings[0].text
    assert "lengthen a run" in findings[0].text


def test_two_labels_on_one_page_do_not_collide() -> None:
    a = fx.wire(((96, 64), (96, 112)), "n1")
    b = fx.wire(((96, 64), (96, 112)), "n2")  # the same run: both want the same box
    placement, routes, prob = fx.case((a, b), _nets("n1", "n2"))
    labels, findings = label_nets(placement, routes, Annotations(), prob, OPTIONS)
    assert findings == ()
    assert [w.box for w in labels] == [Box(104, 80, 24, 8), Box(104, 88, 24, 8)]
    assert not overlaps(labels[0].box, labels[1].box)


def test_a_net_takes_the_wire_with_the_longest_run_and_then_the_next() -> None:
    short = fx.wire(((300, 64), (300, 80)), "n1")
    long = fx.wire(((96, 64), (96, 112)), "n1")
    placement, routes, prob = fx.case((short, long), _nets("n1"))
    labels, _ = label_nets(placement, routes, Annotations(), prob, OPTIONS)
    assert labels[0].box == Box(104, 80, 24, 8)
    blocked = tuple(AnnexBox("S1", 1, b, "BL") for b in fx.walled())
    labels, _ = label_nets(placement, routes, Annotations(annexes=blocked), prob, OPTIONS)
    assert labels[0].box == Box(304, 64, 24, 8)


def test_a_net_with_only_a_marker_on_the_page_gets_no_label_and_no_finding() -> None:
    marker = Marker("n1", RefKind.COPY, 1, "a", 96, 100, PinRef("S1", "p"))
    placement, routes, prob = fx.case((), _nets("n1"))
    labels, findings = label_nets(placement, routes, Annotations(markers=(marker,)), prob, OPTIONS)
    assert (labels, findings) == ((), ())


def test_label_nets_is_deterministic() -> None:
    placement, routes, prob = fx.case((fx.lone(),), _nets("n1"))
    args = (placement, routes, Annotations(), prob, OPTIONS)
    assert label_nets(*args) == label_nets(*args)


def test_the_marker_box_obstacle_is_read_from_the_options() -> None:
    marker = Marker("n1", RefKind.COPY, 1, "a", 96, 100, PinRef("S1", "p"))
    placement, routes, prob = fx.case((fx.lone(),), _nets("n1"))
    with pytest.raises(ValueError, match="marker"):
        label_nets(
            placement,
            routes,
            Annotations(markers=(marker,)),
            prob,
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
