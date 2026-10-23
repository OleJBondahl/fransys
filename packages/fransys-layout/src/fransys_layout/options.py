"""The options a caller passes the layout passes: its conventions as frozen values (seam 1)."""

from enum import Enum

from fransys_layout.geometry import Facing, LayoutError
from fransys_model.kernel import register_enum, value


@register_enum
class TextKind(Enum):
    """What a text is, for the table and key order (not `LabelKind`, which `write` maps)."""

    REFERENCE = "reference"
    STUB = "stub"
    TAG = "tag"
    MARKING = "marking"
    CONTACT_IMAGE = "contact_image"
    CROSS_REFERENCE = "cross_reference"
    POWER = "power"
    HARNESS_LINE = "harness_line"


@value
class Side:
    """One side of a table row: where the text stands, and its steps along it ."""

    facing: Facing | None
    steps: tuple[int, ...]
    mirror: bool = False


@value
class TextPlacement:
    """Where one kind of text may stand, and when it is placed."""

    priority: int  # a lower number is placed first
    sides: tuple[Side, ...]


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
