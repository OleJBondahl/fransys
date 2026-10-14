"""The options a caller passes the layout passes: its conventions as frozen values (seam 1)."""

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.texts.candidates import TextKind, TextPlacement
from fransys_model.kernel import value


@value
class LayoutOptions:
    """What the caller decides about the layout: where each kind of text may stand.

    `texts` has one `TextPlacement` per `TextKind` value: the sides in try-order, the steps along
    each and the priority. A kind with no row fails here, when the options are built.
    """

    texts: frozendict[str, TextPlacement]

    def __post_init__(self) -> None:
        missing = sorted(kind.value for kind in TextKind if kind.value not in self.texts)
        if missing:
            msg = f"LayoutOptions.texts has no row for {', '.join(missing)}"
            raise LayoutError(msg)
