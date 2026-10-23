"""`d.layout.pins_below` advises a generic box to put all its pins on the south side."""

from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._handles import Fn
lazy from fransys_model.layout import PinsBelowHint

from ._unused import _own

if TYPE_CHECKING:
    from fransys_author.design import Design as EngineDesign


def _hinted(engine: EngineDesign) -> set[Any]:
    """The ids of the functions that already carry a pins-below hint."""
    return {r.function for r in engine._design._draft.records() if isinstance(r, PinsBelowHint)}


def hint_pins_below(engine: EngineDesign, box: object) -> None:
    """Write one `PinsBelowHint` per function of `box`; refuse a non-box and a repeat."""
    if not isinstance(box, Device | Fn):
        msg = (
            "d.layout.pins_below takes a device or one of its functions, as "
            f"`d.layout.pins_below(plc)`, not {box!r}"
        )
        raise AuthorError(msg)
    functions = _own(box, "d.layout.pins_below", None)
    if _hinted(engine) & {f.id for f in functions}:
        name = ".".join(str(part) for part in functions[0].key)
        msg = (
            f"d.layout.pins_below: box {name} already has a pins-below hint; "
            "a box takes one, so call it once"
        )
        raise AuthorError(msg)
    for function in functions:
        engine.pins_below(function)
