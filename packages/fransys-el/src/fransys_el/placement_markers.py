"""The box of each lone stub, fitted to its text before placement (R318, MARKER-ANCHORS).

A stub or a copy is a marker symbol; symdef measures it once the text it will print is fitted into
its slot, and the core reserves that box. A text that fits the plain marker adds nothing.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, cast

from electrical_symbols import MARKER_FACING
from fransys_model.derive import stub_far, stub_text_at

from .placement_ids import pin_names, symbol_ids
from .placement_views import marker_boxes

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Box, Orientation, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port, Unit

    from .placement_kit import SymbolKit

__all__ = ["ARROW", "KINDS", "LONE", "facing_views", "marker_fit", "pin_ports"]

#: The reference kind whose box is fitted to the widest line it can print (R350).
ARROW = "arrow"

#: The reference kinds that have one end: each is an off stub, its box fitted to its text.
LONE = ("stub", "copy")

#: Every reference kind; a kind with no fitted symbol of its own gets the plain marker's box.
KINDS = ("tag", "arrow", "star", *LONE)

type Fit = Mapping[tuple[PinRef, str], Mapping[Orientation, Box]]


def facing_views() -> tuple[frozenset[Orientation], Orientation, Orientation]:
    """The marker views that lie above or below a pin, the one above and the one below."""
    up, down = (cast("Orientation", MARKER_FACING[side]) for side in "NS")
    mirrored = cast("Orientation", f"M{up}"), cast("Orientation", f"M{down}")
    return frozenset([up, down, *mirrored]), up, down


def pin_ports(model: Model, kit: SymbolKit) -> dict[PinRef, list[Id[Port]]]:
    """Every model port that each symbol pin draws."""
    found: dict[PinRef, list[Id[Port]]] = defaultdict(list)
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        found[pin].append(port)
    return found


def marker_fit(
    model: Model,
    kit: SymbolKit,
    unit: Id[Unit] | None,
    library: Library,
    pins: Iterable[PinRef],
) -> Fit:
    """The box of each marker kind at `pins`, by (pin, kind): stub and copy fit their text.

    A tag or star takes the plain marker's box; the arrow's box is `link_fit`'s. A pin no
    conductor leaves has none.
    """
    plain = marker_boxes(library)
    ports = pin_ports(model, kit)
    boxes: dict[str, Mapping[Orientation, Box]] = {}
    found = {}
    for pin in set(pins):
        ends = stub_far(model, ports[pin]) if pin in ports else None
        if ends is None:
            continue
        text = stub_text_at(model, unit, ends, north=False)
        if text not in boxes:
            boxes[text] = marker_boxes(library, text)
        own = dict.fromkeys(LONE, boxes[text])
        found.update({(pin, kind): own.get(kind, plain) for kind in KINDS if kind != ARROW})
    return frozendict(found)
