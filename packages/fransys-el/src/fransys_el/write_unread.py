"""One finding per authored hint the core path does not read (`HINT_NOT_READ`, SW9, el-0002)."""

from fransys_model.derive import function_designation, function_item, strip_of
from fransys_model.kernel import Finding, Id, Model, Origin, Severity
from fransys_model.layout import SideHint, layout_of
from fransys_model.vocab import FINDING_CODES, Function, Item

__all__ = ["unread_hint_findings"]

_INFO = next(info for info in FINDING_CODES if info.code == "HINT_NOT_READ")


def unread_hint_findings(model: Model) -> tuple[Finding, ...]:
    """One WARNING per authored hint call (same origin and strip or item), in record order.

    A call on a strip writes one `SideHint` per terminal; each family adds its hints here.
    """
    calls: dict[tuple[Origin | None, Id[Item]], list[Id[Function]]] = {}
    for hint in layout_of(model, SideHint).values():
        item = function_item(model, hint.function)
        item = strip_of(model, item) or item
        calls.setdefault((model.origin_of(hint.id), item), []).append(hint.function)
    return tuple(
        Finding(
            code="HINT_NOT_READ",
            severity=Severity.WARNING,
            subjects=tuple(subjects),
            message=(
                f"hint d.layout.side on {_names(model, subjects)} "
                "is not read by the core path (el-0002); the drawing ignores it"
            ),
            fix=_INFO.filled(),
        )
        for subjects in calls.values()
    )


def _names(model: Model, subjects: list[Id[Function]]) -> str:
    return ", ".join(function_designation(model, function) for function in subjects)
