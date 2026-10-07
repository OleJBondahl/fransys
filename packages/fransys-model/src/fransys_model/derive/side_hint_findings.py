"""The WARNING for a side hint on an interface with no harness line (HL14, model-0176)."""

from typing import Final

from fransys_model.kernel import Finding, Model, Severity
from fransys_model.layout import SideHint, layout_of

from .designation import connector_designation
from .line_end_fact import connector_at_line_end

__all__ = ["check_side_hints"]

SIDE_HINT_NO_HARNESS_LINE: Final[str] = "SIDE_HINT_NO_HARNESS_LINE"


def check_side_hints(model: Model) -> tuple[Finding, ...]:
    """Warn once per side hint whose interface stands at no harness line's end: it does nothing."""
    found = []
    for hint in layout_of(model, SideHint).values():
        if connector_at_line_end(model, hint.function):
            continue
        origin = model.origins[hint.id]
        name = connector_designation(model, hint.function)
        message = (
            f"side hint on interface {name} ({origin.file}:{origin.line}) does nothing: "
            "the interface has no harness line"
        )
        found.append(
            Finding(
                code=SIDE_HINT_NO_HARNESS_LINE,
                severity=Severity.WARNING,
                subjects=(hint.function,),
                message=message,
            )
        )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
