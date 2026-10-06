"""R7.1 attachment x: two adjacent cells with no attachment keep the dx the span stage gave them."""

from types import SimpleNamespace
from typing import Any, cast

from fransys_layout.stages.host_offsets import attachment_offsets


def _cell(function: str, dx: int) -> SimpleNamespace:
    keepout = SimpleNamespace(width=10)
    return SimpleNamespace(
        function=function,
        host=None,
        port="",
        dx=dx,
        left_of_axis=5,
        geometry=SimpleNamespace(keepout=keepout),
    )


def test_adjacent_cells_without_a_host_keep_a_spanning_dx_below_the_packed_value() -> None:
    first, second = _cell("a", 40), _cell("b", 0)
    attachment_offsets(cast("Any", [[first, second]]))
    assert (first.dx, second.dx) == (40, 0)
