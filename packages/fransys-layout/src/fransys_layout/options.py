"""The options a caller passes the layout passes: its conventions as frozen values (seam 1)."""

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.texts.candidates import TextKind, TextPlacement
from fransys_model.kernel import value


@value
class LayoutOptions:
    """What the caller decides about the layout: where each kind of text may stand.

    `texts` has one `TextPlacement` per `TextKind` value: the sides in try-order, the steps along
    each and the priority. A kind with no row fails here, when the options are built.
    `chain_boxes` draws each device chain as boxes whose pins face their neighbours (LC2).
    """

    texts: frozendict[str, TextPlacement]
    # layout-0215, LC4: a device chain draws as one box per device down a column, its pins
    # facing its neighbours; off, its devices draw as any other
    chain_boxes: bool = False

    def __post_init__(self) -> None:
        missing = sorted(kind.value for kind in TextKind if kind.value not in self.texts)
        if missing:
            msg = f"LayoutOptions.texts has no row for {', '.join(missing)}"
            raise LayoutError(msg)
