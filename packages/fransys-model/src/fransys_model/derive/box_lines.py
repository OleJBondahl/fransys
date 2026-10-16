"""The text lines of a connector's box: designation, part number, landed pins."""

from fransys_model.derive.facts.roles import function_role
from fransys_model.vocab.tables import boundaries, functions, items, parts
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Unit

from .designation import connector_designation, port_designation
from .indexes import build_indexes
from .lookups import pin_order
from .port_marking import port_marking


def _part_line(model: Model, function: Id[Function]) -> str | None:
    """The item's MPN, only when every function of the item is a connector function."""
    item = items(model)[functions(model)[function].item]
    siblings = build_indexes(model).functions_by_item.get(item.id, ())
    if item.part is None or any(
        not function_role(model, sibling).pin_group for sibling in siblings
    ):
        return None
    return parts(model)[item.part].mpn


def _pin_lines(model: Model, function: Id[Function], unit: Id[Unit] | None) -> tuple[str, ...]:
    """`port_designation` of each pin of a unit boundary `function` a conductor lands on."""
    if not any(b.function == function for b in boundaries(model).values()):
        return ()
    idx = build_indexes(model)
    landed = [p for p in idx.ports_by_function.get(function, ()) if idx.conductors_by_port.get(p)]
    landed.sort(key=lambda p: pin_order(port_marking(model, p), p))
    return tuple(port_designation(model, p, unit=unit) for p in landed)


def connector_box_lines(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> tuple[str, ...]:
    """The lines of `function`'s connector box: its designation, its part line, its landed pins.

    The designation is `connector_designation` in `unit`'s context. The part line is the MPN, only
    when every function of the item is a connector function. A unit boundary then prints the
    `port_designation` of each pin a conductor lands on; any other connector prints none. A line
    prints once however many ports or conductors reach it.
    """
    designation = connector_designation(model, function, unit=unit)
    part = _part_line(model, function)
    lines = tuple(line for line in (designation, part) if line is not None)
    return tuple(dict.fromkeys(lines + _pin_lines(model, function, unit)))


__all__ = ["connector_box_lines"]
