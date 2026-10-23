"""The one renderer of a designation: the scheme joins the segments (EL-9, model-0331).

`item_designation`, `reference_designation`, `location_node_designation`, `unit_designation` and
the located ends are these functions with another `PrintContext`.
"""

from fransys_model.derive.texts.designation_segments import (
    aspect_segments,
    designation_segments,
    node_segments,
)
from fransys_model.vocab.designation_scheme import DESIGNATION_SCHEME
lazy from fransys_model.derive.rows_designation import Segment
lazy from fransys_model.derive.texts.context import PrintContext
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item


def _text(segments: tuple[Segment, ...], *, bare: bool = False) -> str:
    """The one join: each segment's sign then its label; `bare` leaves the first sign off."""
    return DESIGNATION_SCHEME.join(((s.sign, s.label) for s in segments), bare=bare)


def designation_text(
    model: Model,
    item: Id[Item],
    ctx: PrintContext,
    *,
    held_switches: bool = True,
    bare: bool = True,
) -> str:
    """`item`'s designation in `ctx`: `A1-K1` (bare) or `-A1-K1`; raises as `plain_segments`."""
    return _text(designation_segments(model, item, ctx, held_switches=held_switches), bare=bare)


def aspect_text(model: Model, item: Id[Item], ctx: PrintContext) -> str:
    """The `=` and `+` part of `item`'s reference in `ctx`: `=A1+C1`, empty with no placement."""
    return _text(aspect_segments(model, item, ctx))


def node_text(model: Model, node: Id[AspectNode] | None, ctx: PrintContext) -> str:
    """An aspect node's signed path below `ctx`'s drops (`+C1`, `+ER+C1`, `=G1`); `None`: empty."""
    return _text(node_segments(model, node, ctx))
