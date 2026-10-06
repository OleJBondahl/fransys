"""FD5/FD6: pure joins over two `NumberingPins`, the pin source and a build's own pins.

`release()` and `build(releases=)` both call these; `pipeline.py` reads the pin source from disk.
`fransys_model` reads no file (its invariant 6): this module reads nothing, imports no pipeline.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.derive.numbering_pins import NumberingItem, NumberingPins, NumberingRetired

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey


@dataclasses.dataclass(frozen=True, slots=True)
class DesignationMove:
    """One pin source entry still matched by a current item (FD6): its OLD and CURRENT own label."""

    key: AuthoringKey
    old_text: str
    new_text: str


def _current_by_key(current: NumberingPins) -> dict[AuthoringKey, NumberingItem]:
    return {item.key: item for item in current.items}


def gone_or_moved(source: NumberingPins, current: NumberingPins) -> tuple[NumberingRetired, ...]:
    """Every `source` pin no longer matched by a current item of the same (key, scope, code).

    Gone or moved (group/class code), carried forward at `source`'s position, plus `source.retired`.
    It seeds FD5's reserved facets and serves `release()`: decided once.
    """
    current_by_key = _current_by_key(current)
    newly_retired = [
        NumberingRetired(scope=entry.scope, code=entry.code, text=entry.text)
        for entry in source.items
        if (match := current_by_key.get(entry.key)) is None
        or match.scope != entry.scope
        or match.code != entry.code
    ]
    combined = (*source.retired, *newly_retired)
    return tuple(
        sorted(
            combined,
            key=lambda r: (r.scope is None, r.scope or (), r.code is None, r.code or "", r.text),
        )
    )


def designation_moves(source: NumberingPins, current: NumberingPins) -> tuple[DesignationMove, ...]:
    """FD6: every pin still matched (as in `gone_or_moved`) whose current own text now differs.

    `own_designation_or_none` reads the authored tag first, as `NumberingItem.text` does.
    """
    current_by_key = _current_by_key(current)
    moves = [
        DesignationMove(key=entry.key, old_text=entry.text, new_text=match.text)
        for entry in source.items
        if (match := current_by_key.get(entry.key)) is not None
        and match.scope == entry.scope
        and match.code == entry.code
        and match.text != entry.text
    ]
    return tuple(sorted(moves, key=lambda m: m.key))
