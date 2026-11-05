"""Read the elecdef figures of a rating, an operating envelope and a block (R783).

The one place that turns a `Range` or `Quantity` into the `Decimal` a check compares: elecdef
decides units and conditions, this decides which end of a figure a check reads.
"""

lazy from decimal import Decimal

from fransys_model.elecdef import Block, Breaker, Current, Fuse, Quantity, Range, Unit


def value(item: Range, unit: Unit) -> Decimal | None:
    """The value, in `unit`, of a figure: its nom, else max, else typ; `None` for a min-only one."""
    end = item.nom or item.max or item.typ
    return None if end is None else end.to(unit).value


def figure(ranges: tuple[Range, ...], current: Current | None, unit: Unit) -> Decimal | None:
    """The value, in `unit`, of the first figure stated at `current` (see `value`)."""
    return next((value(item, unit) for item in ranges if item.at.get(Current) is current), None)


def condition(item: Range, unit: Unit) -> Decimal | None:
    """The condition of `item.at` of `unit`'s kind, in `unit`; `None` when it has none."""
    found = item.at.get(unit.kind)
    return found.to(unit).value if isinstance(found, Quantity) else None


def breaking(block: Block | None) -> tuple[Range, ...]:
    """Every breaking figure of a block: a fuse's `breaking_capacity`, a breaker's `icn`, `icu`, `ics`."""
    if isinstance(block, Fuse):
        return block.breaking_capacity
    if isinstance(block, Breaker):
        return tuple(item for item in (block.icn, block.icu, block.ics) if item is not None)
    return ()


def breaking_points(block: Block | None, current: Current) -> tuple[Range, ...]:
    """The breaking figures stated at a voltage and at `current` (the points a fault is checked at)."""
    return tuple(r for r in breaking(block) if r.at.get(Current) is current and condition(r, Unit.V) is not None)


def minimum_breaking(block: Block | None) -> Decimal | None:
    """The lowest current a partial-range fuse breaks, in A: a figure with a `min` and no voltage."""
    found = [r.min for r in breaking(block) if r.min is not None and condition(r, Unit.V) is None]
    return found[0].to(Unit.A).value if found else None
