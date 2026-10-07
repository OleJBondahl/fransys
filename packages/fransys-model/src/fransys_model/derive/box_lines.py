"""The text lines of a connector's box: designation, part number, interface name (HL5, HL7)."""

from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import boundaries, functions, items, parts
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Unit

from .designation import connector_designation
from .indexes import build_indexes


def _part_line(model: Model, function: Id[Function]) -> str | None:
    """The item's MPN, only when every function of the item is a connector function."""
    item = items(model)[functions(model)[function].item]
    siblings = build_indexes(model).functions_by_item.get(item.id, ())
    if item.part is None or any(
        functions(model)[sibling].kind is not FunctionKind.CONNECTOR for sibling in siblings
    ):
        return None
    return parts(model)[item.part].mpn


def _name_line(model: Model, function: Id[Function], unit: Id[Unit] | None) -> str | None:
    """The interface name of `function`, the given unit's first, else the lowest boundary's."""
    named = sorted(
        (b for b in boundaries(model).values() if b.function == function and b.name is not None),
        key=lambda b: (b.unit != unit, b.id),
    )
    return named[0].name if named else None


def connector_box_lines(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> tuple[str, ...]:
    """The lines of `function`'s connector box: its designation, then its part and name lines.

    The designation is `connector_designation` in `unit`'s context. The part line is the MPN, only
    when every function of the item is a connector function. The name line is the unit
    interface's field name, only when it differs from the designation, ignoring case and the
    leading dash. A connector that is no unit boundary has no name line.
    """
    designation = connector_designation(model, function, unit=unit)
    part = _part_line(model, function)
    name = _name_line(model, function, unit)
    if name is not None and name.casefold() == designation.lstrip("-").casefold():
        name = None
    return tuple(line for line in (designation, part, name) if line is not None)


__all__ = ["connector_box_lines"]
