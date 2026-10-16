"""Row shapes of the numbering seed and the pin moves (model-0281, model-0199).

They sit beside `rows_baseline.py`, whose `NumberingItem`, `NumberingPins` and
`NumberingRetired` they build on. Plain values: no facet, no id and no origin.
"""

from fransys_model.kernel import AuthoringKey, Id, value
from fransys_model.vocab.core import Item, Unit

from .rows_baseline import NumberingRetired


@value
class PinPosition:
    """A unit's item or instance by structure alone: `(key, scope, code)`, no text yet."""

    key: AuthoringKey
    scope: AuthoringKey | None
    code: str | None


@value
class AssignedSeed:
    """An unauthored item a pin still matches and the pin's text for it; `key` is the item's."""

    item: Id[Item]
    key: AuthoringKey
    text: str


@value
class UnitTagSeed:
    """An untagged instance a pin still matches and the pin's text; `key` is the instance's."""

    instance: Id[Unit]
    key: AuthoringKey
    text: str


@value
class SeedRows:
    """What a pin source seeds into one unit: assigned items, assigned instances, reserved texts.

    `reserved` holds every pin gone or moved, plus the source's own `retired`.
    """

    assigned: tuple[AssignedSeed, ...]
    tags: tuple[UnitTagSeed, ...]
    reserved: tuple[NumberingRetired, ...]


@value
class DesignationMove:
    """One pin source entry still matched by a current item: its OLD and CURRENT own label."""

    key: AuthoringKey
    old_text: str
    new_text: str
