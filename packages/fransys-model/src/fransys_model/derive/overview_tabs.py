"""The tab at each end of an overview line, on the box border, as the block diagram draws it (O2).

`overview_level` lists a box's tabs; this says which tab each cable line ends on. The rows are the
block diagram's own (`diagram_lines`), keyed by the line they belong to. Reached as `line_tabs`.
"""

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .block_diagram import diagram_lines
from .rows import LineRef, OverviewLinkKind
from .rows_overview import LineTab

__all__ = ["line_tabs"]


def line_tabs(model: Model, unit: Id[Unit] | None) -> tuple[LineTab, ...]:
    """The end tabs of `unit`'s cable lines (`None`: the system), one row per diagram line.

    `ref` is the line's `LineRef` on `overview_level`; `tab_a` stands at its `a` box and `tab_b`
    at its `b` box, each the text the block diagram prints there, `None` for no tab. A line of
    another kind, or a cable line the diagram lifts differently, has no row.
    """
    return tuple(
        LineTab(
            ref=LineRef(a=one.a, b=one.b, kind=OverviewLinkKind.CABLE, via=one.cable),
            tab_a=one.tab_a,
            tab_b=one.tab_b,
        )
        for one in diagram_lines(model, unit)
    )
