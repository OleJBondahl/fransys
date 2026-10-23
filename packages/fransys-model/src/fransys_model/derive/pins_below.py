"""The `layout.pins_below` fact and its WARNING for a hint on a device with no pins to split."""

from typing import Final

from fransys_model.derive.designation import function_designation
from fransys_model.derive.placement_reads import function_item, function_ports, item_functions
from fransys_model.kernel import Finding, Id, Model, Severity
from fransys_model.layout import PinsBelowHint, layout_of
from fransys_model.vocab.codes import fix_text
lazy from fransys_model.vocab import Function

__all__ = ["check_pins_below", "pins_below"]

PINS_BELOW_NOT_A_BOX: Final[str] = "PINS_BELOW_NOT_A_BOX"
_MIN_PINS = 2  # a box splits its pins over two sides; one pin has nothing to keep together


def pins_below(model: Model, function: Id[Function] | None) -> bool:
    """Whether the author advised every pin of `function` onto the south side."""
    return any(h.function == function for h in layout_of(model, PinsBelowHint).values())


def check_pins_below(model: Model) -> tuple[Finding, ...]:
    """Warn once per pins-below hint on an item with fewer than two ports in all: it is no box."""
    found = []
    for hint in layout_of(model, PinsBelowHint).values():
        siblings = item_functions(model)[function_item(model, hint.function)]
        if sum(len(function_ports(model, f)) for f in siblings) >= _MIN_PINS:
            continue
        origin = model.origins[hint.id]
        name = function_designation(model, hint.function)
        message = (
            f"pins-below hint on {name} ({origin.file}:{origin.line}) does nothing: "
            "its device has fewer than two ports, so it is no box to split"
        )
        found.append(
            Finding(
                code=PINS_BELOW_NOT_A_BOX,
                severity=Severity.WARNING,
                subjects=(hint.function,),
                message=message,
                fix=fix_text(PINS_BELOW_NOT_A_BOX),
            )
        )
    return tuple(found)
