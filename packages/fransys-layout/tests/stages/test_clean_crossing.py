"""C22, one rule in one place: `clean_crossing`, the router's step test and the lint's touch test.

The router asks it per step (`_crosses_cleanly`), the coherence lint of what was drawn
(`_touches`, tested in `tests/lint/test_coherence_touch.py`); both call `clean_crossing`.
"""

import pytest

from fransys_layout.geometry import Box, Facing
from fransys_layout.stages._routing import Field, _crosses_cleanly, clean_crossing

H, V, BOTH = frozenset("h"), frozenset("v"), frozenset("hv")


@pytest.mark.parametrize(
    ("mine", "other", "clean"),
    [
        (V, H, True),
        (H, V, True),
        (H, H, False),  # along the other's wire: a shared segment
        (V, V, False),
        (V, BOTH, False),  # at the other's corner or end
        (H, BOTH, False),
        (BOTH, V, False),  # the wire turns or ends in the cell
        (BOTH, BOTH, False),
    ],
)
def test_two_wires_cross_cleanly_only_one_h_against_one_v(mine, other, clean) -> None:
    """Exactly one `h` against one `v` is clean; every other pairing is a touch."""
    assert clean_crossing(mine, other) is clean


def _field(axes) -> Field:
    return Field(
        region=Box(x=0, y=0, width=80, height=80),
        obstacles=(),
        free=frozenset(),
        busy=frozenset(),
        turn_penalty=0,
        crossing_penalty=0,
        axes=axes,
    )


@pytest.mark.parametrize(
    ("other", "clean"), [(H, True), (V, False), (BOTH, False)], ids=["across", "along", "corner"]
)
def test_the_router_enters_a_foreign_cell_north_only_across_its_straight_wire(other, clean) -> None:
    """Heading north into a cell whose foreign wire runs `h` is a crossing; `v` or both is not."""
    field = _field({(40, 32): other})
    assert _crosses_cleanly((40, 40), Facing.N, Facing.N, (40, 32), field) is clean
