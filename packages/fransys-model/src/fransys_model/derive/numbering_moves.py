"""Pure joins over two sets of pins: the pin source and a build's own (model-0281).

`release()` and `build(releases=)` both call these; the facade reads the pin source from disk.
"""

lazy from collections.abc import Iterable

lazy from fransys_model.kernel import AuthoringKey

from .rows_baseline import NumberingItem, NumberingPins, NumberingRetired
from .rows_numbering import DesignationMove, PinPosition


def same_place(pin: NumberingItem, current: NumberingItem | PinPosition) -> bool:
    """Whether `current` still sits where `pin` was stored: the same scope and class code.

    The one answer to "is this pin still matched" (DES-20, DES-21); the caller matches the key.
    """
    return (current.scope, current.code) == (pin.scope, pin.code)


def gone_or_moved(
    source: NumberingPins, current: Iterable[NumberingItem | PinPosition]
) -> tuple[NumberingRetired, ...]:
    """Every `source` pin no longer matched by a current item of the same (key, scope, code).

    Gone or moved (group/class code), carried forward at `source`'s position, plus `source.retired`.
    It seeds the reserved facets and serves `release()`: decided once.
    """
    current_by_key = {item.key: item for item in current}
    newly_retired = [
        NumberingRetired(scope=entry.scope, code=entry.code, text=entry.text)
        for entry in source.items
        if (match := current_by_key.get(entry.key)) is None or not same_place(entry, match)
    ]
    combined = (*source.retired, *newly_retired)
    return tuple(
        sorted(
            combined,
            key=lambda r: (r.scope is None, r.scope or (), r.code is None, r.code or "", r.text),
        )
    )


def designation_moves(source: NumberingPins, current: NumberingPins) -> tuple[DesignationMove, ...]:
    """Every pin still matched (as in `gone_or_moved`) whose current own text now differs.

    `own_designation_or_none` reads the authored tag first, as `NumberingItem.text` does.
    """
    current_by_key: dict[AuthoringKey, NumberingItem] = {item.key: item for item in current.items}
    moves = [
        DesignationMove(key=entry.key, old_text=entry.text, new_text=match.text)
        for entry in source.items
        if (match := current_by_key.get(entry.key)) is not None
        and same_place(entry, match)
        and match.text != entry.text
    ]
    return tuple(sorted(moves, key=lambda m: m.key))


__all__ = ["designation_moves", "gone_or_moved", "same_place"]
