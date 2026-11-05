"""Field case: a wire ran along a harness line that is not its own, and a fan split stood on it.
The bug: the cable's fan-out split stood on the lamp's wire, so the page drew both as one conductor and joined two nets.
Fixed by layout-0246, a fan-out's split stands on no wire, so its line runs along none (DRAWING_SHORTS_NETS)."""

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _field_shared import build_board_cab


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    return build_board_cab()


def test_no_wire_is_drawn_joined_to_a_harness_line(built: fr.BuildResult) -> None:
    assert "DRAWING_SHORTS_NETS" not in [f.code for f in fr.check(built)]


def test_a_cable_of_two_wired_cores_draws_one_trunk(built: fr.BuildResult) -> None:
    """G07-BUNDLES: a cable path draws as one trunk, a parallel lane line per core, not as separate wires (KI-171)."""
    wires = [w for drawing in drawn_pages(built.model).values() for w in drawing.wires]
    assert {w.style for w in wires} == {"wire", "trunk"}
    lanes = [w for w in wires if w.style == "trunk"]
    assert len(lanes) == 2
    assert all(a[1] == b[1] for w in lanes for a, b in [(w.points[0], w.points[-1])])  # each lane line runs level


def test_every_connection_of_the_build_is_drawn(built: fr.BuildResult) -> None:
    assert "CONNECTION_NOT_DRAWN" not in [f.code for f in fr.check(built)]
