"""Stage: the clamp that stands a marker box against the content box's side edges."""

from dataclasses import replace

from fransys_layout.geometry import WIRING_GRID, Box


def stand_against_content_edge(
    box: Box, stubs: tuple[int, int], content_width: int, *, low: int = 0, high: int | None = None
) -> Box | None:
    """D14 M2 (layout-0068), the one clamp: `box` moved along x, every stub over it, or None."""
    margin = WIRING_GRID // 2
    left = max(low, stubs[1] + margin - box.width)
    right = min((content_width if high is None else high) - box.width, stubs[0] - margin)
    if left > right:
        return None
    return replace(box, x=min(max(box.x, left), right))
