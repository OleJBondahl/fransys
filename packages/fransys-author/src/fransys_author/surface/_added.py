"""Which unit `d.add` built, found from what it returned (a document's subject, R363).

The designs live in a weak set, so a finished design and its results are not kept alive here.
"""

from typing import TYPE_CHECKING
from weakref import WeakSet

if TYPE_CHECKING:
    from fransys_author.design import Design
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Unit

_DESIGNS: WeakSet[Design] = WeakSet()


def remember_added(design: Design, result: object, unit: Id[Unit] | None) -> None:
    """Record that `d.add` returned `result` for `unit` in `design`."""
    design._added_units[id(result)] = (result, unit)
    _DESIGNS.add(design)


def added_unit(subject: object) -> Id[Unit] | None:
    """The unit instance that `d.add` built and returned as `subject`, else `None`.

    A unit's result is the only way to name one instance of a release that stands more than once.
    """
    for design in _DESIGNS:
        held = design._added_units.get(id(subject))
        if held is not None and held[0] is subject:
            return held[1]
    return None
